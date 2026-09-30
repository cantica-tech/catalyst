import json
import subprocess
import zipfile
from pathlib import Path

import package_release as pr


def make_workspace(tmp_path: Path) -> Path:
    """catalyst (with a module catalog), a sibling `example-process` module
    repo, and a catalogued module that is not checked out."""
    root = tmp_path / "catalyst"
    root.mkdir()
    (root / "version.txt").write_text("0.33.0\n")

    kernel_dir = root / "framework" / "kernel"
    kernel_dir.mkdir(parents=True)
    (kernel_dir / "README.md").write_text("# Catalyst Kernel\n")
    (kernel_dir / "INVARIANTS.md").write_text("# Invariants\n")
    (root / "framework" / "modules").mkdir()
    (root / "framework" / "modules" / "catalog.md").write_text(
        "# Process module catalog\n\n"
        "| Id | Repository | Default branch |\n"
        "|---|---|---|\n"
        "| `example-process` | `git@example.com:x/catalyst-example-process.git` | `main` |\n"
        "| `absent-process` | `git@example.com:x/catalyst-absent-process.git` | `main` |\n"
    )

    mod_dir = tmp_path / "catalyst-example-process"
    mod_dir.mkdir()
    (mod_dir / "version.txt").write_text("1.2.0\n")
    (mod_dir / "module.yaml").write_text(
        "id: example-process\n"
        "name: Example Process Module\n"
        "version: 1.0.0\n"
        "description: A fictional module for tests.\n"
    )
    (mod_dir / "README.md").write_text("# Module\n")
    (mod_dir / ".git").mkdir()
    (mod_dir / ".git" / "HEAD").write_text("ref\n")
    return root


def test_catalogued_modules_reads_catalog_and_module_yaml(tmp_path: Path):
    root = make_workspace(tmp_path)
    modules = pr.catalogued_modules(root)
    assert [m.id for m in modules] == ["example-process"]
    m = modules[0]
    assert m.name == "Example Process Module"
    assert m.description == "A fictional module for tests."
    # version.txt wins over module.yaml's version.
    assert m.version == "1.2.0"
    assert m.dir == tmp_path / "catalyst-example-process"


def test_read_module_info_not_checked_out(tmp_path: Path):
    root = make_workspace(tmp_path)
    assert pr.read_module_info(root, "absent-process") is None


