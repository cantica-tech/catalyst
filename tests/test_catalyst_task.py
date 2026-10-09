"""The criterion's Taskfile.common.yml runs on its own: catalyst never adds to
or edits a project's own Taskfile."""
import re
import shutil
import sys
from pathlib import Path

import pytest

import project_file as pf
from catalyst import compose, move
from catalyst.__main__ import main
from catalyst_fixtures import make_project

KERNEL = Path(__file__).resolve().parent.parent / "framework" / "kernel"
MODULE = KERNEL.parent.parent.parent / "catalyst-software-engineering"


def _params():
    return compose.Params(module_id="software-engineering", userid="Ab12Cd34")


def test_every_composed_task_runs_from_the_callers_directory():
    module = MODULE if (MODULE / "Taskfile.module.yml").is_file() else None
    text = compose.taskfile(KERNEL, module, _params())
    tasks = re.findall(r"^  ([A-Za-z0-9_-]+):\n    dir: '\{\{\.USER_WORKING_DIR\}\}'\n", text, re.M)
    assert len(tasks) == len(re.findall(r"^  [A-Za-z0-9_-]+:\n", text, re.M)) > 20
    assert "catalyst" in tasks and ".criterion" not in text.split("tasks:", 1)[1]
    assert compose.taskfile(KERNEL, module, _params()) == text


@pytest.mark.skipif(sys.version_info < (3, 11) or shutil.which("task") is None,
                    reason="catalyst.toml needs Python 3.11+; Task not installed")
def test_task_dispatches_from_the_project_root(tmp_path, monkeypatch, capfd):
    project = make_project(tmp_path / "w", git=True)
    move.to_home(project, runtime=False)
    criterion = pf.home_criterion("app")
    (criterion / "Taskfile.common.yml").write_text(compose.taskfile(KERNEL, None, _params()), encoding="utf-8")
    monkeypatch.setenv("AGENT_CMD", "echo")
    (project / "sub").mkdir()
    monkeypatch.chdir(project / "sub")
    assert main(["task", "user-list", "--", "--active-only"]) == 0
    assert "/user-list --active-only" in capfd.readouterr().out
    assert main(["task"]) == 0 and "user-list" in capfd.readouterr().out
    assert sorted(p.name for p in project.iterdir() if p.name.lower().startswith("taskfile")) == []
