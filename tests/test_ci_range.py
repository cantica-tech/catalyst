"""scripts/ci_range.py: the range the Deployment Rules workflow's trace and journal checks read (REQ-000117)."""

import subprocess
from pathlib import Path

import pytest

import ci_range


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


def _repo(tmp_path: Path, with_main: bool) -> tuple[Path, list[str]]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "user.email", "t@localhost")
    shas = []
    for i in range(3):
        _git(repo, "commit", "-q", "--allow-empty", "-m", f"c{i}")
        shas.append(_git(repo, "rev-parse", "HEAD"))
    if with_main:
        _git(repo, "update-ref", "refs/remotes/origin/main", shas[0])
    return repo, shas


def test_pull_request_is_base_to_head(tmp_path):
    assert ci_range.ci_range("pull_request", "merge", base="b", head="h", repo=tmp_path) == "b..h"


def test_pull_request_without_base_is_refused(tmp_path):
    with pytest.raises(ValueError):
        ci_range.ci_range("pull_request", "merge", head="h", repo=tmp_path)


def test_push_is_before_to_sha(tmp_path):
    repo, shas = _repo(tmp_path, with_main=True)
    assert ci_range.ci_range("push", shas[2], before=shas[1], repo=repo) == f"{shas[1]}..{shas[2]}"


def test_force_push_checks_what_main_does_not_have(tmp_path):
    repo, shas = _repo(tmp_path, with_main=True)
    gone = "1" * 40
    assert ci_range.ci_range("push", shas[2], before=gone, repo=repo) == f"origin/main..{shas[2]}"


def test_new_branch_checks_what_main_does_not_have(tmp_path):
    repo, shas = _repo(tmp_path, with_main=True)
    assert ci_range.ci_range("push", shas[2], before=ci_range.ZERO, repo=repo) == f"origin/main..{shas[2]}"


def test_new_branch_without_main_checks_its_tip(tmp_path):
    repo, shas = _repo(tmp_path, with_main=False)
    assert ci_range.ci_range("push", shas[2], before=ci_range.ZERO, repo=repo) == f"{shas[2]}~1..{shas[2]}"


def test_unknown_before_without_main_is_kept(tmp_path):
    repo, shas = _repo(tmp_path, with_main=False)
    gone = "1" * 40
    assert ci_range.ci_range("push", shas[2], before=gone, repo=repo) == f"{gone}..{shas[2]}"


def test_option_like_before_never_reaches_git(tmp_path):
    repo, shas = _repo(tmp_path, with_main=True)
    assert ci_range.ci_range("push", shas[2], before="--output=x", repo=repo) == f"origin/main..{shas[2]}"


def test_main_prints_the_range(capsys):
    assert ci_range.main(["--event", "pull_request", "--base", "b", "--head", "h"]) == 0
    assert capsys.readouterr().out.strip() == "b..h"
    assert ci_range.main(["--event", "push"]) == 2
