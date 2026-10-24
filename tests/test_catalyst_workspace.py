"""VS Code workspace criterion (roadmap R3.1b)."""

import json
import sys
from pathlib import Path

import pytest

import project_file as pf
import schema_check
from catalyst import move, workspace as ws
from catalyst.__main__ import main
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
    file.write_text(
        '{\n  // the platform\n  "folders": [\n    {"path": "a/app"},\n    {"path": "b/app"}, '
        '/* no catalyst */ {"path": "docs"},\n  ],\n  "settings": {"x": "a // not a comment"},\n}\n',
        encoding="utf-8",
    )
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
    # people are catalyst-users' (design 29): the pointer and the first signer, no users.json
    pointer = json.loads((root / "IAM" / "identity.json").read_text(encoding="utf-8"))
    assert pointer["provider"] == "static" and pointer["people"][0]["name"] == "Ada Lovelace"
    assert json.loads((root / "IAM" / "signers.jsonl").read_text(encoding="utf-8").splitlines()[0])["username"] == "ada"
    assert not (root / "IAM" / "users" / "users.json").exists()
    for project in (a, b):
        assert pf.read(project / "catalyst.toml")["workspace"] == "platform"
    assert [r["member"] for r in ws.status(file)["folders"]] == [True, True, False]
    with pytest.raises(ws.WorkspaceError, match="already exists"):
        ws.init(file, KERNEL, "Ada Lovelace")


def test_a_member_sees_the_workspace_rules_and_pointer(tmp_path):
    """A member inherits the workspace's rules, and its pointer to catalyst-users when it has none (design 29)."""
    from catalyst import provider

    file, a, _ = _workspace(tmp_path)
    root, _ = ws.init(file, KERNEL, "Ada Lovelace", "ada")
    (root / "rules" / "ws-shared-rules.md").write_text(
        f"# Shared rules\n\n## Contents\n\n### `{SHARED}` Shared logging\n\n**Status:** ✅\n", encoding="utf-8"
    )
    from conftest import legacy_signers

    member = pf.home_criterion("app")
    # the member keeps its signers ledger (who signed its IDs), and points nowhere itself
    (member / "IAM" / "signers.jsonl").write_text("".join(json.dumps(e) + "\n" for e in legacy_signers(member)))
    (member / "IAM" / "users" / "users.json").unlink()
    dep = load(a)
    assert provider.pointer(dep) == json.loads((root / "IAM" / "identity.json").read_text(encoding="utf-8"))
    item = pf.home_criterion("app") / "items" / "ITEM-000001-first-item.md"
    item.write_text(
        item.read_text(encoding="utf-8").replace(f"`br-AUTH-000001-{USERID}`", f"`{SHARED}`"), encoding="utf-8"
    )
    corpus = load_corpus(dep)
    assert SHARED in corpus.rules and corpus.rules[SHARED][0].inherited
    assert [f for f in validate(dep, corpus) if f.level == ERROR] == []


def test_a_member_inherits_the_workspace_roles_and_cannot_propose_an_inherited_rule(tmp_path):
    """R3.1b audit (BUG-000021): roles were not inherited; proposing an inherited rule crashed."""
    from catalyst import proposals
    from catalyst.corpus import roles
    from catalyst.edit import reconciliation_level
    from catalyst.views import list_items

    file, a, _ = _workspace(tmp_path)
    root, _ = ws.init(file, KERNEL, "Ada Lovelace", "ada")
    (root / "rules" / "ws-shared-rules.md").write_text(
        f"# Shared rules\n\n## Contents\n\n### `{SHARED}` Shared logging\n\n**Status:** ✅\n", encoding="utf-8"
    )
    # the role catalogue is the roles template, for display (fw-IDENTITY-000010): a member inherits the workspace's
    template = root / "IAM" / "roles" / "templates" / "TEMPLATE-ROLES-v1.json"
    data = json.loads(template.read_text(encoding="utf-8"))
    data["roles"].append(
        {"name": "Platform Reviewer", "id": "platform-reviewer", "actions": [], "reconciliation": "full"}
    )
    template.write_text(json.dumps(data), encoding="utf-8")

    dep = load(a)
    corpus = load_corpus(dep)
    names = [r["name"] for r in roles(dep)]
    assert "Platform Reviewer" in names and len(names) == len(set(names))  # the member's own win on a clash
    assert "Platform Reviewer" in [r["name"] for r in list_items(dep, corpus, "role", [])]
    # what a person may do is catalyst-users' grants, not a role's name (fw-IDENTITY-000008)
    grace = {
        "name": "Grace Hopper",
        "git_username": "grace",
        "roles": ["Platform Reviewer"],
        "userid": "Gr4ceHop",
        "grants": ["cmd:*", "reconcile:full"],
        "reconciliation": "full",
    }
    assert reconciliation_level(dep, grace) == ("full", "catalyst-users grants")
    with pytest.raises(proposals.ProposalError, match="inherited from the workspace criterion"):
        proposals.propose(dep, corpus, SHARED, "# changed\n", grace)


def test_status_prints_the_folders_and_their_projects(tmp_path, capsys):
    file, _, _ = _workspace(tmp_path)
    assert main(["workspace", "status", str(file), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["workspace"] == "platform" and out["criterion"] is None
    assert [(r["project"], r["member"]) for r in out["folders"]] == [("app", False), ("billing", False), (None, False)]
    assert schema_check.problems(out, schema_check.load("workspace-status")) == []
