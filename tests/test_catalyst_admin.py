"""Administration verbs (roadmap R2 W3): users, roles, freeze/unfreeze, definitions."""
import json

import pytest

from catalyst import admin
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst_fixtures import USER, USERID, make_project, write

ITEM = f"ITEM-000001-{USERID}"


def _dep(tmp_path):
    project = make_project(tmp_path, git=True)
    dep = load(project)
    return project, dep, load_corpus(dep).users[0]


def _users(project):
    return json.loads((project / ".criterion" / "IAM" / "users" / "users.json").read_text(encoding="utf-8"))["users"]


def _last_entry(project):
    lines = (project / ".criterion" / "development" / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    return json.loads(lines[-1])


def test_roles_then_users_with_every_refusal(tmp_path):
    project, dep, me = _dep(tmp_path)
    role = admin.role_add(dep, "Developer", ["/create-item"], me, [])
    assert role["reconciliation"] == "propose"                       # never silently full
    assert _last_entry(project)["command"] == "/role-add"
    with pytest.raises(admin.AdminError, match="role modify"):
        admin.role_add(dep, "Developer", [], me, [])
    with pytest.raises(admin.AdminError, match="role add"):
        admin.user_add(dep, "Grace Hopper", "Tester", me, [])
    grace = admin.user_add(dep, "Grace Hopper", "Developer", me, [], git_username="grace")
    assert grace["active"] and len(grace["userid"]) == len(USERID) and grace["userid"] != USERID
    with pytest.raises(admin.AdminError, match="already registered"):
        admin.user_add(dep, "grace", "Developer", me, [])
    with pytest.raises(admin.AdminError, match="already has role"):
        admin.user_assign_role(dep, "grace", "Developer", me, [])
    for field in ("roles", "name", "userid"):
        with pytest.raises(admin.AdminError):
            admin.user_modify(dep, "grace", field, "x", me, [])
    admin.user_modify(dep, "grace", "notes", "on loan", me, [])
    admin.user_remove(dep, "grace", me, [])
    assert [u["active"] for u in _users(project)] == [True, False]   # kept, deactivated
    with pytest.raises(admin.AdminError, match="only active user"):
        admin.user_remove(dep, USER, me, [])
    admin.role_modify(dep, "Developer", ["/status"], me, [])
    assert _last_entry(project)["command"] == "/role-modify"


def test_freeze_resolves_ids_types_and_paths_and_unfreezes(tmp_path):
    project, dep, me = _dep(tmp_path)
    assert admin.freeze(dep, ITEM, me, []) == "items/ITEM-000001-first-item.md"
    assert admin.freeze(dep, "subs", me, []) == "subs"
    with pytest.raises(admin.AdminError, match="already frozen"):
        admin.freeze(dep, ITEM, me, [])
    admin.freeze(dep, ITEM, me, [], unfreeze=True)
    assert (project / ".criterion" / ".frozen").read_text(encoding="utf-8") == "subs\n"
    with pytest.raises(admin.AdminError, match="not frozen"):
        admin.freeze(dep, ITEM, me, [], unfreeze=True)
    with pytest.raises(admin.AdminError, match="not an artifact"):
        admin.freeze(dep, "nothing-here", me, [])


def test_definition_migrate_moves_only_to_an_existing_version(tmp_path):
    project, dep, me = _dep(tmp_path)
    kernel = tmp_path / "kernel"
    write(kernel / "definitions" / "role" / "DEFINITION-ROLE-v1.md", "| **Version** | 1 |\n")
    write(kernel / "definitions" / "role" / "DEFINITION-ROLE-v2.md", "| **Version** | 2 |\n")
    write(project / ".criterion" / "definitions" / "role.md", "| **Version** | 1 |\n")
    assert admin.migrate_definition(dep, "role", 2, kernel, me, []) == ("role", 1)
    assert "| 2 |" in (project / ".criterion" / "definitions" / "role.md").read_text(encoding="utf-8")
    with pytest.raises(admin.AdminError, match="already v2"):
        admin.migrate_definition(dep, "role", 2, kernel, me, [])
    with pytest.raises(admin.AdminError, match="highest is v2"):
        admin.migrate_definition(dep, "role", 3, kernel, me, [])
    with pytest.raises(admin.AdminError, match="not an entity type"):
        admin.migrate_definition(dep, "widget", 1, kernel, me, [])


def test_the_cli_runs_them(tmp_path, capsys):
    project, _, _ = _dep(tmp_path)
    run = lambda *a: main(["--project", str(project), *a])
    assert run("role", "add", "QA", "--action", "/create-test", "--reconciliation", "none") == 0
    assert run("user", "add", "Grace Hopper", "QA", "--json") == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["roles"] == ["QA"]
    assert run("freeze", "items") == 1                    # two active users: who signs?
    assert "--as" in capsys.readouterr().err
    assert run("freeze", "items", "--as", USER) == 0
    assert run("user", "remove", USER, "--as", USER) == 0
    assert run("user", "remove", "Grace Hopper", "--as", "Grace Hopper") == 1
    assert "only active user" in capsys.readouterr().err
