"""Installed modules (roadmap R4.9, step N1): one way to build a module's
tree, and the record of what a criterion holds.

`release_tree` gives what a release of a module ships — its zip unpacked, or
a checkout reduced to the shipped files plus the manifest a release carries —
so `init` and `sync` seed the same tree. `modules/modules.json` in the
criterion records each installed module: id, version, where it came from (a
repository URL, a release file's name or a directory's name, never a path),
the commit when the source is a git checkout, and the sha256 of the deployed
tree. `verify` recomputes that hash: a module file changed outside catalyst
shows as a difference.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

from module_loader import parse_simple_yaml

RECORD = "modules/modules.json"
NOT_SHIPPED = ("node_modules", "dist", "catalyst", "__pycache__")


class ModuleError(Exception):
    pass


# --- the tree a release ships -------------------------------------------------
def shipped_files(src: Path):
    """(file, name in the release) for what a release ships from `src`: no
    hidden files, no node_modules, dist, caches or packaged releases
    (`catalyst/`)."""
    for file in sorted(src.rglob("*")):
        if not file.is_file():
            continue
        rel = file.relative_to(src)
        if any(p.startswith(".") or p in NOT_SHIPPED for p in rel.parts):
            continue
        yield file, rel.as_posix()


def identity(module_dir: Path) -> dict:
    """A module directory's id, name, version, description and kernel range,
    from its `module.yaml` (and `version.txt`, which wins for the version)."""
    manifest = module_dir / "module.yaml"
    if not manifest.is_file():
        raise ModuleError(f"{module_dir.name} is not a module (no module.yaml)")
    data = parse_simple_yaml(manifest.read_text(encoding="utf-8"))
    data = data if isinstance(data, dict) else {}
    version_file = module_dir / "version.txt"
    version = (
        version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else str(data.get("version") or "")
    )
    return {
        "id": str(data.get("id") or module_dir.name),
        "name": str(data.get("name") or data.get("id") or module_dir.name),
        "version": version or "1.0.0",
        "description": str(data.get("description") or ""),
        "kernel_version": str(data["kernel_version"]) if data.get("kernel_version") else None,
    }


def manifest_of(info: dict, requires: str) -> dict:
    """The `manifest.json` a release of the module carries."""
    return {
        "id": info["id"],
        "name": info["name"],
        "version": info["version"],
        "description": info["description"],
        "kernelVersion": requires,
        # Legacy name of kernelVersion. Host UIs that predate kernelVersion
        # only read this field and skip manifests without it.
        "frameworkVersion": requires,
        "entry": "ui/index.js",
    }


def release_tree(src: Path, out: Path, kernel_version: str) -> Path:
    """What a release of the module at `src` ships, written to `out`: a
    release zip unpacked, or a checkout reduced to its shipped files with the
    manifest the release would carry (its kernel range, or this kernel on)."""
    if src.suffix == ".zip":
        if not src.is_file():
            raise ModuleError(f"{src.name} is not a file")
        with zipfile.ZipFile(src) as zf:
            zf.extractall(out)
        return out
    if not src.is_dir():
        raise ModuleError(f"{src.name} is neither a directory nor a .zip")
    info = identity(src)
    for file, name in shipped_files(src):
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, out / name)
    manifest = manifest_of(info, info["kernel_version"] or f">={kernel_version}")
    (out / "manifest.json").write_bytes(json.dumps(manifest, indent=2).encode("utf-8"))
    return out


# --- where a module came from ---------------------------------------------------
def _git(src: Path, *args: str) -> str | None:
    res = subprocess.run(["git", "-C", str(src), *args], capture_output=True, text=True, encoding="utf-8", check=False)
    return res.stdout.strip() if res.returncode == 0 else None


def source_of(src: Path | None) -> tuple[str | None, str | None]:
    """(source, commit) of a module source, for the record: a git checkout's
    remote URL (credentials removed; with the module's folder when it is not
    the repository's top) and its HEAD; else the zip's or the directory's
    name. Never a path on this machine."""
    if src is None:
        return None, None
    if src.suffix == ".zip" or not src.is_dir():
        return src.name, None
    top = _git(src, "rev-parse", "--show-toplevel")
    if top is None:
        return src.name, None
    url = _git(src, "remote", "get-url", "origin")
    commit = _git(src, "rev-parse", "HEAD")
    if not url:
        return src.name, commit
    url = re.sub(r"^([a-z+]+://)[^/@]+@", r"\1", url)
    prefix = (_git(src, "rev-parse", "--show-prefix") or "").strip("/")
    return (f"{url}#{prefix}" if prefix else url), commit


# --- the record -----------------------------------------------------------------
def tree_hash(tree: Path) -> str:
    """sha256 of a module tree: every file's name and content, in name order.
    Text files count with LF line endings, so a checkout that converts them
    gives the same hash."""
    digest = hashlib.sha256()
    for file in sorted(f for f in tree.rglob("*") if f.is_file()):
        data = file.read_bytes()
        if b"\0" not in data:
            data = data.replace(b"\r\n", b"\n")
        name = file.relative_to(tree).as_posix().encode("utf-8")
        digest.update(len(name).to_bytes(4, "big") + name + len(data).to_bytes(8, "big") + data)
    return digest.hexdigest()


def read_record(root: Path) -> list[dict]:
    """The recorded modules of the criterion at `root` (none recorded: [])."""
    path = root / RECORD
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ModuleError(f"{RECORD} is not JSON ({exc})") from None
    entries = data.get("modules") if isinstance(data, dict) else None
    return [e for e in entries if isinstance(e, dict) and e.get("id")] if isinstance(entries, list) else []


def deployed_identity(tree: Path) -> dict:
    """id and version of a deployed module tree (its manifest, else its yaml)."""
    manifest = tree / "manifest.json"
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return {"id": str(data.get("id") or tree.name), "version": str(data.get("version") or "")}
    info = identity(tree)
    return {"id": info["id"], "version": info["version"]}


def entry_for(root: Path, module_id: str, source: str | None, commit: str | None) -> dict:
    tree = root / "modules" / module_id
    return {
        "id": module_id,
        "version": deployed_identity(tree)["version"],
        "source": source,
        "commit": commit,
        "sha256": tree_hash(tree),
        "installed": datetime.date.today().isoformat(),
    }


def needs_record(root: Path, module_id: str) -> bool:
    """Whether the record lacks `module_id` or no longer matches its tree."""
    tree = root / "modules" / module_id
    if not tree.is_dir():
        return False
    entry = next((e for e in read_record(root) if e["id"] == module_id), None)
    return entry is None or entry.get("sha256") != tree_hash(tree)


def record(root: Path, module_id: str, source: str | None, commit: str | None) -> Path:
    """Write (or replace) `module_id`'s entry from its deployed tree. A source
    that is not known keeps the one already recorded."""
    path = root / RECORD
    entries = read_record(root)
    old = next((e for e in entries if e["id"] == module_id), None)
    if source is None and old is not None:
        source, commit = old.get("source"), None
    entry = entry_for(root, module_id, source, commit)
    entries = sorted([e for e in entries if e["id"] != module_id] + [entry], key=lambda e: e["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"modules": entries}, indent=2) + "\n", encoding="utf-8")
    return path


# --- verify ---------------------------------------------------------------------
@dataclass
class Finding:
    id: str
    state: str  # ok, changed, unrecorded, missing
    version: str | None = None
    source: str | None = None
    commit: str | None = None
    sha256: str | None = None  # recorded
    actual: str | None = None  # recomputed, when it differs

    def as_dict(self) -> dict:
        return asdict(self)


def verify(root: Path, only: str | None = None) -> list[Finding]:
    """Each installed or recorded module against the record: `ok`, `changed`
    (its tree differs from the recorded hash), `unrecorded` (installed before
    the record existed) or `missing` (recorded, its tree gone)."""
    mods = root / "modules"
    recorded = {e["id"]: e for e in read_record(root)}
    present = sorted(d.name for d in mods.iterdir() if (d / "module.yaml").is_file()) if mods.is_dir() else []
    findings = []
    for module_id in sorted(set(present) | set(recorded)):
        if only and module_id != only:
            continue
        entry = recorded.get(module_id)
        if entry is None:
            version = deployed_identity(mods / module_id)["version"]
            findings.append(Finding(module_id, "unrecorded", version))
            continue
        base = Finding(
            module_id, "ok", entry.get("version"), entry.get("source"), entry.get("commit"), entry.get("sha256")
        )
        if module_id not in present:
            base.state = "missing"
        else:
            actual = tree_hash(mods / module_id)
            if actual != entry.get("sha256"):
                base.state, base.actual = "changed", actual
        findings.append(base)
    if only and not findings:
        raise ModuleError(f"no module '{only}' in this criterion")
    return findings
