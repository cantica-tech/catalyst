import json
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
    # Mock run_cmd to prevent git push in unit test
    monkeypatch.setattr(pr, "run_cmd", lambda cmd, cwd: calls.append(cmd) or "")

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
    assert ["git", "add", "catalyst"] in calls

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
        assert not any(n.startswith("modules/") for n in namelist)

    # 3. Verify cantica-tech deployment
    cantica_dir = tmp_path / "cantica-tech"
    cantica_dir.mkdir()
    calls.clear()
    monkeypatch.setattr(pr, "run_cmd",
                        lambda cmd, cwd: calls.append(cmd) or ("M x" if "status" in cmd else ""))
    pr.deploy_to_cantica_tech(root)

    cantica_kernel_dir = cantica_dir / "catalyst" / "kernel" / "v0.33.0"
    assert (cantica_kernel_dir / "manifest.json").is_file()
    assert (cantica_kernel_dir / "kernel-v0.33.0.zip").is_file()

    cantica_mod_dir = cantica_dir / "catalyst" / "modules" / "example-process" / "v1.2.0"
    assert (cantica_mod_dir / "manifest.json").is_file()
    assert (cantica_mod_dir / "example-process-v1.2.0.zip").is_file()
    assert not (cantica_dir / "catalyst" / "modules" / "absent-process").exists()

    commit = next(c for c in calls if c[:2] == ["git", "commit"])
    assert commit[-1] == "Deploy release: kernel v0.33.0, example-process module v1.2.0"

    readme = (cantica_dir / "catalyst" / "modules" / "README.md").read_text()
    assert "Example Process Module" in readme


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
