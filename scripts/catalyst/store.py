"""The criterion's store (roadmap R3.2): where its files live, and how it is
shared. Two seams, each behind a handful of verbs, so a driver can change
without the rest of catalyst knowing:

- `Store`, the working form: `read`, `list`, `append` (append-only files,
  such as the journal's shards) and `lock`. Driver `home`: the criterion's
  own directory (`$CATALYST_HOME/projects/<name>/criterion`, or a legacy
  working copy). A server driver (`catalyst serve`, roadmap R3.9) implements
  the same four verbs.
- `Share`, publishing the working form to others: `info`, `status`, `head`,
  `pull` and `push`. Drivers: `local` (not shared) and `git` (a criterion
  repository: today's `catalyst criterion` code). `catalyst.toml` may name
  the driver (`share = "git"`); without it, a criterion with a git remote, or
  a project file naming its repository, is `git`, any other `local`.
"""

from __future__ import annotations

import contextlib
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from catalyst import lock
from catalyst.deployment import Deployment

SHARE_KEY = "share"


class ShareError(Exception):
    pass


# --- the working form ---------------------------------------------------------
class Store(Protocol):
    driver: str

    def read(self, rel: str) -> str | None: ...
    def list(self, prefix: str, suffix: str = "") -> list[str]: ...
    def append(self, rel: str, line: str) -> None: ...
    def lock(self, name: str, **options) -> contextlib.AbstractContextManager: ...


@dataclass
class HomeStore:
    """The criterion's files on this machine."""

    root: Path
    driver: str = "home"

    def read(self, rel: str) -> str | None:
        """A file's text, or None when it does not exist."""
        path = self.root / rel
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def list(self, prefix: str, suffix: str = "") -> list[str]:
        """Files at or under `prefix` ending in `suffix`, criterion-relative,
        sorted."""
        base = self.root / prefix
        if base.is_file():
            return [prefix] if prefix.endswith(suffix) else []
        if not base.is_dir():
            return []
        found = (p for p in base.rglob(f"*{suffix}") if p.is_file())
        return sorted(p.relative_to(self.root).as_posix() for p in found)

    def append(self, rel: str, line: str) -> None:
        """Add one line to an append-only file (created when missing)."""
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(line.rstrip("\n") + "\n")

    def lock(self, name: str, **options) -> contextlib.AbstractContextManager:
        """Hold the criterion's `<name>` lock (catalyst.lock) for a block."""
        return lock.held(self.root, name, **options)


def store_for(dep: Deployment) -> Store:
    return HomeStore(dep.root)


# --- sharing -------------------------------------------------------------------
@dataclass
class ShareStatus:
    driver: str
    location: str | None  # where the shared copy is (a URL), None when not shared
    branch: str | None
    dirty: list[str]  # local changes not yet published
    ahead: int | None  # published copy vs. this one, when known
    behind: int | None
    mode: str | None = None  # the driver's own detail (git: home, submodule, local)

    def as_dict(self) -> dict:
        return asdict(self)


class Share(Protocol):
    driver: str

    def info(self) -> dict: ...
    def status(self, fetch: bool = False) -> ShareStatus: ...
    def head(self) -> str | None: ...
    def pull(self) -> str: ...
    def push(self, signer: dict, message: str, open_pr: bool = True) -> dict: ...


NOT_SHARED = "this criterion is not shared — `catalyst criterion create <url>` publishes it to a git repository"


@dataclass
class LocalShare:
    """Not shared: everything stays on this machine."""

    dep: Deployment
    driver: str = "local"

    def info(self) -> dict:
        return {"driver": self.driver, "location": None, "capabilities": []}

    def status(self, fetch: bool = False) -> ShareStatus:
        return ShareStatus(self.driver, None, None, [], None, None)

    def head(self) -> str | None:
        return None

    def pull(self) -> str:
        raise ShareError(NOT_SHARED)

    def push(self, signer: dict, message: str, open_pr: bool = True) -> dict:
        raise ShareError(NOT_SHARED)


@dataclass
class GitShare:
    """A criterion repository (Rules-of-Rules.md §13, INV-18): pull
    fast-forwards to the shared branch, push lands a topic branch through a
    pull request (`criterion.py`)."""

    dep: Deployment
    driver: str = "git"

    def info(self) -> dict:
        from catalyst import criterion as cr

        return {
            "driver": self.driver,
            "location": cr.remote_url(self.dep.root) or self.dep.pointer.get("catalyst_repo_url"),
            "branch": cr.shared_branch(self.dep),
            "capabilities": ["pull", "push", "pull-request", "integrity", "protect"],
        }

    def status(self, fetch: bool = False) -> ShareStatus:
        from catalyst import criterion as cr

        st = cr.status(self.dep, fetch=fetch)
        return ShareStatus(self.driver, st.remote, st.branch, st.dirty, st.ahead, st.behind, st.mode)

    def head(self) -> str | None:
        """The shared branch's last commit, as last fetched."""
        from catalyst import criterion as cr

        res = subprocess.run(
            ["git", "-C", str(self.dep.root), "rev-parse", "-q", "--verify", f"origin/{cr.shared_branch(self.dep)}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        return res.stdout.strip() or None

    def pull(self) -> str:
        from catalyst import criterion as cr

        try:
            return cr.sync(self.dep)
        except cr.NeedsURL:
            raise ShareError(NOT_SHARED) from None

    def push(self, signer: dict, message: str, open_pr: bool = True) -> dict:
        from catalyst import criterion as cr

        try:
            res = cr.push(self.dep, signer, message, open_pr=open_pr)
        except cr.NeedsURL:
            raise ShareError(NOT_SHARED) from None
        return {"branch": res.branch, "commits": res.commits, "pull_request": res.pr, "regenerated": res.regenerated}


DRIVERS: dict[str, type] = {"local": LocalShare, "git": GitShare}


def share_driver(dep: Deployment) -> str:
    """The driver the project file names, else the one the criterion implies."""
    named = dep.pointer.get(SHARE_KEY)
    if named is not None:
        return str(named)
    from catalyst import criterion as cr

    return "git" if dep.pointer.get("catalyst_repo_url") or cr.remote_url(dep.root) else "local"


def share_for(dep: Deployment) -> Share:
    name = share_driver(dep)
    if name not in DRIVERS:
        raise ShareError(f"unknown share driver '{name}' in catalyst.toml (known: {', '.join(sorted(DRIVERS))})")
    return DRIVERS[name](dep)
