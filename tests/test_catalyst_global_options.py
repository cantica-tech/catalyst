"""The global options (BUG-000053, rr-META-000014): `--project` reaches every command, and `--working-copy` is never
silently ignored."""

from __future__ import annotations

import pytest

from catalyst import serve
from catalyst.__main__ import main


class _StopError(Exception):
    pass


@pytest.mark.parametrize("before", [True, False])
def test_serve_local_takes_the_global_project(tmp_path, monkeypatch, before):
    seen = []

    def make_local(project, *_a, **_k):
        seen.append(project)
        raise _StopError

    monkeypatch.setattr(serve, "make_local", make_local)
    monkeypatch.chdir(tmp_path)
    argv = ["--project", "elsewhere", "serve", "--local"] if before else ["serve", "--local", "--project", "elsewhere"]
    with pytest.raises(_StopError):
        main(argv)
    assert seen == [tmp_path / "elsewhere"]


@pytest.mark.parametrize(
    "argv", [["where"], ["open"], ["task"], ["runtime", "status"], ["move", "--to-home"], ["migrate"], ["mcp"]]
)
def test_working_copy_is_refused_where_it_would_be_ignored(tmp_path, capsys, argv):
    assert main(["--working-copy", str(tmp_path), *argv]) == 2
    assert "instead of --working-copy" in capsys.readouterr().err
