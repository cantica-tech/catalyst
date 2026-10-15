"""`catalyst check`: uncommitted product changes are judged by what the
deployment governs (scope.py) and ignore operating-system noise."""

from __future__ import annotations

import json
import subprocess

from catalyst.__main__ import main
from catalyst.check import unrecorded_changes
from catalyst.deployment import load
from catalyst.scope import clear_cache
from catalyst_fixtures import git_init, make_project, write


def _changes(project):
    clear_cache()
    return unrecorded_changes(load(project))


def test_catalystignore_nested_deployments_and_noise_are_not_reported(tmp_path, monkeypatch):
    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)
    write(project / "src" / "new.py", "x = 1\n")
    write(project / "vendor" / "x.txt", "v\n")
    write(project / ".catalystignore", "vendor\n")
    write(project / "inner" / "inner.catalyst", json.dumps({"project_name": "inner"}))
    write(project / "inner" / "code.py", "y = 2\n")
    write(project / ".DS_Store", "\0")
    write(project / "src" / ".DS_Store", "\0")
    write(project / "src" / "Thumbs.db", "\0")
    assert _changes(project) == [".catalystignore", "src/new.py"]


def test_project_in_a_subdirectory_reports_paths_from_the_project(tmp_path, monkeypatch):
    mono = tmp_path / "mono"
    project = make_project(mono)  # mono/app, working copy mono/app/.criterion
    write(mono / "README.md", "mono\n")
    write(mono / ".gitignore", "/app/.criterion\n")
    git_init(project / ".criterion")
    git_init(mono)
    monkeypatch.chdir(project)
    write(mono / "other" / "file.txt", "outside the deployment\n")
    write(project / "src" / "new.py", "x = 1\n")
    assert _changes(project) == ["src/new.py"]


def test_a_rename_reports_the_new_path_only(tmp_path, monkeypatch):
    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)
    write(project / "src" / "longname_file.txt", "content\n")
    subprocess.run(["git", "add", "-A"], cwd=project, check=True)
    subprocess.run(["git", "commit", "-qm", "add"], cwd=project, check=True)
    subprocess.run(["git", "mv", "src/longname_file.txt", "src/renamed.txt"], cwd=project, check=True)
    assert _changes(project) == ["src/renamed.txt"]


def _stop(project, monkeypatch, hook_input="{}"):
    import io

    from catalyst.__main__ import main

    monkeypatch.setattr("sys.stdin", io.StringIO(hook_input))
    return main(["--project", str(project), "hook", "stop"])


def test_stop_hook_fails_closed_on_a_corrupt_journal(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)
    (project / ".criterion" / "development" / "journal.jsonl").write_bytes(b'{"a": "\xff"}\n')
    assert _stop(project, monkeypatch) == 2
    err = capsys.readouterr().err
    assert "UnicodeDecodeError" in err
    # a stop already blocked once is let through, still reporting why
    assert _stop(project, monkeypatch, '{"stop_hook_active": true}') == 0
    assert "UnicodeDecodeError" in capsys.readouterr().err


def test_stop_hook_fails_closed_when_the_deployment_cannot_be_read(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)

    def broken(args):
        raise RuntimeError("unreadable pointer")

    monkeypatch.setattr("catalyst.__main__.open_deployment", broken)
    assert _stop(project, monkeypatch) == 2
    err = capsys.readouterr().err
    assert "catalyst hook stop" in err and "unreadable pointer" in err


def test_stop_and_start_hooks_speak_each_agents_format(tmp_path, monkeypatch, capsys):
    import io

    from catalyst.__main__ import main

    project = make_project(tmp_path, git=True)
    (project / ".criterion" / "development" / "journal.jsonl").write_bytes(b'{"a": "\xff"}\n')
    write(project / ".criterion" / "INVARIANTS.md", "# Invariants\n\n- INV-1\n")
    monkeypatch.chdir(tmp_path)  # the project comes from the hook's input
    named = json.dumps({"cwd": str(project)})
    for fmt, decision in (("json", "block"), ("gemini", "deny")):
        monkeypatch.setattr("sys.stdin", io.StringIO(named))
        assert main(["hook", "stop", "--format", fmt]) == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == decision and "UnicodeDecodeError" in out["reason"]
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"workspace_roots": [str(project)]})))
    assert main(["hook", "stop", "--format", "cursor"]) == 0
    assert "UnicodeDecodeError" in json.loads(capsys.readouterr().out)["followup_message"]
    monkeypatch.setattr("sys.stdin", io.StringIO(named))
    assert main(["hook", "start", "--format", "json"]) == 0
    assert "INV-1" in json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"cwd": str(tmp_path)})))
    assert main(["hook", "stop", "--format", "json"]) == 0 and capsys.readouterr().out == ""  # no project


