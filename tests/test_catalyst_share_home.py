"""Sharing a home-store criterion (roadmap R3.1 stage F): the criterion is its
own git repository with a remote; a collaborator joins by cloning it into
their own $CATALYST_HOME. No submodule."""
import subprocess
import sys

import pytest

import project_file as pf
from catalyst import criterion as cr
from catalyst import move
from catalyst.deployment import load
from catalyst_fixtures import make_project
from test_catalyst_criterion import allow_file_submodules, git  # noqa: F401  (fixture)

pytestmark = pytest.mark.skipif(sys.version_info < (3, 11), reason="catalyst.toml needs Python 3.11+")


@pytest.fixture
def shared(tmp_path, monkeypatch):
    remote, product = tmp_path / "criterion.git", tmp_path / "product.git"
    for bare in (remote, product):
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    ada_home = tmp_path / "ada-home"
    monkeypatch.setenv("CATALYST_HOME", str(ada_home))
    ada = make_project(tmp_path / "ada", git=True)
    move.to_home(ada, runtime=False)
    git(ada, "commit", "-q", "-m", "catalyst.toml")
    steps = cr.create(load(ada), str(remote), "criterion", cr.CI_TEMPLATE)
    git(ada, "commit", "-q", "-m", "share the criterion")
    git(ada, "remote", "add", "origin", str(product))
    git(ada, "push", "-q", "origin", "HEAD:refs/heads/main")
    bob = tmp_path / "bob" / "app"
    subprocess.run(["git", "clone", "-q", "-b", "main", str(product), str(bob)], check=True)
    return {"ada": ada, "bob": bob, "remote": remote, "ada_home": ada_home,
            "bob_home": tmp_path / "bob-home", "steps": steps}


def test_create_publishes_the_home_criterion_without_a_submodule(shared):
    ada = shared["ada"]
    criterion = pf.home_criterion("app")
    assert git(criterion, "remote", "get-url", "origin") == str(shared["remote"])
    assert git(shared["remote"], "rev-parse", "criterion") == git(criterion, "rev-parse", "HEAD")
    data = pf.read(ada / "catalyst.toml")
    assert data["repoed"] is True and data["catalyst_repo_url"] == str(shared["remote"])
    assert not (ada / ".gitmodules").exists() and not (ada / ".criterion").exists()
    assert cr.status(load(ada)).mode == "home"


def test_a_collaborator_joins_by_cloning_into_their_own_home(shared, monkeypatch):
    monkeypatch.setenv("CATALYST_HOME", str(shared["bob_home"]))
    head = cr.join_home(shared["bob"], runtime=False)
    target = shared["bob_home"] / "projects" / "app" / "criterion"
    assert target.is_dir() and git(target, "symbolic-ref", "--short", "HEAD") == "criterion"
    assert head == git(target, "rev-parse", "--short", "HEAD")
    dep = load(shared["bob"])
    assert dep.root == target
    assert cr.join_home(shared["bob"], runtime=False) == head            # joining again is a no-op


def test_a_change_landed_on_the_shared_branch_reaches_the_collaborator(shared, monkeypatch):
    ada_criterion = shared["ada_home"] / "projects" / "app" / "criterion"
    monkeypatch.setenv("CATALYST_HOME", str(shared["bob_home"]))
    cr.join_home(shared["bob"], runtime=False)
    (ada_criterion / "NOTE.md").write_text("from Ada\n", encoding="utf-8")
    git(ada_criterion, "add", "NOTE.md")
    git(ada_criterion, "-c", "user.name=Ada", "-c", "user.email=a@x", "commit", "-q", "-m", "note")
    git(ada_criterion, "push", "-q", "origin", "HEAD:refs/heads/criterion")    # a merged pull request
    cr.sync(load(shared["bob"]))
    assert (shared["bob_home"] / "projects" / "app" / "criterion" / "NOTE.md").is_file()


def test_join_refuses_a_same_named_criterion_with_another_remote(shared, monkeypatch, tmp_path):
    monkeypatch.setenv("CATALYST_HOME", str(shared["bob_home"]))
    other = shared["bob_home"] / "projects" / "app" / "criterion"
    other.mkdir(parents=True)
    git(other, "init", "-q")
    git(other, "remote", "add", "origin", str(tmp_path / "elsewhere.git"))
    (other / "x").write_text("x", encoding="utf-8")
    with pytest.raises(cr.CriterionError, match="another remote"):
        cr.join_home(shared["bob"], runtime=False)


@pytest.mark.skipif(__import__("shutil").which("uv") is None, reason="a runtime build is slow without uv")
def test_the_commit_msg_hook_checks_a_home_store_project_with_its_own_runtime(tmp_path, monkeypatch):
    import os
    from catalyst import runtime as rt
    from catalyst.trace import install_hook
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    project = make_project(tmp_path / "w", git=True)
    move.to_home(project)
    git(project, "commit", "-q", "-m", "chore: catalyst.toml")
    rt.install_launcher()
    install_hook(project)
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    (project / "src.py").write_text("x = 1\n", encoding="utf-8")
    git(project, "add", "src.py")
    refused = subprocess.run(["git", "-C", str(project), "commit", "-q", "-m", "no id here"],
                             capture_output=True, text=True, encoding="utf-8", env=env)
    assert refused.returncode != 0
    ok = subprocess.run(["git", "-C", str(project), "commit", "-q", "-m", "chore: tidy"],
                        capture_output=True, text=True, encoding="utf-8", env=env)
    assert ok.returncode == 0, ok.stderr
