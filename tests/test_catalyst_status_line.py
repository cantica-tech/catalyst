"""The CLI's status line (brand roadmap item 9, `09` §5.4): the last recorded
check after a command, on an interactive terminal only, never a new check."""

from __future__ import annotations

import datetime

from catalyst.__main__ import main
from catalyst.check import last, run, status_line
from catalyst.deployment import load
from catalyst_fixtures import make_project


def test_check_records_its_result_and_the_line_reads_it(tmp_path):
    dep = load(make_project(tmp_path, git=True))
    assert last(dep) is None
    assert status_line(dep).endswith("not checked yet (catalyst check)")
    report = run(dep)
    recorded = last(dep)
    assert recorded is not None and recorded["errors"] == len(report.errors)
    at = datetime.datetime.fromisoformat(recorded["at"])
    line = status_line(dep, now=at)
    assert line.startswith("catalyst · ") and f"checked {at.astimezone():%H:%M} · " in line
    assert f"{len(report.warnings)} warning(s)" in line
    later = status_line(dep, now=at + datetime.timedelta(days=2))
    assert f"checked {at.astimezone():%Y-%m-%d %H:%M}" in later  # another day: the date too


def test_the_line_never_reaches_a_pipe(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)
    capsys.readouterr()
    assert main(["list", "ITEM"]) == 0
    assert "catalyst · " not in capsys.readouterr().err  # captured output is not a terminal


def test_on_a_terminal_the_line_follows_a_command_and_can_be_turned_off(tmp_path, monkeypatch, capsys):
    import sys

    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True, raising=False)
    capsys.readouterr()
    assert main(["list", "ITEM"]) == 0
    assert "catalyst · " in capsys.readouterr().err
    assert main(["list", "ITEM", "--json"]) == 0
    assert "catalyst · " not in capsys.readouterr().err  # never with --json
    monkeypatch.setenv("CATALYST_FOOTER", "0")
    assert main(["list", "ITEM"]) == 0
    assert "catalyst · " not in capsys.readouterr().err
