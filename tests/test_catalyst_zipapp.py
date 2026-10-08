from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

import package_release as pr
from catalyst_fixtures import USERID, make_project

REPO = Path(__file__).resolve().parent.parent


def run(pyz: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.run([sys.executable, str(pyz), *args], cwd=cwd, env=env,
                          capture_output=True, text=True, encoding="utf-8")


def test_zipapp_runs_standalone_with_embedded_kernel_entities(tmp_path):
    pyz = pr.build_cli(REPO, tmp_path / "bin" / "catalyst.pyz")
    names = zipfile.ZipFile(pyz).namelist()
    assert {"__main__.py", "catalyst/__main__.py", "module_loader.py",
            "check_deployment.py", "kernel_entities_embedded.py", "catalyst/_build.py"} <= set(names)
    project = make_project(tmp_path / "p")
    version = run(pyz, "--version", cwd=project)
    assert version.stdout.strip().startswith(f"catalyst {pr.read_kernel_version(REPO)}")
    assert run(pyz, "id", "next", "RECON", cwd=project).stdout.strip() == f"RECON-000001-{USERID}"
    assert run(pyz, "validate", cwd=project).returncode == 0


def test_zipapp_propagates_exit_codes(tmp_path):
    """A failing check must fail the process, or a hook can never block."""
    pyz = pr.build_cli(REPO, tmp_path / "catalyst.pyz")
    project = make_project(tmp_path / "p")
    item = project / ".criterion" / "items" / "ITEM-000001-first-item.md"
    item.write_text(item.read_text(encoding="utf-8").replace("| Ada Lovelace |", "| Mallory |"), encoding="utf-8")
    assert run(pyz, "validate", cwd=project).returncode == 1
    hook = subprocess.run([sys.executable, str(pyz), "hook", "stop"], cwd=project, input="{}",
                          env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"},
                          capture_output=True, text=True, encoding="utf-8")
    assert hook.returncode == 2 and "signer" in hook.stderr
    assert run(pyz, "--project", str(tmp_path / "nowhere"), "validate", cwd=project).returncode == 2


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout.strip()


def test_a_build_names_the_commit_it_was_built_from(tmp_path):
    root = tmp_path / "src"
    import shutil
    shutil.copytree(REPO / "framework" / "kernel" / "entities", root / "framework" / "kernel" / "entities")
    (root / "version.txt").write_text("9.8.7\n", encoding="utf-8")
    project = make_project(tmp_path / "p")
    # outside git: the plain version
    plain = pr.build_cli(root, tmp_path / "plain.pyz")
    assert run(plain, "--version", cwd=project).stdout.strip() == "catalyst 9.8.7"
    _git(root, "init", "-q")
    _git(root, "add", "version.txt")
    _git(root, "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-qm", "v")
    sha = _git(root, "rev-parse", "--short=12", "HEAD")
    clean = pr.build_cli(root, tmp_path / "clean.pyz")
    assert run(clean, "--version", cwd=project).stdout.strip() == f"catalyst 9.8.7+g{sha}"
    (root / "version.txt").write_text("9.8.7\n\n", encoding="utf-8")
    dirty = pr.build_cli(root, tmp_path / "dirty.pyz")
    assert run(dirty, "--version", cwd=project).stdout.strip() == f"catalyst 9.8.7+g{sha}.dirty"
