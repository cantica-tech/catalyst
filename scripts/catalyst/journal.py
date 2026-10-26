"""The journal (Rules-of-Rules.md §12, INV-17): append, verify, restore, pin.

It is sharded: each actor on each machine appends to its own file,
`development/journal/<actor>@<machine>/<YYYY-MM>.jsonl` (the machine is a
random id kept in `$CATALYST_HOME/machine`), so two people — or one person
on two machines — never append to the same file and a shared criterion
merges without conflicts. A deployment made before kernel 0.50 also keeps
`development/journal.jsonl`, read as one more source and never written.
The journal reads as every source merged by timestamp, each source keeping
its own order. Appends run under the criterion's journal lock (`lock.py`),
so concurrent sessions never compute a `before` from a stale state. Every
read, append and lock goes through the criterion's store (`store.py`).

Paths are relative to the project root; working-copy files start with
`.criterion/` and are hashed into the working copy's own git repository,
every other path into the project's. Legacy entries (bare working-copy
paths, `<repo>:path` prefixes, absolute paths) are normalised on read.

Every blob a CLI-written entry references is pinned under
`refs/catalyst/journal` in its repository — a commit chain whose tree holds
each blob under its own hash — so `git gc` can never prune it and
point-in-time restore keeps working.

This writes into the repositories' own `.git` — the product's included:
`journal append` (and `init`, which journals the install) stores each
product file's blob (`git hash-object -w`) and creates or moves
`refs/catalyst/journal` there. The ref is local: it is pushed to `origin`
only by `catalyst journal pin --share`. Creating it is announced once per
repository on stderr; `git update-ref -d refs/catalyst/journal` removes it
(blobs it no longer reaches are then left to `git gc`, which breaks
point-in-time restore of those states).
"""

from __future__ import annotations

import collections
import datetime
import json
import os
import re
import secrets
import string
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import project_file
from catalyst import __version__, proc
from catalyst.deployment import Deployment
from catalyst.store import store_for

LEGACY = "development/journal.jsonl"  # before kernel 0.50: read, never written
SHARDS = "development/journal"
LOCK_STALE = 300.0  # an append hashes and pins every file it names
PIN_REF = "refs/catalyst/journal"
WC = ".criterion/"
ACTIONS = ("create", "update", "close", "retire", "status-change", "sync", "redact")
REQUIRED = ("timestamp", "actor", "command", "action", "artifact", "targets", "intent", "files")
VIA = ("agent", "person", "server")  # how an entry's change was made (fw-STRUCTURE-000022, design 33 §3)
VIA_VARIABLE = "CATALYST_VIA"  # says it outright: `catalyst mcp` and `agent run` set it for what they run
AGENT_VARIABLES = ("AI_AGENT", "CLAUDECODE", "GEMINI_CLI")  # set by an agent for the commands its session runs


class JournalError(Exception):
    pass


def git(repo: Path, *args: str, input: str | None = None, check: bool = True) -> str:
    res = proc.run(["git", "-C", str(repo), *args], input=input)
    if check and res.returncode != 0:
        raise JournalError(f"git {' '.join(args)} failed in {repo}: {res.stderr.strip()}")
    return res.stdout.strip() if res.returncode == 0 else ""


def revisions(revs: list[str]) -> list[str]:
    """User-supplied git revisions/ranges, refused when one could be read as
    an option (`--output=F` makes `git log` write a file): every revision a
    user names reaches git through here."""
    for rev in revs:
        if not rev or rev.startswith("-") or "\0" in rev:
            raise ValueError(f"'{rev}' is not a revision or range")
    return list(revs)


def object_id(sha: str) -> bool:
    """A full hexadecimal git object id (what the journal records)."""
    return isinstance(sha, str) and len(sha) in (40, 64) and all(c in "0123456789abcdef" for c in sha)


def now() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value: str) -> datetime.datetime:
    """An ISO 8601 timestamp as an aware UTC datetime (JournalError if not)."""
    try:
        t = datetime.datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        raise JournalError(f"'{value}' is not an ISO 8601 timestamp") from None
    if t.tzinfo is None:
        t = t.replace(tzinfo=datetime.UTC)
    return t.astimezone(datetime.UTC)


def _entry_time(entry: dict) -> datetime.datetime | None:
    try:
        return parse_time(entry.get("timestamp", ""))
    except JournalError:
        return None


