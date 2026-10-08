"""`catalyst sync plan|apply` (roadmap R2 W4): the mechanical half of
`/sync-framework` (SYNCHRONIZE.md).

`plan` compares a deployment with a target kernel (and module) release and
lists what a sync would do; `apply` does it: re-vendor the CLI, copy the
invariants, refresh the module tree, recompose the governing documents,
refresh command files the release changed (never one edited locally),
create definitions for new entity types (never touch a deployed one,
INV-23), set the versions, and journal it. What stays with the agent: the
migrations' judgment steps, which `plan` lists, and conflicts it reports.

Sources are a directory or a release `.zip`: the kernel's `framework/kernel`
(or the extracted `kernel-vX.Y.Z.zip`), the module's directory or zip. The
base the deployment was composed from is found next to a release zip
(`…/kernel/v<deployed>/kernel-v<deployed>.zip`) or, for a catalyst checkout,
from the git tag of the deployed version.
"""
from __future__ import annotations

import datetime
import filecmp
import io
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from catalyst import compose, journal
from catalyst.deployment import Deployment

MIGRATION_ROW = re.compile(r"^\|\s*\[`([^`]+)`\]\([^)]*\)\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|\s*$")
AGENT_COMMANDS_DIRS = {"claude-code": ".claude/commands"}


class SyncError(Exception):
    pass


def vt(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", version)[:3])


@dataclass
class Action:
    kind: str           # cli, invariants, module, document, command, definition, version
    target: str         # what it touches
    change: str         # add, update, conflict, skip
    detail: str = ""


@dataclass
class Plan:
    from_kernel: str
    to_kernel: str
    from_module: str | None
    to_module: str | None
    actions: list[Action] = field(default_factory=list)
    migrations: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {**{k: v for k, v in asdict(self).items() if k not in ("actions",)},
                "actions": [asdict(a) for a in self.actions]}


# --- sources --------------------------------------------------------------
class Sources:
    """Resolved directories for the new kernel/module, their bases and the CLI."""

    def __init__(self, dep: Deployment, kernel: Path, module: Path | None, base_kernel: Path | None,
                 cli: Path | None):
        self.tmp = Path(tempfile.mkdtemp(prefix="catalyst-sync-"))
        self.kernel_arg = kernel
        self.kernel = self._open(kernel, "kernel")
        if not (self.kernel / "rules-of-rules.template.md").is_file():
            raise SyncError(f"{kernel} is not a catalyst kernel (framework/kernel or a kernel release)")
        self.deployed = (dep.root / "version.txt").read_text(encoding="utf-8").strip()
        self.version = self._kernel_version(self.kernel, kernel)
        self.base_kernel = self._open(base_kernel, "base-kernel") if base_kernel else self._find_base()
        mod_id = dep.module.id if dep.module else None
        self.base_module = None
        if mod_id:
            deployed_mod = dep.root / "modules" / mod_id
            self.base_module = self.tmp / "base-module"
            if deployed_mod.is_dir():
                shutil.copytree(deployed_mod, self.base_module)
        self.module = self._open_module(module) if module else None
        self.cli = cli or self._find_cli()

    def _open(self, path: Path, name: str) -> Path:
        if path.suffix == ".zip":
            out = self.tmp / name
            with zipfile.ZipFile(path) as zf:
                zf.extractall(out)
            return out
        if not path.is_dir():
            raise SyncError(f"{path} is neither a directory nor a .zip")
        return path

    def _open_module(self, path: Path) -> Path:
        """A module release: its zip, or a checkout reduced to what its release
        ships (plus the manifest the release would carry)."""
        if path.suffix == ".zip":
            return self._open(path, "module")
        import package_release
        info = package_release.module_info_at(path)
        if info is None:
            raise SyncError(f"{path} is not a module (no module.yaml)")
        out = self.tmp / "module"
        for file, arcname in package_release.shipped_files(path):
            (out / arcname).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, out / arcname)
        manifest = package_release.module_manifest(info, info.kernel_version or f">={self.version}")
        (out / "manifest.json").write_bytes(json.dumps(manifest, indent=2).encode("utf-8"))
        return out

    @staticmethod
    def _kernel_version(kernel: Path, arg: Path) -> str:
        for candidate in (kernel / "manifest.json",):
            if candidate.is_file():
                return str(json.loads(candidate.read_text(encoding="utf-8"))["version"])
        root_version = kernel.parent.parent / "version.txt"
        if root_version.is_file():
            return root_version.read_text(encoding="utf-8").strip()
        raise SyncError(f"cannot tell the version of {arg}")

    def _find_base(self) -> Path | None:
        arg = self.kernel_arg
        if arg.suffix == ".zip":
            sibling = arg.parent.parent / f"v{self.deployed}" / f"kernel-v{self.deployed}.zip"
            return self._open(sibling, "base-kernel") if sibling.is_file() else None
        repo = arg.parent.parent
        archive = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", self.deployed, "framework/kernel"],
                                 capture_output=True)
        if archive.returncode != 0:
            return None
        out = self.tmp / "base-kernel-tree"
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            tar.extractall(out)
        return out / "framework" / "kernel"

    def _find_cli(self) -> Path | None:
        shipped = self.kernel / "bin" / "catalyst.pyz"
        if shipped.is_file():
            return shipped
        repo = self.kernel.parent.parent
        if (repo / "scripts" / "catalyst" / "__main__.py").is_file():
            import package_release
            return package_release.build_cli(repo, self.tmp / "catalyst.pyz")
        return None

    def close(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)


