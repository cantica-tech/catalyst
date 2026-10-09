"""`catalyst move` (roadmap R2 W5, R3.1 stage E)."""
import json
import shutil
import subprocess
import sys

import pytest

import project_file as pf
from catalyst import move
from catalyst.corpus import load_corpus
from catalyst.validate import ERROR, validate
from catalyst.deployment import load
from catalyst_fixtures import git_init, make_project
from test_catalyst_criterion import allow_file_submodules, git, world  # noqa: F401  (fixtures)

pytestmark = pytest.mark.skipif(sys.version_info < (3, 11), reason="catalyst.toml needs Python 3.11+")


def _entries(root):
    return [json.loads(l) for l in (root / "development" / "journal.jsonl").read_text(encoding="utf-8").splitlines()]


def test_a_symlinked_working_copy_moves_home_with_its_history(tmp_path):
    project = make_project(tmp_path / "w", git=True)
    agent = tmp_path / "agent" / ".criterion"
    agent.parent.mkdir()
    shutil.move(str(project / ".criterion"), agent)
    (project / ".criterion").symlink_to(agent)
    (project / ".gitignore").write_text("node_modules\n/.criterion\n", encoding="utf-8")
    head = git(agent, "rev-parse", "HEAD")
    target, _ = move.to_home(project, runtime=False)
    assert target == pf.home_criterion("app") and not (project / ".criterion").exists() and not agent.exists()
    assert git(target, "rev-parse", "HEAD") == head                      # history travelled
    assert (project / "catalyst.toml").is_file() and not (project / "app.catalyst").exists()
    assert (project / ".gitignore").read_text(encoding="utf-8") == "node_modules\n"
    assert pf.read(project / "catalyst.toml")["project_name"] == "app"
    assert "app.catalyst" in git(project, "diff", "--cached", "--name-only")      # staged, not committed
    assert _entries(target)[-1]["command"] == "catalyst move"
    assert load(project).root == target


def test_an_in_project_directory_moves_home(tmp_path):
    project = make_project(tmp_path / "w", git=True)
    target, _ = move.to_home(project, runtime=False)
    assert target.is_dir() and not (project / ".criterion").exists()
    with pytest.raises(move.MoveError, match="already in the home store"):
        move.to_home(project, runtime=False)


def test_a_shared_submodule_becomes_a_standalone_repository_with_its_remote(world):
    ada = world["ada"]
    wc = ada / ".criterion"
    branch, head = git(wc, "symbolic-ref", "--short", "HEAD"), git(wc, "rev-parse", "HEAD")
    (wc / "local-note.md").write_text("unpushed\n", encoding="utf-8")
    target, steps = move.to_home(ada, runtime=False)
    assert git(target, "rev-parse", "HEAD") == head and git(target, "symbolic-ref", "--short", "HEAD") == branch
    assert git(target, "remote", "get-url", "origin") == str(world["remote"])
    assert (target / "local-note.md").is_file()                          # unpushed work travelled
    assert not (ada / ".criterion").exists() and not (ada / ".git" / "modules" / ".criterion").exists()
    staged = git(ada, "diff", "--cached", "--name-only").splitlines()
    assert ".criterion" in staged and "catalyst.toml" in staged
    assert pf.read(ada / "catalyst.toml")["repoed"] is True
    dep = load(ada)
    assert dep.root == target
    assert [f for f in validate(dep, load_corpus(dep)) if f.level == ERROR] == []


def test_rename_moves_the_criterion_and_the_name(tmp_path):
    project = make_project(tmp_path / "w", git=True)
    move.to_home(project, runtime=False)
    target, _ = move.rename(project, "renamed")
    assert target == pf.home_criterion("renamed") and target.is_dir()
    assert not pf.home_criterion("app").exists()
    assert pf.read(project / "catalyst.toml")["project_name"] == "renamed"
    assert load(project).root == target


def test_a_name_already_taken_is_refused(tmp_path):
    first = make_project(tmp_path / "one", git=True)
    move.to_home(first, runtime=False)
    second = make_project(tmp_path / "two", git=True)
    with pytest.raises(move.MoveError, match="another project is named 'app'"):
        move.to_home(second, runtime=False)
    assert (second / ".criterion").is_dir()                               # untouched