def test_a_suspended_governance_never_blocks_the_stop(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)
    (project / ".criterion" / "development" / "journal.jsonl").write_bytes(b'{"a": "\xff"}\n')
    assert _stop(project, monkeypatch) == 2
    capsys.readouterr()
    pointer = project / "app.catalyst"
    pointer.write_text(
        json.dumps({**json.loads(pointer.read_text(encoding="utf-8")), "governance": "suspended"}), encoding="utf-8"
    )
    assert _stop(project, monkeypatch) == 0
    assert "suspended" in capsys.readouterr().err


def _broken(tmp_path, monkeypatch):
    """The fixture project: `check` already fails on it (structure errors),
    which is what a session finds when it starts."""
    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)
    return project


def _stop_with(project, monkeypatch, data: dict, capsys) -> tuple[int, str]:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(data)))
    capsys.readouterr()
    code = main(["--project", str(project), "hook", "stop"])
    return code, capsys.readouterr().err


def _start_with(project, monkeypatch, data: dict, capsys, *extra: str) -> str:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(data)))
    capsys.readouterr()
    assert main(["--project", str(project), "hook", "start", *extra]) == 0
    return capsys.readouterr().out


def _fail(project) -> None:
    """Add a failure `check` reports as an error: a file in an entity folder
    that is not named `<id>-<short-summary>.md` (INV-7)."""
    from catalyst.check import run

    write(project / ".criterion" / "items" / "stray notes.md", "# notes\n")
    assert any("stray notes.md" in e for e in run(load(project)).errors)


def test_a_session_does_not_block_on_what_it_found(tmp_path, monkeypatch, capsys):
    """ADR-002 (REQ-000035): a failure already there at session start is
    reported at stop but does not block."""
    project = _broken(tmp_path, monkeypatch)
    _fail(project)
    assert _start_with(project, monkeypatch, {"session_id": "s-1"}, capsys, "--quiet") == ""  # quiet: nothing printed
    code, err = _stop_with(project, monkeypatch, {"session_id": "s-1"}, capsys)
    assert code == 0 and "already there when this session started; not blocking" in err


def test_a_session_blocks_on_what_it_broke(tmp_path, monkeypatch, capsys):
    project = _broken(tmp_path, monkeypatch)
    _start_with(project, monkeypatch, {"session_id": "s-2"}, capsys, "--format", "json")
    _fail(project)
    code, err = _stop_with(project, monkeypatch, {"session_id": "s-2"}, capsys)
    assert code == 2 and "fix these before stopping" in err and "stray notes.md" in err
    # what was there at the start is counted, not listed: the new failure is what the agent must fix
    assert "INV-16" not in err and "more were already there when this session started" in err


def test_without_a_session_or_its_baseline_every_failure_blocks(tmp_path, monkeypatch, capsys):
    project = _broken(tmp_path, monkeypatch)
    _fail(project)
    code, err = _stop_with(project, monkeypatch, {}, capsys)
    assert code == 2 and "no session id from the agent: every failure counts" in err
    code, err = _stop_with(project, monkeypatch, {"session_id": "never-started"}, capsys)
    assert code == 2 and "no baseline for this session" in err
    code, _ = _stop_with(project, monkeypatch, {"session_id": "never-started", "stop_hook_active": True}, capsys)
    assert code == 0  # a second stop after a block is still let through


def test_baselines_stay_local_and_expire(tmp_path, monkeypatch, capsys):
    import os
    import time

    from catalyst import check, lock

    project = _broken(tmp_path, monkeypatch)
    dep = load(project)
    _start_with(project, monkeypatch, {"sessionId": "copilot.1"}, capsys, "--quiet")  # another agent's key
    folder = lock.state_dir(dep.root) / "sessions"
    assert (folder / "copilot.1.json").is_file() and ".git" in folder.parts  # inside the criterion's git dir
    old = folder / "old.json"
    old.write_text("{}", encoding="utf-8")
    week = time.time() - (check.BASELINE_DAYS + 1) * 86400
    os.utime(old, (week, week))
    _start_with(project, monkeypatch, {"session_id": "s-3"}, capsys, "--quiet")
    assert not old.exists() and (folder / "s-3.json").is_file()
    assert check.session_of({"session_id": "../etc/passwd"}) is None  # never a path
