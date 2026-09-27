#!/usr/bin/env python3
"""Package the kernel and modules into versioned zipped archives with manifests.

The catalyst framework is the kernel (framework/kernel/, everything
independent of process modules) plus its process modules
(framework/modules/). Each ships as its own versioned release.

1. Every module listed in framework/modules/catalog.md, from its own
   repository checked out as a sibling of catalyst (../catalyst-<id>/).
   Modules are full repositories, not catalyst submodules; a module that is
   not checked out is skipped. Id, name and description come from the
   module's module.yaml, its version from its version.txt.
   - Zips the module contents (excluding .git, node_modules, catalyst output).
   - Includes manifest.json inside the zip and alongside it.
   - Saves to <module repo>/catalyst/modules/<id>/v[version]/
   - Commits and pushes changes to origin main of the module repository.

2. Catalyst Kernel:
   - Zips framework/kernel/.
   - Includes manifest.json inside the zip and alongside it.
   - Saves to catalyst/kernel/v[version]/ at the root workspace.
"""
from __future__ import annotations

import json
import os
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path

from check_kernel_purity import catalog_module_ids
from module_loader import parse_simple_yaml

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class ModuleInfo:
    id: str
    name: str
    description: str
    version: str
    dir: Path


def module_repo_dir(root: Path, module_id: str) -> Path:
    """Process modules live in their own repositories, checked out next to
    catalyst as catalyst-<id>/."""
    return root.parent / f"catalyst-{module_id}"


def read_module_info(root: Path, module_id: str) -> ModuleInfo | None:
    """The module's identity from its sibling checkout's module.yaml and
    version.txt, or None if it is not checked out."""
    module_dir = module_repo_dir(root, module_id)
    manifest = module_dir / "module.yaml"
    if not manifest.is_file():
        return None
    data = parse_simple_yaml(manifest.read_text(encoding="utf-8"))
    data = data if isinstance(data, dict) else {}
    version_file = module_dir / "version.txt"
    if version_file.is_file():
        version = version_file.read_text(encoding="utf-8").strip()
    else:
        version = str(data.get("version") or "1.0.0")
    mid = str(data.get("id") or module_id)
    return ModuleInfo(
        id=mid,
        name=str(data.get("name") or mid),
        description=str(data.get("description") or ""),
        version=version,
        dir=module_dir,
    )


def catalogued_modules(root: Path) -> list[ModuleInfo]:
    """Modules listed in framework/modules/catalog.md that are checked out."""
    catalog = root / "framework" / "modules" / "catalog.md"
    found: list[ModuleInfo] = []
    for module_id in catalog_module_ids(catalog):
        info = read_module_info(root, module_id)
        if info is None:
            print(f"Skipping module {module_id}: not checked out at "
                  f"{module_repo_dir(root, module_id)}")
            continue
        found.append(info)
    return found


def run_cmd(cmd: list[str], cwd: Path) -> str:
    res = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=True)
    return res.stdout.strip()


