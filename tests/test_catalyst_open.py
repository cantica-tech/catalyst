"""`catalyst open` (roadmap R3.5): a fresh clone on a second machine becomes
ready with one command; the session-start hook reports, changing nothing."""

from __future__ import annotations

import json
import subprocess

import project_file
import test_catalyst_criterion as shared
from catalyst import move
from catalyst.__main__ import main
from catalyst.open import open_project
from catalyst_fixtures import make_project

allow_file_submodules = shared.allow_file_submodules


def _published(tmp_path, monkeypatch):
    """Ada's home-store criterion shared through git; the product pushed."""
    remote, product = tmp_path / "criterion.git", tmp_path / "product.git"
    for bare in (remote, product):
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "machine-a"))
    ada = make_project(tmp_path / "ada", git=True)
    move.to_home(ada, runtime=False)
    monkeypatch.chdir(ada)
    assert main(["share", "create", str(remote), "--yes"]) == 0
    shared.git(ada, "add", "-A")
    shared.git(ada, "commit", "-qm", "share the criterion")
    shared.git(ada, "remote", "add", "origin", str(product))
    shared.git(ada, "push", "-q", "origin", "HEAD:refs/heads/main")
    assert main(["journal", "pin", "--share"]) == 0  # product blobs journaled but never committed
    return ada, product


def test_a_fresh_clone_on_another_machine_is_ready_after_catalyst_open(tmp_path, monkeypatch, capsys):
    _, product = _published(tmp_path, monkeypatch)
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "machine-b"))
    bob = tmp_path / "bob" / "app"
    subprocess.run(["git", "clone", "-q", "-b", "main", str(product), str(bob)], check=True)
    monkeypatch.chdir(bob)

    assert main(["hook", "start"]) == 0  # the session hook changes nothing, says what to run
    out = capsys.readouterr().out
    assert "not on this machine" in out and "`catalyst open` (clones the shared criterion" in out
    assert not project_file.home_criterion("app").exists()

    assert main(["open"]) == 0
    out = capsys.readouterr().out
    assert "joined: cloned" in out and out.rstrip().endswith("ready")
    assert (project_file.home() / "bin" / "catalyst").is_file()  # the launcher
    main(["check"])  # the fixture is a minimal deployment: only the journal matters here
    assert "ERROR   journal" not in capsys.readouterr().out
    assert shared.git(bob, "status", "--porcelain") == ""  # nothing written in the project

    assert main(["hook", "start"]) == 0
    out = capsys.readouterr().out
    assert "(home)" in out and out.rstrip().endswith("ready")


def test_the_agent_is_this_users_choice_never_a_project_edit(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path / "w", git=True)
    move.to_home(project, runtime=False)
    monkeypatch.chdir(project)
    before = (project / "catalyst.toml").read_text(encoding="utf-8")
    assert main(["open", "--agent", "codex", "--json"]) in (0, 1)
    report = json.loads(capsys.readouterr().out)
    assert report["agent"] == "codex" and any("agent codex recorded" in d for d in report["done"])
    assert project_file.agent_of(project_file.read_dir(project)) == "codex"
    assert (project / "catalyst.toml").read_text(encoding="utf-8") == before


def test_open_names_what_is_left_to_do(tmp_path, monkeypatch):
    project = make_project(tmp_path / "w", git=True)
    o = open_project(project, act=False)
    assert o.kind == "legacy" and any("catalyst move --to-home" in t for t in o.todo)
    move.to_home(project, runtime=False)
    toml = project / "catalyst.toml"
    project_file.write(toml, dict(project_file.read(toml), kernel_version="9.9.9"))
    o = open_project(project, act=False)
    assert o.kind == "home" and not o.ready
    assert any("catalyst.toml pins 9.9.9" in t for t in o.todo)
