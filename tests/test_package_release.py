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
    (root / "version.txt").write_text("0.33.0\n", encoding="utf-8")

    kernel_dir = root / "framework" / "kernel"
    kernel_dir.mkdir(parents=True)
    (kernel_dir / "README.md").write_text("# Catalyst Kernel\n", encoding="utf-8")
    (kernel_dir / "INVARIANTS.md").write_text("# Invariants\n", encoding="utf-8")
    (root / "framework" / "modules").mkdir()
    (root / "framework" / "modules" / "catalog.md").write_text(
        "# Process module catalog\n\n"
        "| Id | Repository | Default branch |\n"
        "|---|---|---|\n"
        "| `example-process` | `git@example.com:x/catalyst-example-process.git` | `main` |\n"
        "| `absent-process` | `git@example.com:x/catalyst-absent-process.git` | `main` |\n",
        encoding="utf-8",
    )

    mod_dir = tmp_path / "catalyst-example-process"
    mod_dir.mkdir()
    (mod_dir / "version.txt").write_text("1.2.0\n", encoding="utf-8")
    (mod_dir / "module.yaml").write_text(
        "id: example-process\n"
        "name: Example Process Module\n"
        "version: 1.0.0\n"
        "description: A fictional module for tests.\n",
        encoding="utf-8",
    )
    (mod_dir / "README.md").write_text("# Module\n", encoding="utf-8")
    (mod_dir / ".git").mkdir()
    (mod_dir / ".git" / "HEAD").write_text("ref\n", encoding="utf-8")
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
    (root / "LICENSE").write_text("Apache License\n", encoding="utf-8")

    released = pr.package_modules(root)
    pr.package_kernel(root)

    # 1. Verify module output: staged in catalyst's own output, never in the module's repository (REQ-000112)
    mod_release_dir = root / "catalyst" / "modules" / "example-process" / "v1.2.0"
    assert not (mod_dir / "catalyst").exists()
    assert released == [mod_release_dir]
    manifest_data = json.loads((mod_release_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_data == {
        "id": "example-process",
        "name": "Example Process Module",
        "version": "1.2.0",
        "description": "A fictional module for tests.",
        "kernelVersion": ">=0.33.0",
        # Kept for extension builds that predate kernelVersion.
        "frameworkVersion": ">=0.33.0",
        # no `entry`: the module ships no built UI bundle
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
    kernel_manifest_data = json.loads((kernel_release_dir / "manifest.json").read_text(encoding="utf-8"))
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
    monkeypatch.setattr(pr, "run_cmd", lambda cmd, cwd: calls.append(cmd) or ("M x" if "status" in cmd else ""))
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

    readme = (publish_dir / "catalyst" / "modules" / "README.md").read_text(encoding="utf-8")
    assert "Example Process Module" in readme
    assert "example/" not in (publish_dir / "catalyst" / "README.md").read_text(encoding="utf-8")
    (publish_dir / "catalyst" / "example").mkdir()
    (publish_dir / "catalyst" / "example" / "README.md").write_text("# Example\n", encoding="utf-8")
    pr.publish_releases(root, publish_dir)
    assert "[example/](example/README.md)" in (publish_dir / "catalyst" / "README.md").read_text(encoding="utf-8")

    # 4. With push, only the publish directory is committed and pushed: nothing goes into a module repository
    pr.package_modules(root)
    pr.publish_releases(root, publish_dir, push=True)
    commits = [c for c in calls if c[:2] == ["git", "commit"]]
    assert [c[-1] for c in commits] == ["Deploy release: kernel v0.33.0, example-process module v1.2.0"]
    assert calls.count(["git", "push", "origin", "main"]) == 1  # publish directory
    assert not any("HEAD:main" in c or "worktree" in c for c in calls)
    assert not (mod_dir / "catalyst").exists()


def test_publish_releases_missing_dir(tmp_path: Path):
    root = make_workspace(tmp_path)
    assert pr.publish_releases(root, tmp_path / "absent") is None


def test_package_modules_skips_when_not_checked_out(tmp_path: Path, monkeypatch):
    root = tmp_path / "catalyst"
    (root / "framework" / "modules").mkdir(parents=True)
    (root / "version.txt").write_text("0.35.0\n", encoding="utf-8")
    (root / "framework" / "modules" / "catalog.md").write_text(
        "| Id | Repository | Default branch |\n|---|---|---|\n| `absent-process` | `x` | `main` |\n", encoding="utf-8"
    )
    monkeypatch.setattr(pr, "run_cmd", lambda cmd, cwd: "")
    assert pr.package_modules(root) == []


def test_package_modules_without_catalog(tmp_path: Path):
    root = tmp_path / "catalyst"
    root.mkdir()
    assert pr.package_modules(root) == []


def test_only_the_named_modules_are_packaged_and_published(tmp_path: Path, monkeypatch):
    """REQ-000112: --module packages and publishes only the modules asked for; the kernel can be left out."""
    root = make_workspace(tmp_path)
    other = tmp_path / "catalyst-other-process"
    other.mkdir()
    (other / "module.yaml").write_text("id: other-process\nname: Other\n", encoding="utf-8")
    (other / "version.txt").write_text("0.1.0\n", encoding="utf-8")
    catalog = root / "framework" / "modules" / "catalog.md"
    catalog.write_text(catalog.read_text(encoding="utf-8") + "| `other-process` | `x` | `main` |\n", encoding="utf-8")
    assert [m.id for m in pr.catalogued_modules(root)] == ["example-process", "other-process"]
    assert pr.package_modules(root, ["other-process"]) == [root / "catalyst" / "modules" / "other-process" / "v0.1.0"]
    assert not (root / "catalyst" / "modules" / "example-process").exists()
    publish_dir = tmp_path / "dist-repo"
    publish_dir.mkdir()
    pr.publish_releases(root, publish_dir, only=["other-process"], kernel=False)
    assert (publish_dir / "catalyst" / "modules" / "other-process" / "v0.1.0" / "manifest.json").is_file()
    assert not (publish_dir / "catalyst" / "modules" / "example-process").exists()
    assert not (publish_dir / "catalyst" / "kernel" / "v0.33.0").exists()

    monkeypatch.setattr(pr, "ROOT", root)
    assert pr.main(["--module", "nope-process"]) == 2


def test_publishing_refuses_a_module_checkout_not_at_its_tag(tmp_path: Path, monkeypatch, capsys):
    """Fleet fix plan 6.3: a module is published only from its release tag, unless --unreleased."""
    root = make_workspace(tmp_path)
    mod_dir = tmp_path / "catalyst-example-process"
    import shutil

    shutil.rmtree(mod_dir / ".git")

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=mod_dir, check=True, capture_output=True)

    git("init", "-q")
    git("-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "--allow-empty", "-m", "start")
    module = pr.module_info_at(mod_dir, "example-process")
    assert module is not None
    assert "example-process module 1.2.0 has no release tag" in (pr.unreleased_module(module) or "")
    git("tag", "v1.2.0")
    assert pr.unreleased_module(module) is None
    git("-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "--allow-empty", "-m", "after")
    assert "not at the 1.2.0 tag" in (pr.unreleased_module(module) or "")

    monkeypatch.setattr(pr, "ROOT", root)
    published = []
    monkeypatch.setattr(pr, "publish_releases", lambda *a, **k: published.append(a))
    monkeypatch.setattr(pr, "package_kernel", lambda *a, **k: root)
    assert pr.main(["--publish-dir", str(tmp_path), "--no-kernel"]) == 2
    assert "Refused: the example-process module checkout" in capsys.readouterr().out and not published
    assert pr.main(["--publish-dir", str(tmp_path), "--no-kernel", "--unreleased"]) == 0 and published


def test_the_manifest_names_a_ui_entry_only_when_the_bundle_ships(tmp_path: Path):
    """Fleet fix plan 6.4: `entry` only for a built bundle a release ships (module.yaml's `entry`, else ui/index.js)."""
    root = make_workspace(tmp_path)
    mod_dir = tmp_path / "catalyst-example-process"
    release = root / "catalyst" / "modules" / "example-process" / "v1.2.0"

    def manifest() -> dict:
        pr.package_modules(root)
        return json.loads((release / "manifest.json").read_text(encoding="utf-8"))

    (mod_dir / "ui").mkdir()
    (mod_dir / "ui" / "Backlog.tsx").write_text("export {}\n", encoding="utf-8")
    assert "entry" not in manifest()  # sources only
    (mod_dir / "ui" / "dist").mkdir()
    (mod_dir / "ui" / "dist" / "index.js").write_text("x\n", encoding="utf-8")
    with (mod_dir / "module.yaml").open("a") as f:
        f.write("entry: ui/dist/index.js\n")
    assert "entry" not in manifest()  # dist/ is not shipped
    (mod_dir / "ui" / "index.js").write_text("x\n", encoding="utf-8")
    yaml = (mod_dir / "module.yaml").read_text(encoding="utf-8").replace("entry: ui/dist/index.js\n", "")
    (mod_dir / "module.yaml").write_text(yaml, encoding="utf-8")
    assert manifest()["entry"] == "ui/index.js"
    (mod_dir / "ui" / "bundle.js").write_text("x\n", encoding="utf-8")
    (mod_dir / "module.yaml").write_text(yaml + "entry: ui/bundle.js\n", encoding="utf-8")
    assert manifest()["entry"] == "ui/bundle.js"
    with zipfile.ZipFile(release / "example-process-v1.2.0.zip") as zf:
        assert "ui/bundle.js" in zf.namelist()


def test_release_archives_are_reproducible(tmp_path: Path, monkeypatch):
    """Rebuilding an unchanged release gives byte-identical archives, so
    publishing it again commits nothing."""
    import os
    import time

    root = make_workspace(tmp_path)
    monkeypatch.setattr(pr, "run_cmd", lambda cmd, cwd: "")
    (root / "LICENSE").write_text("Apache License\n", encoding="utf-8")
    mod_zip = root / "catalyst" / "modules" / "example-process" / "v1.2.0" / "example-process-v1.2.0.zip"
    kernel_dir = root / "catalyst" / "kernel" / "v0.33.0"

    pr.package_modules(root)
    pr.package_kernel(root)
    first = {p: p.read_bytes() for p in (mod_zip, kernel_dir / "kernel-v0.33.0.zip", kernel_dir / "catalyst.pyz")}
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
    release = root / "catalyst" / "modules" / "example-process" / "v1.2.0"

    pr.package_modules(root)
    manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["kernelVersion"] == manifest["frameworkVersion"] == ">=0.30.0"
    first = {p.name: p.read_bytes() for p in release.iterdir()}
    assert "declares no kernel_version" not in capsys.readouterr().out

    (root / "version.txt").write_text("0.99.0\n", encoding="utf-8")  # a newer kernel packages it again
    pr.package_modules(root)
    assert {p.name: p.read_bytes() for p in release.iterdir()} == first


def test_a_module_without_a_declaration_falls_back_with_a_warning(tmp_path: Path, capsys):
    root = make_workspace(tmp_path)
    pr.package_modules(root)
    out = capsys.readouterr().out
    assert "example-process declares no kernel_version" in out and ">=0.33.0" in out


def test_publishing_refuses_a_kernel_that_is_not_a_tagged_release(tmp_path: Path, monkeypatch, capsys):
    """`--publish-dir` publishes only a tagged release, from a checkout at its tag: a development checkout whose
    version is ahead of its last tag would otherwise publish an unreleased kernel (catalyst-docs' report)."""
    root = make_workspace(tmp_path)

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)

    git("init", "-q")
    git("-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "--allow-empty", "-m", "start")
    assert "has no release tag" in (pr.unreleased_kernel(root) or "")
    git("tag", "0.33.0")
    assert pr.unreleased_kernel(root) is None
    git("-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "--allow-empty", "-m", "after the release")
    assert "not at the 0.33.0 tag" in (pr.unreleased_kernel(root) or "")
    monkeypatch.setattr(pr, "ROOT", root)
    published = []
    monkeypatch.setattr(pr, "publish_releases", lambda *a, **k: published.append(a))
    monkeypatch.setattr(pr, "package_modules", lambda *a, **k: [])
    monkeypatch.setattr(pr, "package_kernel", lambda *a, **k: root)
    assert pr.main(["--publish-dir", str(tmp_path)]) == 2
    out = capsys.readouterr().out
    assert "Refused: the kernel checkout" in out and "is not at the 0.33.0 tag" in out and not published
    assert pr.main(["--publish-dir", str(tmp_path), "--unreleased"]) == 0 and published
