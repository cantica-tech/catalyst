from __future__ import annotations

import subprocess

import pytest

from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst.trace import check_message, install_hook, trace
from catalyst_fixtures import USERID, make_project, write


@pytest.fixture
def project(tmp_path, monkeypatch):
    p = make_project(tmp_path, git=True)
    monkeypatch.chdir(p)
    return p


def commit(repo, message, name="f.txt"):
    write(repo / name, message)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", message], check=True)


def test_message_rules(project):
    corpus = load_corpus(load(project))
    assert check_message(f"Fix login (ITEM-000001-{USERID})", corpus) is None       # full ID
    assert check_message("Fix login\n\nITEM-000001", corpus) is None                 # short ID
    assert check_message(f"Tighten br-AUTH-000001-{USERID}", corpus) is None         # a rule
    assert check_message("chore: reformat", corpus) is None
    assert check_message("chore(docs): typo", corpus) is None
    assert "no artifact" in check_message("Fix things", corpus)
    assert "resolve to nothing" in check_message("Fix ITEM-000099", corpus)
    assert check_message("# only a comment\n", corpus) == "empty message"


def test_pattern_only_mode():
    assert check_message("Deliver REQ-000013", None) is None
    assert check_message("Deliver roadmap item RM-000027-yCNjAMXO", None) is None
    assert check_message("Bump version to 0.30.0", None) is not None


def test_trace_a_range_skips_merges(project):
    commit(project, "chore: first")
    base = subprocess.check_output(["git", "-C", str(project), "rev-parse", "HEAD"], text=True).strip()
    commit(project, f"Work on ITEM-000001-{USERID}", "a.txt")
    commit(project, "Untraced change", "b.txt")
    checked, failures = trace(project, f"{base}..HEAD", load_corpus(load(project)))
    assert checked == 2 and [f.subject for f in failures] == ["Untraced change"]


def test_commit_msg_hook_and_install(project, capsys):
    msg = project / "MSG"
    msg.write_text("Untraced\n")
    assert main(["hook", "commit-msg", str(msg)]) == 1
    assert "commit refused" in capsys.readouterr().err
    msg.write_text("chore: fine\n")
    assert main(["hook", "commit-msg", str(msg)]) == 0
    hook = install_hook(project)
    text = hook.read_text()
    # the routing hook (fw-STRUCTURE-000017): each owning deployment's CLI checks the message
    assert hook.name == "commit-msg" and '"commit-msg", "--route"' in text
    assert "catalyst hook install" in text and text.startswith("#!/usr/bin/env python3")
    install_hook(project)                                     # idempotent
    hook.write_text("#!/bin/sh\necho mine\n")
    with pytest.raises(ValueError, match="not written by catalyst"):
        install_hook(project)


def test_trace_cli(project, capsys):
    commit(project, "chore: a")
    commit(project, "Untraced", "c.txt")
    assert main(["trace", "HEAD~1..HEAD"]) == 1
    assert main(["trace", "HEAD~2..HEAD~1"]) == 0


def test_report_counts_actors_tiers_and_traced_commits(project):
    from catalyst import journal as j
    from catalyst.report import build, render
    dep = load(project)
    write(project / "src" / "a.py", "a\n")
    j.append(dep, j.AppendRequest(command="/create-item", action="create", artifact="x", targets=[],
                                  intent=["x"], files=["src/a.py"], actor="ada", tier="feature"))
    commit(project, f"Work on ITEM-000001-{USERID}", "b.txt")
    r = build(dep)
    assert r["actors"] == {"ada": 1} and r["tiers"] == {"feature": 1}
    assert r["commits"] == 2 and r["commits_traced"] == 1          # init commit is untraced
    assert "commits traced: 1/2" in render(r)


def test_format_is_declared_and_checked(project):
    import json
    from catalyst.check import run as run_checks
    pointer = project / "app.catalyst"
    assert any("declares no `format`" in w for w in run_checks(load(project)).warnings)
    data = json.loads(pointer.read_text())
    data["format"] = "9.0"
    pointer.write_text(json.dumps(data))
    assert any("format 9.0" in e for e in run_checks(load(project)).errors)
    data["format"] = "1.0-rc"
    pointer.write_text(json.dumps(data))
    report = run_checks(load(project))
    assert not any("format" in m for m in report.errors + report.warnings)


def test_paths_and_versions_are_not_ids(project):
    corpus = load_corpus(load(project))
    assert "no artifact" in check_message("Merge branch 'x' of /tmp/claude-501/app", corpus)
    assert "no artifact" in check_message("Bump to v0-123", corpus)


def test_ambiguous_short_id_must_be_written_in_full(project):
    from catalyst.corpus import load_corpus as lc
    dep = load(project)
    users = project / ".criterion" / "IAM" / "users" / "users.json"
    import json
    data = json.loads(users.read_text())
    data["users"].append({"name": "Bob", "active": True, "userid": "Bb4xR9pQ"})
    users.write_text(json.dumps(data))
    other = (project / ".criterion" / "items" / "ITEM-000001-first-item.md").read_text().replace(USERID, "Bb4xR9pQ")
    write(project / ".criterion" / "items" / "ITEM-000001-bobs-item.md", other)
    reason = check_message("Fix ITEM-000001", lc(dep))
    assert reason and "ambiguous" in reason
    assert check_message(f"Fix ITEM-000001-{USERID}", lc(dep)) is None


def test_commit_msg_hook_lets_merges_through(project):
    git_dir = project / ".git"
    (git_dir / "MERGE_HEAD").write_text("0" * 40 + "\n")
    msg = project / "MSG"
    msg.write_text("Merge branch 'main' of /some/path\n")
    assert main(["hook", "commit-msg", str(msg)]) == 0
