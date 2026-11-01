"""The CLI's exit codes (fw-STRUCTURE-000025, REQ-000110; CLI.md "Exit codes"): 0 success, 1 failure, 2 a usage
error or a blocking `hook stop`, 3 assent needed, 4 no deployment."""

from __future__ import annotations

import io
import shutil

import pytest

from catalyst.__main__ import EXIT_NO_DEPLOYMENT, EXIT_USAGE, NEEDS_ASSENT, main
from catalyst_fixtures import make_project


def test_the_codes_are_named_once():
    assert (EXIT_USAGE, NEEDS_ASSENT, EXIT_NO_DEPLOYMENT) == (2, 3, 4)


@pytest.mark.parametrize(
    "argv",
    [
        ["where"],
        ["open"],
        ["validate"],
        ["index", "regen"],
        ["move", "--to-home"],
        ["migrate"],
        ["task"],
        ["id", "next", "ITEM"],
        ["journal", "verify"],
    ],
)
def test_no_deployment_exits_4(tmp_path, monkeypatch, capsys, argv):
    monkeypatch.chdir(tmp_path)
    assert main(argv) == EXIT_NO_DEPLOYMENT
    assert "catalyst" in capsys.readouterr().err


def test_a_working_copy_that_is_none_exits_4(tmp_path, capsys):
    assert main(["--working-copy", str(tmp_path), "validate"]) == EXIT_NO_DEPLOYMENT
    assert "not a catalyst working copy" in capsys.readouterr().err


def test_an_unreachable_criterion_exits_4_but_fails_check_and_blocks_hook_stop(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path)
    shutil.rmtree(project / ".criterion")
    monkeypatch.chdir(project)
    assert main(["validate"]) == EXIT_NO_DEPLOYMENT
    assert main(["check"]) == 1
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    assert main(["hook", "stop"]) == 2


def test_outside_any_project_check_and_the_hooks_exit_0(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["check"]) == 0
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    assert main(["hook", "stop"]) == 0
    msg = tmp_path / "MSG"
    msg.write_text("anything\n", encoding="utf-8")
    assert main(["hook", "commit-msg", str(msg)]) == 0
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    assert main(["hook", "start", "--quiet"]) == 0


def test_usage_errors_exit_2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:  # argparse's own
        main(["where", "--no-such-option"])
    assert exc.value.code == EXIT_USAGE
    assert main(["--working-copy", str(tmp_path), "where"]) == EXIT_USAGE  # project-only command
    project = make_project(tmp_path / "p")
    assert main(["--project", str(project), "id", "next", "ITEM", "--count", "0"]) == EXIT_USAGE