def test_package_release_kernel_and_modules(tmp_path: Path, monkeypatch):
    root = make_workspace(tmp_path)
    mod_dir = tmp_path / "catalyst-example-process"
    calls: list[list[str]] = []
    # Mock run_cmd to record, and never run, git commands
    monkeypatch.setattr(pr, "run_cmd", lambda cmd, cwd: calls.append(cmd) or "")
    (root / "LICENSE").write_text("Apache License\n")

    released = pr.package_modules(root)
    pr.package_kernel(root)

    # 1. Verify module output
    mod_release_dir = mod_dir / "catalyst" / "modules" / "example-process" / "v1.2.0"
    assert released == [mod_release_dir]
    manifest_data = json.loads((mod_release_dir / "manifest.json").read_text())
    assert manifest_data == {
        "id": "example-process",
        "name": "Example Process Module",
        "version": "1.2.0",
        "description": "A fictional module for tests.",
        "kernelVersion": ">=0.33.0",
        # Kept for extension builds that predate kernelVersion.
        "frameworkVersion": ">=0.33.0",
        "entry": "ui/index.js",
    }

    zip_file = mod_release_dir / "example-process-v1.2.0.zip"
    with zipfile.ZipFile(zip_file) as zf:
        namelist = zf.namelist()
        assert "manifest.json" in namelist
        assert "module.yaml" in namelist
        assert not any(n.startswith(".git") for n in namelist)
    # Without push, nothing is committed or pushed (INV-4)
    assert calls == []

    # 2. Verify kernel output
    kernel_release_dir = root / "catalyst" / "kernel" / "v0.33.0"
    kernel_manifest_data = json.loads((kernel_release_dir / "manifest.json").read_text())
    assert kernel_manifest_data["id"] == "catalyst-kernel"
    assert kernel_manifest_data["version"] == "0.33.0"

    with zipfile.ZipFile(kernel_release_dir / "kernel-v0.33.0.zip") as zf:
        namelist = zf.namelist()
        assert "manifest.json" in namelist
        assert "README.md" in namelist
        assert "INVARIANTS.md" in namelist
        assert "LICENSE" in namelist
        assert "bin/catalyst.pyz" in namelist
        assert not any(n.startswith("modules/") for n in namelist)
    assert (kernel_release_dir / "catalyst.pyz").is_file()

    # 3. Verify publishing into a distribution repository checkout
    publish_dir = tmp_path / "dist-repo"
    publish_dir.mkdir()
    monkeypatch.setattr(pr, "run_cmd",
                        lambda cmd, cwd: calls.append(cmd) or ("M x" if "status" in cmd else ""))
    pr.publish_releases(root, publish_dir)
    assert calls == []

    kernel_dest = publish_dir / "catalyst" / "kernel" / "v0.33.0"
    assert (kernel_dest / "manifest.json").is_file()
    assert (kernel_dest / "kernel-v0.33.0.zip").is_file()

    mod_dest = publish_dir / "catalyst" / "modules" / "example-process" / "v1.2.0"
    assert (mod_dest / "manifest.json").is_file()
    assert (mod_dest / "example-process-v1.2.0.zip").is_file()
    assert not (publish_dir / "catalyst" / "modules" / "absent-process").exists()
    assert not (publish_dir / "README.md").exists()

    readme = (publish_dir / "catalyst" / "modules" / "README.md").read_text()
    assert "Example Process Module" in readme
    assert "example/" not in (publish_dir / "catalyst" / "README.md").read_text()
    (publish_dir / "catalyst" / "example").mkdir()
    (publish_dir / "catalyst" / "example" / "README.md").write_text("# Example\n")
    pr.publish_releases(root, publish_dir)
    assert "[example/](example/README.md)" in (publish_dir / "catalyst" / "README.md").read_text()

    # 4. With push, the module repositories and the publish directory are
    # committed and pushed
    pr.package_modules(root, push=True)
    pr.publish_releases(root, publish_dir, push=True)
    commits = [c for c in calls if c[:2] == ["git", "commit"]]
    assert commits[0][-1] == "Release example-process module v1.2.0"
    assert commits[1][-1] == "Deploy release: kernel v0.33.0, example-process module v1.2.0"
    assert calls.count(["git", "push", "origin", "HEAD:main"]) == 1  # module, from its main worktree
    assert calls.count(["git", "push", "origin", "main"]) == 1  # publish directory


def test_publish_releases_missing_dir(tmp_path: Path):
    root = make_workspace(tmp_path)
    assert pr.publish_releases(root, tmp_path / "absent") is None


def test_package_modules_skips_when_not_checked_out(tmp_path: Path, monkeypatch):
    root = tmp_path / "catalyst"
    (root / "framework" / "modules").mkdir(parents=True)
    (root / "version.txt").write_text("0.35.0\n")
    (root / "framework" / "modules" / "catalog.md").write_text(
        "| Id | Repository | Default branch |\n|---|---|---|\n"
        "| `absent-process` | `x` | `main` |\n"
    )
    monkeypatch.setattr(pr, "run_cmd", lambda cmd, cwd: "")
    assert pr.package_modules(root) == []


def test_package_modules_without_catalog(tmp_path: Path):
    root = tmp_path / "catalyst"
    root.mkdir()
    assert pr.package_modules(root) == []


