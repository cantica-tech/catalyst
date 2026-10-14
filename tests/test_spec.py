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
    ("backlog", ["backlog"]),
    ("graph", ["graph"]),
    ("journal", ["journal", "show"]),
    ("check", ["check"]),
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
    ],
)
def test_a_wrong_payload_is_refused(schema, wrong):
    assert schema_check.problems(wrong, schema_check.load(schema))


def test_every_schema_in_spec_is_listed_in_its_readme():
    readme = (schema_check.SPEC / "README.md").read_text(encoding="utf-8")
    for f in sorted(schema_check.SPEC.glob("*.schema.json")):
        assert f"`{f.name}`" in readme, f.name
