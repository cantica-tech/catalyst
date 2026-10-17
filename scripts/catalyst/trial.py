"""`catalyst try <verb …>` (owner decision T; design `docs/design/27`): one
change made on a scratch copy of the criterion, and what it would do —
the files it writes, the `check` findings it adds and clears, the trace of
the entity it changes and the approvals it would leave waiting. Nothing in
the criterion or the project changes; the copy is removed after.

The copy is a `git clone --shared` of the criterion (its objects read
where they are, its refs its own, so the journal's pins move only in the
copy) with the criterion's files as they are now copied over it,
uncommitted changes and new files included, never its `.venv` or `bin/`.
It is loaded as a bare working copy, as `catalyst serve` reads one.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from catalyst.deployment import Deployment, load_working_copy

# The writing verbs a try may make (design 27 §7.5): the change, never sharing or installing.
VERBS = ("status", "new", "link", "rename", "restore", "approve", "reconcile", "propose")
SKIP = {".git", ".venv", "bin", "__pycache__"}


class TryError(Exception):
    pass


@dataclass
class Scratch:
    root: Path
    keep: bool = False
    _files: dict[str, str] = field(default_factory=dict)


def _home() -> Path:
    from project_file import home

    return home()


def _walk(root: Path) -> dict[str, str]:
    """Every file under `root` but the skipped folders: path -> git blob hash."""
    out: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for name in filenames:
            path = Path(dirpath) / name
            data = path.read_bytes()
            out[path.relative_to(root).as_posix()] = hashlib.sha1(  # noqa: S324 (git's own blob hash)
                b"blob %d\0" % len(data) + data
            ).hexdigest()
    return out


def make(dep: Deployment, keep: bool = False) -> Scratch:
    """The scratch copy: a shared clone of the criterion, its files as they are now."""
    if not (dep.root / ".git").exists():
        raise TryError(f"the criterion at {dep.root} is not a git repository: a try needs its history")
    stamp = time.strftime("%Y%m%dT%H%M%S")
    name = dep.pointer.get("project_name") or dep.root.parent.name
    root = _home() / "scratch" / f"{name}-{stamp}-{os.getpid()}"
    root.parent.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(
        ["git", "clone", "-q", "--shared", str(dep.root), str(root)], capture_output=True, text=True, check=False
    )
    if res.returncode != 0:
        raise TryError(f"the scratch copy could not be made: {res.stderr.strip()}")
    now = _walk(dep.root)
    for rel in set(_walk(root)) - set(now):  # deleted in the criterion, not yet committed
        (root / rel).unlink()
    for rel in now:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dep.root / rel, target)
    return Scratch(root, keep)


def remove(scratch: Scratch) -> None:
    if not scratch.keep:
        shutil.rmtree(scratch.root, ignore_errors=True)


def _findings(dep: Deployment) -> list[dict]:
    from catalyst import check

    report = check.run(dep)
    return check.as_json(report, dep, False)["findings"]


def _waiting(dep: Deployment) -> set[tuple[str, str, int]]:
    from catalyst import gates
    from catalyst.corpus import load_corpus

    return {(w["id"], w["gate"], w["missing"]) for w in gates.waiting(dep, load_corpus(dep))}


def _run(scratch: Scratch, argv: list[str]) -> tuple[int, str, str]:
    """The verb, run by this catalyst on the copy, its output captured."""
    from catalyst.__main__ import main

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(["--working-copy", str(scratch.root), *argv])
        except SystemExit as exc:  # argparse refusing the arguments
            code = int(exc.code) if isinstance(exc.code, int) else 2
    return code, out.getvalue(), err.getvalue()


def attempt(dep: Deployment, argv: list[str], keep: bool = False) -> dict:
    """Make the change `argv` names on a scratch copy and report what it did."""
    from catalyst import journal
    from catalyst.corpus import load_corpus

    if not argv or argv[0] not in VERBS:
        raise TryError(f"a try makes one of catalyst's writing verbs ({', '.join(VERBS)}); not {argv[:1] or '—'}")
    if any(a in ("--working-copy", "--project") for a in argv):
        raise TryError("a try chooses where the change is made: no --working-copy or --project")
    scratch = make(dep, keep)
    try:
        copy = load_working_copy(scratch.root)
        before_files, before = _walk(scratch.root), _findings(copy)
        before_waiting = _waiting(copy)
        seen = sum(1 for _ in journal.read(copy))
        code, out, err = _run(scratch, argv)
        copy = load_working_copy(scratch.root)
        after_files = _walk(scratch.root)
        files = [
            {"path": rel, "before": before_files.get(rel), "after": after_files.get(rel)}
            for rel in sorted(set(before_files) | set(after_files))
            if before_files.get(rel) != after_files.get(rel) and not rel.startswith("development/journal/")
        ]
        report: dict = {
            "change": shlex.join(["catalyst", *argv]),
            "ok": code == 0,
            "refused": None if code == 0 else (err.strip() or out.strip() or f"exit {code}"),
            "output": out.strip(),
            "files": files,
            "check": {"added": [], "cleared": []},
            "impact": None,
            "gates": [],
            "scratch": str(scratch.root) if keep else None,
        }
        if code != 0:
            return report
        after = _findings(copy)
        key = lambda f: (f["level"], f["text"])  # noqa: E731
        had, has = {key(f) for f in before}, {key(f) for f in after}
        report["check"] = {
            "added": [f for f in after if key(f) not in had],
            "cleared": [f for f in before if key(f) not in has],
        }
        changed = [e.get("artifact") for _, e, _ in list(journal.read(copy))[seen:] if e]
        report["impact"] = _impact(copy, load_corpus(copy), changed)
        report["gates"] = [{"id": i, "gate": g, "missing": m} for i, g, m in sorted(_waiting(copy) - before_waiting)]
        return report
    finally:
        remove(scratch)


def _impact(dep: Deployment, corpus, changed: list) -> dict | None:
    from catalyst import impact, views

    for item in reversed([c for c in changed if isinstance(c, str)]):
        try:
            found = views.resolve(corpus, item)
        except views.ViewError:
            continue
        if found:
            return impact.impact(dep, corpus, found)
    return None


def render(report: dict) -> str:
    lines = [f"tried: {report['change']} (on a scratch copy; nothing in the criterion changed)"]
    if not report["ok"]:
        lines.append(f"refused: {report['refused']}")
        return "\n".join(lines) + "\n"
    lines.append(f"files it writes: {len(report['files'])}")
    lines += [
        f"  {f['path']}" + ("  (new)" if not f["before"] else "  (removed)" if not f["after"] else "")
        for f in report["files"]
    ]
    added, cleared = report["check"]["added"], report["check"]["cleared"]
    lines.append(f"check: {len(added)} finding(s) added, {len(cleared)} cleared")
    lines += [f"  + {f['level']}: {f['text']}" for f in added]
    lines += [f"  - {f['level']}: {f['text']}" for f in cleared]
    for g in report["gates"]:
        lines.append(f"  waits for {g['missing']} approval(s) under gate {g['gate']}: {g['id']}")
    if report["impact"]:
        up, down = (len(report["impact"].get(k) or []) for k in ("upstream", "downstream"))
        lines.append(f"impact: {report['impact'].get('id')} rests on {up} and reaches {down} entities")
    if report.get("scratch"):
        lines.append(f"scratch copy kept at {report['scratch']}")
    return "\n".join(lines) + "\n"
