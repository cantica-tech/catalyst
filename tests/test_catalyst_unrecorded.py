"""Changes made outside catalyst: detection, severity, the hook, trace,
check, report, and adoption (roadmap manual-changes, RM-000030..032)."""
from __future__ import annotations

import json
import subprocess

import pytest

from catalyst import journal as j
from catalyst import unrecorded as u
from catalyst.__main__ import main
from catalyst.check import run as check_run
from catalyst.deployment import load
from catalyst_fixtures import USERID, make_project, write


def git(repo, *args) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout.strip()


def set_pointer(project, **fields):
    p = project / "app.catalyst"
    data = json.loads(p.read_text(encoding="utf-8"))
    data.update(fields)
    p.write_text(json.dumps(data), encoding="utf-8")


def manual_commit(project, path="src/app.py", text="print('hi')\n", msg="Hand edit ITEM-000001"):
    write(project / path, text)
    git(project, "add", "-A")
    git(project, "commit", "-qm", msg)
    return git(project, "rev-parse", "HEAD")


def journaled_commit(project, path="src/lib.py", text="x = 1\n"):
    dep = load(project)
    write(project / path, text)
    j.append(dep, j.AppendRequest(command="/status", action="update", artifact=f"ITEM-000001-{USERID}",
                                  targets=[], intent=["agent work"], files=[path], actor="ada"))
    git(project, "add", path)
    git(project, "commit", "-qm", f"ITEM-000001: {path}")
    return git(project, "rev-parse", "HEAD")


def fresh_project(tmp_path, monkeypatch):
    """A project whose committed, journaled pointer sets the baseline."""
    p = make_project(tmp_path, git=True)
    set_pointer(p, format="1.0-rc")
    git(p, "commit", "-qam", "chore: format")
    monkeypatch.chdir(p)
    set_pointer(p, journal_since=git(p, "rev-parse", "HEAD"))
    # as a migration does: the pointer edit is journaled, then committed
    j.append(load(p), j.AppendRequest(command="/sync-framework", action="sync", artifact="baseline",
                                      targets=[], intent=["declare the baseline"], files=["app.catalyst"],
                                      actor="ada"))
    git(p, "commit", "-qam", "chore: declare the baseline")
    return p


@pytest.fixture
def proj(tmp_path, monkeypatch):
    return fresh_project(tmp_path, monkeypatch)


def test_level_follows_the_format_and_the_opt_in(proj):
    assert u.level(load(proj)) == "warning"                 # 1.0-rc: the beta
    set_pointer(proj, format="1.0")
    assert u.level(load(proj)) == "error"                   # after the beta
    set_pointer(proj, format="1.0-rc", strict_journal=True)
    assert u.level(load(proj)) == "error"                   # opted in early
    set_pointer(proj, format=None, strict_journal=False)
    assert u.level(load(proj)) == "warning"


def test_manual_commit_is_detected_and_a_journaled_one_is_not(proj):
    journaled_commit(proj)
    sha = manual_commit(proj)
    found = u.since_baseline(load(proj))
    assert [c.sha for c in found] == [sha]
    assert [p for p, _, _ in found[0].changes] == ["src/app.py"]


def test_history_before_the_baseline_and_merges_are_not_checked(proj):
    manual_commit(proj)
    set_pointer(proj, journal_since=git(proj, "rev-parse", "HEAD"))
    assert u.since_baseline(load(proj)) == []
    git(proj, "checkout", "-qb", "side")
    journaled_commit(proj, "src/side.py")
    git(proj, "checkout", "-q", "-")
    journaled_commit(proj, "src/main.py")
    git(proj, "merge", "-q", "--no-edit", "side")
    assert u.since_baseline(load(proj)) == []


def test_no_baseline_means_history_is_not_checked(proj):
    manual_commit(proj)
    set_pointer(proj, journal_since=None)
    data = json.loads((proj / "app.catalyst").read_text(encoding="utf-8"))
    del data["journal_since"]
    (proj / "app.catalyst").write_text(json.dumps(data), encoding="utf-8")
    dep = load(proj)
    assert u.baseline(dep) is None and u.since_baseline(dep) == []
    assert any("declares no `journal_since`" in w for w in check_run(dep).warnings)


def test_empty_baseline_checks_the_whole_history(proj):
    set_pointer(proj, journal_since="")
    assert u.since_baseline(load(proj))           # the fixture's own commits were never journaled


def test_check_warns_in_the_beta_and_errors_after(proj):
    manual_commit(proj)
    report = check_run(load(proj))
    assert any("unrecorded-change" in w for w in report.warnings) and not any(
        "unrecorded-change" in e for e in report.errors)
    set_pointer(proj, format="1.0")
    # 1.0 is not a supported format yet: the format error comes first, the change is an error too
    report = check_run(load(proj))
    assert any("unrecorded-change" in e for e in report.errors)


