#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_git(args: list[str], cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True, encoding="utf-8")


def load_submodule_entries(root: Path) -> list[tuple[str, str]]:
    gitmodules = root / ".gitmodules"
    if not gitmodules.exists():
        return []
    entries: list[tuple[str, str]] = []
    current = None
    for raw in gitmodules.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
        elif current and line.startswith("path = "):
            path = line.split("=", 1)[1].strip()
            entries.append((current, path))
    return entries


def validate_plugin_structure(root: Path) -> list[str]:
    errors: list[str] = []
    plugin_root = root / "framework" / "kernel" / "plugins" / "repository"
    if not plugin_root.exists():
        return ["framework/kernel/plugins/repository directory is missing"]

    for path in sorted(plugin_root.iterdir()):
        if not path.is_dir():
            continue
        if path.name.startswith("."):
            continue
        readme = path / "README.md"
        contract = path / "working-contract.md"
        if not readme.exists():
            errors.append(f"{path.relative_to(root)}/README.md is missing")
        if not contract.exists():
            errors.append(f"{path.relative_to(root)}/working-contract.md is missing")

    return errors


def validate_submodule_policy(root: Path) -> list[str]:
    errors: list[str] = []
    entries = load_submodule_entries(root)
    plugin_entries = [(name, path) for name, path in entries if path.startswith("framework/kernel/plugins/")]
    for _, path in plugin_entries:
        if not (root / path).exists():
            errors.append(f"{path} is not present in the workspace")
    return errors


def parse_submodule_status(status: str, plugin_paths: set[str]) -> list[str]:
    """Pure parse of `git submodule status` output. A leading '-' means the
    submodule is not initialized/checked out; only flagged for tracked plugin
    paths."""
    errors: list[str] = []
    for line in status.splitlines():
        if not line.strip():
            continue
        prefix = line[0]
        path = line[1:].split()[1]
        if path in plugin_paths and prefix == "-":
            errors.append(f"{path} is not initialized or checked out")
    return errors


def validate_plugin_sources(root: Path) -> list[str]:
    entries = load_submodule_entries(root)
    plugin_paths = {path for _, path in entries if path.startswith("framework/kernel/plugins/")}
    try:
        status = run_git(["submodule", "status"], cwd=root)
    except subprocess.CalledProcessError as exc:
        return [f"git submodule status failed: {exc}"]
    return parse_submodule_status(status, plugin_paths)


def main() -> int:
    errors = []
    errors.extend(validate_plugin_structure(ROOT))
    errors.extend(validate_submodule_policy(ROOT))
    errors.extend(validate_plugin_sources(ROOT))

    if errors:
        print("Plugin rule validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Plugin rules validated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