# --- paths ---------------------------------------------------------------
def canonical(dep: Deployment, path: str) -> str:
    """A journal path for a user-supplied path (absolute, or relative to the
    current directory)."""
    p = Path(path)
    absolute = p if p.is_absolute() else Path(os.getcwd()) / p
    absolute = Path(os.path.normpath(absolute))
    for base, prefix in (
        (dep.root, WC),
        (dep.root.resolve(), WC),
        (dep.project_root, ""),
        (dep.project_root.resolve(), ""),
    ):
        try:
            rel = absolute.relative_to(base)
        except ValueError:
            continue
        rel_s = rel.as_posix()
        if prefix == "" and rel_s.startswith(WC.rstrip("/")):
            return rel_s  # already through the .criterion symlink
        return prefix + rel_s
    real = Path(os.path.realpath(absolute))
    for base, prefix in ((dep.root.resolve(), WC), (dep.project_root.resolve(), "")):
        try:
            return prefix + real.relative_to(base).as_posix()
        except ValueError:
            continue
    raise JournalError(f"{path} is outside the project and its working copy")


def normalise(dep: Deployment, recorded: str, shas: tuple = ()) -> str:
    """Read a (possibly legacy) journal path as a canonical one. `shas`
    (the entry's before/after) settle a bare path that exists in neither
    tree any more: it belongs to whichever repository holds its blobs."""
    path = recorded
    if ":" in path and not path.startswith("/") and "/" not in path.split(":", 1)[0]:
        repo, rest = path.split(":", 1)
        if repo == "criterion":
            return WC + rest
        if repo == dep.project_root.name:
            return rest
        return path  # another repository: kept as recorded, not verifiable here
    if path.startswith("/"):
        try:
            return canonical(dep, path)
        except JournalError:
            return path
    if path.startswith(WC):
        return path
    in_wc, in_project = (dep.root / path).exists(), (dep.project_root / path).exists()
    if in_project and not in_wc:
        return path
    if not in_wc and not in_project:
        for sha in shas:
            if sha and blob_exists(dep.project_root, sha) and not blob_exists(dep.root, sha):
                return path
    return WC + path  # the pre-0.38 schema's paths were working-copy relative


def locate(dep: Deployment, path: str) -> tuple[Path, str] | None:
    """(repository, path inside it) for a canonical journal path."""
    if path.startswith(WC):
        return dep.root, path[len(WC) :]
    if dep.standalone or ":" in path.split("/", 1)[0] or path.startswith("/"):
        return None  # a bare working copy has no project files to check
    return dep.project_root, path


# --- reading -------------------------------------------------------------
def sources(dep: Deployment) -> list[str]:
    """Every file the journal is read from, criterion-relative: the legacy
    single file first, then each shard, in a stable order."""
    store = store_for(dep)
    return [*store.list(LEGACY), *store.list(SHARDS, ".jsonl")]


def texts(dep: Deployment) -> list[str]:
    """The raw text of every journal source (ID allocation scans it)."""
    store = store_for(dep)
    return [store.read(rel) or "" for rel in sources(dep)]