def test_module_release_lands_on_main_from_a_development_checkout(tmp_path: Path):
    """The module checkout sits on development: the archive is committed on
    origin main, and development neither receives it nor gets pushed."""
    def git(*args, cwd):
        return subprocess.run(["git", *args], cwd=cwd, check=True, text=True,
                              capture_output=True).stdout.strip()

    origin = tmp_path / "origin.git"
    git("init", "-q", "--bare", str(origin), cwd=tmp_path)
    mod_dir = tmp_path / "catalyst-example-process"
    git("clone", "-q", str(origin), str(mod_dir), cwd=tmp_path)
    for k, v in (("user.name", "T"), ("user.email", "t@example.com")):
        git("config", k, v, cwd=mod_dir)
    (mod_dir / "module.yaml").write_text("id: example-process\n")
    git("add", ".", cwd=mod_dir)
    git("commit", "-q", "-m", "init", cwd=mod_dir)
    git("push", "-q", "origin", "HEAD:main", cwd=mod_dir)
    git("checkout", "-q", "-b", "development", cwd=mod_dir)
    dev_head = git("rev-parse", "HEAD", cwd=mod_dir)

    dest = mod_dir / "catalyst" / "modules" / "example-process" / "v1.2.0"
    dest.mkdir(parents=True)
    (dest / "manifest.json").write_text("{}\n")
    module = pr.ModuleInfo("example-process", "Example", "d", "1.2.0", mod_dir)
    pr.commit_module_release(module, dest)

    assert git("rev-parse", "HEAD", cwd=mod_dir) == dev_head
    assert git("branch", "--show-current", cwd=mod_dir) == "development"
    files = git("ls-tree", "-r", "--name-only", "main", cwd=origin)
    assert "catalyst/modules/example-process/v1.2.0/manifest.json" in files
    assert git("log", "-1", "--format=%s", "main", cwd=origin) == "Release example-process module v1.2.0"
    assert "development" not in git("branch", cwd=origin)
    assert git("worktree", "list", "--porcelain", cwd=mod_dir).count("worktree ") == 1


def test_release_archives_are_reproducible(tmp_path: Path, monkeypatch):
    """Rebuilding an unchanged release gives byte-identical archives, so
    publishing it again commits nothing."""
    import os
    import time
    root = make_workspace(tmp_path)
    monkeypatch.setattr(pr, "run_cmd", lambda cmd, cwd: "")
    (root / "LICENSE").write_text("Apache License\n")
    mod_zip = (tmp_path / "catalyst-example-process" / "catalyst" / "modules"
               / "example-process" / "v1.2.0" / "example-process-v1.2.0.zip")
    kernel_dir = root / "catalyst" / "kernel" / "v0.33.0"

    pr.package_modules(root)
    pr.package_kernel(root)
    first = {p: p.read_bytes() for p in (mod_zip, kernel_dir / "kernel-v0.33.0.zip",
                                         kernel_dir / "catalyst.pyz")}
    later = time.time() + 3600
    for p in (root / "framework").rglob("*"):
        os.utime(p, (later, later))
    pr.package_modules(root)
    pr.package_kernel(root)
    for p, data in first.items():
        assert p.read_bytes() == data, p.name
    assert os.access(kernel_dir / "catalyst.pyz", os.X_OK)


def test_a_module_release_states_its_own_kernel_requirement(tmp_path: Path, capsys):
    """fw-STRUCTURE-000016: the manifest says what module.yaml declares, and
    packaging an unchanged module with a newer kernel changes nothing."""
    root = make_workspace(tmp_path)
    mod_dir = tmp_path / "catalyst-example-process"
    with (mod_dir / "module.yaml").open("a") as f:
        f.write('kernel_version: ">=0.30.0"\n')
    release = mod_dir / "catalyst" / "modules" / "example-process" / "v1.2.0"

    pr.package_modules(root)
    manifest = json.loads((release / "manifest.json").read_text())
    assert manifest["kernelVersion"] == manifest["frameworkVersion"] == ">=0.30.0"
    first = {p.name: p.read_bytes() for p in release.iterdir()}
    assert "declares no kernel_version" not in capsys.readouterr().out

    (root / "version.txt").write_text("0.99.0\n")              # a newer kernel packages it again
    pr.package_modules(root)
    assert {p.name: p.read_bytes() for p in release.iterdir()} == first


def test_a_module_without_a_declaration_falls_back_with_a_warning(tmp_path: Path, capsys):
    root = make_workspace(tmp_path)
    pr.package_modules(root)
    out = capsys.readouterr().out
    assert "example-process declares no kernel_version" in out and ">=0.33.0" in out
