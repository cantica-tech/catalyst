"""Approval gates, opt-in (decision G, design 25, REQ-000051 A1 and A2):
`IAM/gates.json` read and checked, `catalyst approve` journaling an
approval of one version, `catalyst approvals` counting them."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import schema_check
from catalyst import check, gates
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst_fixtures import journal_entries, write
from test_catalyst_history import RULE, lived  # noqa: F401 (the fixture)

SPEC = Path(__file__).resolve().parents[1]
ROLES = {"roles": [{"name": "Admin", "actions": [], "reconciliation": "full"}, {"name": "Reviewer", "actions": []}]}
GATES = {
    "gates": [
        {"id": "auth-rules", "covers": {"rules": {"domain": "AUTH"}}, "approvals": 2, "role": "Reviewer"},
        {"id": "item-done", "covers": {"type": "ITEM", "to": "Done"}, "approvals": 1, "role": "Reviewer"},
    ]
}


def _iam(project, gates_doc=GATES):
    root = project / ".criterion"
    users = json.loads((root / "IAM" / "users" / "users.json").read_text())
    users["users"] += [
        {"name": "Bob", "git_username": "bob", "roles": ["Reviewer"], "active": True, "userid": "Bb12Cd34"},
        {"name": "Cy", "git_username": "cy", "roles": ["Reviewer"], "active": True, "userid": "Cc12Dd34"},
        {"name": "Dee", "git_username": "dee", "roles": ["Admin"], "active": True, "userid": "Dd12Ee34"},
    ]
    write(root / "IAM" / "users" / "users.json", json.dumps(users))
    write(root / "IAM" / "roles" / "roles.json", json.dumps(ROLES))
    if gates_doc is not None:
        write(root / gates.GATES, json.dumps(gates_doc))


def _problems(project):
    dep = load(project)
    return gates.problems(dep, load_corpus(dep))


def test_no_file_no_gate(lived):  # noqa: F811
    project, item, _ = lived
    _iam(project, None)
    assert _problems(project) == []
    dep = load(project)
    assert gates.report(dep, load_corpus(dep), item)["gates"] == []


def test_a_malformed_gate_is_a_check_error(lived):  # noqa: F811
    project, _, _ = lived
    bad = {
        "gates": [
            {"id": "Bad Id", "covers": {"rules": {"domain": "NOPE"}}, "approvals": 0, "role": "Nobody"},
            {"id": "x", "covers": {"type": "ITEM", "to": "Shipped"}, "approvals": 1, "role": "Reviewer"},
            {"id": "x", "covers": {"type": "NOPE", "to": "Done"}, "approvals": 1, "role": "Reviewer"},
        ]
    }
    _iam(project, bad)
    found = "\n".join(_problems(project))
    for said in (
        "`id` is a lowercase",
        "`approvals` is a whole number",
        "'Nobody' is not a role",
        "'NOPE' is not registered",
        "'Shipped' is not a",
        "declared twice",
        "type 'NOPE' is not declared",
    ):
        assert said in found
    assert any(e.startswith("gates: ") for e in check.run(load(project)).errors)
    _iam(project)
    assert _problems(project) == []
    kernel = SPEC / "framework" / "kernel" / "schemas" / "gates.schema.json"
    assert schema_check.problems(GATES, json.loads(kernel.read_text(encoding="utf-8"))) == []


def test_an_approval_is_of_a_version_and_never_the_authors(lived, capsys):  # noqa: F811
    project, item, _ = lived
    _iam(project)
    assert main(["approvals", item, "--json"]) == 0
    before = json.loads(capsys.readouterr().out)
    assert [(g["gate"], g["missing"]) for g in before["gates"]] == [("item-done", 1)]
    # ada wrote the version and is no reviewer; Dee holds the wrong role
    assert main(["approve", item, "--gate", "item-done", "--as", "ada"]) == 1
    assert "does not hold the role Reviewer" in capsys.readouterr().err
    assert main(["approve", item, "--gate", "auth-rules", "--as", "bob"]) == 1
    assert "does not cover" in capsys.readouterr().err
    assert main(["approve", item, "--gate", "item-done", "--as", "bob", "--intent", "Reviewed", "--json"]) == 0
    entry = json.loads(capsys.readouterr().out)
    assert (entry["action"], entry["gate"], entry["actor"], entry["missing"]) == ("approve", "item-done", "bob", 0)
    assert entry["approved"]["blob"] == before["version"] and entry["files"] == []
    assert journal_entries(project / ".criterion")[-1]["action"] == "approve"
    assert main(["approve", item, "--gate", "item-done", "--as", "bob"]) == 1
    assert "already approved this version" in capsys.readouterr().err
    # a new version: the earlier approval no longer counts for it
    assert main(["rename", item, "--title", "Renamed", "--as", "bob", "--intent", "retitle"]) == 0
    capsys.readouterr()
    assert main(["approvals", item, "--json"]) == 0
    now = json.loads(capsys.readouterr().out)
    assert schema_check.problems(now, schema_check.load("approvals")) == []
    assert now["version"] != before["version"] and now["gates"][0]["missing"] == 1
    assert main(["approve", item, "--gate", "item-done", "--as", "bob"]) == 1  # bob wrote this one
    assert "never approves their own change" in capsys.readouterr().err
    assert main(["approve", item, "--gate", "item-done", "--as", "cy"]) == 0
    capsys.readouterr()
    assert main(["approvals", item]) == 0
    assert "1/1 from Reviewer (cy); passed" in capsys.readouterr().out
    errors = check.run(load(project)).errors  # the fixture is no full deployment: its structure errors aside,
    assert [e for e in errors if e.startswith(("journal", "gates"))] == []  # approvals keep the journal sound


def test_a_rule_gate_counts_two_reviewers(lived, capsys):  # noqa: F811
    project, _, _ = lived
    _iam(project)
    for who in ("bob", "cy"):
        assert main(["approve", RULE, "--gate", "auth-rules", "--as", who]) == 0
    capsys.readouterr()
    dep = load(project)
    got = gates.report(dep, load_corpus(dep), RULE)["gates"][0]
    assert (got["counted"], got["missing"]) == (["bob", "cy"], 0)
    with pytest.raises(gates.GateError):
        gates.approve(dep, load_corpus(dep), "ITEM-999999", "item-done", load_corpus(dep).user("bob"), [])
