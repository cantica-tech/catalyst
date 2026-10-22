"""Workflow governance (REQ-000084): conditions on field values in guards
and gates (W1), due dates the inbox escalates (W2), and a WORKFLOW that
governs a type's moves (W3)."""

from __future__ import annotations

import datetime
import json
import re
import subprocess
from pathlib import Path

import pytest

from catalyst import conditions, workflows
from catalyst.__main__ import main
from catalyst.deployment import load
from catalyst_fixtures import write
from test_catalyst_init import KERNEL

MODULE = """id: doc-process
name: Document Process
version: 0.1.0
description: Documents, reviewed and published.
grounding_type: rule
format: 3
namespace: DOCP
kernel_version: ">=0.83.0"

entities:
  DOC:
    name: "Document"
    folder: documents
    grounding: none
    fields:
      Level:
        kind: enum
        required: true
        values: [Public, Internal, Confidential, Restricted]
      Reviewed:
        kind: date
      Owner:
        kind: text
    states: [Draft, Review, Published, Withdrawn]
    initial: Draft
    closed: [Withdrawn]
    due: "Reviewed + 30 days"
    guards:
      Published:
        - holds: "Owner is set"
    sections:
      - Body: |
          What it says.
    definition: "A `DOC-NNNNNN` is one document."
"""


