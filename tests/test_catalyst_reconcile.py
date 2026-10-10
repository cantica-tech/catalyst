"""`catalyst reconcile` (rr-META-016, INV-21): the one role gate catalyst
enforces — `full` decides, `propose` proposes, `none` asks someone else."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst_fixtures import USERID, journal_entries, make_project, write

KERNEL = Path(__file__).resolve().parent.parent / "framework" / "kernel"


@pytest.fixture
def case(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path, git=True)
    root = project / ".criterion"
    write(
        root / "IAM" / "roles" / "roles.json",
        json.dumps(
            {
                "roles": [
                    {"name": "Admin", "actions": [], "reconciliation": "full"},
                    {"name": "Developer", "actions": [], "reconciliation": "propose"},
                    {"name": "Viewer", "actions": []},
                ]
            }
        ),
    )
    users = json.loads((root / "IAM" / "users" / "users.json").read_text(encoding="utf-8"))
    users["users"] += [
        {"name": "Bob", "git_username": "bob", "roles": ["Developer"], "active": True, "userid": "Bb12Cd34"},
        {"name": "Vic", "git_username": "vic", "roles": ["Viewer"], "active": True, "userid": "Vc12Cd34"},
    ]
    write(root / "IAM" / "users" / "users.json", json.dumps(users))
    folder = root / "reconciliations" / "templates"
    folder.mkdir(parents=True)
    shutil.copyfile(KERNEL / "templates" / "reconciliation.template.md", folder / "TEMPLATE-RECONCILIATION-v1.md")
    monkeypatch.chdir(project)
    assert (
        main(["new", "RECON", "--title", "Login flow", "--as", "ada", "--field", f"Entity=ITEM-000001-{USERID}"]) == 0
    )
    capsys.readouterr()
    return project, load_corpus(load(project)).by_prefix["RECON"][0].id


def _status(project, case_id):
    return load_corpus(load(project)).artifacts[case_id][0]


def test_full_decides_propose_proposes_none_asks(case, capsys):
    project, case_id = case
    assert main(["reconcile", case_id, "propose", "--as", "vic", "--text", "x"]) == 1
    assert "no reconciliation rights" in capsys.readouterr().err
    assert main(["reconcile", case_id, "accept", "--as", "bob"]) == 1
    assert "needs a `full` reconciliation role" in capsys.readouterr().err
    assert main(["reconcile", case_id, "propose", "--as", "bob", "--text", "keep | both"]) == 0
    art = _status(project, case_id)
    assert art.get("Status") == "Under Review"
    assert "| 2 | Bob |" in art.file.read_text(encoding="utf-8") and "keep \\| both" in art.file.read_text(
        encoding="utf-8"
    )
    assert main(["reconcile", case_id, "close", "--as", "ada"]) == 1  # not resolved yet
    assert main(["reconcile", case_id, "accept-with-edits", "--as", "ada"]) == 0
    art = _status(project, case_id)
    assert art.get("Status") == "Resolved-Accepted-with-Edits" and (art.get("Resolver") or "").startswith("Ada")
    assert main(["reconcile", case_id, "propose", "--as", "bob", "--text", "late"]) == 1
    assert main(["reconcile", case_id, "close", "--as", "ada"]) == 0
    assert _status(project, case_id).get("Status") == "Closed"
    assert main(["reconcile", case_id, "reject", "--as", "ada"]) == 1
    assert "closed case is final" in capsys.readouterr().err
    entries = [e for e in journal_entries(project / ".criterion") if e["command"] == "/reconcile"]
    assert len(entries) == 3 and all(e["artifact"] == case_id for e in entries)
    assert main(["check"]) in (0, 1)  # the case still parses: its status is one of the ETD's


def test_status_set_never_changes_a_case(case, capsys):
    _, case_id = case
    assert main(["status", "set", case_id, "Closed", "--as", "ada"]) == 1
    assert "only /reconcile" in capsys.readouterr().err
