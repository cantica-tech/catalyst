"""Whether a finished workflow run is retried once (.github/workflows/retry-stalled.yml).

A macOS job now and then stalls: it never gets a runner, GitHub cancels it after 15 minutes of waiting, with no log
and no steps run, and a rerun passes. (A job that times out while running is treated the same way.)
A run is retried only when it is its first attempt, it did not succeed, and every job that did not pass is a macOS
job that was cancelled or timed out. A real failure, or any job on another OS that did not pass, is never retried.

Usage: python3 scripts/retry_stalled.py <jobs.json> <run attempt> <run conclusion>
  <jobs.json> is the response of GET /repos/{repo}/actions/runs/{id}/attempts/{n}/jobs.
Prints one line: `retry: <why>` or `no retry: <why>`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

UNSUCCESSFUL_RUN = {"failure", "cancelled", "timed_out"}
PASSED = {"success", "skipped", "neutral"}
STALLED = {"cancelled", "timed_out"}


def is_macos(job: dict[str, Any]) -> bool:
    labels = job.get("labels") or []
    return any(re.match(r"macos", str(label), re.IGNORECASE) for label in labels) or bool(
        re.search(r"macos", str(job.get("name") or ""), re.IGNORECASE)
    )


def _describe(job: dict[str, Any]) -> str:
    return f"{job.get('name') or '?'} ({job.get('conclusion') or 'no conclusion'})"


def decide(attempt: int, conclusion: str, jobs: list[dict[str, Any]]) -> tuple[bool, str]:
    """(retry, why) for a run's first-or-later attempt, its conclusion and that attempt's jobs."""
    if attempt != 1:
        return False, f"attempt {attempt}: a run is retried once, from its first attempt only"
    if conclusion not in UNSUCCESSFUL_RUN:
        return False, f"the run's conclusion is {conclusion}"
    not_passed = [job for job in jobs if job.get("conclusion") not in PASSED]
    if not not_passed:
        return False, "no job failed"
    other = [job for job in not_passed if not is_macos(job)]
    if other:
        return False, "a job on another OS did not pass: " + ", ".join(map(_describe, other))
    failed = [job for job in not_passed if job.get("conclusion") not in STALLED]
    if failed:
        return False, "a macOS job really failed: " + ", ".join(map(_describe, failed))
    return True, "macOS job(s) stalled: " + ", ".join(map(_describe, not_passed))


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: retry_stalled.py <jobs.json> <run attempt> <run conclusion>", file=sys.stderr)
        return 2
    file, attempt, conclusion = argv
    body = json.loads(Path(file).read_text(encoding="utf-8"))
    retry, why = decide(int(attempt), conclusion, body.get("jobs") or [])
    print(f"{'retry' if retry else 'no retry'}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
