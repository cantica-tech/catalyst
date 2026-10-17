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
import os
import re
import shutil
import subprocess
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

from catalyst import proc
from module_loader import DEFAULT_TIERS, parse_simple_yaml

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


# --- fetching a module ----------------------------------------------------------
URL_RE = re.compile(r"^(?:(?!file:)[a-z][a-z0-9+.-]*://|[\w.-]+@[\w.-]+:)")
REF_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*$")


def is_url(spec: str) -> bool:
    """A remote git URL (`https://…`, `ssh://…`, `git@host:…`), not a path."""
    return bool(URL_RE.match(spec))


def clean_url(url: str) -> str:
    """The URL without the credentials it may embed."""
    return re.sub(r"^([a-z][a-z0-9+.-]*://)[^/@]+@", r"\1", url)


def split_ref(spec: str) -> tuple[str, str | None]:
    """`<source>@<ref>` as (source, ref). An `@` that belongs to the source
    (`git@host:…`, `https://user@host/…`) is not a ref: only one after the
    last `/` or `:` is."""
    at = spec.rfind("@")
    if at <= 0 or at < max(spec.rfind("/"), spec.rfind(":")):
        return spec, None
    return spec[:at], spec[at + 1 :] or None


def _is_repository(path: Path) -> bool:
    return path.is_dir() and _git(path, "rev-parse", "--git-dir") is not None and not (path / "module.yaml").is_file()


# The clone holds the files as the repository stores them: a machine that
# converts line endings on checkout would otherwise seed a different tree.
AS_STORED = ("-c", "core.autocrlf=false", "-c", "core.eol=lf")