def package_module(root: Path, module: ModuleInfo) -> Path:
    module_dir = module.dir
    kernel_version = read_kernel_version(root)

    dest_dir = module_dir / "catalyst" / "modules" / module.id / f"v{module.version}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    manifest_data = {
        "id": module.id,
        "name": module.name,
        "version": module.version,
        "description": module.description,
        "kernelVersion": f">={kernel_version}",
        # Legacy name of kernelVersion. Host UIs that predate kernelVersion
        # only read this field and skip manifests without it.
        "frameworkVersion": f">={kernel_version}",
        "entry": "ui/index.js"
    }

    manifest_json_bytes = json.dumps(manifest_data, indent=2).encode("utf-8")

    # Save manifest.json outside zip
    manifest_file = dest_dir / "manifest.json"
    manifest_file.write_bytes(manifest_json_bytes)

    # Save zip
    zip_path = dest_dir / f"{module.id}-v{module.version}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add manifest.json to zip
        zf.writestr("manifest.json", manifest_json_bytes)

        # Add module contents
        for file in module_dir.rglob("*"):
            if not file.is_file():
                continue
            rel_path = file.relative_to(module_dir)
            parts = rel_path.parts
            if any(p.startswith(".") or p in ("node_modules", "dist", "catalyst") for p in parts):
                continue
            zf.write(file, arcname=str(rel_path))

    # Remove legacy unversioned zip if present
    canonical_zip_path = dest_dir / f"{module.id}.zip"
    if canonical_zip_path.is_file():
        canonical_zip_path.unlink()

    print(f"Packaged {module.id} module v{module.version} -> {dest_dir}")

    # Commit and push in the module repository
    try:
        run_cmd(["git", "add", "catalyst"], cwd=module_dir)
        status = run_cmd(["git", "status", "--porcelain"], cwd=module_dir)
        if status:
            run_cmd(["git", "commit", "-m", f"Release {module.id} module v{module.version}"], cwd=module_dir)
            run_cmd(["git", "push", "origin", "main"], cwd=module_dir)
            print(f"Committed and pushed module release from {module_dir}")
        else:
            print(f"No changes to commit in {module.id} module repository.")
    except Exception as exc:
        print(f"Warning: Git commit/push in module repository failed: {exc}")

    return dest_dir


def package_modules(root: Path) -> list[Path]:
    """Package every catalogued module that is checked out."""
    return [package_module(root, m) for m in catalogued_modules(root)]


def read_kernel_version(root: Path) -> str:
    """The kernel version: catalyst's root version.txt."""
    version_file = root / "version.txt"
    return version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else "0.35.0"


def package_kernel(root: Path) -> Path:
    kernel_dir = root / "framework" / "kernel"
    kernel_version = read_kernel_version(root)

    dest_dir = root / "catalyst" / "kernel" / f"v{kernel_version}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    manifest_data = {
        "id": "catalyst-kernel",
        "name": "Catalyst Kernel",
        "version": kernel_version,
        "description": "Catalyst kernel: the module-independent part of the framework (specifications, templates, definitions, and plugins)."
    }

    manifest_json_bytes = json.dumps(manifest_data, indent=2).encode("utf-8")

    # Save manifest.json outside zip
    manifest_file = dest_dir / "manifest.json"
    manifest_file.write_bytes(manifest_json_bytes)

    # Save zip
    zip_path = dest_dir / f"kernel-v{kernel_version}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add manifest.json to zip
        zf.writestr("manifest.json", manifest_json_bytes)

        # Add kernel contents
        for file in kernel_dir.rglob("*"):
            if not file.is_file():
                continue
            rel_path = file.relative_to(kernel_dir)
            parts = rel_path.parts
            if any(p.startswith(".") or p in ("node_modules", "dist", "catalyst") for p in parts):
                continue
            zf.write(file, arcname=str(rel_path))

    # Remove legacy unversioned zip if present
    canonical_zip_path = dest_dir / "kernel.zip"
    if canonical_zip_path.is_file():
        canonical_zip_path.unlink()

    print(f"Packaged kernel v{kernel_version} -> {dest_dir}")
    return dest_dir


