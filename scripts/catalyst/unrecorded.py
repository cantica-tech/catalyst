"""Changes made outside catalyst: committed (or staged) product changes the
journal does not record.

The journal records every file's content as a git blob hash (`after`), in
order: each file has a chain of journaled states. A product commit's change
to a file is recorded when its result is a state the chain reaches after the
commit's starting state; anything else — a blob no entry records, or a
return to an older state — was written without catalyst (by hand, with git)
and is an *unrecorded change*. Content decides, never clocks: committing
before journaling, rebases and skewed machines change nothing. Only history after the deployment's baseline is checked: the
pointer's `journal_since` (a commit; empty means the whole history), set by
`catalyst init` and by migration 0.42.0. Merge commits carry their parents'
changes and are skipped; the working copy (`.criterion`) is never a product
file.

Severity follows the beta rollout (the format and trace checks'): an
unrecorded change is a warning while the deployment's format is a release
candidate (`1.0-rc`) and an error from format `1.0`, or earlier when the
pointer sets `"strict_journal": true`.

`catalyst journal adopt <commit>` records a manual commit in the journal
after the fact (`origin: manual`, the git author as actor); rejecting one
means reverting it.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from catalyst import __version__, journal
from catalyst.deployment import Deployment
from catalyst.scope import governs

ZERO = "0" * 40
GITLINK = "160000"
BASELINE_KEY = "journal_since"


@dataclass
class Commit:
    sha: str
    author: str
    subject: str
    changes: list[tuple[str, str | None, str | None]] = field(default_factory=list)  # path, before, after
    time: float = 0.0  # committer time

    @property
    def short(self) -> str:
        return self.sha[:10]


@dataclass
class Journaled:
    """What the journal records, per product path: its states in journal
    order, every blob it names (before or after), and the commits adopted
    for it."""

    states: dict[str, list[str | None]] = field(default_factory=dict)
    seen: dict[str, set[str | None]] = field(default_factory=dict)
    adopted: set[tuple[str, str]] = field(default_factory=set)

    def latest(self, path: str) -> tuple[bool, str | None]:
        """(journaled at all, its last journaled state)."""
        chain = self.states.get(path)
        return (True, chain[-1]) if chain else (False, None)

    def add(self, path: str, before: str | None, after: str | None) -> None:
        self.states.setdefault(path, []).append(after)
        self.seen.setdefault(path, set()).update({before, after})

    def records(self, commit: Commit, change: tuple[str, str | None, str | None]) -> bool:
        """A commit's change is recorded when that commit was adopted for the
        path, or when the path's chain reaches the change's result after its
        starting state (so a revert to an older state is not)."""
        path, before, after = change
        if (path, commit.sha) in self.adopted:
            return True
        chain = self.states.get(path, [])
        start = chain.index(before) + 1 if before is not None and before in chain else 0
        return after in chain[start:]


def level(dep: Deployment) -> str:
    """ "error" once the deployment is out of the beta (a release format) or
    opts in; "warning" while its format is a release candidate."""
    if dep.pointer.get("strict_journal") is True:
        return "error"
    fmt = str(dep.pointer.get("format") or "")
    return "error" if fmt and "-" not in fmt else "warning"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")


def recorded(dep: Deployment) -> Journaled:
    j = Journaled()
    for _, entry, _ in journal.read_checked(dep):
        if entry is None:
            continue
        for f in entry.get("files", []) or []:
            if not (isinstance(f, dict) and "path" in f):
                continue
            path = journal.entry_path(dep, entry, f)
            if entry.get("commit"):
                j.adopted.add((path, str(entry["commit"])))
            if not f.get("superseded"):
                j.add(path, f.get("before"), f.get("after"))
    return j


def product_path(path: str) -> bool:
    return not (path == ".criterion" or path.startswith(".criterion/"))


def _parse_raw(tokens: list[str]) -> list[tuple[str, str | None, str | None]]:
    """`git ... --raw -z --no-renames` tokens -> (path, before, after)."""
    out, i = [], 0
    while i < len(tokens):
        meta = tokens[i]
        if not meta.startswith(":"):
            i += 1
            continue
        path = tokens[i + 1] if i + 1 < len(tokens) else ""
        i += 2
        parts = meta[1:].split()
        if len(parts) < 5:
            continue
        old_mode, new_mode, old, new = parts[0], parts[1], parts[2], parts[3]
        if GITLINK in (old_mode, new_mode) or not product_path(path) or old == new:
            continue
        out.append((path, None if old == ZERO else old, None if new == ZERO else new))
    return out


def commits(repo: Path, revs: list[str], walk: bool = True) -> list[Commit]:
    """Non-merge commits in `revs` (revisions or ranges, never options),
    oldest first, with the product files each one changes; `walk=False`:
    only the named commits."""
    # --relative: paths from the project's own directory, as the journal records them
    res = _git(
        repo,
        "log",
        "--reverse",
        "--no-merges",
        "--no-renames",
        "--relative",
        "--raw",
        "--no-abbrev",
        "-z",
        "--format=%x1e%H%x00%an%x00%ct%x00%s",
        *([] if walk else ["--no-walk"]),
        *journal.revisions(revs),
    )
    if res.returncode != 0:
        raise ValueError(res.stderr.strip() or f"bad range {' '.join(revs)}")
    out = []
    for record in res.stdout.split("\x1e"):
        if not record.strip("\0\n"):
            continue
        head, _, raw = record.partition("\n")
        parts = head.split("\x00")
        if len(parts) < 4:
            continue
        sha, author, when, subject = parts[0], parts[1], parts[2], parts[3]
        # whatever follows the subject on the header line, then the raw tokens
        tokens = [t.lstrip("\n") for t in ("\x00".join(parts[4:]) + "\x00" + raw).split("\x00")]
        changes = [c for c in _parse_raw([t for t in tokens if t]) if governs(repo, c[0])]
        out.append(Commit(sha, author, subject, changes, float(when) if when.isdigit() else 0.0))
    return out


def unrecorded_in(commit: Commit, journaled: Journaled) -> list[tuple[str, str | None, str | None]]:
    return [c for c in commit.changes if not journaled.records(commit, c)]


def baseline(dep: Deployment) -> str | None:
    """The pointer's baseline: a commit, "" for the whole history, or None
    when the pointer declares none (history is then not checked)."""
    value = dep.pointer.get(BASELINE_KEY)
    if value is None:
        return None
    return str(value)


def baseline_missing(dep: Deployment) -> bool:
    """The baseline names a commit this clone does not have (a shallow CI
    checkout, rewritten history): history cannot be scoped, so it is not
    checked."""
    base = baseline(dep)
    if base and base.startswith("-"):
        return True  # never handed to git as an option
    return bool(base) and _git(dep.project_root, "cat-file", "-e", f"{base}^{{commit}}").returncode != 0


MISSING_BASELINE = (
    "the baseline `journal_since` is not in this clone (a shallow checkout, or rewritten "
    "history): changes outside catalyst are not checked — fetch the full history"
)


def scoped(dep: Deployment, revs: list[str]) -> list[str]:
    """`revs` limited to history after the baseline."""
    base = baseline(dep)
    return revs + ([f"^{base}"] if base else [])


def since_baseline(dep: Deployment) -> list[Commit]:
    """Commits after the baseline with at least one unrecorded change (each
    commit's `changes` narrowed to those)."""
    if dep.standalone or baseline(dep) is None or baseline_missing(dep):
        return []
    if _git(dep.project_root, "rev-parse", "--verify", "-q", "HEAD").returncode != 0:
        return []  # no commits yet
    journaled = recorded(dep)
    out = []
    for c in commits(dep.project_root, scoped(dep, ["HEAD"])):
        missing = unrecorded_in(c, journaled)
        if missing:
            out.append(Commit(c.sha, c.author, c.subject, missing, c.time))
    return out


def staged(dep: Deployment) -> list[tuple[str, str | None, str | None]]:
    """Staged product changes the journal does not record (the commit-msg hook)."""
    res = _git(dep.project_root, "diff", "--cached", "--raw", "--no-renames", "--relative", "--no-abbrev", "-z")
    if res.returncode != 0:
        return []
    journaled = recorded(dep)
    out = []
    for c in _parse_raw([t for t in res.stdout.split("\x00") if t]):
        if not governs(dep.project_root, c[0]):
            continue  # a nested deployment's, or opted out
        known, state = journaled.latest(c[0])  # the commit being made: the chain's end
        if not known or state != c[2]:
            out.append(c)
    return out


def describe(commit: Commit) -> str:
    paths = [p for p, _, _ in commit.changes]
    shown = ", ".join(paths[:3]) + (f" (+{len(paths) - 3} more)" if len(paths) > 3 else "")
    return (
        f"{commit.short} by {commit.author} ({commit.subject[:50]!r}): {shown} not in the journal "
        f"(`catalyst journal adopt {commit.short}`)"
    )


# --- adopt ---------------------------------------------------------------
def adopt(
    dep: Deployment,
    revs: list[str],
    intent: list[str],
    tier: str | None = None,
    targets: list[str] | None = None,
    artifact: str | None = None,
    actor: str | None = None,
) -> list[dict]:
    """Record each commit's unrecorded changes as one journal entry, oldest
    first, the git author as actor unless `actor` is given. A file whose
    journal chain has not moved past the commit continues it (`before` its
    last journaled state, else the parent's blob); a file journaled again
    since the commit is recorded as history only (`superseded`, the parent's
    blob as `before`), so it never becomes the file's current state —
    "since" read from content: the chain has moved on from the parent and
    already went through the commit's result. Returns the entries written."""
    if not intent or not all(i.strip() for i in intent):
        raise journal.JournalError("at least one non-empty --intent is required: why the change was made")
    if tier is not None and tier not in journal.TIERS:
        raise journal.JournalError(f"tier '{tier}' is not one of {', '.join(journal.TIERS)}")
    if dep.standalone:
        raise journal.JournalError("a standalone working copy has no product history to adopt")
    with journal.journal_lock(dep):
        return _adopt(dep, revs, intent, tier, targets or [], artifact, actor)


def _adopt(dep, revs, intent, tier, targets, artifact, actor) -> list[dict]:
    journaled = recorded(dep)
    written = []
    single = not any(".." in r for r in revs)  # named commits, not ranges: just those
    found = commits(dep.project_root, revs, walk=not single)
    for c in sorted(found, key=lambda c: c.time) if single else found:
        missing = unrecorded_in(c, journaled)
        if not missing:
            continue
        files = []
        for path, parent, after in missing:
            known, last = journaled.latest(path)
            if known and last != parent and after in journaled.seen.get(path, set()):
                files.append({"path": path, "before": parent, "after": after, "superseded": True})
                continue
            before = last if known else parent
            files.append({"path": path, "before": before, "after": after})
            journaled.add(path, before, after)
        entry = {
            "timestamp": journal.now(),
            "actor": actor or c.author,
            "command": "/adopt",
            "action": "update",
            "artifact": artifact or f"commit {c.short}",
            "targets": targets,
            "intent": intent,
            "files": files,
            "writer": f"catalyst/{__version__}",
            "origin": "manual",
            "commit": c.sha,
        }
        if tier:
            entry["tier"] = tier
        journal.pin(dep.project_root, {a for _, _, a in missing if a})
        journal.write(dep, entry)
        journaled.adopted.update((p, c.sha) for p, _, _ in missing)
        written.append(entry)
    return written
