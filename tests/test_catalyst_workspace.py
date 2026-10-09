"""VS Code workspace criterion (roadmap R3.1b)."""
import json
import sys
from pathlib import Path

import pytest

import project_file as pf
from catalyst import move
from catalyst import workspace as ws
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst.validate import ERROR, validate
from catalyst_fixtures import USERID, make_project

pytestmark = pytest.mark.skipif(sys.version_info < (3, 11), reason="catalyst.toml needs Python 3.11+")
KERNEL = Path(__file__).resolve().parent.parent / "framework" / "kernel"
SHARED = f"ws-SHARED-000001-{USERID}"


def _workspace(tmp_path):
    a = make_project(tmp_path / "a", git=True)
    move.to_home(a, runtime=False)
    b = make_project(tmp_path / "b", git=True)
    pointer = b / "app.catalyst"
    pointer.write_text(pointer.read_text(encoding="utf-8").replace('"app"', '"billing"'), encoding="utf-8")
    move.to_home(b, runtime=False)
    (tmp_path / "docs").mkdir()
    file = tmp_path / "platform.code-workspace"
    file.write_text('{\n  // the platform\n  "folders": [\n    {"path": "a/app"},\n    {"path": "b/app"}, '
                    '/* no catalyst */ {"path": "docs"},\n  ],\n  "settings": {"x": "a // not a comment"},\n}\n',
                    encoding="utf-8")
    return file, a, b


def test_a_workspace_file_with_comments_and_trailing_commas_is_read(tmp_path):
    file, a, b = _workspace(tmp_path)
    name, folders = ws.read(file)
    assert name == "platform" and folders == [a.resolve(), b.resolve(), (tmp_path / "docs").resolve()]
    assert ws.members(file) == [a.resolve(), b.resolve()]


def test_init_creates_the_meta_criterion_and_registers_the_members(tmp_path):
    file, a, b = _workspace(tmp_path)
    root, steps = ws.init(file, KERNEL, "Ada Lovelace", "ada")
    assert root == pf.workspace_criterion("platform") and (root / "rules" / "rules.md").is_file()
    assert json.loads((root / "IAM" / "users" / "users.json").read_text(encoding="utf-8"))["users"][0]["roles"] == ["Admin"]
    for project in (a, b):
        assert pf.read(project / "catalyst.toml")["workspace"] == "platform"
    assert [r["member"] for r in ws.status(file)["folders"]] == [True, True, False]
    with pytest.raises(ws.WorkspaceError, match="already exists"):
        ws.init(file, KERNEL, "Ada Lovelace")


def test_a_member_sees_the_workspace_rules_and_users(tmp_path):
    file, a, _ = _workspace(tmp_path)
    root, _ = ws.init(file, KERNEL, "Ada Lovelace", "ada")
    (root / "rules" / "ws-shared-rules.md").write_text(
        f"# Shared rules\n\n## Contents\n\n### `{SHARED}` Shared logging\n\n**Status:** ✅\n", encoding="utf-8")
    users = root / "IAM" / "users" / "users.json"
    data = json.loads(users.read_text(encoding="utf-8"))
    data["users"].append({"name": "Grace Hopper", "git_username": "grace", "roles": ["Admin"], "active": True,
                          "userid": "Gr4ceHop"})
    users.write_text(json.dumps(data), encoding="utf-8")
    dep = load(a)
    item = pf.home_criterion("app") / "items" / "ITEM-000001-first-item.md"
    item.write_text(item.read_text(encoding="utf-8").replace(f"`br-AUTH-000001-{USERID}`", f"`{SHARED}`"),
                    encoding="utf-8")
    corpus = load_corpus(dep)
    assert SHARED in corpus.rules and corpus.rules[SHARED][0].inherited
    assert corpus.user("grace") is not None
    assert [f for f in validate(dep, corpus) if f.level == ERROR] == []