def test_deletions_and_gitlinks(proj):
    journaled_commit(proj, "src/gone.py")
    (proj / "src" / "gone.py").unlink()
    git(proj, "commit", "-qam", "chore: remove by hand")
    found = u.since_baseline(load(proj))
    assert [(p, a) for p, _, a in found[0].changes] == [("src/gone.py", None)]


def test_adopt_records_the_commit_with_its_author(proj, capsys):
    sha = manual_commit(proj)
    assert main(["journal", "adopt", sha[:10], "--intent", "hand-written greeting", "--tier", "chore"]) == 0
    assert "adopted" in capsys.readouterr().out
    entry = [e for _, e, _ in j.read(load(proj)) if e][-1]
    assert entry["origin"] == "manual" and entry["commit"] == sha and entry["actor"] == "Ada Lovelace"
    assert entry["files"][0]["path"] == "src/app.py" and entry["files"][0]["before"] is None
    assert entry["tier"] == "chore" and entry["command"] == "/adopt"
    dep = load(proj)
    assert u.since_baseline(dep) == []
    assert [i for i in j.verify(dep) if i.level == "error"] == []
    assert main(["journal", "adopt", sha[:10], "--intent", "again"]) == 0
    assert "nothing to adopt" in capsys.readouterr().out


def test_adopt_a_range_in_order_keeps_the_chain(proj):
    first = manual_commit(proj, text="one\n", msg="chore: one")
    manual_commit(proj, text="two\n", msg="chore: two")
    entries = u.adopt(load(proj), [f"{first}~1..HEAD"], ["hand edits"])
    assert len(entries) == 2 and entries[1]["files"][0]["before"] == entries[0]["files"][0]["after"]
    dep = load(proj)
    assert [i for i in j.verify(dep) if i.code == "chain"] == []
    with pytest.raises(j.JournalError, match="intent"):
        u.adopt(dep, ["HEAD"], [])


def test_commit_msg_hook_warns_in_the_beta_and_refuses_after(proj, capsys):
    write(proj / "src" / "hand.py", "x\n")
    git(proj, "add", "src/hand.py")
    msg = proj / "MSG"
    msg.write_text("chore: by hand\n", encoding="utf-8")
    assert main(["hook", "commit-msg", str(msg)]) == 0
    assert "warning" in capsys.readouterr().err
    set_pointer(proj, strict_journal=True)
    assert main(["hook", "commit-msg", str(msg)]) == 1
    assert "not recorded in the journal" in capsys.readouterr().err
    j.append(load(proj), j.AppendRequest(command="/status", action="create", artifact="x", targets=[],
                                         intent=["journaled"], files=["src/hand.py"], actor="ada"))
    assert main(["hook", "commit-msg", str(msg)]) == 0


def test_trace_reports_unrecorded_changes(proj, capsys):
    manual_commit(proj)
    assert main(["trace", "HEAD~1..HEAD"]) == 0                  # a warning in the beta
    out = capsys.readouterr().out
    assert "WARNING unrecorded-change" in out and "1 with unrecorded changes" in out
    set_pointer(proj, strict_journal=True)
    assert main(["trace", "HEAD~1..HEAD"]) == 1
    assert "ERROR   unrecorded-change" in capsys.readouterr().out


