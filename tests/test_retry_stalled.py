"""scripts/retry_stalled.py: whether retry-stalled.yml reruns a run's failed jobs once.

Fed with the jobs GitHub recorded for the Tests run 41669902586, attempt 1 (both macOS jobs stalled and were
cancelled at 15 minutes), and variants of it.
"""

import json
import subprocess
import sys
from pathlib import Path

import retry_stalled

FIXTURE = Path(__file__).parent / "fixtures" / "retry_stalled_jobs.json"
SCRIPT = Path(__file__).parent.parent / "scripts" / "retry_stalled.py"
RECORDED = json.loads(FIXTURE.read_text(encoding="utf-8"))["jobs"]
MAC_311 = "pytest (macos-latest, Python 3.11)"
MAC_313 = "pytest (macos-latest, Python 3.13)"
LINUX_311 = "pytest (ubuntu-latest, Python 3.11)"


def _with(changes: dict[str, str]) -> list[dict]:
    """The recorded jobs, with the conclusions in `changes` (keyed by job name)."""
    return [{**job, "conclusion": changes.get(job["name"], job["conclusion"])} for job in RECORDED]


def test_cancelled_macos_jobs_are_retried():
    retry, why = retry_stalled.decide(1, "cancelled", RECORDED)
    assert retry
    assert MAC_311 in why and MAC_313 in why


def test_a_timed_out_macos_job_is_retried():
    assert retry_stalled.decide(1, "failure", _with({MAC_311: "timed_out", MAC_313: "success"}))[0]


def test_a_macos_job_that_really_failed_is_not_retried():
    retry, why = retry_stalled.decide(1, "failure", _with({MAC_313: "failure"}))
    assert not retry
    assert "really failed" in why


def test_a_cancelled_linux_job_is_not_retried():
    retry, why = retry_stalled.decide(
        1, "cancelled", _with({MAC_311: "success", MAC_313: "success", LINUX_311: "cancelled"})
    )
    assert not retry
    assert "another OS" in why


def test_a_stalled_macos_job_beside_a_linux_failure_is_not_retried():
    assert not retry_stalled.decide(1, "failure", _with({LINUX_311: "failure"}))[0]


def test_a_second_attempt_is_never_retried():
    retry, why = retry_stalled.decide(2, "cancelled", RECORDED)
    assert not retry
    assert why.startswith("attempt 2")


def test_a_successful_run_is_not_retried():
    assert not retry_stalled.decide(1, "success", _with({MAC_311: "success", MAC_313: "success"}))[0]


def test_the_command_line_prints_one_line():
    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE), "1", "cancelled"], capture_output=True, text=True, check=True
    ).stdout
    assert out == f"retry: macOS job(s) stalled: {MAC_311} (cancelled), {MAC_313} (cancelled)\n"
    again = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE), "2", "cancelled"], capture_output=True, text=True, check=True
    ).stdout
    assert again.startswith("no retry: attempt 2")
