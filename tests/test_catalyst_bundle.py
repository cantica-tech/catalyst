"""The kernel catalyst.pyz carries: `catalyst init` from an installed runtime, no checkout (REQ-000106)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

import package_release as pr
from catalyst import bundle
from catalyst.check import run as run_checks
from catalyst.deployment import load
from test_catalyst_init import example_module

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def pyz(tmp_path_factory) -> Path:
    return pr.build_cli(REPO, tmp_path_factory.mktemp("cli") / "catalyst.pyz")


def test_the_pyz_carries_the_kernel_and_its_version(pyz, tmp_path):
    names = set(zipfile.ZipFile(pyz).namelist())
    assert {"catalyst_kernel/rules-of-rules.template.md", "catalyst_kernel/manifest.json"} <= names
    kernel = bundle.extract_kernel(pyz, tmp_path)
    assert kernel is not None and (kernel / "INVARIANTS.md").is_file()
    manifest = json.loads((kernel / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == pr.read_kernel_version(REPO)
    entities = {p.name for p in (REPO / "framework" / "kernel" / "entities").glob("*.yaml")}
    assert {p.name for p in (kernel / "entities").glob("*.yaml")} == entities


def test_a_runtime_finds_the_pyz_it_runs_from(pyz, tmp_path):
    """A runtime runs `python -m catalyst` with the pyz on sys.path (its catalyst.pth), not `python catalyst.pyz`."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = str(pyz)
    res = subprocess.run(
        [
            sys.executable,
            "-c",
            "from catalyst.bundle import running_pyz, checkout_kernel; print(running_pyz()); print(checkout_kernel())",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert res.stdout.split() == [str(pyz), "None"]


def test_init_without_kernel_uses_the_bundled_one_and_vendors_the_running_pyz(pyz, tmp_path, monkeypatch):
    from catalyst.__main__ import main

    monkeypatch.setattr(bundle, "checkout_kernel", lambda: None)  # no checkout: only the runtime's pyz
    monkeypatch.setattr(bundle, "running_pyz", lambda: pyz)
    project = tmp_path / "app"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    subprocess.run(["git", "-C", str(project), "config", "user.name", "Grace Hopper"], check=True)
    code = main(
        [
            "--project",
            str(project),
            "init",
            "--name",
            "app",
            "--module",
            "example-process",
            "--module-dir",
            str(example_module(tmp_path)),
            "--no-runtime",
        ]
    )
    assert code == 0
    dep = load(project)
    assert (dep.root / "version.txt").read_text(encoding="utf-8").strip().startswith(pr.read_kernel_version(REPO))
    assert (dep.root / "bin" / "catalyst.pyz").read_bytes() == pyz.read_bytes()
    assert run_checks(dep).errors == []


def test_init_with_neither_a_kernel_nor_a_bundle_asks_for_one(tmp_path, monkeypatch, capsys):
    from catalyst.__main__ import main

    monkeypatch.setattr(bundle, "checkout_kernel", lambda: None)
    monkeypatch.setattr(bundle, "running_pyz", lambda: None)
    assert main(["--project", str(tmp_path), "init", "--name", "app", "--no-module"]) == 2
    assert "pass --kernel" in capsys.readouterr().err
