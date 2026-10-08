"""Writing verbs (roadmap R2 W2): new, status set, link — driven by the ETDs."""
import datetime
import json

import pytest

from catalyst import edit
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst.validate import ERROR, validate
from catalyst_fixtures import USER, USERID, make_project, write

ITEM, SUB, RULE = f"ITEM-000001-{USERID}", f"SUB-000001-{USERID}", f"br-AUTH-000001-{USERID}"
TEMPLATE = """# `ITEM-NNNNNN` — <title>

| Field | Value |
|---|---|
| **ID** | `ITEM-NNNNNN-<userid>` |
| **Name** | short name |
| **Filename** | file name |
| **Status** | one of Open / Done |
| **Opened** | YYYY-MM-DD |
| **Targets** | rule IDs |
| **Domain** | domain code |
| **Subs** | SUB IDs |
| **Signed-off-by** | signer |

## Description

What the agent writes.
"""
SUB_TEMPLATE = """# `SUB-NNNNNN` — <title>

| Field | Value |
|---|---|
| **ID** | `SUB-NNNNNN-<userid>` |
| **Status** | Open |
| **Item** | ITEM ID |
| **Signed-off-by** | signer |
"""


def _project(tmp_path):
    project = make_project(tmp_path, git=True)
    write(project / ".criterion" / "items" / "templates" / "TEMPLATE-ITEM-v1.md", "old\n")
    write(project / ".criterion" / "items" / "templates" / "TEMPLATE-ITEM-v2.md", TEMPLATE)
    write(project / ".criterion" / "subs" / "templates" / "TEMPLATE-SUB-v1.md", SUB_TEMPLATE)
    return project


def _state(project):
    dep = load(project)
    return dep, load_corpus(dep)


def _signer(corpus):
    return corpus.users[0]


def test_new_fills_the_latest_template_signs_indexes_and_journals(tmp_path):
    project = _project(tmp_path)
    dep, corpus = _state(project)
    res = edit.new(dep, corpus, "items", "Second item", {"Targets": RULE, "Domain": "AUTH"},
                   _signer(corpus), [], today=datetime.date(2026, 10, 8))
    assert res.id == f"ITEM-000002-{USERID}" and res.file.name == "ITEM-000002-second-item.md"
    text = res.file.read_text(encoding="utf-8")
    for row in (f"| **ID** | `{res.id}` |", "| **Status** | Open |", "| **Opened** | 2026-10-08 |",
                f"| **Targets** | `{RULE}` |", f"| **Signed-off-by** | {USER} |", "| **Subs** | *(none yet)* |"):
        assert row in text
    assert text.startswith(f"# `{res.id}` — Second item") and "## Description" in text
    assert res.id in (project / ".criterion" / "items" / "items.md").read_text(encoding="utf-8")
    last = json.loads((project / ".criterion" / "development" / "journal.jsonl").read_text(
        encoding="utf-8").splitlines()[-1])
    assert last["artifact"] == res.id and last["action"] == "create" and last["targets"] == [RULE]
    dep, corpus = _state(project)
    assert not [f for f in validate(dep, corpus) if f.level == ERROR]


def test_new_keeps_back_references(tmp_path):
    project = _project(tmp_path)
    dep, corpus = _state(project)
    res = edit.new(dep, corpus, "SUB", "Another sub", {"Item": ITEM}, _signer(corpus), [])
    assert res.id in load_corpus(dep).artifacts[ITEM][0].get("Subs")
    assert len(res.touched) == 2


def test_new_refuses_missing_required_fields_and_unknown_references(tmp_path):
    dep, corpus = _state(_project(tmp_path))
    with pytest.raises(edit.EditError, match="--field Targets"):
        edit.new(dep, corpus, "ITEM", "x", {"Domain": "AUTH"}, _signer(corpus), [])
    with pytest.raises(edit.EditError, match="does not exist"):
        edit.new(dep, corpus, "ITEM", "x", {"Targets": "br-AUTH-000099-nope", "Domain": "AUTH"},
                 _signer(corpus), [])
    with pytest.raises(edit.EditError, match="no field"):
        edit.new(dep, corpus, "ITEM", "x", {"Colour": "blue"}, _signer(corpus), [])


def test_status_set_checks_values_and_refuses_reconciliation_cases(tmp_path):
    project = _project(tmp_path)
    dep, corpus = _state(project)
    edit.set_status(dep, corpus, ITEM, "Done", _signer(corpus), [])
    dep, corpus = _state(project)
    assert corpus.artifacts[ITEM][0].get("Status") == "Done"
    with pytest.raises(edit.EditError, match="not a Item status"):
        edit.set_status(dep, corpus, ITEM, "Bogus", _signer(corpus), [])
    edit.set_status(dep, corpus, ITEM, "Bogus", _signer(corpus), [], force=True)
    recon = corpus.artifacts[ITEM][0]
    recon.prefix = "RECON"
    with pytest.raises(edit.EditError, match="/reconcile"):
        edit.set_status(dep, corpus, ITEM, "Open", _signer(corpus), [])


def test_link_adds_ids_once_and_writes_the_back_reference(tmp_path):
    project = _project(tmp_path)
    dep, corpus = _state(project)
    sub = edit.new(dep, corpus, "SUB", "Loose sub", {"Item": ITEM}, _signer(corpus), [])
    dep, corpus = _state(project)
    with pytest.raises(edit.EditError, match="already cites"):
        edit.link(dep, corpus, ITEM, "Subs", [sub.id], _signer(corpus), [])
    other = edit.new(dep, corpus, "ITEM", "Other", {"Targets": RULE, "Domain": "AUTH"}, _signer(corpus), [])
    dep, corpus = _state(project)
    with pytest.raises(edit.EditError, match="takes one ID"):
        edit.link(dep, corpus, sub.id, "Item", [other.id], _signer(corpus), [])
    third = edit.new(dep, corpus, "SUB", "Third sub", {"Item": other.id}, _signer(corpus), [])
    dep, corpus = _state(project)
    edit.link(dep, corpus, ITEM, "Subs", [third.id], _signer(corpus), [])
    dep, corpus = _state(project)
    assert third.id in corpus.artifacts[ITEM][0].get("Subs")
    with pytest.raises(edit.EditError, match="not a reference"):
        edit.link(dep, corpus, ITEM, "Status", ["x"], _signer(corpus), [])


def test_the_cli_creates_and_reports(tmp_path, capsys):
    project = _project(tmp_path)
    assert main(["--project", str(project), "new", "ITEM", "--title", "From the CLI",
                 "--field", f"Targets={RULE}", "--field", "Domain=AUTH", "--json"]) == 0
    created = json.loads(capsys.readouterr().out)["id"]
    assert main(["--project", str(project), "status", "set", created, "Done"]) == 0
    assert main(["--project", str(project), "new", "ITEM", "--title", "x"]) == 1
    assert "--field Targets" in capsys.readouterr().err


def test_a_back_reference_row_an_older_artifact_lacks_is_added(tmp_path):
    project = _project(tmp_path)
    item = project / ".criterion" / "items" / "ITEM-000001-first-item.md"
    text = item.read_text(encoding="utf-8")
    item.write_text("\n".join(l for l in text.split("\n") if "**Subs**" not in l), encoding="utf-8")
    dep, corpus = _state(project)
    res = edit.new(dep, corpus, "SUB", "Late sub", {"Item": ITEM}, _signer(corpus), [])
    assert f"| **Subs** | `{res.id}` |" in item.read_text(encoding="utf-8")
