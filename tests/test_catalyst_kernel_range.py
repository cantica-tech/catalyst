"""A module's `kernel_version` is enforced (fw-STRUCTURE-000016,
REQ-000023): init and sync refuse a kernel outside it, check reports it."""

from __future__ import annotations

import json

import pytest

from catalyst import sync
from catalyst.__main__ import main
from catalyst.init import InitError, init
from catalyst.versions import VersionError, satisfies
from catalyst_fixtures import make_project, write
from test_catalyst_init import request
from test_catalyst_sync import _deployment, _release


@pytest.mark.parametrize(
    ("version", "spec", "inside"),
    [
        ("0.54.0", ">=0.52.0", True),
        ("0.54.0+g6548800", ">=0.52,<1.0", True),
        ("0.51.9", ">=0.52.0", False),
        ("1.0", ">=0.52,<1.0", False),
        ("0.54.0", "==0.54.0", True),
        ("0.54.1", "0.54.0", False),
        ("0.54.0", None, True),
        ("0.54.0", "", True),
    ],
)
def test_a_version_against_a_range(version, spec, inside):
    assert satisfies(version, spec) is inside


def test_a_version_must_be_one():
    with pytest.raises(VersionError):
        satisfies("latest", ">=0.1")


def test_init_refuses_a_module_outside_the_kernel(tmp_path):
    req = request(tmp_path)
    assert req.module is not None
    mod = req.module / "module.yaml"
    write(mod, mod.read_text(encoding="utf-8") + 'kernel_version: ">=99.0"\n')
    with pytest.raises(InitError, match=r"works with kernel >=99\.0, not "):
        init(req)


def test_sync_refuses_a_kernel_outside_the_deployed_module(tmp_path):
    project, deployed = _deployment(tmp_path)
    mod = project / ".criterion" / "modules" / "example-process" / "module.yaml"
    write(mod, mod.read_text(encoding="utf-8") + f'kernel_version: "=={deployed}"\n')
    from catalyst.deployment import load

    src = sync.Sources(load(project), _release(tmp_path, "9.9.9"), None, _release(tmp_path, deployed), None)
    with pytest.raises(sync.SyncError, match=rf"works with kernel =={deployed}, not 9\.9\.9"):
        sync.plan(load(project), src, None)


def test_check_reports_a_deployment_outside_its_module(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path, git=True)
    mod = project / ".criterion" / "modules" / "example-process" / "module.yaml"
    write(mod, mod.read_text(encoding="utf-8") + 'kernel_version: ">=99.0"\n')
    monkeypatch.chdir(project)
    capsys.readouterr()
    main(["check", "--json"])
    errors = json.loads(capsys.readouterr().out)["errors"]
    assert any(e.startswith("module: example-process") and "works with kernel >=99.0" in e for e in errors)
    write(mod, mod.read_text(encoding="utf-8").replace(">=99.0", ">=0.1"))
    main(["check", "--json"])
    assert not any(e.startswith("module:") for e in json.loads(capsys.readouterr().out)["errors"])


def _gated(tmp_path, shared_version=None):
    """A deployment whose criterion has the CI gate and a fetched shared
    branch, and a release of its module that needs kernel 9.9.9."""
    import shutil
    import subprocess

    from catalyst import criterion as cr

    project, deployed = _deployment(tmp_path)
    root = project / ".criterion"
    write(root / cr.CI_WORKFLOW, "name: catalyst\n")
    if shared_version:
        write(root / "version.txt", shared_version + "\n")
    git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "the shared branch"], check=True)
    subprocess.run([*git, "update-ref", "refs/remotes/origin/criterion", "HEAD"], check=True)
    if shared_version:
        write(root / "version.txt", deployed + "\n")
    module = tmp_path / "module-next"
    shutil.copytree(root / "modules" / "example-process", module)
    write(module / "module.yaml", (module / "module.yaml").read_text(encoding="utf-8") + 'kernel_version: ">=9.9.9"\n')
    return project, deployed, module


def test_sync_refuses_a_module_the_shared_gate_cannot_check(tmp_path):
    """BUG-000011: the gate runs the shared branch's CLI, so a module that
    needs the kernel being synced cannot arrive with it."""
    from catalyst.deployment import load

    project, deployed, module = _gated(tmp_path)
    src = sync.Sources(load(project), _release(tmp_path, "9.9.9"), module, _release(tmp_path, deployed), None)
    with pytest.raises(sync.SyncError, match=rf"gate still runs {deployed}.*kernel alone first"):
        sync.plan(load(project), src, None)
    src.close()
    # the kernel alone is what goes first
    src = sync.Sources(load(project), tmp_path / "kernel-9.9.9", None, tmp_path / f"kernel-{deployed}", None)
    sync.plan(load(project), src, None)
    src.close()


def test_sync_takes_the_module_once_the_shared_branch_runs_its_kernel(tmp_path):
    from catalyst.deployment import load

    project, deployed, module = _gated(tmp_path, shared_version="9.9.9")
    assert sync.gate_version(load(project)) == "9.9.9"
    src = sync.Sources(load(project), _release(tmp_path, "9.9.9"), module, _release(tmp_path, deployed), None)
    sync.plan(load(project), src, None)
    src.close()


def test_sync_takes_both_when_nothing_gates_the_criterion(tmp_path):
    from catalyst import criterion as cr
    from catalyst.deployment import load

    project, deployed, module = _gated(tmp_path)
    (project / ".criterion" / cr.CI_WORKFLOW).unlink()
    assert sync.gate_version(load(project)) is None
    src = sync.Sources(load(project), _release(tmp_path, "9.9.9"), module, _release(tmp_path, deployed), None)
    sync.plan(load(project), src, None)
    src.close()