@pytest.fixture
def project(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    module = tmp_path / "catalyst-doc-process"
    write(module / "module.yaml", MODULE)
    write(module / "version.txt", "0.1.0\n")
    write(
        module / "code-of-conduct.module.md",
        "# doc-process\n\n## 3. Standard document types\n\n## 4. Slash-command entry points\n",
    )
    write(module / "rules-of-rules.module.md", "# doc-process\n")
    write(
        module / "INVARIANTS.module.md", "# doc-process\n\n## The law\n\n<!-- catalyst: end of the session brief -->\n"
    )
    app = tmp_path / "app"
    subprocess.run(["git", "init", "-q", str(app)], check=True)
    argv = ["--project", str(app), "init", "--kernel", str(KERNEL), "--name", "app", "--module", "doc-process"]
    argv += ["--module-dir", str(module), "--git-username", "ada", "--rule-doc", "doc-rules.md:dr"]
    assert main([*argv, "--agent", "claude-code", "--no-runtime"]) == 0, capsys.readouterr().err
    monkeypatch.chdir(app)
    capsys.readouterr()
    return app


def _cli(capsys, *argv: str) -> str:
    capsys.readouterr()
    code = main(list(argv))
    out = capsys.readouterr()
    assert code == 0, out.err + out.out
    return out.out


def _doc(capsys, *fields: str) -> str:
    argv = ["new", "DOC", "--title", "A document", "--as", "ada", "--intent", "a document to move through its workflow"]
    for f in fields:
        argv += ["--field", f]
    return json.loads(_cli(capsys, *argv, "--json"))["id"]


def _root(capsys) -> Path:
    return Path(re.search(r"criterion\s+(\S+)", _cli(capsys, "where")).group(1))  # type: ignore[union-attr]


def _journal(capsys, path: Path, artifact: str, why: str) -> None:
    _cli(
        capsys,
        "journal",
        "append",
        "--command",
        "chore",
        "--action",
        "update",
        "--artifact",
        artifact,
        "--file",
        str(path),
        "--intent",
        why,
        "--tier",
        "chore",
        "--as",
        "ada",
    )


# --- W1 ---------------------------------------------------------------------------
def test_the_condition_language_parses_orders_and_refuses(project):
    dep = load(project)
    etd = dep.etds["DOC"]
    c = conditions.parse("Level at least Confidential")
    assert (c.field, c.test, c.values) == ("Level", "at least", ("Confidential",))
    assert conditions.parse("Level in Public, `Internal`").values == ("Public", "Internal")
    assert conditions.problems(conditions.parse("Level is Secret"), etd)
    assert conditions.problems(conditions.parse("Colour is set"), etd)
    assert conditions.problems(conditions.parse("Owner at least x"), etd)  # a text has no order
    with pytest.raises(conditions.ConditionError):
        conditions.parse("Level")


def test_a_holds_guard_refuses_until_its_condition_holds(project, capsys):
    doc = _doc(capsys, "Level=Internal")
    _cli(capsys, "status", "set", doc, "Review", "--intent", "ready to be read by its reviewers")
    assert main(["status", "set", doc, "Published", "--intent", "the reviewers agree to publish it"]) == 1
    assert "`Owner is set` does not hold" in capsys.readouterr().err
    root = _root(capsys)
    file = root / json.loads(_cli(capsys, "view", doc, "--json"))["file"]
    file.write_text(
        file.read_text(encoding="utf-8").replace("| **Owner** | *(none yet)* |", "| **Owner** | ada |"),
        encoding="utf-8",
    )
    _journal(capsys, file, doc, "its owner named before publishing")
    _cli(capsys, "status", "set", doc, "Published", "--intent", "the reviewers agree to publish it")


def test_a_gate_applies_only_when_its_condition_holds(project, capsys):
    root = _root(capsys)
    gates = root / "IAM" / "gates.json"
    gates.write_text(
        json.dumps(
            {
                "gates": [
                    {
                        "id": "sensitive",
                        "covers": {"type": "DOC", "to": "Review"},
                        "when": "Level at least Confidential",
                        "approvals": 1,
                        "role": "Admin",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    _journal(capsys, gates, "gates", "a confidential document is approved before review")
    public = _doc(capsys, "Level=Public")
    _cli(capsys, "status", "set", public, "Review", "--intent", "a public document needs no approval")
    secret = _doc(capsys, "Level=Restricted")
    assert main(["status", "set", secret, "Review", "--intent", "a restricted one waits for its approval"]) == 1
    assert "gate sensitive lacks 1 of 1" in capsys.readouterr().err
    gates.write_text(
        gates.read_text(encoding="utf-8").replace("Level at least Confidential", "Level at least Secret"),
        encoding="utf-8",
    )
    capsys.readouterr()
    assert main(["check"]) == 1
    assert "Secret is not a value of `Level`" in capsys.readouterr().out


# --- W2 ---------------------------------------------------------------------------
def test_an_overdue_entity_waits_in_the_inbox_and_check_warns(project, capsys):
    old = (datetime.date.today() - datetime.timedelta(days=40)).isoformat()
    late = _doc(capsys, "Level=Internal", f"Reviewed={old}")
    fresh = _doc(capsys, "Level=Internal", f"Reviewed={datetime.date.today().isoformat()}")
    found = json.loads(_cli(capsys, "inbox", "--json"))
    overdue = [i for i in found["items"] if i["kind"] == "overdue"]
    assert [i["id"] for i in overdue] == [late] and found["counts"]["overdue"] == 1
    assert overdue[0]["evidence"]["days"] == 10 and overdue[0]["evidence"]["field"] == "Reviewed"
    assert fresh not in json.dumps(overdue)
    out = _cli(capsys, "check")
    assert f"overdue: {late}" in out


def test_a_due_that_names_no_date_field_is_reported(project):
    dep = load(project)
    dep.etds["DOC"].workflow.due = "Owner + 3 days"
    assert any("a text field, not a date" in p for p in workflows.definition_problems(dep))


# --- W3 ---------------------------------------------------------------------------
def _governing(capsys, root: Path, rows: str, escalates: str = "Admin") -> str:
    wf = json.loads(
        _cli(
            capsys,
            "new",
            "WORKFLOW",
            "--title",
            "How documents move",
            "--as",
            "ada",
            "--field",
            "Governs=DOC",
            "--field",
            f"Escalates to={escalates}",
            "--intent",
            "documents move only as agreed",
            "--json",
        )
    )["id"]
    file = root / json.loads(_cli(capsys, "view", wf, "--json"))["file"]
    text = file.read_text(encoding="utf-8")
    text = text.replace(
        "| From | To | Role | When |\n|---|---|---|---|\n", f"| From | To | Role | When |\n|---|---|---|---|\n{rows}"
    )
    file.write_text(text, encoding="utf-8")
    _journal(capsys, file, wf, "the moves documents may make")
    _cli(capsys, "status", "set", wf, "Active", "--as", "ada", "--intent", "the workflow governs documents from now on")
    return wf


def test_an_active_workflow_governs_its_types_moves(project, capsys):
    root = _root(capsys)
    _cli(
        capsys,
        "role",
        "add",
        "Editor",
        "--action",
        "/status",
        "--action",
        "/create",
        "--intent",
        "editors move documents through review",
    )
    _cli(capsys, "user", "add", "Bob Editor", "Editor", "--git-username", "bob", "--intent", "an editor")
    wf = _governing(
        capsys,
        root,
        "| Draft | Review | Editor | |\n| Review | Published | Admin | Level at most Internal |\n| * | Withdrawn | | |\n",
    )
    doc = _doc(capsys, "Level=Confidential", "Owner=ada")
    view = json.loads(_cli(capsys, "view", doc, "--json"))
    assert [n["state"] for n in view["next"]] == ["Review", "Withdrawn"]  # the workflow's moves, not the type's
    # a move the table lists, by a role it names
    _cli(capsys, "status", "set", doc, "Review", "--as", "bob", "--intent", "bob sends it to review")
    # a move the table does not list, even with --force
    assert main(["status", "set", doc, "Draft", "--force", "--as", "ada", "--intent", "back to draft"]) == 1
    assert f"{wf}, which governs it, lists no such move" in capsys.readouterr().err
    # a listed move whose condition fails
    assert main(["status", "set", doc, "Published", "--as", "ada", "--intent", "publish it"]) == 1
    assert "`Level at most Internal` does not hold" in capsys.readouterr().err
    blocked = {n["state"]: n["blocked_by"] for n in json.loads(_cli(capsys, "view", doc, "--json"))["next"]}
    assert any("Level at most Internal" in b for b in blocked["Published"])
    # a listed move whose role the signer lacks
    other = _doc(capsys, "Level=Public", "Owner=ada")
    _cli(capsys, "status", "set", other, "Review", "--as", "bob", "--intent", "bob sends it to review")
    assert main(["status", "set", other, "Published", "--as", "bob", "--intent", "bob publishes it"]) == 1
    assert "it needs the role Admin" in capsys.readouterr().err
    _cli(capsys, "status", "set", other, "Published", "--as", "ada", "--intent", "an admin publishes it")
    _cli(capsys, "status", "set", doc, "Withdrawn", "--as", "bob", "--intent", "anyone may withdraw it")
    assert "workflow:" not in _cli(capsys, "check")


def test_a_governing_workflow_with_unknown_states_or_roles_fails_check(project, capsys):
    root = _root(capsys)
    _governing(capsys, root, "| Draft | Archived | Clerk | Colour is red |\n", escalates="Nobody")
    assert main(["check"]) == 1
    out = capsys.readouterr().out
    for expected in (
        "`Archived` is not a Document state",
        "`Clerk` is not a role",
        "no field `Colour`",
        "escalates to `Nobody`",
    ):
        assert expected in out, expected
