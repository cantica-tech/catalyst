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
   - With --push only: commits it onto origin main of the module
     repository, through a temporary worktree (whatever branch the
     checkout is on), and pushes it.

2. Catalyst Kernel:
   - Zips framework/kernel/, plus the `catalyst` CLI as bin/catalyst.pyz.
   - Includes manifest.json inside the zip and alongside it.
   - Saves to catalyst/kernel/v[version]/ at the root workspace.

3. With --publish-dir DIR: copies every release into DIR/catalyst/ (a
   distribution repository checkout) and refreshes its release READMEs;
   with --push as well, commits and pushes DIR to origin main.

Nothing is committed or pushed without --push (INV-4: no push without the
user's explicit assent).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
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
    kernel_version: str | None = None      # module.yaml's declared requirement


def module_repo_dir(root: Path, module_id: str) -> Path:
    """Process modules live in their own repositories, checked out next to
    catalyst as catalyst-<id>/."""
    return root.parent / f"catalyst-{module_id}"


def read_module_info(root: Path, module_id: str) -> ModuleInfo | None:
    """The module's identity from its sibling checkout's module.yaml and
    version.txt, or None if it is not checked out."""
    return module_info_at(module_repo_dir(root, module_id), module_id)


def module_info_at(module_dir: Path, module_id: str | None = None) -> ModuleInfo | None:
    """A module checkout's identity, wherever it is."""
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
    mid = str(data.get("id") or module_id or module_dir.name)
    return ModuleInfo(
        id=mid,
        name=str(data.get("name") or mid),
        description=str(data.get("description") or ""),
        version=version,
        dir=module_dir,
        kernel_version=str(data["kernel_version"]) if data.get("kernel_version") else None,
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



# Archives are reproducible: fixed entry timestamps, sorted entries and
# normalised permissions, so rebuilding an unchanged release yields the same
# bytes (and publishing it again commits nothing).
ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def zip_bytes(zf: zipfile.ZipFile, arcname: str, data: bytes, executable: bool = False) -> None:
    info = zipfile.ZipInfo(arcname, ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o100755 if executable else 0o100644) << 16
    zf.writestr(info, data)


def zip_file(zf: zipfile.ZipFile, path: Path, arcname: str) -> None:
    zip_bytes(zf, arcname, path.read_bytes(), executable=os.access(path, os.X_OK))


def run_cmd(cmd: list[str], cwd: Path) -> str:
    res = subprocess.run(cmd, cwd=cwd, text=True, encoding="utf-8", capture_output=True, check=True)
    return res.stdout.strip()


def shipped_files(src: Path):
    """(file, archive name) for what a release ships from `src`: no hidden
    files, no node_modules, dist or packaged releases (`catalyst/`)."""
    for file in sorted(src.rglob("*")):
        if not file.is_file():
            continue
        rel_path = file.relative_to(src)
        if any(p.startswith(".") or p in ("node_modules", "dist", "catalyst") for p in rel_path.parts):
            continue
        yield file, rel_path.as_posix()


def module_manifest(module: ModuleInfo, requires: str) -> dict:
    return {
        "id": module.id,
        "name": module.name,
        "version": module.version,
        "description": module.description,
        "kernelVersion": requires,
        # Legacy name of kernelVersion. Host UIs that predate kernelVersion
        # only read this field and skip manifests without it.
        "frameworkVersion": requires,
        "entry": "ui/index.js"
    }


def package_module(root: Path, module: ModuleInfo, push: bool = False) -> Path:
    module_dir = module.dir
    # The module's own declaration; the packaging kernel only when it has none
    # (and then the release claims more than the module may need).
    requires = module.kernel_version
    if not requires:
        requires = f">={read_kernel_version(root)}"
        print(f"Warning: {module.id} declares no kernel_version in module.yaml — its manifest "
              f"says {requires}, the kernel packaging it")

    dest_dir = module_dir / "catalyst" / "modules" / module.id / f"v{module.version}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    manifest_data = module_manifest(module, requires)

    manifest_json_bytes = json.dumps(manifest_data, indent=2).encode("utf-8")

    # Save manifest.json outside zip
    manifest_file = dest_dir / "manifest.json"
    manifest_file.write_bytes(manifest_json_bytes)

    # Save zip
    zip_path = dest_dir / f"{module.id}-v{module.version}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add manifest.json to zip
        zip_bytes(zf, "manifest.json", manifest_json_bytes)

        # Add module contents
        for file, arcname in shipped_files(module_dir):
            zip_file(zf, file, arcname)

    # Remove legacy unversioned zip if present
    canonical_zip_path = dest_dir / f"{module.id}.zip"
    if canonical_zip_path.is_file():
        canonical_zip_path.unlink()

    print(f"Packaged {module.id} module v{module.version} -> {dest_dir}")

    if not push:
        return dest_dir

    try:
        commit_module_release(module, dest_dir)
    except Exception as exc:
        print(f"Warning: Git commit/push in module repository failed: {exc}")

    return dest_dir


def commit_module_release(module: ModuleInfo, dest_dir: Path) -> None:
    """Commit the packaged release onto the module repository's origin main
    and push it, through a temporary worktree: the module checkout is
    usually on development, whose branch must not receive the archive (and
    pushing main from that checkout would push a stale local main)."""
    module_dir = module.dir
    rel = dest_dir.relative_to(module_dir)
    run_cmd(["git", "fetch", "origin", "main"], cwd=module_dir)
    with tempfile.TemporaryDirectory() as tmp:
        worktree = Path(tmp) / "main"
        run_cmd(["git", "worktree", "add", "--detach", str(worktree), "origin/main"], cwd=module_dir)
        try:
            target = worktree / rel
            target.mkdir(parents=True, exist_ok=True)
            for f in dest_dir.iterdir():
                if f.is_file():
                    shutil.copy2(f, target / f.name)
            run_cmd(["git", "add", "-f", str(rel)], cwd=worktree)
            status = run_cmd(["git", "status", "--porcelain"], cwd=worktree)
            if status:
                run_cmd(["git", "commit", "-m", f"Release {module.id} module v{module.version}"], cwd=worktree)
                run_cmd(["git", "push", "origin", "HEAD:main"], cwd=worktree)
                print(f"Committed and pushed module release to {module.id} origin main")
            else:
                print(f"No changes to commit in {module.id} module repository.")
        finally:
            run_cmd(["git", "worktree", "remove", "--force", str(worktree)], cwd=module_dir)


def package_modules(root: Path, push: bool = False) -> list[Path]:
    """Package every catalogued module that is checked out."""
    return [package_module(root, m, push) for m in catalogued_modules(root)]


def read_kernel_version(root: Path) -> str:
    """The kernel version: catalyst's root version.txt."""
    version_file = root / "version.txt"
    return version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else "0.35.0"


CLI_MODULES = ("module_loader.py", "check_deployment.py", "project_file.py")


def build_id(root: Path) -> str:
    """What a build is made from, so two builds of one version can be told
    apart: `g<short sha>` of `root`'s HEAD, `.dirty` when the files a build
    embeds differ from it; "" outside git."""
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "--short=12", "HEAD"],
                          capture_output=True, text=True, encoding="utf-8")
    if head.returncode != 0 or not head.stdout.strip():
        return ""
    dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no",
                            "--", "scripts", "framework/kernel/entities", "version.txt"],
                           capture_output=True, text=True, encoding="utf-8")
    return f"g{head.stdout.strip()}" + (".dirty" if dirty.returncode != 0 or dirty.stdout.strip() else "")


