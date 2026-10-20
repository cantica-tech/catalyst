"""Proposals (design 26, REQ-000053): a change offered for review before it
lands, as a reconciliation case carrying the proposed content; `accept`
writes it, refused when the base has moved and for its own author; gates
count approvals of the proposed version once it lands."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import schema_check
from catalyst import check, gates, inbox, views
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst_fixtures import USERID, journal_entries, make_project, write

KERNEL = Path(__file__).resolve().parent.parent / "framework" / "kernel"
ITEM = f"ITEM-000001-{USERID}"
RULE = f"br-AUTH-000001-{USERID}"
ROLES = {
    "roles": [
        {"name": "Admin", "actions": [], "reconciliation": "full"},
        {"name": "Developer", "actions": [], "reconciliation": "propose"},
        {"name": "Reviewer", "actions": []},
    ]
}


@pytest.fixture
def project(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path, git=True)
    root = project / ".criterion"
    write(root / "IAM" / "roles" / "roles.json", json.dumps(ROLES))
    users = json.loads((root / "IAM" / "users" / "users.json").read_text(encoding="utf-8"))
    users["users"] += [
        {"name": "Bob", "git_username": "bob", "roles": ["Developer"], "active": True, "userid": "Bb12Cd34"},
        {"name": "Rev", "git_username": "rev", "roles": ["Reviewer"], "active": True, "userid": "Rv12Cd34"},
        {"name": "Ria", "git_username": "ria", "roles": ["Reviewer"], "active": True, "userid": "Ri12Cd34"},
    ]
    write(root / "IAM" / "users" / "users.json", json.dumps(users))
    folder = root / "reconciliations" / "templates"
    folder.mkdir(parents=True)
    shutil.copyfile(KERNEL / "templates" / "reconciliation.template.md", folder / "TEMPLATE-RECONCILIATION-v1.md")
    monkeypatch.chdir(project)
    capsys.readouterr()
    return project


def _file(project, item=ITEM):
    dep = load(project)
    corpus = load_corpus(dep)
    return corpus.artifacts[item][0].file if item in corpus.artifacts else corpus.rules[item][0].file


def _offer(project, tmp_path, capsys, who="bob", item=ITEM, change=("Text.", "Better text."), name="p.md"):
    proposed = _file(project, item).read_text(encoding="utf-8").replace(*change)
    src = write(tmp_path / name, proposed)
    assert main(["propose", item, "--from", str(src), "--as", who, "--intent", "Clearer", "--json"]) == 0, (
        capsys.readouterr().err
    )
    found = json.loads(capsys.readouterr().out)
    assert schema_check.problems(found, schema_check.load("propose")) == []
    return found, proposed


def _case(project, case_id):
    return load_corpus(load(project)).artifacts[case_id][0]


def test_a_proposal_waits_beside_its_entity_then_lands_when_accepted(project, tmp_path, capsys):
    before = _file(project).read_text(encoding="utf-8")
    found, proposed = _offer(project, tmp_path, capsys)
    case_id = found["case"]
    assert (found["entity"], found["author"], found["status"]) == (ITEM, "bob", "Open")
    assert _file(project).read_text(encoding="utf-8") == before  # the entity is untouched
    case = _case(project, case_id)
    assert case.get("Trigger").strip("` ") == "proposal" and found["base"] in case.get("Baseline")
    assert (project / ".criterion" / found["file"]).read_text(encoding="utf-8") == proposed
    assert journal_entries(project / ".criterion")[-1]["command"] == "catalyst propose"
    dep = load(project)
    corpus = load_corpus(dep)
    waiting = [i for i in inbox.inbox(dep, corpus)["items"] if i["kind"] == "proposal"]
    assert [(i["id"], i["evidence"]["author"], i["evidence"]["base"]) for i in waiting] == [
        (case_id, "bob", found["base"])
    ]
    assert not [i for i in inbox.inbox(dep, corpus)["items"] if i["kind"] == "reconciliation"]
    assert schema_check.problems(inbox.inbox(dep, corpus), schema_check.load("inbox")) == []
    shown = views.view(dep, corpus, case_id)["proposal"]
    assert (shown["content_base"], shown["content_proposed"]) == (before, proposed)
    assert schema_check.problems(views.view(dep, corpus, case_id), schema_check.load("view")) == []
    assert [e for e in check.run(dep).errors if e.startswith("proposal")] == []
    # bob may propose, not decide; ada decides
    assert main(["reconcile", case_id, "accept", "--as", "bob"]) == 1
    assert "needs a `full` reconciliation role" in capsys.readouterr().err
    assert main(["reconcile", case_id, "accept", "--as", "ada", "--intent", "Reads better"]) == 0
    capsys.readouterr()
    assert _file(project).read_text(encoding="utf-8") == proposed
    assert _case(project, case_id).get("Status").strip() == "Resolved-Accepted"
    entry = journal_entries(project / ".criterion")[-1]
    assert (entry["actor"], entry["proposal"], entry["proposed_by"]) == ("ada", case_id, "bob")
    assert {f["path"] for f in entry["files"]} >= {".criterion/items/ITEM-000001-first-item.md"}
    errors = check.run(load(project)).errors
    assert [e for e in errors if e.startswith(("journal", "proposal", "gates:"))] == []


def test_the_author_never_accepts_their_own_proposal(project, tmp_path, capsys):
    found, _ = _offer(project, tmp_path, capsys, who="ada")
    assert main(["reconcile", found["case"], "accept", "--as", "ada"]) == 1
    assert "never accepts their own proposal" in capsys.readouterr().err


def test_a_moved_base_refuses_accept_until_the_proposal_is_revised(project, tmp_path, capsys):
    found, _ = _offer(project, tmp_path, capsys)
    case_id = found["case"]
    assert main(["rename", ITEM, "--title", "Renamed", "--as", "ada", "--intent", "retitle"]) == 0
    capsys.readouterr()
    assert main(["reconcile", case_id, "accept", "--as", "ada"]) == 1
    assert "changed since" in capsys.readouterr().err
    revised = write(tmp_path / "r.md", _file(project).read_text(encoding="utf-8").replace("Text.", "Best text."))
    assert main(["reconcile", case_id, "propose", "--from", str(revised), "--as", "bob"]) == 0
    capsys.readouterr()
    case = _case(project, case_id)
    assert case.get("Status").strip() == "Under Review" and "Revised proposal" in case.file.read_text(encoding="utf-8")
    assert main(["reconcile", case_id, "accept", "--as", "ada"]) == 0
    capsys.readouterr()
    assert "Best text." in _file(project).read_text(encoding="utf-8")


def test_accept_with_edits_writes_the_acceptors_content_and_an_author_withdraws(project, tmp_path, capsys):
    found, _ = _offer(project, tmp_path, capsys)
    assert main(["reconcile", found["case"], "accept-with-edits", "--as", "ada"]) == 1
    assert "needs the content it accepts" in capsys.readouterr().err
    edited = write(tmp_path / "e.md", _file(project).read_text(encoding="utf-8").replace("Text.", "Edited text."))
    assert main(["reconcile", found["case"], "accept-with-edits", "--from", str(edited), "--as", "ada"]) == 0
    capsys.readouterr()
    assert "Edited text." in _file(project).read_text(encoding="utf-8")
    assert "proposed_by" not in journal_entries(project / ".criterion")[-1]  # the acceptor wrote this version
    other, _ = _offer(project, tmp_path, capsys, change=("Edited text.", "Withdrawn text."), name="w.md")
    assert main(["reconcile", other["case"], "close", "--as", "bob"]) == 0  # its author withdraws it, open
    capsys.readouterr()
    assert _case(project, other["case"]).get("Status").strip() == "Closed"


def test_gates_count_the_proposed_version_once_it_lands(project, tmp_path, capsys):
    write(
        project / ".criterion" / gates.GATES,
        json.dumps(
            {
                "gates": [
                    {"id": "item-done", "covers": {"type": "ITEM", "to": "Done"}, "approvals": 1, "role": "Reviewer"},
                    {"id": "auth-rules", "covers": {"rules": {"domain": "AUTH"}}, "approvals": 2, "role": "Reviewer"},
                ]
            }
        ),
    )
    done, _ = _offer(project, tmp_path, capsys, change=("| **Status** | Open |", "| **Status** | Done |"))
    assert main(["reconcile", done["case"], "accept", "--as", "ada"]) == 1
    assert "gate item-done lacks 1 of 1" in capsys.readouterr().err
    assert main(["approve", done["case"], "--gate", "item-done", "--as", "rev", "--json"]) == 0
    entry = json.loads(capsys.readouterr().out)
    assert (entry["artifact"], entry["proposal"], entry["approved"]["blob"], entry["missing"]) == (
        ITEM,
        done["case"],
        done["proposed"],
        0,
    )
    assert main(["reconcile", done["case"], "accept", "--as", "ada"]) == 0
    capsys.readouterr()
    assert "| **Status** | Done |" in _file(project).read_text(encoding="utf-8")
    # a gated rule's document: approved before it lands, so check never errors on it
    rule, _ = _offer(
        project, tmp_path, capsys, item=RULE, change=("Login flow", "Login flow, with a lockout"), name="r.md"
    )
    for who in ("rev", "ria"):
        assert main(["approve", rule["case"], "--gate", "auth-rules", "--as", who]) == 0
    assert main(["approve", rule["case"], "--gate", "auth-rules", "--as", "bob"]) == 1  # no Reviewer, and its author
    capsys.readouterr()
    assert main(["reconcile", rule["case"], "accept", "--as", "ada"]) == 0
    capsys.readouterr()
    dep = load(project)
    assert [e for e in check.run(dep).errors if e.startswith("gates")] == []
    got = gates.report(dep, load_corpus(dep), RULE)["gates"][0]
    assert (got["counted"], got["missing"]) == (["rev", "ria"], 0)


def test_check_reports_a_proposed_file_changed_outside_catalyst(project, tmp_path, capsys):
    found, _ = _offer(project, tmp_path, capsys)
    (project / ".criterion" / found["file"]).write_text("tampered\n", encoding="utf-8")
    errors = [e for e in check.run(load(project)).errors if e.startswith("proposal")]
    assert len(errors) == 1 and "changed outside catalyst" in errors[0]
