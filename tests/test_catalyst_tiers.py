"""Ceremony tiers come from the active module (rr-META-006, REQ-000023):
`module.yaml` `tiers:`, else chore, fix and feature."""

from __future__ import annotations

import pytest

from catalyst import journal as j, tiers
from catalyst.__main__ import main
from catalyst.deployment import load
from catalyst.trace import check_message
from catalyst_fixtures import USERID, make_project, write

ITEM = f"ITEM-000001-{USERID}"
RULE = f"br-AUTH-000001-{USERID}"
MODULE_TIERS = """
tiers:
  - id: clerical
    artifact: none
    commit: "clerical:"
  - id: conforming
    artifact: ITEM
  - id: position
    artifact: ITEM
"""


def _with_tiers(project):
    mod = project / ".criterion" / "modules" / "example-process" / "module.yaml"
    write(mod, mod.read_text(encoding="utf-8") + MODULE_TIERS)


def _append(project, tier):
    item = project / ".criterion" / "items" / "ITEM-000001-first-item.md"
    item.write_text(item.read_text(encoding="utf-8") + f"\n{tier}\n", encoding="utf-8")
    return j.append(
        load(project),
        j.AppendRequest(
            command="/x",
            action="update",
            artifact=ITEM,
            targets=[RULE],
            intent=[f"a {tier} change"],
            files=[str(item)],
            actor="ada",
            tier=tier,
        ),
    )


def test_without_declared_tiers_the_default_three_apply(tmp_path):
    project = make_project(tmp_path, git=True)
    dep = load(project)
    assert tiers.ids(dep) == ["chore", "fix", "feature"]
    assert tiers.commit_prefixes(dep) == ("chore:",)
    assert _append(project, "fix")["tier"] == "fix"
    with pytest.raises(j.JournalError, match="tier 'hotfix' is not one of chore, fix, feature"):
        _append(project, "hotfix")


def test_a_module_declares_its_own_tiers(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path, git=True)
    _with_tiers(project)
    dep = load(project)
    assert tiers.ids(dep) == ["clerical", "conforming", "position"]
    assert [t.needs_artifact for t in tiers.tiers_for(dep)] == [False, True, True]
    assert _append(project, "position")["tier"] == "position"
    with pytest.raises(j.JournalError, match="tier 'chore' is not one of clerical, conforming, position"):
        _append(project, "chore")
    monkeypatch.chdir(project)
    capsys.readouterr()
    fields = ["--field", f"Targets={RULE}", "--field", "Domain=AUTH"]
    assert main(["new", "ITEM", "--title", "Second", "--as", "ada", *fields, "--tier", "chore"]) == 1
    assert "not one of clerical" in capsys.readouterr().err
    assert main(["status", "set", ITEM, "Done", "--as", "ada", "--tier", "position"]) == 0


def test_trace_accepts_only_the_no_artifact_tiers_prefix(tmp_path):
    project = make_project(tmp_path, git=True)
    assert check_message("chore: tidy", None, tiers.commit_prefixes(load(project))) is None
    _with_tiers(project)
    prefixes = tiers.commit_prefixes(load(project))
    assert prefixes == ("clerical:",)
    assert check_message("clerical(R1): tidy", None, prefixes) is None
    reason = check_message("chore: tidy", None, prefixes)
    assert reason is not None and "`clerical:`" in reason