def build_cli(root: Path, dest: Path) -> Path:
    """Build the single-file `catalyst` CLI zipapp at `dest`: the
    scripts/catalyst package, the modules it imports, the kernel's entity
    types embedded as data (a deployment has no framework/kernel/entities/),
    the kernel version and the build's commit (`build_id`), which
    `catalyst --version` reports as `<version>+g<sha>[.dirty]`."""
    kernel_version = read_kernel_version(root)
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)
        scripts = Path(__file__).resolve().parent     # the CLI's own sources
        shutil.copytree(scripts / "catalyst", stage / "catalyst",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in CLI_MODULES:
            shutil.copy2(scripts / name, stage / name)
        entities = {p.name: p.read_text(encoding="utf-8")
                    for p in sorted((root / "framework" / "kernel" / "entities").glob("*.yaml"))}
        (stage / "kernel_entities_embedded.py").write_text(
            '"""Generated by package_release.py: the kernel\'s entity types."""\n'
            f"ENTITIES = {entities!r}\n", encoding="utf-8")
        (stage / "catalyst" / "_build.py").write_text(
            f'VERSION = "{kernel_version}"\nBUILD = "{build_id(root)}"\n', encoding="utf-8")
        # Our own entry point: zipapp's generated one discards main()'s
        # return value, so every run would exit 0 and a hook could never block.
        (stage / "__main__.py").write_text(
            "import sys\n\nfrom catalyst.__main__ import main\n\nsys.exit(main())\n",
            encoding="utf-8")
        dest.parent.mkdir(parents=True, exist_ok=True)
        # What zipapp.create_archive writes, minus the build-time timestamps.
        with dest.open("wb") as fh:
            fh.write(b"#!/usr/bin/env python3\n")
            with zipfile.ZipFile(fh, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in sorted(stage.rglob("*")):
                    if path.is_file():
                        zip_file(zf, path, path.relative_to(stage).as_posix())
        dest.chmod(0o755)
    return dest


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
        zip_bytes(zf, "manifest.json", manifest_json_bytes)

        # Add kernel contents
        for file in sorted(kernel_dir.rglob("*")):
            if not file.is_file():
                continue
            rel_path = file.relative_to(kernel_dir)
            parts = rel_path.parts
            if any(p.startswith(".") or p in ("node_modules", "dist", "catalyst") for p in parts):
                continue
            zip_file(zf, file, rel_path.as_posix())

        # The kernel's command files (never /dogfood) and the agent
        # templates, so an install or a sync from a release has them.
        for file in sorted((root / ".claude" / "commands").glob("*.md")):
            if file.stem != "dogfood":
                zip_file(zf, file, f"commands/{file.name}")
        for file in sorted((root / "agents").rglob("*")):
            if file.is_file() and not any(p.startswith(".") for p in file.relative_to(root).parts):
                zip_file(zf, file, file.relative_to(root).as_posix())

        # The CLI, vendored by install and /sync-framework into
        # .criterion/bin/catalyst.pyz.
        cli = build_cli(root, dest_dir / "catalyst.pyz")
        zip_file(zf, cli, "bin/catalyst.pyz")

        # The kernel ships under catalyst's own license.
        license_file = root / "LICENSE"
        if license_file.is_file():
            zip_file(zf, license_file, "LICENSE")

    # Remove legacy unversioned zip if present
    canonical_zip_path = dest_dir / "kernel.zip"
    if canonical_zip_path.is_file():
        canonical_zip_path.unlink()

    print(f"Packaged kernel v{kernel_version} -> {dest_dir}")
    return dest_dir


def update_publish_readmes(publish_dir: Path) -> None:
    """Refresh the release READMEs under publish_dir/catalyst/. The
    distribution repository's own root README is left to that repository."""
    catalyst_dir = publish_dir / "catalyst"
    catalyst_dir.mkdir(parents=True, exist_ok=True)

    # 1. catalyst/README.md
    cat_readme = catalyst_dir / "README.md"
    cat_readme.write_text(
        "# Catalyst Kernel & Module Releases\n\n"
        "This directory contains official versioned release packages and manifests for the Catalyst framework: its kernel and its process modules.\n\n"
        "## Release Categories\n\n"
        "- **[kernel/](kernel/README.md)**: Catalyst kernel releases (the module-independent part of the framework: specifications, templates, definitions, and plugins).\n"
        "- **[modules/](modules/README.md)**: Catalyst process modules, one directory per module id.\n"
        + ("- **[vsix/](vsix/README.md)**: VS Code extension releases (`.vsix`), each with the kernel versions it works with.\n"
           if (catalyst_dir / "vsix" / "README.md").is_file() else "")
        + ("- **[example/](example/README.md)**: a small project governed by catalyst, end to end.\n"
           if (catalyst_dir / "example" / "README.md").is_file() else ""),
        encoding="utf-8"
    )

    # 2. catalyst/kernel/README.md
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

    # 3. catalyst/modules/README.md & 4. catalyst/modules/<module>/README.md
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


def publish_releases(root: Path, publish_dir: Path, push: bool = False) -> Path | None:
    """Copy the kernel and every catalogued module release into
    publish_dir/catalyst/ and refresh its release READMEs; with push, commit
    and push publish_dir to origin main."""
    if not publish_dir.is_dir():
        print(f"Warning: publish directory not found at {publish_dir}")
        return None

    kernel_version = read_kernel_version(root)

    # (source, target) directory pairs: the kernel, then each catalogued module.
    kernel_src = root / "catalyst" / "kernel" / f"v{kernel_version}"
    kernel_dest = publish_dir / "catalyst" / "kernel" / f"v{kernel_version}"
    pairs = [(kernel_src, kernel_dest)]
    released = [f"kernel v{kernel_version}"]
    for module in catalogued_modules(root):
        rel = Path("catalyst") / "modules" / module.id / f"v{module.version}"
        mod_src = module.dir / rel
        pairs.append((mod_src, publish_dir / rel))
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

    update_publish_readmes(publish_dir)

    print(f"Published release artifacts to {publish_dir}")

    if not push:
        return publish_dir

    try:
        run_cmd(["git", "add", "catalyst"], cwd=publish_dir)
        status = run_cmd(["git", "status", "--porcelain"], cwd=publish_dir)
        if status:
            run_cmd(["git", "commit", "-m", f"Deploy release: {', '.join(released)}"], cwd=publish_dir)
            run_cmd(["git", "push", "origin", "main"], cwd=publish_dir)
            print(f"Committed and pushed release from {publish_dir}")
        else:
            print(f"No changes to commit in {publish_dir}.")
    except Exception as exc:
        print(f"Warning: Git commit/push in {publish_dir} failed: {exc}")

    return publish_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--publish-dir", type=Path,
                        help="distribution repository checkout to copy releases into")
    parser.add_argument("--push", action="store_true",
                        help="commit and push the module repositories and the publish directory")
    args = parser.parse_args(argv)

    print("Starting release packaging...")
    package_modules(ROOT, args.push)
    package_kernel(ROOT)
    if args.publish_dir:
        publish_releases(ROOT, args.publish_dir.expanduser().resolve(), args.push)
    print("Release packaging completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
