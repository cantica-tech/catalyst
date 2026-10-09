"""`catalyst check`: uncommitted product changes are judged by what the
deployment governs (scope.py) and ignore operating-system noise."""

from __future__ import annotations

import json
import subprocess

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
