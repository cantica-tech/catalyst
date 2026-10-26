"""Landing, phase 1 (design 33; REQ-000099): every journal entry says how its
change was made (`via`, fw-STRUCTURE-000022), and a criterion declares how
its changes land, `IAM/landing.json`, the kernel's standard policy when
absent, chosen with `catalyst landing init` and validated by `check`
(fw-STRUCTURE-000023)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import schema_check
from catalyst import check, journal, landing
from catalyst.__main__ import main
from catalyst.deployment import load
from catalyst_fixtures import journal_entries, write
from test_catalyst_gates import ROLES as GATE_ROLES, _iam
from test_catalyst_history import lived  # noqa: F401 (the fixture)

KERNEL = Path(__file__).resolve().parents[1] / "framework" / "kernel"
ROLES = {"roles": [*GATE_ROLES["roles"], {"name": "Criterion Admin", "actions": []}]}


@pytest.fixture
def landed(lived, monkeypatch):  # noqa: F811
    """The lived project with Bob (a Reviewer, not an admin) and the roles the kernel's policies name."""
    project, _, _ = lived
    _iam(project, None)
    write(project / ".criterion" / "IAM" / "roles" / "roles.json", json.dumps(ROLES))
    for v in (journal.VIA_VARIABLE, *journal.AGENT_VARIABLES):
        monkeypatch.delenv(v, raising=False)
    return project


# --- via -----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("env", "said"),
    [
        ({}, "person"),
        ({"CLAUDECODE": "1"}, "agent"),
        ({"AI_AGENT": "some-agent"}, "agent"),
        ({"GEMINI_CLI": "1"}, "agent"),
        ({"CATALYST_VIA": "agent"}, "agent"),
        ({"CATALYST_VIA": "person", "CLAUDECODE": "1"}, "person"),  # a UI's host says so outright
        ({"CATALYST_VIA": "nonsense"}, "person"),
    ],
)
def test_via_says_how_a_change_was_made(env, said):
    assert journal.via(env) == said


def test_every_entry_written_carries_via(landed, capsys, monkeypatch):
    project = landed
    assert main(["landing", "init", "--as", "dee"]) == 0
    monkeypatch.setenv("CLAUDECODE", "1")
    assert main(["landing", "init", "--policy", "open", "--force", "--as", "dee"]) == 0
    entries = journal_entries(project / ".criterion")
    assert [e["via"] for e in entries[-2:]] == ["person", "agent"]
    spec = json.loads((KERNEL.parents[1] / "spec" / "journal-entry.schema.json").read_text(encoding="utf-8"))
    assert schema_check.problems(entries[-1], spec) == []


def test_an_entry_from_before_has_no_via_and_stays_so(landed):
    entries = journal_entries(landed / ".criterion")
    assert entries and all("via" not in e or e["via"] in journal.VIA for e in entries)


# --- the policy ------------------------------------------------------------------
def test_no_file_is_the_standard_policy(landed, capsys):
    dep = load(landed)
    data, source = landing.effective(dep)
    assert data == landing.POLICIES["standard"] and "no IAM/landing.json" in source
    assert landing.problems(dep) == []
    capsys.readouterr()
    assert main(["landing", "show", "--json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["policy"]["policy"] == "standard"
    spec = KERNEL.parents[1] / "spec"
    assert schema_check.problems(shown, json.loads((spec / "landing-show.schema.json").read_text())) == []
    assert main(["landing", "init", "--as", "dee", "--json"]) == 0
    made = json.loads(capsys.readouterr().out)
    assert schema_check.problems(made, json.loads((spec / "landing-init.schema.json").read_text())) == []


@pytest.mark.parametrize("name", sorted(landing.POLICIES))
def test_each_kernel_policy_is_its_template_and_holds(landed, name):
    template = KERNEL / "templates" / f"landing.{name}.template.json"
    assert json.loads(template.read_text(encoding="utf-8")) == landing.POLICIES[name]
    schema = json.loads((KERNEL / "schemas" / "landing.schema.json").read_text(encoding="utf-8"))
    assert schema_check.problems(landing.POLICIES[name], schema) == []
    write(landed / ".criterion" / landing.LANDING, json.dumps(landing.POLICIES[name]))
    assert landing.problems(load(landed)) == []


def test_init_journals_the_choice_as_the_admins_assent(landed, capsys):
    assert main(["landing", "init", "--policy", "reviewed", "--as", "dee"]) == 0
    path = landed / ".criterion" / landing.LANDING
    assert json.loads(path.read_text(encoding="utf-8"))["policy"] == "reviewed"
    last = journal_entries(landed / ".criterion")[-1]
    assert last["command"] == "catalyst landing init" and last["action"] == "create"
    assert "assent" in last["intent"][0] and last["files"][0]["path"].endswith("IAM/landing.json")
    capsys.readouterr()
    assert main(["landing", "init", "--as", "dee"]) == 1  # it exists
    assert "--force" in capsys.readouterr().err
    assert main(["landing", "init", "--force", "--as", "dee"]) == 0
    assert journal_entries(landed / ".criterion")[-1]["action"] == "update"


def test_only_an_admin_chooses_it(landed, capsys):
    assert main(["landing", "init", "--as", "bob"]) == 1
    assert "an admin's" in capsys.readouterr().err
    assert not (landed / ".criterion" / landing.LANDING).exists()


def test_a_malformed_policy_is_a_check_error(landed):
    bad = {
        "policy": "Bad Name",
        "target": {"kind": "svn"},
        "rules": [
            {
                "id": "x",
                "match": {"via": "robot", "who": ["Nobody"], "types": ["NOPE"]},
                "group": "day",
                "review": {"approvals": 0, "role": "Nobody"},
                "merge": "maybe",
            },
            {
                "id": "x",
                "match": {"change": "sideways", "colour": "red"},
                "group": {"by": "window", "minutes": 0},
                "review": "none",
                "merge": "auto",
            },
        ],
        "default": {"group": "change", "review": "none", "merge": "auto", "id": "extra"},
        "extra": 1,
    }
    write(landed / ".criterion" / landing.LANDING, json.dumps(bad))
    found = "\n".join(landing.problems(load(landed)))
    for said in (
        "no field extra",
        "`policy` names the policy",
        '`target` is {"kind": "git"',
        "`match.via` is one of",
        "`match.who` 'Nobody' is not a role",
        "`match.types` 'NOPE' is not a declared type",
        "`group` is one of",
        "`review.approvals` is a whole number",
        "`review.role` 'Nobody' is not a role",
        "`merge` is one of",
        "declared twice",
        "`match.change` is one of",
        "`match` has no colour",
        "`group.minutes` is a whole number",
        "default: it takes group, review and merge only",
    ):
        assert said in found, said
    assert any(e.startswith("landing: ") for e in check.run(load(landed)).errors)
    write(landed / ".criterion" / landing.LANDING, "{not json")
    assert "not JSON" in landing.problems(load(landed))[0]


def test_a_served_criterion_without_a_credential_is_warned(landed):
    dep = load(landed)
    assert landing.warnings(dep) == []
    dep.pointer["share"] = "serve"
    assert landing.warnings(dep) == []  # the standard policy names one
    policy = landing.policy("standard")
    policy["target"]["credential"] = None
    write(landed / ".criterion" / landing.LANDING, json.dumps(policy))
    assert "names no `target.credential`" in landing.warnings(dep)[0]