def _source(dep: Deployment, rel: str) -> list[tuple[str, dict | None, str]]:
    name = rel.removeprefix("development/")
    out = []
    for n, line in enumerate((store_for(dep).read(rel) or "").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            out.append((f"{name}:{n}", entry if isinstance(entry, dict) else None, line))
        except json.JSONDecodeError:
            out.append((f"{name}:{n}", None, line))
    return out


def _changes(entry: dict | None) -> list[tuple[str, object, object]]:
    return [
        (str(f["path"]), f.get("before"), f.get("after"))
        for f in (entry or {}).get("files", []) or []
        if isinstance(f, dict) and "path" in f and not f.get("superseded")
    ]


def read(dep: Deployment) -> list[tuple[str, dict | None, str]]:
    """(where, entry or None if malformed, raw line); `where` is
    `<source>:<line>` (`journal.jsonl:12`, `journal/ada@k3j9q2/2026-10.jsonl:3`).

    Sources are merged in causal order, never by clock alone: a source's own
    order is kept, and the next entry is the earliest one ready — each of its
    files starts from that file's state so far (`before` = the last `after`)
    or, for a file not seen yet, from a state no pending entry produces. When
    none is ready (merged concurrent work), the earliest of all. Timestamps
    only break ties, so a skewed clock cannot reorder a chain."""
    queues = [_source(dep, rel) for rel in sources(dep)]
    if len(queues) == 1:
        return queues[0]
    floor = datetime.datetime.min.replace(tzinfo=datetime.UTC)
    keyed = []
    for i, rows in enumerate(queues):
        last, out = floor, []
        for row in rows:
            t = _entry_time(row[1]) if row[1] else None
            last = max(last, t) if t else last  # an unreadable timestamp sorts with the one before it
            out.append(((last, i), row, _changes(row[1])))
        keyed.append(out)
    pending = collections.Counter((path, after) for rows in keyed for _, _, ch in rows for path, _, after in ch)
    heads, state, merged = [0] * len(keyed), {}, []

    def fits(path: str, before: object) -> bool:
        if path in state:
            return state[path] == before
        return before is None or not pending[(path, before)]

    def unmet(changes: list[tuple[str, object, object]]) -> set[tuple[str, object]]:
        """The states an entry waits for; a file it changes twice chains on its own earlier change first."""
        own: dict[str, object] = {}
        out = set()
        for path, before, after in changes:
            if not (own[path] == before if path in own else fits(path, before)):
                out.add((path, before))
            own[path] = after
        return out

    while True:
        ready, waiting = [], []
        for i, rows in enumerate(keyed):
            if heads[i] < len(rows):
                key, _, changes = rows[heads[i]]
                (waiting if unmet(changes) else ready).append((key, i))
        if not ready and not waiting:
            return merged
        first = min(ready + waiting)
        if first in ready or not ready:
            _, i = first
        else:
            # The earliest entry waits. Another source overtakes it only if that source will produce the state it
            # waits for (causality beats clocks); if only its own later entries do (an old journal out of causal
            # order), it takes its turn in time, and an unrelated source's later entries stay after it. A state the
            # entry produces itself (a file it recorded unchanged) is not waited for from a source producing it later.
            s = first[1]
            when, _, own = keyed[s][heads[s]]
            needs, made = unmet(own), {(p, a) for p, _, a in own}
            providers = {
                k
                for k, rows in enumerate(keyed)
                if k != s
                and any(
                    (p, a) in needs and ((p, a) not in made or t[0] <= when[0])
                    for t, _, ch in rows[heads[k] :]
                    for p, _, a in ch
                )
            }
            helping = [r for r in ready if r[1] in providers]
            _, i = min(helping) if helping else (min(ready) if providers else first)
        _, row, changes = keyed[i][heads[i]]
        heads[i] += 1
        for path, _, after in changes:
            state[path] = after
            pending[(path, after)] -= 1
        merged.append(row)


# --- writing -------------------------------------------------------------
def machine() -> str:
    """This machine's id in shard names: random, created once in
    `$CATALYST_HOME/machine`, never derived from the host name."""
    path = project_file.home() / "machine"
    try:
        value = path.read_text(encoding="utf-8").strip()
        if re.fullmatch(r"[a-z0-9]{4,32}", value):
            return value
    except OSError:
        pass
    value = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return machine()  # another process created it first
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(value + "\n")
    return value


def actor_slug(actor: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", str(actor).strip().lower()).strip("-.")
    return slug[:64] or "unknown"


def shard(entry: dict) -> str:
    """The shard an entry is appended to (relative to the criterion)."""
    month = str(entry.get("timestamp", ""))[:7]
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        month = now()[:7]
    return f"{SHARDS}/{actor_slug(str(entry.get('actor', '')))}@{machine()}/{month}.jsonl"


def journal_lock(dep: Deployment):
    """Held around every append: read the last states, then write."""
    return store_for(dep).lock("journal", stale=LOCK_STALE, error=JournalError)


def via(environ=None) -> str:
    """How the change being journaled is made: `CATALYST_VIA` when it says
    `agent` or `person`, else `agent` inside an agent's session, else `person`."""
    env = os.environ if environ is None else environ
    said = str(env.get(VIA_VARIABLE, "")).strip().lower()
    if said in ("agent", "person"):
        return said
    return "agent" if any(env.get(v) for v in AGENT_VARIABLES) else "person"


def write(dep: Deployment, entry: dict) -> str:
    """Append one entry to its shard (call with the journal lock held);
    returns the shard, criterion-relative."""
    entry.setdefault("via", via())
    rel = shard(entry)
    store_for(dep).append(rel, json.dumps(entry, ensure_ascii=False))
    return rel


_NORMAL: dict[tuple, str] = {}


def entry_path(dep: Deployment, entry: dict, f: dict) -> str:
    """A file's canonical path: as written when the entry is CLI-written
    (already canonical), else normalised from its legacy form (once per
    process: every reader of the journal asks for the same entries)."""
    if str(entry.get("writer", "")).startswith("catalyst/"):
        return str(f["path"])
    key = (str(dep.root), str(dep.project_root), str(f["path"]), f.get("before"), f.get("after"))
    if key not in _NORMAL:
        _NORMAL[key] = normalise(dep, str(f["path"]), (f.get("before"), f.get("after")))
    return _NORMAL[key]


_CHECKED: dict[tuple, list] = {}


def read_checked(dep: Deployment) -> list[tuple[str, dict | None, str]]:
    """`read`, with every blob the entries name looked up in one
    `cat-file --batch-check` per repository; kept for the process while no
    source changes (check, verify and unrecorded all read the journal)."""
    stamps = []
    for rel in sources(dep):
        try:
            st = (dep.root / rel).stat()
            stamps.append((rel, st.st_size, st.st_mtime_ns))
        except OSError:
            stamps.append((rel, -1, -1))
    key = (str(dep.root), str(dep.project_root), tuple(stamps))
    if key not in _CHECKED:
        entries = read(dep)
        shas = {
            f.get(k)
            for _, e, _ in entries
            for f in (e or {}).get("files", []) or []
            if isinstance(f, dict)
            for k in ("before", "after")
        }
        for repo in (dep.root, dep.project_root):
            prefetch(repo, shas)
        _CHECKED.clear()  # one deployment's journal at a time
        _CHECKED[key] = entries
    return _CHECKED[key]


def last_after(dep: Deployment) -> dict[str, str | None]:
    last: dict[str, str | None] = {}
    entries = read_checked(dep)
    for _, entry, _ in entries:
        for f in (entry or {}).get("files", []) or []:
            # a superseded file is history recorded after the fact, not the file's current state
            if isinstance(f, dict) and "path" in f and not f.get("superseded"):
                last[entry_path(dep, entry, f)] = f.get("after")
    return last


# --- pinning -------------------------------------------------------------
def redacted_in(repo: Path) -> set[str]:
    """The blobs the journal of `repo` says are redacted (R3.7, decision A5):
    every `redact` entry's `redacted` list. For a product repository, its
    criterion's journal is read."""
    import project_file

    roots = [repo]
    criterion = project_file.resolve(repo) if project_file.is_project(repo) else None
    if criterion is not None:
        roots.append(criterion)
    found: set[str] = set()
    for root in roots:
        sources = [root / "development" / "journal.jsonl", *sorted((root / "development" / "journal").rglob("*.jsonl"))]
        for source in sources:
            if not source.is_file():
                continue
            for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
                if '"redact"' not in line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict) and entry.get("action") == "redact":
                    found |= {s for s in entry.get("redacted") or [] if isinstance(s, str)}
    return found


def unpin(repo: Path, shas: set[str]) -> bool:
    """Take blobs out of the pins. The pin ref is rewritten as one commit
    without history: an older pin commit would keep the blob reachable.
    Returns whether anything changed."""
    have = pinned(repo)
    if not have & shas:
        return False
    tree = git(repo, "mktree", input="".join(f"100644 blob {s}\t{s}\n" for s in sorted(have - shas)))
    commit = git(
        repo,
        "-c",
        "user.name=catalyst",
        "-c",
        "user.email=catalyst@localhost",
        "commit-tree",
        tree,
        "-m",
        f"catalyst journal: redact {len(have & shas)} blob(s)",
    )
    git(repo, "update-ref", PIN_REF, commit)
    return True


def pinned(repo: Path) -> set[str]:
    if not git(repo, "rev-parse", "--verify", "-q", PIN_REF, check=False):
        return set()
    listing = git(repo, "ls-tree", PIN_REF)
    return {line.split("\t", 1)[1] for line in listing.splitlines() if "\t" in line}


_EXISTS: dict[tuple[str, str], bool] = {}


def prefetch(repo: Path, shas) -> None:
    """Look up many blobs with one `git cat-file --batch-check`, so verify
    costs one process per repository rather than one per blob."""
    todo = sorted({s for s in shas if s and (str(repo), s) not in _EXISTS})
    if not todo:
        return
    res = proc.run(["git", "-C", str(repo), "cat-file", "--batch-check"], input="".join(f"{s}\n" for s in todo))
    if res.returncode != 0:
        return
    for sha, line in zip(todo, res.stdout.splitlines()):
        _EXISTS[(str(repo), sha)] = line.split()[1:2] == ["blob"]


def blob_exists(repo: Path, sha: str) -> bool:
    key = (str(repo), sha)
    if not object_id(sha):
        return False  # never hand a (merged, third-party) value to git as is
    if key not in _EXISTS:
        res = proc.git(repo, "cat-file", "-e", f"{sha}^{{blob}}")
        _EXISTS[key] = res.returncode == 0
    return _EXISTS[key]


def current_hashes(repo: Path, rels: list[str]) -> dict[str, str | None]:
    """Current blob hashes of many files with one `git hash-object`."""
    present = [r for r in rels if (repo / r).is_file()]
    out: dict[str, str | None] = dict.fromkeys(rels)
    if present:
        # absolute paths: --stdin-paths reads them from the repository's top level, not
        # from -C, which is wrong for a project below the top level (a monorepo)
        res = proc.run(
            ["git", "-C", str(repo), "hash-object", "--stdin-paths"],
            input="".join(f"{(repo / r).resolve()}\n" for r in present),
        )
        if res.returncode == 0:
            out.update(zip(present, res.stdout.split()))
    return out


def pin(repo: Path, shas: set[str]) -> int:
    """Add blobs to refs/catalyst/journal; returns how many were new."""
    have = pinned(repo)
    gone = redacted_in(repo)  # never pinned again once redacted
    new = {s for s in shas if s and s not in have and s not in gone and blob_exists(repo, s)}
    if not new:
        return 0
    for _ in range(5):  # compare-and-swap: a concurrent pin never loses blobs
        parent = git(repo, "rev-parse", "--verify", "-q", PIN_REF, check=False)
        have = pinned(repo)
        tree_in = "".join(f"100644 blob {s}\t{s}\n" for s in sorted(have | new))
        tree = git(repo, "mktree", input=tree_in)
        cmd = ["-c", "user.name=catalyst", "-c", "user.email=catalyst@localhost", "commit-tree", tree]
        if parent:
            cmd += ["-p", parent]
        commit = git(repo, *cmd, "-m", f"catalyst journal: pin {len(new)} blob(s)")
        res = subprocess.run(
            ["git", "-C", str(repo), "update-ref", PIN_REF, commit, parent or "0" * 40],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if res.returncode == 0:
            if not parent:  # never silent: this writes into the repository's .git
                print(
                    f"catalyst: created {PIN_REF} in {repo} (pins the blobs the journal records so "
                    f"`git gc` keeps them; local only unless `journal pin --share`)",
                    file=sys.stderr,
                )
            return len(new)
    raise JournalError(f"could not update {PIN_REF} in {repo} (concurrent writers)")


# --- append --------------------------------------------------------------
ARTIFACT_ID_RE = re.compile(r"\b[A-Za-z]+(?:-[A-Z]+)?-\d{3,6}\b")  # REQ-000001, br-AUTH-000001, RECON-000002


@dataclass
class AppendRequest:
    command: str
    action: str
    artifact: str
    targets: list[str]
    intent: list[str]
    files: list[str]
    actor: str
    allow_unchanged: bool = False
    timestamp: str = field(default_factory=now)
    tier: str | None = None
    # fields a verb adds to its entry (`proposed_by`, `proposal`: a proposal accepted, design 26)
    extra: dict | None = None


def head_blob(repo: Path, rel: str) -> str | None:
    # ./ makes the path relative to `repo`, not the repository's top level
    return git(repo, "rev-parse", "-q", "--verify", f"HEAD:./{rel}", check=False) or None


def append(dep: Deployment, req: AppendRequest) -> dict:
    _validate(req)
    check_tier(dep, req.tier, req)
    with journal_lock(dep):
        return _append(dep, req)


_ID_LIKE = re.compile(r"^[A-Za-z]{1,12}[-.]?[0-9][\w.-]*$")  # REQ-000070, R4.8, ADR-002, a3


def intent_thin(intent: list[str]) -> bool:
    """Whether an intent says too little to tell why (R4.8): fewer than three
    words once IDs and roadmap numbers are left out ("work starts",
    "acceptance met", "R4.8"). An empty intent is not thin: the verb writes
    its own."""
    text = " ".join(intent).strip()
    if not text:
        return False
    words = [w for w in re.findall(r"[\w.-]+", text) if not _ID_LIKE.match(w) and re.search(r"[A-Za-z]{2}", w)]
    return len(words) < 3


def command_known(dep: Deployment, command: str) -> bool:
    """Whether an entry's `command` is one this deployment has (R4.8): a
    command of the deployed §4 or one of its aliases (`/create-<type>`), a
    `catalyst <verb>`, or a tier's name (`chore`, `fix`: FORMAT.md lets an
    entry name its tier as its command). A deployment without §4 knows all."""
    from catalyst import spec, tiers

    name = command.strip()
    if name.startswith("catalyst "):
        return True
    if name in {t.id for t in tiers.tiers_for(dep)}:
        return True
    try:
        s = spec.load_section4(dep)
    except spec.SpecError:
        return True
    bare = name.lstrip("/")
    return bare in s.bullets or bare in s.aliases


def check_tier(
    dep: Deployment,
    tier: str | None,
    req: AppendRequest | None = None,
    targets: list[str] | None = None,
    artifact: str | None = None,
) -> None:
    """The tier is one the active module declares (rr-META-006), and a change
    whose tier needs an artifact names one: its artifact is an ID, or it
    targets one (what `trace` asks of a commit, asked of the entry too) —
    from `req`, or from `targets` and `artifact` (`journal adopt`)."""
    from catalyst import tiers

    try:
        tiers.check(dep, tier)
    except ValueError as exc:
        raise JournalError(str(exc)) from None
    needs = next((t for t in tiers.tiers_for(dep) if t.id == tier and t.needs_artifact), None)
    if req is not None:
        targets, artifact = req.targets, req.artifact
    named = req is not None or targets is not None or artifact is not None
    if needs is not None and named and not (targets or ARTIFACT_ID_RE.search(artifact or "")):
        raise JournalError(
            f"a {tier} change serves an artifact: give --artifact <ID> or --target <ID> "
            f"(a change that needs none is --tier {', '.join(t.id for t in tiers.tiers_for(dep) if not t.needs_artifact) or 'chore'})"
        )


def _validate(req: AppendRequest) -> None:
    if req.action not in ACTIONS:
        raise JournalError(f"action '{req.action}' is not one of {', '.join(ACTIONS)}")
    if not req.intent or not all(i.strip() for i in req.intent):
        raise JournalError("at least one non-empty --intent is required: the goal, not a label")
    if not req.files:
        raise JournalError("at least one --file is required")
    if not all(str(f).strip() for f in req.files):
        raise JournalError("an empty --file names no file")
    parse_time(req.timestamp)


def _append(dep: Deployment, req: AppendRequest) -> dict:
    previous = last_after(dep)
    files, to_pin, seen = [], {}, set()
    for raw in req.files:
        path = canonical(dep, raw)
        if Path(os.path.abspath(raw)).is_dir():
            raise JournalError(f"{raw} is a directory: name each file")
        if path in seen:
            continue  # the same file named twice (or under two spellings)
        seen.add(path)
        where = locate(dep, path)
        if where is None:
            raise JournalError(f"{raw} cannot be journaled from this deployment")
        repo, rel = where
        before = previous[path] if path in previous else head_blob(repo, rel)
        after = git(repo, "hash-object", "-w", "--", rel) if (repo / rel).is_file() else None
        if after:
            _EXISTS[(str(repo), after)] = True  # written now: never trust a stale "absent"
        if before is None and after is None:
            hint = f"; did you mean {WC}{raw}?" if (dep.root / raw).is_file() else ""
            raise JournalError(
                f"{raw} does not exist and was never journaled or committed (a criterion file is named "
                f"absolute or as {WC}<path>, a project file relative to the project){hint}"
            )
        if before == after and not req.allow_unchanged:
            raise JournalError(
                f"{path} is unchanged since its last journaled state (pass --allow-unchanged if that is intended)"
            )
        files.append({"path": path, "before": before, "after": after})
        if after:
            to_pin.setdefault(repo, set()).add(after)
    entry = {
        "timestamp": req.timestamp,
        "actor": req.actor,
        "command": req.command,
        "action": req.action,
        "artifact": req.artifact,
        "targets": req.targets,
        "intent": req.intent,
        "files": files,
        "writer": f"catalyst/{__version__}",
    }
    if req.tier:
        entry["tier"] = req.tier
    for key, value in (req.extra or {}).items():
        entry.setdefault(key, value)
    for repo, shas in to_pin.items():  # pin first: a failed pin leaves no entry behind
        pin(repo, shas)
    write(dep, entry)
    return entry


def redact(dep: Deployment, shas: list[str], intent: list[str], actor: str, tier: str | None = None) -> dict:
    """Redact content the journal names (R3.7, decision A5): one `redact`
    entry naming the blobs, and the blobs out of the pins of the criterion
    and of the product repository. No entry, hash or commit is rewritten; a
    commit holding the file may still hold the blob (see the CLI)."""
    if not intent or not all(i.strip() for i in intent):
        raise JournalError("at least one non-empty --intent is required: why the content is redacted")
    named: dict[str, set[str]] = {}
    for _, entry, _ in read(dep):
        for f in (entry or {}).get("files", []) or []:
            if isinstance(f, dict):
                for sha in (f.get("before"), f.get("after")):
                    if sha:
                        named.setdefault(sha, set()).add(str(f.get("path")))
    wanted = list(dict.fromkeys(shas))
    unknown = [s for s in wanted if s not in named]
    if unknown:
        raise JournalError(f"not a blob the journal names: {', '.join(unknown)} (full 40-character hashes)")
    check_tier(dep, tier)
    entry = {
        "timestamp": now(),
        "actor": actor,
        "command": "catalyst journal redact",
        "action": "redact",
        "artifact": "journal",
        "targets": [],
        "intent": intent,
        "files": [],
        "redacted": wanted,
        "writer": f"catalyst/{__version__}",
    }
    if tier:
        entry["tier"] = tier
    write(dep, entry)
    repos = [dep.root] + ([] if dep.standalone else [dep.project_root])
    entry["unpinned_in"] = [r.name for r in dict.fromkeys(repos) if unpin(r, set(wanted))]
    entry["paths"] = sorted({p for s in wanted for p in named[s]})
    return entry


def unjournaled(dep: Deployment) -> list[str]:
    """Journal paths whose current content differs from their last entry."""
    last = last_after(dep)
    by_repo: dict[Path, dict[str, str]] = {}
    for path in last:
        where = locate(dep, path)
        if where is not None:
            by_repo.setdefault(where[0], {})[where[1]] = path
    changed = []
    for repo, rels in by_repo.items():
        for rel, current in current_hashes(repo, list(rels)).items():
            if current != last[rels[rel]]:
                changed.append(rels[rel])
    return sorted(changed)


# --- verify --------------------------------------------------------------
@dataclass
class Issue:
    level: str
    code: str
    at: str  # `<source>:<line>`, "" when about the journal as a whole
    message: str
    legacy: bool = False  # about an entry not written by the catalyst CLI
    path: str | None = None  # the file an issue is about, when it is about one

    def __str__(self) -> str:
        where = self.at or "journal"
        return f"{self.level.upper():7} {self.code:18} {where}: {self.message}"


def verify(dep: Deployment) -> list[Issue]:
    issues: list[Issue] = []
    last: dict[str, tuple[str | None, str, bool]] = {}  # path -> (after, where, cli-written)
    seen: dict[str, set] = {}  # path -> every after recorded
    prev_t: datetime.datetime | None = None
    pins: dict[Path, set[str]] = {}

    def level(strict: bool) -> str:
        return "error" if strict else "warning"

    entries = read_checked(dep)
    redacted = {
        s
        for _, e, _ in entries
        if isinstance(e, dict) and e.get("action") == "redact"
        for s in e.get("redacted") or []
        if isinstance(s, str)
    }

    for n, entry, _ in entries:
        if entry is None:
            issues.append(Issue("error", "malformed", n, "not a JSON object"))
            continue
        if entry.get("action") == "redact":  # history, never a problem: what was removed, by whom, why
            count = len(entry.get("redacted") or [])
            issues.append(Issue("note", "redacted", n, f"{count} blob(s) redacted by {entry.get('actor')}"))
        cli = str(entry.get("writer", "")).startswith("catalyst/")
        missing = [k for k in REQUIRED if k not in entry]
        if missing:
            issues.append(Issue(level(cli), "schema", n, f"missing {', '.join(missing)}", not cli))
        t = _entry_time(entry)
        if t is None:
            issues.append(
                Issue(level(cli), "schema", n, f"timestamp '{entry.get('timestamp')}' is not ISO 8601", not cli)
            )
        elif prev_t is not None and t < prev_t:
            # expected after a merge: each side's entries keep their own order
            issues.append(
                Issue("warning", "time-order", n, f"{entry.get('timestamp')} is earlier than a previous entry", not cli)
            )
        if t is not None and (prev_t is None or t > prev_t):
            prev_t = t
        for f in entry.get("files", []) or []:
            if not isinstance(f, dict) or "path" not in f:
                continue
            recorded = str(f["path"])
            if recorded.startswith("/"):
                issues.append(
                    Issue("warning", "absolute-path", n, f"{recorded} is machine-specific (INV-1, INV-6)", not cli)
                )
            before, after = f.get("before"), f.get("after")
            path = entry_path(dep, entry, f)
            superseded = bool(f.get("superseded"))  # adopted history, outside the chain
            if not superseded and path in last and last[path][0] != before:
                if before is not None and before in seen[path]:
                    # both sides of a merge edited this file from the same
                    # earlier state: a fork, resolved by a later entry
                    issues.append(
                        Issue(
                            "note",
                            "concurrent-edit",
                            n,
                            f"{path}: edited from an earlier state than {last[path][1]} (merged work)",
                            not cli,
                        )
                    )
                else:
                    issues.append(
                        Issue(
                            level(cli),
                            "chain",
                            n,
                            f"{path}: before {str(before)[:10]} != after {str(last[path][0])[:10]} at {last[path][1]}",
                            not cli,
                        )
                    )
            where = locate(dep, path)
            if where is not None:
                repo = where[0]
                for sha in (before, after):
                    if sha and sha in redacted:
                        continue  # redacted (R3.7): gone on purpose, reported once below
                    if sha and not blob_exists(repo, sha):
                        # a before inherited from a legacy entry carries that entry's gap
                        inherited = sha == before and path in last and not last[path][2]
                        strict = cli and not inherited
                        issues.append(
                            Issue(
                                level(strict),
                                "missing-blob",
                                n,
                                f"{path}: blob {sha[:10]} is not in {repo.name}'s object store"
                                + (" (inherited from a pre-CLI entry)" if inherited else ""),
                                not strict,
                            )
                        )
                if cli and after and after not in redacted:
                    if repo not in pins:
                        pins[repo] = pinned(repo)
                    if after not in pins[repo]:
                        issues.append(
                            Issue(
                                "warning",
                                "unpinned",
                                n,
                                f"{path}: blob {after[:10]} is not pinned — `catalyst journal pin`",
                            )
                        )
            if not superseded:
                last[path] = (after, n, cli)
            seen.setdefault(path, {None}).update({before, after})

    by_repo: dict[Path, list[str]] = {}
    for path in last:
        where = locate(dep, path)
        if where is not None:
            by_repo.setdefault(where[0], []).append(where[1])
    current_by = {repo: current_hashes(repo, rels) for repo, rels in by_repo.items()}
    for path, (after, n, cli) in sorted(last.items()):
        where = locate(dep, path)
        if where is None:
            continue
        repo, rel = where
        current = current_by[repo][rel]
        if current != after:
            state = "deleted" if current is None else "changed"
            issues.append(
                Issue(level(cli), "unjournaled", n, f"{path} {state} since its last journal entry", not cli, path=path)
            )
    return issues


# --- restore -------------------------------------------------------------
def restore(dep: Deployment, timestamp: str, out: Path) -> tuple[list[str], list[str]]:
    """Materialise every journaled path as of `timestamp` into `out`.
    Returns (restored paths, paths whose blob is missing)."""
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise JournalError(f"{out} exists and is not an empty directory — restore never overwrites")
    until = parse_time(timestamp)
    state: dict[str, str | None] = {}
    later_before: dict[str, str | None] = {}  # a file first journaled after `until`: its `before`
    for _, entry, _ in read(dep):
        t = _entry_time(entry) if entry else None
        if entry is None or t is None:
            continue
        for f in entry.get("files", []) or []:
            if not (isinstance(f, dict) and "path" in f) or f.get("superseded"):
                continue
            path = entry_path(dep, entry, f)
            if t <= until:
                state[path] = f.get("after")
            else:
                later_before.setdefault(path, f.get("before"))
    for path, sha in later_before.items():
        state.setdefault(path, sha)
    restored, missing = [], []
    gone = redacted_in(dep.root)
    for path, sha in sorted(state.items()):
        where = locate(dep, path)
        if sha is None or where is None:
            continue
        repo = where[0]
        if not object_id(sha) or sha in gone:
            missing.append(path)  # a redacted blob is never restored, even while git still has it
            continue
        res = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", sha], capture_output=True)
        if res.returncode != 0:
            missing.append(path)
            continue
        target = out / path
        if not os.path.abspath(target).startswith(os.path.abspath(out) + os.sep):
            missing.append(path)  # would escape the side directory
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(res.stdout)
        restored.append(path)
    return restored, missing


def pin_all(dep: Deployment) -> dict[str, int]:
    """Pin every blob any entry references (backfill)."""
    wanted: dict[Path, set[str]] = {}
    for _, entry, _ in read(dep):
        for f in (entry or {}).get("files", []) or []:
            if not isinstance(f, dict) or "path" not in f:
                continue
            where = locate(dep, entry_path(dep, entry, f))
            if where is None:
                continue
            for sha in (f.get("before"), f.get("after")):
                if sha:
                    wanted.setdefault(where[0], set()).add(sha)
    return {repo.name: pin(repo, shas) for repo, shas in wanted.items()}
