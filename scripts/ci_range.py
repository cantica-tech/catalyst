"""The git revision range a CI run checks, from the GitHub event that started it.

- a pull request: `base..head`;
- a push whose previous tip this clone does not have (a force push, or a new branch: `before` is all zeros) while
  `origin/main` is known: `origin/main..sha`, whatever main does not have yet;
- any other push: `before..sha`;
- a new branch without `origin/main`: `sha~1..sha`.

Used by the Deployment Rules workflow's trace and journal checks (REQ-000117); prints the range on stdout.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ZERO = "0" * 40


def _git_ok(repo: Path, *args: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False).returncode == 0


def ci_range(event: str, sha: str, before: str = "", base: str = "", head: str = "", repo: Path = Path()) -> str:
    """The range for `event` (a GitHub event name). Raises ValueError when the event lacks what it needs."""
    if event == "pull_request":
        if not (base and head):
            raise ValueError("a pull_request range needs --base and --head")
        return f"{base}..{head}"
    if not sha:
        raise ValueError("a push range needs --sha")
    known = bool(before) and not before.startswith("-") and _git_ok(repo, "cat-file", "-e", f"{before}^{{commit}}")
    if not known and _git_ok(repo, "rev-parse", "-q", "--verify", "origin/main"):
        # a force push (the previous tip is gone) or a new branch
        return f"origin/main..{sha}"
    if before and before != ZERO:
        return f"{before}..{sha}"
    return f"{sha}~1..{sha}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--event", required=True, help="github.event_name")
    parser.add_argument("--sha", default="", help="github.sha")
    parser.add_argument("--before", default="", help="github.event.before (a push)")
    parser.add_argument("--base", default="", help="github.event.pull_request.base.sha")
    parser.add_argument("--head", default="", help="github.event.pull_request.head.sha")
    args = parser.parse_args(argv)
    try:
        print(ci_range(args.event, args.sha, args.before, args.base, args.head))
    except ValueError as exc:
        print(f"ci_range: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
