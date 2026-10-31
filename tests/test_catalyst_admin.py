"""Administration verbs (roadmap R2 W3): freeze/unfreeze, definitions; `user` and `role` only refuse."""

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
    """People and roles are catalyst-users' (design 29, fw-IDENTITY-000002): `user` and `role` refuse, and say where
    to make the change; the other administration verbs still run."""
    project, _, _ = _dep(tmp_path)
    run = lambda *a: main(["--project", str(project), *a])
    for argv in (
        ("role", "add", "QA", "--action", "/create-test", "--reconciliation", "none"),
        ("user", "add", "Grace Hopper", "QA", "--json"),
        ("user", "remove", USER, "--as", USER),
    ):
        assert run(*argv) == 1
        assert "catalyst-users" in capsys.readouterr().err
    assert run("freeze", "items", "--as", USER) == 0
