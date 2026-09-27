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
                          capture_output=True, text=True)


def test_zipapp_runs_standalone_with_embedded_kernel_entities(tmp_path):
    pyz = pr.build_cli(REPO, tmp_path / "bin" / "catalyst.pyz")
    names = zipfile.ZipFile(pyz).namelist()
    assert {"__main__.py", "catalyst/__main__.py", "module_loader.py",
            "check_deployment.py", "kernel_entities_embedded.py", "catalyst/_build.py"} <= set(names)
    project = make_project(tmp_path / "p")
    version = run(pyz, "--version", cwd=project)
    assert version.stdout.strip() == f"catalyst {pr.read_kernel_version(REPO)}"
    assert run(pyz, "id", "next", "RECON", cwd=project).stdout.strip() == f"RECON-000001-{USERID}"
    assert run(pyz, "validate", cwd=project).returncode == 0


def test_zipapp_propagates_exit_codes(tmp_path):
    """A failing check must fail the process, or a hook can never block."""
    pyz = pr.build_cli(REPO, tmp_path / "catalyst.pyz")
    project = make_project(tmp_path / "p")
    item = project / ".criterion" / "items" / "ITEM-000001-first-item.md"
    item.write_text(item.read_text().replace("| Ada Lovelace |", "| Mallory |"))
    assert run(pyz, "validate", cwd=project).returncode == 1
    hook = subprocess.run([sys.executable, str(pyz), "hook", "stop"], cwd=project, input="{}",
                          env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"},
                          capture_output=True, text=True)
    assert hook.returncode == 2 and "signer" in hook.stderr
    assert run(pyz, "--project", str(tmp_path / "nowhere"), "validate", cwd=project).returncode == 2
