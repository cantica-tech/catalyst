"""Per-criterion runtime and launcher (roadmap R3.1a)."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import package_release
import project_file
from catalyst import runtime as rt
from catalyst_fixtures import make_project

REPO = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(shutil.which("uv") is None and sys.version_info < (3, 11),
                                reason="a runtime needs uv or Python 3.11+")


@pytest.fixture(scope="module")
def pyz(tmp_path_factory):
    return package_release.build_cli(REPO, tmp_path_factory.mktemp("cli") / "catalyst.pyz")


def _run(python: Path, *args, cwd=None):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.run([str(python), *args], capture_output=True, text=True, encoding="utf-8",
                          cwd=cwd, env=env)


def _home_project(tmp_path):
    project = make_project(tmp_path / "w")
    target = project_file.home_criterion("app")
    target.parent.mkdir(parents=True)
    shutil.move(str(project / ".criterion"), target)
    return project, target


def test_a_runtime_is_built_once_and_copied_into_each_criterion(tmp_path, pyz):
    _, criterion = _home_project(tmp_path)
    venv, changed = rt.install_into(criterion, "1.0.0", pyz)
    assert changed and rt.installed_version(venv) == "1.0.0"
    out = _run(rt.venv_python(venv), "-m", "catalyst", "--version")
    assert out.returncode == 0 and out.stdout.startswith("catalyst "), out.stderr
    assert rt.install_into(criterion, "1.0.0", pyz) == (venv, False)          # already there
    assert "/.venv" in (criterion / ".gitignore").read_text(encoding="utf-8").splitlines()
    rt.install_into(criterion, "2.0.0", pyz)                                    # another pin replaces it
    assert rt.installed_version(venv) == "2.0.0"
    assert sorted(p.name for p in rt.runtimes().iterdir()) == ["1.0.0", "2.0.0"]   # both kept


def test_the_launcher_runs_the_projects_criterion_or_a_legacy_vendored_cli(tmp_path, pyz):
    project, criterion = _home_project(tmp_path)
    rt.install_into(criterion, "1.0.0", pyz)
    launcher = rt.install_launcher()
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    (project / "src").mkdir()
    env["PWD"] = str(project / "src")
    out = subprocess.run([sys.executable, str(launcher), "where", "--json"], capture_output=True, text=True,
                         encoding="utf-8", cwd=project / "src", env=env)
    assert out.returncode == 0 and '"kind": "home"' in out.stdout, out.stderr

    legacy = make_project(tmp_path / "legacy")
    pointer = legacy / "app.catalyst"
    pointer.write_text(pointer.read_text(encoding="utf-8").replace('"app"', '"legacy-app"'), encoding="utf-8")
    (legacy / ".criterion" / "bin").mkdir(parents=True)
    shutil.copyfile(pyz, legacy / ".criterion" / "bin" / "catalyst.pyz")
    env["PWD"] = str(legacy)
    out = subprocess.run([sys.executable, str(launcher), "where", "--json"], capture_output=True, text=True,
                         encoding="utf-8", cwd=legacy, env=env)
    assert out.returncode == 0 and '"kind": "legacy"' in out.stdout, out.stderr


def test_outside_any_project_the_launcher_uses_the_newest_runtime(tmp_path, pyz):
    rt.ensure_runtime("1.2.0", pyz)
    rt.ensure_runtime("1.10.0", pyz)
    launcher = rt.install_launcher()
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PWD"] = str(tmp_path)
    out = subprocess.run([sys.executable, str(launcher), "--version"], capture_output=True, text=True,
                         encoding="utf-8", cwd=tmp_path, env=env)
    assert out.returncode == 0 and out.stdout.startswith("catalyst "), out.stderr


def test_mcp_always_runs_the_newest_runtime(tmp_path, pyz):
    project, _ = _home_project(tmp_path)          # its criterion has no runtime of its own
    rt.ensure_runtime("1.0.0", pyz)
    launcher = rt.install_launcher()
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PWD"] = str(project)
    run = lambda *args: subprocess.run([sys.executable, str(launcher), *args], capture_output=True, text=True,
                                       encoding="utf-8", cwd=project, env=env, input="")
    assert run("where").returncode != 0
    out = run("mcp")
    assert out.returncode == 0 and out.stdout == "", out.stderr
