"""`catalyst module install|upgrade` (roadmap R4.9, N2; REQ-000028): a
module installed into a deployment that has none, from a directory, a
release zip or a git repository, seeded as `init` does; and upgraded
through `sync`."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from catalyst import modules
from catalyst.__main__ import main
from catalyst.check import run as run_checks
from catalyst.deployment import load
from catalyst.init import init
from catalyst_fixtures import journal_entries, write
from test_catalyst_init import KERNEL, request
from test_catalyst_sync import _deployment, _release

USERID = "Abcdefg1"


def _bare(tmp: Path, userid: str = USERID):
    """A deployment with the kernel's types only, and the example module's
    directory beside it."""
    tmp.mkdir(parents=True, exist_ok=True)
    req = request(tmp, module_id=None, userid=userid)
    init(req)
    return req.project, tmp / "example-process"


def _files(root: Path, skip=(".git", "journal", "bin")) -> dict[str, str]:
    return {
        f.relative_to(root).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in sorted(root.rglob("*"))
        if f.is_file() and not set(skip) & set(f.relative_to(root).parts)
    }


def _install(project: Path, source, *extra: str) -> int:
    return main(["--project", str(project), "module", "install", str(source), "--kernel", str(KERNEL), *extra])


def _repository(tmp: Path, module: Path) -> tuple[Path, str]:
    """`module` committed, tagged v1, as a bare repository; its commit."""
    work = tmp / "work"
    shutil.copytree(module, work)
    git = ["git", "-C", str(work), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q", str(work)], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "v1"], check=True)
    subprocess.run([*git, "tag", "v1"], check=True)
    head = subprocess.run([*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    bare = tmp / "example-process.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(work), str(bare)], check=True)
    return bare, head


def test_a_deployment_can_hold_the_kernels_types_only(tmp_path):
    project, _ = _bare(tmp_path)
    dep = load(project)
    assert dep.module is None and not (dep.root / "modules").exists()
    assert json.loads(next(project.glob("*.catalyst")).read_text(encoding="utf-8"))["module"] is None
    assert run_checks(dep).errors == []
    assert modules.verify(dep.root) == []


def test_init_still_refuses_to_choose_a_module(tmp_path, capsys):
    (tmp_path / "p").mkdir()
    assert main(["--project", str(tmp_path / "p"), "init", "--kernel", str(KERNEL), "--name", "p"]) == 2
    assert "--no-module" in capsys.readouterr().err
    args = ["--project", str(tmp_path / "p"), "init", "--kernel", str(KERNEL), "--name", "p"]
    assert main([*args, "--module", "x", "--no-module"]) == 2


def test_install_from_a_directory_seeds_the_module_as_init_does(tmp_path, capsys):
    project, module = _bare(tmp_path / "later")
    assert _install(project, module) == 0
    assert "installed module example-process 0.2.0" in capsys.readouterr().out
    dep = load(project)
    assert dep.module is not None and dep.module.id == "example-process"
    assert run_checks(dep).errors == []
    assert [f.state for f in modules.verify(dep.root)] == ["ok"]
    last = journal_entries(dep.root)[-1]
    assert last["command"] == "catalyst module install" and last["artifact"] == "module example-process 0.2.0"
    assert any(f["path"].endswith("modules/modules.json") for f in last["files"])

    # the same criterion as `init --module`, apart from the deployment note
    (tmp_path / "whole").mkdir()
    whole = request(tmp_path / "whole", userid=USERID)
    init(whole)
    a, b = _files(whole.project / ".criterion"), _files(project / ".criterion")
    del a["DEPLOYMENT.md"], b["DEPLOYMENT.md"]
    assert sorted(a) == sorted(b)
    assert [f for f in a if a[f] != b[f]] == []


def test_install_from_a_release_zip(tmp_path):
    project, module = _bare(tmp_path)
    tree = modules.release_tree(module, tmp_path / "tree", "0.58.0")
    archive = tmp_path / "example-process-v0.2.0.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for f in sorted(tree.rglob("*")):
            if f.is_file():
                zf.write(f, f.relative_to(tree).as_posix())
    assert _install(project, archive) == 0
    (entry,) = modules.read_record(project / ".criterion")
    assert entry["source"] == "example-process-v0.2.0.zip" and entry["commit"] is None
    assert run_checks(load(project)).errors == []


@pytest.mark.parametrize("ref", [None, "v1", "commit"])
def test_install_from_a_git_repository(tmp_path, ref):
    project, module = _bare(tmp_path)
    bare, head = _repository(tmp_path, module)
    spec = str(bare) if ref is None else f"{bare}@{head if ref == 'commit' else ref}"
    assert _install(project, spec) == 0
    (entry,) = modules.read_record(project / ".criterion")
    assert entry["source"] == "example-process" and entry["commit"] == head  # a name, never the path
    assert str(tmp_path) not in json.dumps(entry)
    assert not (project / ".criterion" / "modules" / "example-process" / ".git").exists()
    assert run_checks(load(project)).errors == []


def test_every_refusal_leaves_the_criterion_untouched(tmp_path, capsys):
    project, module = _bare(tmp_path)
    root = project / ".criterion"
    before = _files(root, skip=(".git",))

    def refused(source, *extra, kernel=KERNEL) -> str:
        code = main(["--project", str(project), "module", "install", str(source), "--kernel", str(kernel), *extra])
        assert code == 1 and _files(root, skip=(".git",)) == before
        return capsys.readouterr().err

    assert "neither a module directory" in refused(tmp_path / "nope")
    assert "not a usable branch" in refused(f"{_repository(tmp_path, module)[0]}@-x")
    assert "is at kernel" in refused(module, kernel=_release(tmp_path, "9.9.9"))
    newer = tmp_path / "newer" / "example-process"
    shutil.copytree(module, newer)
    write(newer / "module.yaml", (newer / "module.yaml").read_text(encoding="utf-8") + 'kernel_version: ">=99.0"\n')
    assert "works with kernel >=99.0" in refused(newer)
    clash = tmp_path / "clash" / "example-process"
    shutil.copytree(module, clash)
    schema = clash / "schemas" / "item.yaml"
    write(schema, schema.read_text(encoding="utf-8").replace("id_prefix: ITEM", "id_prefix: RECON"))
    assert "which the kernel already has" in refused(clash)

    assert _install(project, module) == 0
    capsys.readouterr()
    assert _install(project, module) == 1  # one module per deployment, until several are supported
    assert "already has the module example-process" in capsys.readouterr().err


def test_upgrade_goes_through_sync(tmp_path, capsys):
    project, deployed = _deployment(tmp_path)
    root = project / ".criterion"
    kernel = _release(tmp_path, deployed)
    newer = tmp_path / "newer" / "example-process"
    shutil.copytree(tmp_path / "example-process", newer)
    write(newer / "version.txt", "0.3.0\n")
    write(newer / "guidance.md", "# Guidance\n")
    args = ["--project", str(project), "module", "upgrade", "example-process"]

    assert main([*args, "--kernel", str(kernel)]) == 1  # the record names a directory, not a repository
    assert "names no repository" in capsys.readouterr().err
    assert main(["--project", str(project), "module", "upgrade", "other", str(newer), "--kernel", str(kernel)]) == 1
    assert "no module 'other' here (installed: example-process)" in capsys.readouterr().err

    before = _files(root, skip=(".git",))
    assert main([*args, str(newer), "--kernel", str(kernel), "--plan"]) == 0
    assert "module 0.2.0 -> 0.3.0" in capsys.readouterr().out and _files(root, skip=(".git",)) == before

    assert main([*args, str(newer), "--kernel", str(kernel)]) == 0
    (entry,) = modules.read_record(root)
    assert entry["version"] == "0.3.0" and (root / "modules" / "example-process" / "guidance.md").is_file()
    assert [f.state for f in modules.verify(root)] == ["ok"]


def test_sync_takes_a_git_repository_for_the_module(tmp_path, capsys):
    project, deployed = _deployment(tmp_path)
    write(tmp_path / "example-process" / "guidance.md", "# Guidance\n")  # a change since the install
    bare, head = _repository(tmp_path, tmp_path / "example-process")
    kernel = _release(tmp_path, deployed)
    args = ["--project", str(project), "sync", "apply", "--kernel", str(kernel), "--base-kernel", str(kernel)]
    assert main([*args, "--module", f"{bare}@v1"]) == 0
    (entry,) = modules.read_record(project / ".criterion")
    assert entry["commit"] == head and entry["source"] == "example-process"
    assert main([*args, "--module", f"{bare}@nope"]) == 1
    assert "could not fetch example-process.git@nope" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("spec", "source", "ref"),
    [
        ("https://example.test/acme/mod.git", "https://example.test/acme/mod.git", None),
        ("https://example.test/acme/mod.git@v1.2", "https://example.test/acme/mod.git", "v1.2"),
        ("https://user@example.test/acme/mod.git", "https://user@example.test/acme/mod.git", None),
        ("git@example.test:acme/mod.git", "git@example.test:acme/mod.git", None),
        ("git@example.test:acme/mod.git@main", "git@example.test:acme/mod.git", "main"),
        ("/srv/mod.git@abc123", "/srv/mod.git", "abc123"),
    ],
)
def test_a_ref_is_what_follows_the_last_at(spec, source, ref):
    assert modules.split_ref(spec) == (source, ref)
    assert modules.clean_url("https://user:pw@example.test/acme/mod.git") == "https://example.test/acme/mod.git"
    assert modules.is_url("git@example.test:acme/mod.git") and not modules.is_url("/srv/mod.git")