def fetch(spec: str, tmp: Path) -> tuple[Path, str | None, str | None]:
    """A module source as (directory or zip, source, commit): a directory or
    a release zip as they are; a git repository (a URL, or a bare repository
    on this machine), optionally `@<ref>` (branch, tag or commit), cloned
    shallow into `tmp`."""
    path = Path(spec)
    if path.is_file() or (path.is_dir() and not _is_repository(path)):
        return path, *source_of(path)
    repo, ref = split_ref(spec)
    if not is_url(repo) and not _is_repository(Path(repo)):
        raise ModuleError(f"{Path(spec).name}: neither a module directory, a release .zip nor a git repository")
    if repo.startswith("-") or "::" in repo or any(ord(c) < 32 or ord(c) == 127 for c in repo):
        raise ModuleError(f"{repo!r} is not a usable repository URL")
    if ref is not None and not REF_RE.match(ref):
        raise ModuleError(f"{ref!r} is not a usable branch, tag or commit")
    dest = tmp / "clone"
    shallow = [
        "git",
        *AS_STORED,
        "clone",
        "-q",
        "--depth",
        "1",
        *(["--branch", ref] if ref else []),
        "--",
        repo,
        str(dest),
    ]
    res = subprocess.run(shallow, capture_output=True, text=True, encoding="utf-8", check=False)
    if res.returncode != 0 and ref:  # a commit is not a branch: clone whole, then check it out
        shutil.rmtree(dest, ignore_errors=True)
        res = subprocess.run(
            ["git", *AS_STORED, "clone", "-q", "--", repo, str(dest)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if res.returncode == 0:
            res = subprocess.run(
                ["git", *AS_STORED, "-C", str(dest), "checkout", "-q", "--detach", ref],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
    if res.returncode != 0:
        said = (res.stderr or res.stdout).strip().splitlines()
        raise ModuleError(
            f"could not fetch {clean_url(repo) if is_url(repo) else Path(repo).name}"
            + (f"@{ref}" if ref else "")
            + (f": {said[-1]}" if said else "")
        )
    if not (dest / "module.yaml").is_file():
        raise ModuleError("the repository has no module.yaml at its top: it is not a module")
    source = clean_url(repo) if is_url(repo) else re.sub(r"\.git$", "", Path(repo).name)
    return dest, source, _git(dest, "rev-parse", "HEAD")


# --- where a module came from ---------------------------------------------------
def _git(src: Path, *args: str) -> str | None:
    res = proc.git(src, *args)
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
    if not is_url(url):  # cloned from a repository on this machine: its name, never its path
        return re.sub(r"\.git$", "", Path(url.removeprefix("file://")).name) or src.name, commit
    url = clean_url(url)
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


def installed_ids(root: Path) -> list[str]:
    """The ids of the modules under the criterion's `modules/`, in install
    order: the record's order, then any it does not list, by name."""
    mods = root / "modules"
    present = sorted(d.name for d in mods.iterdir() if (d / "module.yaml").is_file()) if mods.is_dir() else []
    try:
        recorded = [e["id"] for e in read_record(root)]
    except ModuleError:
        recorded = []
    return [i for i in recorded if i in present] + [i for i in present if i not in recorded]


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
    # install order is kept: a module's part is composed after those installed before it
    entries = [entry if e["id"] == module_id else e for e in entries] if old is not None else [*entries, entry]
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
    order = installed_ids(root) + [i for i in recorded if i not in present]  # install order, then the missing
    for module_id in order:
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


# --- install --------------------------------------------------------------------
def _snapshot(root: Path) -> dict[Path, bytes]:
    """Each file's digest, `.git` and `.venv` never entered: git's background
    gc moves loose objects while a walk would list them."""
    skip = {".git", ".venv"}
    found = {}
    for here, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in files:
            f = Path(here) / name
            if f.is_file():
                found[f] = hashlib.sha256(f.read_bytes()).digest()
    return found


BULLET_RE = re.compile(r"^- `/.*?(?: —|\n(?! ))", re.M | re.S)
HEAD_NAME_RE = re.compile(r"`/([a-z0-9][a-z0-9-]*)")
KERNEL_COMMANDS_WITH_PARTS = {"create"}  # a module's bullet for one is a part (ADR-021)


def command_names(module_dir: Path) -> set[str]:
    """The slash commands a module brings: each catalogue bullet's names, its
    aliases included, and the create command catalyst generates for each of
    its v3 types. A part of a kernel command (`/create item` (`/create-item`),
    ADR-021) brings its aliases, not the kernel command."""
    from catalyst import compose, generate

    part = module_dir / "code-of-conduct.module.md"
    text = part.read_text(encoding="utf-8") if part.is_file() else ""
    names = {generate.create_command(e) for e in compose.generated_commands(module_dir, text)}
    for head in BULLET_RE.findall(text):
        found = HEAD_NAME_RE.findall(head)
        names |= set(found[1:] if found[0] in KERNEL_COMMANDS_WITH_PARTS else found)
    return names


META_RULE_RE = re.compile(r"^#{2,3} (?:\d+\. )?`(rr-[A-Z]+-\d+)", re.M)


def meta_rules(directory: Path, name: str = "rules-of-rules.module.md") -> set[str]:
    """The meta-rule IDs a module's handbook part defines."""
    part = directory / name
    return set(META_RULE_RE.findall(part.read_text(encoding="utf-8"))) if part.is_file() else set()


def collision(manifest, tree: Path, kernel: Path, kernel_types: dict, installed: list, root: Path) -> str | None:
    """What the module at `tree` shares with the kernel or an installed
    module and must not (None: nothing): its id, an entity type, a folder,
    a definition, a namespace, a command, a tier, or its grounding type."""
    if any(m.id == manifest.id for m in installed):
        return f"it is already installed (`catalyst module upgrade {manifest.id}` moves it to another release)"
    owners = [("the kernel", kernel_types)] + [(f"the module {m.id}", m.entity_types) for m in installed]
    for etd in manifest.entity_types.values():
        for owner, types in owners:
            if etd.id_prefix in types:
                return f"its type {etd.id_prefix} is also a type of {owner}"
            if etd.folder in {e.folder for e in types.values()}:
                return f"its folder {etd.folder} (type {etd.id_prefix}) is also a folder of {owner}"
    defs = tree / "definitions"
    for name in sorted(d.name for d in defs.iterdir() if d.is_dir()) if installed and defs.is_dir() else []:
        if (root / "definitions" / f"{name}.md").exists():
            return f"its definition `{name}` already exists in this criterion"
    for m in installed:
        if manifest.namespace and manifest.namespace == m.namespace:
            return f"its namespace {manifest.namespace} is also the namespace of the module {m.id}"
        if manifest.grounding_type != m.grounding_type:
            return (
                f"it grounds on `{manifest.grounding_type}` and the module {m.id} on `{m.grounding_type}`: "
                "the modules of one deployment ground on the same type"
            )
        theirs = {t.id: t for t in m.tiers or DEFAULT_TIERS}
        for tier in manifest.tiers or DEFAULT_TIERS:
            other = theirs.get(tier.id)
            if other is not None and (other.artifact, other.commit) != (tier.artifact, tier.commit):
                return f"its tier `{tier.id}` means something else in the module {m.id}"
    rules = meta_rules(tree)
    for owner, theirs in [("the kernel", meta_rules(kernel, "rules-of-rules.template.md"))] + [
        (f"the module {m.id}", meta_rules(root / "modules" / m.id)) for m in installed
    ]:
        shared = sorted(rules & theirs)
        if shared and owner != "the kernel":
            return f"its meta-rule {shared[0]} is also a meta-rule of {owner}"
    template = (kernel / "rules-of-development.template.md").read_text(encoding="utf-8")
    mine = command_names(tree)
    others = [("the kernel", {n for head in BULLET_RE.findall(template) for n in HEAD_NAME_RE.findall(head)})]
    others += [(f"the module {m.id}", command_names(root / "modules" / m.id)) for m in installed]
    for owner, theirs in others:
        shared = sorted(mine & theirs)
        if shared:
            return f"its command /{shared[0]} is also a command of {owner}"
    return None


def install(dep, kernel: Path, spec: str, actor: str, intent: list[str]) -> dict:
    """Install the module `spec` names (`catalyst module install`), as the
    deployment's first module or beside those it has: fetch, check, seed as
    `init` does, recompose the governing documents, name a first module in
    the project file, journal one entry. Every refusal comes before
    anything is written."""
    import tempfile

    from catalyst import compose, init, journal, sync
    from catalyst.versions import satisfies
    from module_loader import load_kernel_entities, load_module

    root = dep.root
    installed = dep.installed()
    if not (kernel / "rules-of-rules.template.md").is_file():
        raise ModuleError("pass --kernel <framework/kernel of the catalyst release this deployment is at>")
    deployed = (root / "version.txt").read_text(encoding="utf-8").strip()
    try:
        given = sync.Sources._kernel_version(kernel, kernel)
    except sync.SyncError as exc:
        raise ModuleError(str(exc)) from None
    if given != deployed:
        raise ModuleError(
            f"this deployment is at kernel {deployed} and --kernel is {given}: `catalyst sync apply` moves the "
            "kernel first, or pass the kernel the deployment is at"
        )
    with tempfile.TemporaryDirectory(prefix="catalyst-module-") as tmp:
        src, source, commit = fetch(spec, Path(tmp))
        tree = release_tree(src, Path(tmp) / "module", deployed)
        manifest = load_module(module_dir=tree)
        if manifest is None:
            raise ModuleError("the module has no readable module.yaml")
        which = f"{manifest.id} {manifest.version}"
        if not satisfies(deployed, manifest.kernel_version):
            raise ModuleError(
                f"{which} works with kernel {manifest.kernel_version}, not {deployed}: install a module release "
                "that does, or sync the kernel first"
            )
        gate = sync.gate_version(dep)
        if gate and not satisfies(gate, manifest.kernel_version):
            raise ModuleError(
                f"{which} needs kernel {manifest.kernel_version}, and the shared criterion's gate still runs {gate}: "
                "publish and merge the kernel sync, pull, then install the module"
            )
        clash = collision(manifest, tree, kernel, load_kernel_entities(), installed, root)
        if clash:
            raise ModuleError(f"{which} cannot be installed here: {clash}")
        params = compose.deployed_params(root, installed[0].id if installed else "")
        if not installed:
            params.module_id = manifest.id
        have = dep.module_dirs()
        conflicts = [
            r.path
            for r in compose.recompose(root, params, (kernel, have), (kernel, [*have, tree]), write=False)
            if r.conflicts
        ]
        if conflicts:
            raise ModuleError(
                "adding the module's part to " + ", ".join(conflicts) + " would conflict with local edits there: "
                "resolve with `catalyst recompose` by hand, then install"
            )
        before = _snapshot(root)
        stamp = datetime.date.today().isoformat()
        init.seed_module(root, tree, manifest, params, stamp, source, commit, first=not installed)
        compose.recompose(root, params, (kernel, have), (kernel, [*have, tree]))
        (root / compose.PARAMS_FILE).write_text(json.dumps(params.as_dict(), indent=2) + "\n", encoding="utf-8")
    after = _snapshot(root)
    touched = sorted(f for f, digest in after.items() if before.get(f) != digest)
    import project_file

    pointer = project_file.find(dep.project_root)
    if pointer is not None and not dep.standalone and not installed:  # the project file names the first module
        data = project_file.read(pointer)
        data["module"] = manifest.id
        data["updated"] = datetime.date.today().isoformat()
        project_file.write(pointer, data)
        touched.append(pointer)
    journal.append(
        dep,
        journal.AppendRequest(
            command="catalyst module install",
            action="create",
            artifact=f"module {which}",
            targets=[],
            intent=intent or [f"Install the module {which}, on the user's explicit request (INV-2)."],
            files=[str(t) for t in touched],
            actor=actor,
            tier="chore",
        ),
    )
    return {"id": manifest.id, "version": manifest.version, "source": source, "commit": commit, "files": len(touched)}
