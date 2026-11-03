"""Roles grant commands (owner decision D5, R4.6; INV-16, rr-META-011): a
writing verb refuses a signer none of whose roles grants its command."""

from __future__ import annotations

import json

import pytest

from catalyst import permissions
from catalyst.__main__ import main
from catalyst.deployment import load
from catalyst_fixtures import USERID, write
from test_catalyst_edit import _project

ITEM = f"ITEM-000001-{USERID}"

COC = """# Rules of Development

## 4. Slash-command entry points

- `/create <type> <title>` (`/create-item`) — create an artifact.
- `/status` — change a status.
- `/user` (`/user-add`, `/user-remove`) — the users.
- `/journal` (`/journal-restore`) — the journal.
- `/reconcile` — reconciliation cases.
- `/share` — sharing the criterion.

When the user enters `/status`, run `catalyst status set`.

## 5. Next
"""

ROLES = {
    "roles": [
        {"name": "Developer", "actions": ["implement things", "/status on tasks"], "reconciliation": "propose"},
        {"name": "Onboarder", "actions": ["/user-add"], "reconciliation": "none"},
        {"name": "Lead", "actions": ["*"], "reconciliation": "full"},
        {"name": "Admin", "actions": ["/user"], "reconciliation": "full"},
    ]
}


@pytest.fixture
def team(tmp_path, monkeypatch, capsys):
    project = _project(tmp_path)
    root = project / ".criterion"
    write(root / "CODE-OF-CONDUCT.md", COC)
    write(root / "IAM" / "roles" / "roles.json", json.dumps(ROLES))
    users = json.loads((root / "IAM" / "users" / "users.json").read_text(encoding="utf-8"))
    users["users"] += [
        {"name": "Bob", "git_username": "bob", "roles": ["Developer"], "active": True, "userid": "B0bB0bB0"},
        {"name": "Cy", "git_username": "cy", "roles": ["Onboarder"], "active": True, "userid": "Cy0Cy0Cy"},
        {"name": "Dee", "git_username": "dee", "roles": ["Lead"], "active": True, "userid": "De3De3De"},
        {"name": "Eve", "git_username": "eve", "roles": ["Developer"], "active": False, "userid": "Ev3Ev3Ev"},
    ]
    write(root / "IAM" / "users" / "users.json", json.dumps(users))
    monkeypatch.chdir(project)
    capsys.readouterr()
    return project


def _user(name: str, roles: list[str], grants: list[str] = ()) -> dict:
    """A signer as catalyst-users presents it: its roles shown, its grants from the token (fw-IDENTITY-000008)."""
    return {"name": name, "roles": roles, "grants": list(grants)}


def test_what_a_role_grants(team):
    dep = load(team)
    developer = _user("Bob", ["Developer"], ["cmd:status", "reconcile:propose"])
    assert permissions.grants(dep, developer) == {"status"}  # a reconciliation level is no command
    assert permissions.grants(dep, _user("Dee", ["Lead"], ["cmd:*"])) == {"*"}
    assert permissions.grants(dep, _user("Ada", ["Admin"])) == set()  # a role's name grants nothing: its grants do
    assert permissions.required(dep, "/status on tasks") == ["status"]
    assert permissions.required(dep, "/user-add") == ["user-add", "user"]
    assert permissions.required(dep, "create", ("create-item", "create-nothing")) == ["create", "create-item"]
    assert permissions.required(dep, "chore") is None  # a tier is not a command
    assert permissions.required(dep, "/implement") is None  # nor a command the deployment lacks
    onboarder = _user("Cy", ["Onboarder"], ["cmd:user-add"])
    assert permissions.refusal(dep, onboarder, "/user-add") is None  # an alias grants itself
    assert permissions.refusal(dep, onboarder, "/user-remove") is not None
    assert permissions.refusal(dep, _user("Ada", ["Admin"], ["cmd:user"]), "/user-remove") is None  # and its aliases


def test_a_writing_verb_refuses_what_no_role_grants(team, capsys):
    assert main(["status", "set", ITEM, "Done", "--as", "bob", "--intent", "the work is finished and checked"]) == 0
    capsys.readouterr()
    assert main(["new", "ITEM", "--title", "Another", "--as", "bob", "--field", "Domain=AUTH"]) == 1
    err = capsys.readouterr().err
    assert "Bob (Developer) may not run /create" in err and "Grant it in catalyst-users" in err
    assert main(["new", "SUB", "--title", "A sub", "--as", "dee", "--field", f"Item={ITEM}"]) == 0  # `*`


def test_a_deactivated_user_signs_nothing(team, capsys):
    assert main(["status", "set", ITEM, "Done", "--as", "eve"]) == 1
    assert "eve is disabled" in capsys.readouterr().err  # disabled in catalyst-users, never deleted


def test_warn_mode_writes_and_says_why(team, capsys):
    pointer = team / "app.catalyst"
    data = json.loads(pointer.read_text(encoding="utf-8"))
    data["role_check"] = "warn"
    pointer.write_text(json.dumps(data), encoding="utf-8")
    assert main(["new", "SUB", "--title", "A sub", "--as", "bob", "--field", f"Item={ITEM}"]) == 0
    assert "may not run /create" in capsys.readouterr().err


