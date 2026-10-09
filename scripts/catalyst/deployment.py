"""Locate a deployment and the entity types that govern it.

A deployment is a project root (the directory holding the `*.catalyst`
pointer) plus its working copy, reached through `<project root>/.criterion`
(INV-6). Its entity types are the kernel's (framework/kernel/entities/, or the copy
module_loader finds embedded in the zipapp) plus the active module's ETDs.
"""

from __future__ import annotations

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
    root: Path  # the working copy (.criterion)
    pointer: dict
    module: ModuleManifest | None
    etds: dict[str, ETD] = field(default_factory=dict)  # by id prefix
    standalone: bool = False  # a bare working copy, with no project around it

    def folder(self, etd: ETD) -> Path | None:
        """The ETD's folder in the working copy: at the root, or nested one
        level down (e.g. development/bugs)."""
        if etd.location:
            declared = self.root / etd.location / etd.folder
            if declared.is_dir():
                return declared
        direct = self.root / etd.folder
        if direct.is_dir():
            return direct
        # never hidden directories: .github/workflows is not the workflows type
        for sub in sorted(p for p in self.root.iterdir() if p.is_dir() and not p.name.startswith(".")):
            nested = sub / etd.folder
            if nested.is_dir():
                return nested
        return None


def read_pointer(project_root: Path) -> dict:
    """The project file's fields (catalyst.toml, else a legacy *.catalyst)."""
    import project_file

    return project_file.read_dir(project_root)


def load(start: Path | None = None) -> Deployment:
    # Never resolve symlinks here: from inside the .criterion symlink,
    # walking up the real (agent-owned) path would miss the project.
    start = Path(os.path.abspath(start)) if start else logical_cwd()
    root = find_deploy_root(start)
    project_root = find_project_root(start)
    import project_file

    pointer_dir = project_file.find_up(start)
    if root is None or project_root is None:
        if pointer_dir is not None:
            name = project_file.project_name(project_file.read_dir(pointer_dir)) or "<name>"
            raise WorkingCopyMissing(
                f"{pointer_dir} has {project_file.find(pointer_dir).name} but its criterion is not reachable "
                f"(expected {project_file.home_criterion(name)}, or a legacy .criterion)"
            )
        raise DeploymentNotFound(
            f"no catalyst deployment found at or above {start} "
            "(expected a catalyst.toml, or a legacy *.catalyst pointer)"
        )
    if not project_file.is_project(project_root):
        raise DeploymentNotFound(
            f"{project_root} has a .criterion directory but no catalyst.toml (or *.catalyst pointer) — "
            "run catalyst from the project instead"
        )
    module = load_module(project_root)
    etds = dict(load_kernel_entities())
    if module is not None:
        for etd in module.entity_types.values():
            etds[etd.id_prefix] = etd
    return Deployment(project_root, root, read_pointer(project_root), module, etds)


def load_working_copy(path: Path) -> Deployment:
    """A bare working copy — e.g. the criterion repository checked out on its
    own in CI. Its module is the one under modules/; project files are out
    of scope."""
    root = Path(os.path.abspath(path))
    if not (root / "version.txt").is_file() or not (root / "rules").is_dir():
        raise DeploymentNotFound(f"{root} is not a catalyst working copy")
    mods = (
        sorted(d for d in (root / "modules").glob("*") if (d / "module.yaml").is_file())
        if (root / "modules").is_dir()
        else []
    )
    module = load_module(module_dir=mods[0]) if len(mods) == 1 else None
    etds = dict(load_kernel_entities())
    if module is not None:
        for etd in module.entity_types.values():
            etds[etd.id_prefix] = etd
    return Deployment(root, root, {}, module, etds, standalone=True)
