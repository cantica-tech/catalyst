import io
import sys
from pathlib import Path

import stop_hook as sh


def write_check(root: Path, name: str, code: int, out: str = "") -> None:
    scripts = root / "scripts"
    scripts.mkdir(exist_ok=True)
    (scripts / name).write_text(f"print({out!r})\nraise SystemExit({code})\n", encoding="utf-8")


def fake_root(tmp_path: Path, failing: set[str]) -> Path:
    for check in sh.CHECKS:
        write_check(tmp_path, check, 1 if check in failing else 0,
                    f"{check} broke" if check in failing else "ok")
    pkg = tmp_path / "scripts" / "catalyst"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    code = 1 if "catalyst check" in failing else 0
    (pkg / "__main__.py").write_text(
        "import sys\n"
        f"code = {code} if sys.argv[1] == 'check' else 0\n"
        "print(f'catalyst {sys.argv[1]} said {code}')\nraise SystemExit(code)\n", encoding="utf-8")
    return tmp_path


def test_run_checks_collects_only_failures(tmp_path: Path):
    root = fake_root(tmp_path, {"check_plugins.py"})
    assert sh.run_checks(root) == [("check_plugins.py", "check_plugins.py broke")]


def test_run_checks_includes_catalyst_check(tmp_path: Path):
    root = fake_root(tmp_path, {"catalyst check"})
    assert sh.run_checks(root) == [("catalyst check", "catalyst check said 1")]


def test_all_pass_exits_0(monkeypatch, capsys):
    monkeypatch.setattr(sh, "run_checks", lambda root=None: [])
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    assert sh.main() == 0
    assert capsys.readouterr().err == ""


def test_failure_blocks_with_stderr(monkeypatch, capsys):
    monkeypatch.setattr(sh, "run_checks", lambda root=None: [("check_deployment.py", "bad naming")])
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"stop_hook_active": false}'))
    assert sh.main() == 2
    err = capsys.readouterr().err
    assert "check_deployment.py FAILED" in err
    assert "bad naming" in err


def test_second_block_lets_stop_through(monkeypatch, capsys):
    monkeypatch.setattr(sh, "run_checks", lambda root=None: [("check_deployment.py", "bad naming")])
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"stop_hook_active": true}'))
    assert sh.main() == 0
    assert "not blocking again" in capsys.readouterr().err


def test_malformed_hook_input_is_treated_as_empty():
    assert sh.read_hook_input(io.StringIO("not json")) == {}
    assert sh.read_hook_input(io.StringIO("")) == {}


def test_a_crash_blocks_the_stop(monkeypatch, capsys):
    def boom(root=None):
        raise OSError("python3 vanished")
    monkeypatch.setattr(sh, "run_checks", boom)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    assert sh.main() == 2
    assert "python3 vanished" in capsys.readouterr().err