# BUG-000050 (rr-META-000011): every writing verb checks the grant of the command its change is for.
VERBS = [
    (["id", "next", "ITEM"], "create"),
    (["rename", ITEM, "--title", "Renamed"], "create"),
    (["edit", ITEM, "--field", "Domain=AUTH"], "create"),
    (["link", ITEM, "Targets", ITEM], "create"),
    (["unlink", ITEM, "Targets", ITEM], "create"),
    (["repair", "derived"], "create"),
    (["approve", ITEM, "--gate", "any"], "status"),
    (["landing", "init", "--policy", "open"], "share"),
    (["propose", ITEM, "--from", "-"], "reconcile"),
    (["reconcile", "RECON-000001-x", "close"], "reconcile"),
]


@pytest.mark.parametrize(("argv", "command"), VERBS, ids=[" ".join(v[0][:2]) for v in VERBS])
def test_each_writing_verb_needs_its_commands_grant(team, capsys, argv, command):
    assert main([*argv, "--as", "cy"]) == 1
    assert f"may not run /{command}" in capsys.readouterr().err


def test_a_verb_of_the_deployments_own_is_checked_by_its_name(team, capsys):
    coc = team / ".criterion" / "CODE-OF-CONDUCT.md"
    coc.write_text(
        coc.read_text(encoding="utf-8").replace("## 5. Next", "- `/link` — cite IDs.\n\n## 5. Next"), encoding="utf-8"
    )
    assert main(["link", ITEM, "Targets", ITEM, "--as", "cy"]) == 1
    assert "may not run /link" in capsys.readouterr().err


def test_warn_mode_lets_an_ungranted_verb_through_with_a_warning(team, capsys):
    pointer = team / "app.catalyst"
    data = json.loads(pointer.read_text(encoding="utf-8"))
    data["role_check"] = "warn"
    pointer.write_text(json.dumps(data), encoding="utf-8")
    assert main(["id", "next", "ITEM", "--as", "cy"]) == 0
    assert "may not run /create" in capsys.readouterr().err


def test_every_full_reconciler_of_the_kernels_roles_may_run_reconcile():
    """BUG-000064: a `full` level is only usable with the `/reconcile` grant (fw-IDENTITY-000008)."""
    from pathlib import Path

    template = Path(__file__).resolve().parents[1] / "framework" / "kernel" / "templates" / "roles.template.json"
    roles = json.loads(template.read_text(encoding="utf-8"))["roles"]
    full = [r for r in roles if r.get("reconciliation") == "full" and r.get("scope") != "criterion"]
    assert {r["id"] for r in full} >= {"tech-lead", "release-manager"}
    for role in full:
        assert {"/reconcile", "*"} & set(role["actions"]), role["id"]


MODULE_ROLES = """id: planner
name: Planner
version: 1.0.0
description: A module with role grants.
grounding_type: rule
roles:
  - id: product-owner
    actions: ["/plan", "/review"]
  - id: scrum-master
    actions: ["/review"]
  - id: catalyst-admin
    actions: ["/plan"]
  - id: nobody
    actions: ["/plan"]
"""


def test_a_module_names_the_commands_it_adds_to_kernel_roles(tmp_path):
    """REQ-000118, fw-IDENTITY-000014: `roles` in module.yaml."""
    from module_loader import load_module

    write(tmp_path / "planner" / "module.yaml", MODULE_ROLES)
    manifest = load_module(module_dir=tmp_path / "planner")
    assert [(g.id, g.actions) for g in manifest.roles][:2] == [
        ("product-owner", ["/plan", "/review"]),
        ("scrum-master", ["/review"]),
    ]


def test_the_roles_document_adds_each_modules_commands_once(tmp_path):
    from types import SimpleNamespace

    from module_loader import load_module

    write(tmp_path / "planner" / "module.yaml", MODULE_ROLES)
    planner = load_module(module_dir=tmp_path / "planner")
    kernel = [
        {"id": "product-owner", "name": "Product Owner", "actions": ["/status", "/review"]},
        {"id": "scrum-master", "name": "Scrum Master", "actions": []},
        {"id": "catalyst-admin", "name": "Admin", "actions": ["*"]},
    ]
    dep = SimpleNamespace(installed=lambda: [planner, planner])
    document, skipped = permissions.roles_document(dep, kernel)
    roles = {r["id"]: r["actions"] for r in document["roles"]}
    assert roles == {
        "product-owner": ["/status", "/review", "/plan"],
        "scrum-master": ["/review"],
        "catalyst-admin": ["*"],
    }
    assert kernel[0]["actions"] == ["/status", "/review"]  # the kernel's template is left as it is
    assert skipped and all("'nobody'" in line for line in skipped)


def test_role_document_prints_the_kernels_roles_and_other_role_verbs_refuse(team, capsys):
    assert main(["role", "document"]) == 0
    roles = {r["id"]: r for r in json.loads(capsys.readouterr().out)["roles"]}
    assert "/reconcile" in roles["tech-lead"]["actions"]
    assert main(["role", "add", "Planner"]) == 1
    assert "catalyst role document" in capsys.readouterr().err