# --- planning -------------------------------------------------------------
def _same(a: Path, b: Path) -> bool:
    return a.is_file() and b.is_file() and filecmp.cmp(a, b, shallow=False)


def _tree_changes(new: Path, old: Path) -> list[str]:
    rel = lambda base: {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    new_files, old_files = rel(new), rel(old) if old.is_dir() else set()
    return sorted(f for f in new_files | old_files
                  if f not in new_files or f not in old_files or not _same(new / f, old / f))


def migrations(index: Path, deployed: str, target: str, owner: str) -> list[dict]:
    if not index.is_file():
        return []
    out = []
    for line in index.read_text(encoding="utf-8").splitlines():
        m = MIGRATION_ROW.match(line)
        if m and vt(m.group(2)) >= vt(deployed) and vt(m.group(3)) <= vt(target):
            out.append({"owner": owner, "file": m.group(1), "from": m.group(2), "to": m.group(3),
                        "summary": m.group(4)})
    return out


def commands_dir(dep: Deployment, override: Path | None) -> Path | None:
    if override is not None:
        return override if override.is_absolute() else dep.project_root / override
    rel = AGENT_COMMANDS_DIRS.get(str(dep.pointer.get("agent", "")))
    return dep.project_root / rel if rel else None


def _command_sources(kernel: Path | None, module: Path | None) -> dict[str, Path]:
    from catalyst.init import kernel_command_files
    found = {p.stem: p for p in kernel_command_files(kernel)} if kernel else {}
    if module is not None:
        found.update({p.stem: p for p in (module / "commands").glob("*.md")})
    return found


def plan(dep: Deployment, src: Sources, commands: Path | None) -> Plan:
    mod = dep.module
    new_mod_version = ((src.module / "version.txt").read_text(encoding="utf-8").strip()
                       if src.module and (src.module / "version.txt").is_file() else None)
    p = Plan(src.deployed, src.version, getattr(mod, "version", None) if mod else None, new_mod_version)
    root = dep.root
    if src.cli is not None and not _same(src.cli, root / "bin" / "catalyst.pyz"):
        p.actions.append(Action("cli", ".criterion/bin/catalyst.pyz", "update", f"catalyst {src.version}"))
    module_dir = src.module or (root / "modules" / mod.id if mod else None)
    for name, source in (("INVARIANTS.md", src.kernel / "INVARIANTS.md"),
                         ("INVARIANTS.module.md", module_dir / "INVARIANTS.module.md" if module_dir else None)):
        if source is not None and source.is_file() and not _same(source, root / name):
            p.actions.append(Action("invariants", f".criterion/{name}", "add" if not (root / name).exists() else "update"))
    if src.module is not None and mod is not None:
        changed = _tree_changes(src.module, root / "modules" / mod.id)
        if changed:
            p.actions.append(Action("module", f".criterion/modules/{mod.id}", "update",
                                    f"{len(changed)} file(s), {p.from_module} -> {p.to_module}"))
    moving = p.from_kernel != p.to_kernel or any(a.kind == "module" for a in p.actions)
    if mod is not None and moving and src.base_kernel is not None:
        params = compose.deployed_params(root, mod.id)
        for r in compose.recompose(root, params, (src.base_kernel, src.base_module),
                                   (src.kernel, src.module or root / "modules" / mod.id), write=False):
            if r.changed or r.frozen:
                p.actions.append(Action("document", f".criterion/{r.path}",
                                        "skip" if r.frozen else ("conflict" if r.conflicts else "update"),
                                        "frozen" if r.frozen else (f"{r.conflicts} conflict(s)" if r.conflicts else "")))
    elif mod is not None and moving:
        p.actions.append(Action("document", "governing documents", "skip",
                                f"no base kernel {src.deployed} found: pass --base-kernel to recompose"))
    if commands is not None:
        new_cmds = _command_sources(src.kernel, src.module or (root / "modules" / mod.id if mod else None))
        base_cmds = _command_sources(src.base_kernel, src.base_module)
        for name, source in sorted(new_cmds.items()):
            target = commands / f"{name}.md"
            if not target.exists():
                p.actions.append(Action("command", _rel(dep, target), "add"))
            elif not _same(source, target):
                base = base_cmds.get(name)
                if base is not None and _same(base, target):
                    p.actions.append(Action("command", _rel(dep, target), "update"))
                else:
                    p.actions.append(Action("command", _rel(dep, target), "conflict",
                                            "edited locally or unknown base: compare by hand"))
    deployed_defs = root / "definitions"
    for source in (src.kernel, src.module):
        for folder in sorted((source / "definitions").iterdir()) if source and (source / "definitions").is_dir() else []:
            if folder.is_dir() and not (deployed_defs / f"{folder.name}.md").exists():
                p.actions.append(Action("definition", f".criterion/definitions/{folder.name}.md", "add",
                                        "new entity type; existing definitions are never touched (INV-23)"))
    if p.from_kernel != p.to_kernel:
        p.actions.append(Action("version", ".criterion/version.txt + pointer", "update", f"{p.from_kernel} -> {p.to_kernel}"))
    p.migrations = migrations(src.kernel / "migrations" / "migrations.md", src.deployed, src.version, "kernel")
    if src.module is not None:
        p.migrations += migrations(src.module / "migrations" / "migrations.md", src.deployed, src.version, "module")
    p.migrations.sort(key=lambda m: (vt(m["to"]), m["owner"] != "kernel"))
    return p


def _rel(dep: Deployment, path: Path) -> str:
    try:
        return path.relative_to(dep.project_root).as_posix()
    except ValueError:
        return path.as_posix()


# --- applying -------------------------------------------------------------
def _latest_definition(folder: Path) -> Path | None:
    found = [(int(m.group(1)), p) for p in folder.glob("DEFINITION-*-v*.md") if (m := re.search(r"-v(\d+)\.md$", p.name))]
    return max(found)[1] if found else None


def apply(dep: Deployment, src: Sources, commands: Path | None, actor: str, intent: list[str]) -> tuple[Plan, list[Path]]:
    p = plan(dep, src, commands)
    blocking = [a for a in p.actions if a.change == "conflict" and a.kind == "document"]
    if blocking:
        raise SyncError("recompose would leave conflicts in " + ", ".join(a.target for a in blocking)
                        + ": resolve with `catalyst recompose` by hand, then sync")
    root, touched = dep.root, []
    mod = dep.module
    for a in p.actions:
        if a.kind == "cli":
            shutil.copyfile(src.cli, root / "bin" / "catalyst.pyz")
            touched.append(root / "bin" / "catalyst.pyz")
        elif a.kind == "invariants":
            name = Path(a.target).name
            source = src.kernel / name if name == "INVARIANTS.md" else (src.module or root / "modules" / mod.id) / name
            shutil.copyfile(source, root / name)
            touched.append(root / name)
    if any(a.kind == "module" for a in p.actions):
        target = root / "modules" / mod.id
        before = {f.relative_to(target).as_posix() for f in target.rglob("*") if f.is_file()}
        shutil.rmtree(target)
        shutil.copytree(src.module, target)
        after = {f.relative_to(target).as_posix() for f in target.rglob("*") if f.is_file()}
        touched += [target / f for f in sorted(before | after)
                    if f not in after or f not in before or not _same(target / f, src.base_module / f)]
    if mod is not None and src.base_kernel is not None and any(a.kind == "document" for a in p.actions):
        params = compose.deployed_params(root, mod.id)
        for r in compose.recompose(root, params, (src.base_kernel, src.base_module), (src.kernel, root / "modules" / mod.id)):
            if r.changed:
                touched.append(root / r.path)
    new_cmds = _command_sources(src.kernel, root / "modules" / mod.id if mod else None) if commands else {}
    for a in p.actions:
        if a.kind == "command" and a.change in ("add", "update"):
            target = dep.project_root / a.target
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(new_cmds[target.stem], target)
            touched.append(target)
        elif a.kind == "definition":
            name = Path(a.target).stem
            for source in (src.kernel, root / "modules" / mod.id if mod else None):
                latest = _latest_definition(source / "definitions" / name) if source else None
                if latest is not None:
                    (root / "definitions" / f"{name}.md").write_text(latest.read_text(encoding="utf-8"), encoding="utf-8")
                    touched.append(root / "definitions" / f"{name}.md")
                    break
        elif a.kind == "version":
            (root / "version.txt").write_text(src.version + "\n", encoding="utf-8")
            touched.append(root / "version.txt")
            for pointer in sorted(dep.project_root.glob("*.catalyst")):
                data = json.loads(pointer.read_text(encoding="utf-8"))
                data["kernel_version"] = src.version
                data["updated"] = datetime.date.today().isoformat()
                pointer.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                touched.append(pointer)
    if touched:
        artifact = f"kernel {src.version}" + (f", module {mod.id} {p.to_module}" if p.to_module else "")
        journal.append(dep, journal.AppendRequest(
            command="/sync-framework", action="sync", artifact=artifact, targets=[],
            intent=intent or [f"Sync to {artifact} (catalyst sync apply)"],
            files=[str(t) for t in dict.fromkeys(touched)], actor=actor, tier="chore"))
    return p, touched


# --- text -----------------------------------------------------------------
def render(p: Plan, applied: bool = False) -> str:
    head = f"kernel {p.from_kernel} -> {p.to_kernel}"
    if p.to_module:
        head += f"; module {p.from_module} -> {p.to_module}"
    lines = [("Synced: " if applied else "Plan: ") + head]
    lines += [f"  {a.change:>8}  {a.kind:<10} {a.target}" + (f"  ({a.detail})" if a.detail else "") for a in p.actions]
    if not p.actions:
        lines.append("  nothing to change")
    if p.migrations:
        lines.append("Migrations — their judgment steps are the agent's, in this order:")
        lines += [f"  {m['owner']} {m['file']} ({m['from']} -> {m['to']})" for m in p.migrations]
    return "\n".join(lines) + "\n"
