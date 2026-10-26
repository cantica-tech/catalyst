"""Every read verb's `--json` against its schema in `spec/` (roadmap R5.1;
REQ-000034), with the shared checker of `tests/schema_check.py`."""

from __future__ import annotations

import json
import shutil
from typing import Any

import pytest

import schema_check
from catalyst.__main__ import main
from catalyst_fixtures import USERID, write
from test_catalyst_edit import _project
from test_catalyst_init import KERNEL
from test_catalyst_views import ROW_SCHEMA

ITEM, RULE = f"ITEM-000001-{USERID}", f"br-AUTH-000001-{USERID}"


@pytest.fixture
def project(tmp_path, monkeypatch):
    """The fixture project with templates, a type kept as table rows and
    one row, the kernel's roles, and one artifact created (one journal
    entry)."""
    project = _project(tmp_path)
    root = project / ".criterion"
    mod = root / "modules" / "example-process"
    write(mod / "schemas" / "row.yaml", ROW_SCHEMA)
    write(
        mod / "module.yaml",
        (mod / "module.yaml").read_text(encoding="utf-8") + "  - id: ROW\n    schema: schemas/row.yaml\n",
    )
    write(
        root / "rows" / "rows.md",
        f"# Rows\n\n| ID | Title | Linked |\n|---|---|---|\n| `ROW-000001-{USERID}` | First | `{ITEM}` |\n",
    )
    (root / "IAM" / "roles").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(KERNEL / "templates" / "roles.template.json", root / "IAM" / "roles" / "roles.json")
    monkeypatch.chdir(project)
    assert main(["new", "SUB", "--title", "Its sub", "--as", "ada", "--field", f"Item={ITEM}"]) == 0  # a journal entry
    return project


def _json(capsys, *argv) -> Any:
    capsys.readouterr()
    main([*argv, "--json"])  # check exits 1 on a failing fixture: the payload is what is tested
    return json.loads(capsys.readouterr().out)


CASES = [
    ("list", ["list", "all"]),
    ("list", ["list", "ITEM"]),
    ("list", ["list", "ROW"]),
    ("list", ["list", "rules"]),
    ("list", ["list", "users"]),
    ("list", ["list", "roles"]),
    ("list", ["list", "templates"]),
    ("view", ["view", ITEM]),
    ("view", ["view", RULE]),
    ("view", ["view", f"ROW-000001-{USERID}"]),
    ("backlog", ["backlog"]),
    ("graph", ["graph"]),
    ("journal", ["journal", "show"]),
    ("check", ["check"]),
    ("validate", ["validate"]),
    ("journal-verify", ["journal", "verify"]),
    ("report", ["report"]),
]


@pytest.mark.parametrize(("schema", "argv"), CASES, ids=[" ".join(a) for _, a in CASES])
def test_each_payload_holds_to_its_schema(project, capsys, schema, argv):
    payload = _json(capsys, *argv)
    assert payload, f"{' '.join(argv)} printed nothing to check"
    assert schema_check.problems(payload, schema_check.load(schema)) == []


def test_the_payloads_cover_what_their_schemas_describe(project, capsys):
    kinds = {row.get("type") for row in _json(capsys, "list", "all")}
    assert {"rule", "ITEM", "SUB", "ROW"} <= kinds
    graph = _json(capsys, "graph")
    assert any(a.get("row") for a in graph["artifacts"]) and graph["types"]
    assert _json(capsys, "list", "users") and _json(capsys, "list", "roles") and _json(capsys, "list", "templates")


@pytest.mark.parametrize(
    ("schema", "wrong"),
    [
        ("list", [{"id": "X"}]),
        ("view", {"id": "X", "type": "rule"}),
        ("backlog", {"open": {"ITEM": {"Open": [1]}}, "missing_links": [], "rules_without_open_work": []}),
        ("graph", {"rules": [], "domains": [], "artifacts": [], "types": {}, "extra": 1}),
        ("journal", [{"timestamp": "now"}]),
        ("check", {"ok": "yes", "errors": [], "warnings": []}),
        ("validate", {"ok": True, "findings": [{"level": "fatal", "code": "x", "where": "y", "message": "z"}]}),
        ("journal-verify", {"ok": True, "issues": [{"level": "error", "code": "chain", "at": "j:1", "message": "m"}]}),
        ("report", {"entries": -1}),
        (
            "approvals",
            {
                "id": "X",
                "version": "v",
                "gates": [
                    {"gate": "g", "role": "r", "approvals": 1, "covers": {"domain": "X"}, "counted": [], "missing": 0}
                ],
            },
        ),
    ],
)
def test_a_wrong_payload_is_refused(schema, wrong):
    assert schema_check.problems(wrong, schema_check.load(schema))


def test_every_schema_in_spec_is_listed_in_its_readme():
    readme = (schema_check.SPEC / "README.md").read_text(encoding="utf-8")
    for f in sorted(schema_check.SPEC.glob("*.schema.json")):
        assert f"`{f.name}`" in readme, f.name


@pytest.mark.parametrize(
    ("schema", "argv"),
    [
        ("change", ["new", "SUB", "--title", "Another sub", "--as", "ada", "--field", f"Item={ITEM}"]),
        ("change", ["status", "set", ITEM, "Done", "--as", "ada", "--intent", "the item is finished and checked"]),
        ("freeze", ["freeze", ITEM, "--as", "ada", "--intent", "the item is settled"]),
    ],
    ids=["new", "status set", "freeze"],  # user and role add refuse since design 29
)
def test_each_writing_verb_prints_what_its_schema_describes(project, capsys, schema, argv):
    """R4.4 phase 2: the writing and administration verbs' `--json` output, described."""
    payload = _json(capsys, *argv)
    assert schema_check.problems(payload, schema_check.load(schema)) == []


def test_runtime_status_prints_what_its_schema_describes(project, capsys):
    payload = _json(capsys, "runtime", "status")
    assert payload["criterion"] and schema_check.problems(payload, schema_check.load("runtime-status")) == []


def test_every_json_command_is_described():
    """R4.4: the ratchet ran to zero; a new `--json` command ships with its schema."""
    import gen_docs

    assert gen_docs.json_drift() == [] and set() == gen_docs.UNDESCRIBED


def test_try_carries_the_impact_schema_unchanged():
    """`try`'s `impact` is `catalyst impact --json`: a copy in its `$defs`, since a schema refers only within itself."""
    impact, tried = schema_check.load("impact"), schema_check.load("try")
    body = {k: v for k, v in impact.items() if k not in ("$schema", "$id", "title", "$defs")}
    assert tried["$defs"]["impact"] == body
    assert tried["$defs"]["reached"] == impact["$defs"]["reached"]
