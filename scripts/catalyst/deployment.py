"""Locate a deployment and the entity types that govern it.

A deployment is a project root (the directory holding the `*.catalyst`
pointer) plus its working copy, reached through `<project root>/.criterion`
(INV-6). Its entity types are the kernel's (framework/kernel/entities/, or the copy
module_loader finds embedded in the zipapp) plus the active module's ETDs.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from check_deployment import find_deploy_root, find_project_root
from module_loader import ETD, ModuleManifest, load_kernel_entities, load_module


class DeploymentNotFound(Exception):
    """No catalyst project at or above the start directory."""


class WorkingCopyMissing(DeploymentNotFound):
    """A project pointer exists, but its working copy is not reachable."""


def logical_cwd() -> Path:
    """The current directory as the shell sees it: through the .criterion
    symlink rather than into agent-owned space, so the project is found."""
    pwd = os.environ.get("PWD")
    cwd = os.getcwd()
    if pwd and os.path.isabs(pwd) and os.path.realpath(pwd) == os.path.realpath(cwd):
        return Path(pwd)
    return Path(cwd)


@dataclass
class Deployment:
    project_root: Path
    root: Path                      # the working copy (.criterion)
    pointer: dict
    module: ModuleManifest | None
    etds: dict[str, ETD] = field(default_factory=dict)   # by id prefix

    def folder(self, etd: ETD) -> Path | None:
        """The ETD's folder in the working copy: at the root, or nested one
        level down (e.g. development/bugs)."""
        direct = self.root / etd.folder
        if direct.is_dir():
            return direct
        for sub in sorted(p for p in self.root.iterdir() if p.is_dir()):
            nested = sub / etd.folder
            if nested.is_dir():
                return nested
        return None


def read_pointer(project_root: Path) -> dict:
    for pointer in sorted(project_root.glob("*.catalyst")):
        try:
            data = json.loads(pointer.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return {}


def load(start: Path | None = None) -> Deployment:
    # Never resolve symlinks here: from inside the .criterion symlink,
    # walking up the real (agent-owned) path would miss the project.
    start = Path(os.path.abspath(start)) if start else logical_cwd()
    root = find_deploy_root(start)
    project_root = find_project_root(start)
    pointer_dir = next((d for d in (start, *start.parents) if any(d.glob("*.catalyst"))), None)
    if root is None or project_root is None:
        if pointer_dir is not None:
            raise WorkingCopyMissing(
                f"{pointer_dir} has a *.catalyst pointer but no reachable .criterion "
                "working copy (repair the symlink: BOOTSTRAP.md §1.1)")
        raise DeploymentNotFound(
            f"no catalyst deployment found at or above {start} "
            "(expected a *.catalyst pointer and a .criterion working copy)")
    if not any(project_root.glob("*.catalyst")):
        raise DeploymentNotFound(
            f"{project_root} has a .criterion directory but no *.catalyst pointer — "
            "if this is an agent-owned working copy, run catalyst from the project instead")
    module = load_module(project_root)
    etds = dict(load_kernel_entities())
    if module is not None:
        for etd in module.entity_types.values():
            etds[etd.id_prefix] = etd
    return Deployment(project_root, root, read_pointer(project_root), module, etds)