def test_unrecorded_command_and_report(proj, capsys):
    sha = manual_commit(proj)
    assert main(["unrecorded", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed[0]["commit"] == sha and listed[0]["files"][0]["path"] == "src/app.py"
    from catalyst.report import build, render
    r = build(load(proj))
    assert r["unrecorded_commits"] == 1 and r["adopted_commits"] == 0
    assert "1 unrecorded, 0 adopted" in render(r)
    set_pointer(proj, strict_journal=True)
    assert main(["unrecorded"]) == 1


def test_parse_raw_skips_the_working_copy_and_mode_only_changes():
    a, b = "a" * 40, "b" * 40
    tokens = [f":100644 100644 {a} {b} M", "src/x.py",
              f":160000 160000 {a} {b} M", ".criterion",
              f":100644 100644 {a} {b} M", ".criterion/rules/x.md",
              f":100644 100755 {a} {a} M", "run.sh",
              f":000000 100644 {'0' * 40} {b} A", "new.py"]
    assert u._parse_raw(tokens) == [("src/x.py", a, b), ("new.py", None, b)]


def test_a_hand_commit_to_a_journaled_file_is_one_beta_warning_not_an_error(proj):
    journaled_commit(proj, "src/lib.py", "x = 1\n")
    manual_commit(proj, "src/lib.py", "x = 2\n", "chore: tweak by hand")
    report = check_run(load(proj))
    assert [e for e in report.errors if not e.startswith("structure:")] == []
    assert sum("unrecorded-change" in w and "src/lib.py" in w for w in report.warnings) == 1
    write(proj / "src" / "lib.py", "x = 3\n")          # edited again, not committed: work in progress
    assert any("unjournaled" in e for e in check_run(load(proj)).errors)


# --- regressions from the review (2026-09-28) -------------------------------
import datetime
import os


def at(epoch: int) -> str:
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def commit_at(project, epoch, msg, *paths):
    git(project, "add", *(paths or ["-A"]))
    env = dict(os.environ, GIT_COMMITTER_DATE=f"@{epoch} +0000", GIT_AUTHOR_DATE=f"@{epoch} +0000")
    subprocess.run(["git", "-C", str(project), "commit", "-qm", msg], check=True, env=env,
                   capture_output=True)
    return git(project, "rev-parse", "HEAD")


def journal_at(project, epoch, path):
    j.append(load(project), j.AppendRequest(command="/status", action="update", artifact="x", targets=[],
                                            intent=["agent work"], files=[path], actor="ada",
                                            timestamp=at(epoch)))


def journal_errors(project):
    return [i for i in j.verify(load(project)) if i.level == "error" and not i.legacy]


T = 2_000_000_000


def test_adopt_continues_the_chain_from_an_uncommitted_journaled_state(proj):
    write(proj / "f.txt", "A\n")
    journal_at(proj, T, "f.txt")                     # journaled, never committed
    write(proj / "f.txt", "B\n")
    sha = commit_at(proj, T + 10, "chore: by hand", "f.txt")
    u.adopt(load(proj), [sha], ["hand edit"])
    assert journal_errors(proj) == [] and u.since_baseline(load(proj)) == []


def test_adopting_an_old_commit_after_newer_journal_work_is_history_only(proj):
    write(proj / "f.txt", "B\n")
    old = commit_at(proj, T, "chore: by hand", "f.txt")
    write(proj / "f.txt", "C\n")
    journal_at(proj, T + 10, "f.txt")
    commit_at(proj, T + 20, "chore: agent", "f.txt")
    entries = u.adopt(load(proj), [old], ["hand edit"])
    assert entries[0]["files"][0]["superseded"] is True
    assert journal_errors(proj) == [] and u.since_baseline(load(proj)) == []
    assert j.last_after(load(proj))["f.txt"] != entries[0]["files"][0]["after"]


def test_a_baseline_missing_from_the_clone_warns_instead_of_crashing(proj, capsys):
    set_pointer(proj, journal_since="1" * 40)
    dep = load(proj)
    assert u.baseline_missing(dep) and u.since_baseline(dep) == []
    assert any("not in this clone" in w for w in check_run(dep).warnings)
    assert main(["trace", "HEAD~1..HEAD"]) == 0
    assert "not in this clone" in capsys.readouterr().out
    assert main(["unrecorded"]) == 1


def test_a_hand_revert_to_an_older_journaled_state_is_detected_and_adoptable(proj):
    write(proj / "f.txt", "A\n")
    journal_at(proj, T, "f.txt")
    commit_at(proj, T + 1, "chore: a", "f.txt")
    write(proj / "f.txt", "B\n")
    journal_at(proj, T + 2, "f.txt")
    commit_at(proj, T + 3, "chore: b", "f.txt")
    write(proj / "f.txt", "A\n")
    revert = commit_at(proj, T + 4, "chore: back to a", "f.txt")
    assert [c.sha for c in u.since_baseline(load(proj))] == [revert]
    u.adopt(load(proj), [revert], ["reverted by hand"])
    assert journal_errors(proj) == [] and u.since_baseline(load(proj)) == []


def test_a_path_with_a_space_is_reported_once(proj):
    write(proj / "a b.txt", "1\n")
    journal_at(proj, T, "a b.txt")
    commit_at(proj, T + 1, "chore: a b", "a b.txt")
    write(proj / "a b.txt", "2\n")
    commit_at(proj, T + 2, "chore: by hand", "a b.txt")
    report = check_run(load(proj))
    assert not any("unjournaled" in e for e in report.errors)
    assert sum("a b.txt" in w for w in report.warnings) == 1


def test_a_project_in_a_subdirectory_of_its_repository(tmp_path, monkeypatch):
    from catalyst_fixtures import git_init
    mono = tmp_path / "mono"
    mono.mkdir()
    project = make_project(mono)                       # mono/app, not a repository of its own
    git_init(project / ".criterion")
    subprocess.run(["git", "init", "-q", str(mono)], check=True)
    for k, v in (("user.name", "Ada Lovelace"), ("user.email", "ada@example.com")):
        git(mono, "config", k, v)
    write(mono / ".gitignore", "/app/.criterion\n")
    git(mono, "add", "-A")
    git(mono, "commit", "-qm", "init")
    monkeypatch.chdir(project)
    set_pointer(project, format="1.0-rc", journal_since=git(mono, "rev-parse", "HEAD"))
    journal_at(project, T, "app.catalyst")
    write(project / "src" / "a.py", "a\n")
    journal_at(project, T, "src/a.py")
    commit_at(mono, T + 1, "chore: work")
    assert u.since_baseline(load(project)) == []
    write(project / "src" / "a.py", "b\n")
    commit_at(mono, T + 2, "chore: by hand")
    assert [[p for p, _, _ in c.changes] for c in u.since_baseline(load(project))] == [["src/a.py"]]