def update_cantica_tech_readmes(cantica_dir: Path) -> None:
    catalyst_dir = cantica_dir / "catalyst"
    catalyst_dir.mkdir(parents=True, exist_ok=True)

    # 1. Root cantica-tech/README.md
    root_readme = cantica_dir / "README.md"
    root_readme.write_text(
        "# CanticaTech Release Artifacts Repository\n\n"
        "This repository serves as the central distribution repository for CanticaTech release artifacts, specifications, kernel releases, and process modules.\n\n"
        "## Repository Structure\n\n"
        "- **[catalyst/](catalyst/README.md)**: Official release archives, versioned manifests, and distribution packages for the Catalyst kernel and process modules.\n",
        encoding="utf-8"
    )

    # 2. catalyst/README.md
    cat_readme = catalyst_dir / "README.md"
    cat_readme.write_text(
        "# Catalyst Kernel & Module Releases\n\n"
        "This directory contains official versioned release packages and manifests for the Catalyst framework: its kernel and its process modules.\n\n"
        "## Release Categories\n\n"
        "- **[kernel/](kernel/README.md)**: Catalyst kernel releases (the module-independent part of the framework: specifications, templates, definitions, and plugins).\n"
        "- **[modules/](modules/README.md)**: Catalyst process modules, one directory per module id.\n",
        encoding="utf-8"
    )

    # 3. catalyst/kernel/README.md
    kernel_dir = catalyst_dir / "kernel"
    kernel_dir.mkdir(parents=True, exist_ok=True)
    kernel_releases = []
    for v_dir in sorted(kernel_dir.glob("v*"), reverse=True):
        if not v_dir.is_dir():
            continue
        manifest_file = v_dir / "manifest.json"
        if manifest_file.is_file():
            try:
                m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                v_name = v_dir.name
                version = m_data.get("version", v_name.lstrip("v"))
                desc = m_data.get("description", "Catalyst kernel release")
                zip_file = f"{v_name}/kernel-{v_name}.zip"
                manifest_rel = f"{v_name}/manifest.json"
                kernel_releases.append(f"| `{v_name}` | [`{manifest_rel}`]({manifest_rel}) | [`{zip_file}`]({zip_file}) | {desc} |")
            except Exception:
                pass

    kernel_readme_lines = [
        "# Catalyst Kernel Releases",
        "",
        "This directory contains versioned releases of the Catalyst kernel (the module-independent part of the framework: specifications, templates, definitions, and plugins).",
        "",
        "## Available Kernel Releases",
        "",
        "| Version | Manifest | Archive | Description |",
        "| ------- | -------- | ------- | ----------- |",
    ]
    if kernel_releases:
        kernel_readme_lines.extend(kernel_releases)
    else:
        kernel_readme_lines.append("| *(none)* | - | - | - |")

    (kernel_dir / "README.md").write_text("\n".join(kernel_readme_lines) + "\n", encoding="utf-8")

    # 4. catalyst/modules/README.md & 5. catalyst/modules/<module>/README.md
    mod_root_dir = catalyst_dir / "modules"
    mod_root_dir.mkdir(parents=True, exist_ok=True)

    module_overview_rows = []

    for mod_dir in sorted(mod_root_dir.iterdir()):
        if not mod_dir.is_dir():
            continue
        mod_id = mod_dir.name
        mod_v_dirs = sorted(mod_dir.glob("v*"), reverse=True)
        if not mod_v_dirs:
            continue

        mod_releases = []
        latest_info = None

        for v_dir in mod_v_dirs:
            if not v_dir.is_dir():
                continue
            manifest_file = v_dir / "manifest.json"
            if manifest_file.is_file():
                try:
                    m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                    v_name = v_dir.name
                    mod_name = m_data.get("name", mod_id)
                    # "frameworkVersion" is the pre-0.35.0 name of "kernelVersion".
                    kernel_req = m_data.get("kernelVersion", m_data.get("frameworkVersion", "*"))
                    desc = m_data.get("description", f"{mod_name} release")
                    zip_file = f"{v_name}/{mod_id}-{v_name}.zip"
                    manifest_rel = f"{v_name}/manifest.json"
                    mod_releases.append(f"| `{v_name}` | `{kernel_req}` | [`{manifest_rel}`]({manifest_rel}) | [`{zip_file}`]({zip_file}) | {desc} |")

                    if latest_info is None:
                        latest_info = {
                            "name": mod_name,
                            "version": v_name,
                            "kernel_req": kernel_req,
                            "rel_dir": f"{mod_id}/",
                        }
                except Exception:
                    pass

        # Write module-specific README
        mod_readme_lines = [
            f"# {latest_info['name'] if latest_info else mod_id} Releases",
            "",
            f"This directory contains versioned releases for the `{mod_id}` process module.",
            "",
            "## Available Releases",
            "",
            "| Version | Requires Kernel | Manifest | Archive | Description |",
            "| ------- | --------------- | -------- | ------- | ----------- |",
        ]
        if mod_releases:
            mod_readme_lines.extend(mod_releases)
        else:
            mod_readme_lines.append("| *(none)* | - | - | - | - |")

        (mod_dir / "README.md").write_text("\n".join(mod_readme_lines) + "\n", encoding="utf-8")

        if latest_info:
            module_overview_rows.append(
                f"| {latest_info['name']} | `{latest_info['version']}` | `{latest_info['kernel_req']}` | [`{latest_info['rel_dir']}`]({latest_info['rel_dir']}README.md) |"
            )

    mod_overview_lines = [
        "# Catalyst Process Modules",
        "",
        "This directory contains versioned process modules for the Catalyst framework.",
        "",
        "## Available Process Modules",
        "",
        "| Module | Latest Version | Requires Kernel | Directory |",
        "| ------ | -------------- | --------------- | --------- |",
    ]
    if module_overview_rows:
        mod_overview_lines.extend(module_overview_rows)
    else:
        mod_overview_lines.append("| *(none)* | - | - | - |")

    (mod_root_dir / "README.md").write_text("\n".join(mod_overview_lines) + "\n", encoding="utf-8")


def deploy_to_cantica_tech(root: Path) -> Path | None:
    cantica_dir = root.parent / "cantica-tech"
    if not cantica_dir.is_dir():
        print(f"Warning: cantica-tech repository directory not found at {cantica_dir}")
        return None

    kernel_version = read_kernel_version(root)

    # (source, target) directory pairs: the kernel, then each catalogued module.
    kernel_src = root / "catalyst" / "kernel" / f"v{kernel_version}"
    kernel_dest = cantica_dir / "catalyst" / "kernel" / f"v{kernel_version}"
    pairs = [(kernel_src, kernel_dest)]
    released = [f"kernel v{kernel_version}"]
    for module in catalogued_modules(root):
        rel = Path("catalyst") / "modules" / module.id / f"v{module.version}"
        mod_src = module.dir / rel
        pairs.append((mod_src, cantica_dir / rel))
        if mod_src.is_dir():
            released.append(f"{module.id} module v{module.version}")

    # Copy release files and clean up obsolete ones
    for src, dest in pairs:
        if src.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            src_names = {f.name for f in src.glob("*") if f.is_file()}
            for f in dest.glob("*"):
                if f.is_file() and f.name not in src_names:
                    f.unlink()
            for f in src.glob("*"):
                if f.is_file():
                    (dest / f.name).write_bytes(f.read_bytes())

    # Update README documentation and release tables in cantica-tech
    update_cantica_tech_readmes(cantica_dir)

    print(f"Deployed release artifacts to cantica-tech repository at {cantica_dir}")

    # Commit and push in cantica-tech
    try:
        run_cmd(["git", "add", "catalyst"], cwd=cantica_dir)
        status = run_cmd(["git", "status", "--porcelain"], cwd=cantica_dir)
        if status:
            run_cmd(["git", "commit", "-m", f"Deploy release: {', '.join(released)}"], cwd=cantica_dir)
            run_cmd(["git", "push", "origin", "main"], cwd=cantica_dir)
            print("Committed and pushed release to git@github.com:oliben67/cantica-tech.git")
        else:
            print("No changes to commit in cantica-tech repository.")
    except Exception as exc:
        print(f"Warning: Git commit/push in cantica-tech repository failed: {exc}")

    return cantica_dir


def main() -> int:
    print("Starting release packaging...")
    package_modules(ROOT)
    package_kernel(ROOT)
    deploy_to_cantica_tech(ROOT)
    print("Release packaging and deployment completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
