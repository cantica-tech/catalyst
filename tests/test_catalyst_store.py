"""The criterion's store and its sharing drivers (roadmap R3.2)."""

from __future__ import annotations

import json

import pytest

import test_catalyst_criterion as shared
from catalyst import criterion as cr, store
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst_fixtures import make_project

world = shared.world  # the fixtures: Ada's criterion published, Bob's clone joined
allow_file_submodules = shared.allow_file_submodules


def test_the_home_store_reads_lists_appends_and_locks(tmp_path):
    root = tmp_path / "criterion"
    s = store.HomeStore(root)
    assert s.read("a/b.jsonl") is None and s.list("a") == []
    s.append("a/x/b.jsonl", '{"n": 1}')
    s.append("a/x/b.jsonl", '{"n": 2}\n')
    s.append("a/c.txt", "c")
    assert s.read("a/x/b.jsonl") == '{"n": 1}\n{"n": 2}\n'
    assert s.list("a") == ["a/c.txt", "a/x/b.jsonl"] and s.list("a", ".jsonl") == ["a/x/b.jsonl"]
    assert s.list("a/c.txt") == ["a/c.txt"]
    with s.lock("journal", wait=0.1), pytest.raises(store.lock.LockError), s.lock("journal", wait=0.1):
        pass


def test_a_criterion_without_a_remote_is_local_and_says_how_to_share(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)
    dep = load(project)
    share = store.share_for(dep)
    assert share.driver == "local" and share.head() is None and share.status().location is None
    with pytest.raises(store.ShareError, match="share create"):
        share.pull()
    assert main(["share", "info"]) == 0 and "(not shared)" in capsys.readouterr().out
    assert main(["share", "pull"]) == 1 and "not shared" in capsys.readouterr().err


def test_the_project_file_names_the_driver(tmp_path, monkeypatch):
    project = make_project(tmp_path, git=True)
    pointer = project / "app.catalyst"
    data = json.loads(pointer.read_text(encoding="utf-8"))
    pointer.write_text(json.dumps(dict(data, share="git")), encoding="utf-8")
    assert store.share_for(load(project)).driver == "git"
    pointer.write_text(json.dumps(dict(data, share="couchdb")), encoding="utf-8")
    with pytest.raises(store.ShareError, match="unknown share driver 'couchdb'"):
        store.share_for(load(project))


def test_the_git_driver_publishes_and_pulls_through_the_criterion_repository(world, monkeypatch, capsys):
    monkeypatch.setattr(cr, "_check", shared.NO_CHECK)
    ada, bob = world["ada"], world["bob"]
    share = store.share_for(load(ada))
    assert share.driver == "git" and share.info()["location"] == str(world["remote"])
    assert share.info()["branch"] == "criterion" and "pull-request" in share.info()["capabilities"]
    shared.add_item(ada, "ada", "Ada thing")
    assert share.status().dirty
    signer = load_corpus(load(ada)).user("ada")
    assert signer is not None
    res = share.push(signer, "Ada adds", open_pr=False)
    assert res["commits"] == 1 and res["branch"].startswith("ada/")
    merged = shared.merge_topic(world, res["branch"])
    monkeypatch.chdir(bob)
    assert main(["share", "pull"]) == 0 and "(git)" in capsys.readouterr().out
    bob_share = store.share_for(load(bob))
    assert bob_share.head() == merged == shared.git(bob / ".criterion", "rev-parse", "HEAD")
    assert main(["share", "status", "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["driver"] == "git" and status["ahead"] == 0 and status["behind"] == 0


# --- R3.6: a team on git ----------------------------------------------------------
def test_two_machines_share_one_criterion_through_git(tmp_path, monkeypatch, capsys):
    """Ada publishes her home-store criterion, Bob joins on another machine,
    each publishes only with assent, and pulls bring the other's work —
    journal shards and all."""
    import subprocess

    from catalyst import journal as j, move

    monkeypatch.setattr(cr, "_check", shared.NO_CHECK)
    remote, product = tmp_path / "criterion.git", tmp_path / "product.git"
    for bare in (remote, product):
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "machine-a"))
    ada = make_project(tmp_path / "ada", git=True)
    move.to_home(ada, runtime=False)
    monkeypatch.chdir(ada)
    assert main(["share", "create", str(remote)]) == 3  # no assent, nothing published
    assert "publish this criterion" in capsys.readouterr().out
    assert shared.git(remote, "branch", "--list") == ""
    assert main(["share", "create", str(remote), "--yes"]) == 0
    assert store.share_for(load(ada)).driver == "git"
    shared.git(ada, "add", "-A")
    shared.git(ada, "commit", "-qm", "share the criterion")
    shared.git(ada, "remote", "add", "origin", str(product))
    shared.git(ada, "push", "-q", "origin", "HEAD:refs/heads/main")

    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "machine-b"))
    bob = tmp_path / "bob" / "app"
    subprocess.run(["git", "clone", "-q", "-b", "main", str(product), str(bob)], check=True)
    store.join(bob, runtime=False)
    monkeypatch.chdir(bob)
    shared.add_item(bob, "ada", "From machine B")
    assert main(["share", "push", "-m", "B's item", "--no-pr"]) == 3
    assert "one pull request for the whole batch" in capsys.readouterr().out
    assert main(["share", "push", "-m", "B's item", "--no-pr", "--yes"]) == 0
    topic = next(line for line in capsys.readouterr().out.splitlines() if "published" in line).split(" on ")[1]
    topic = topic.split(" (")[0]
    shared.add_item(bob, "ada", "Second from machine B")
    assert main(["share", "push", "-m", "more", "--no-pr"]) == 3
    assert f"added to the open topic branch {topic}" in capsys.readouterr().out
    assert main(["share", "push", "-m", "more", "--no-pr", "--yes"]) == 0
    shared.merge_topic({"tmp": tmp_path, "remote": remote}, topic)

    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "machine-a"))
    monkeypatch.chdir(ada)
    assert main(["share", "pull"]) == 0
    dep = load(ada)
    shards = {rel.split("/")[2] for rel in j.sources(dep) if rel.startswith(j.SHARDS + "/")}
    assert len({s.split("@")[1] for s in shards}) == 2  # one machine id per home
    items = {p.name.split("-", 2)[-1] for p in (dep.root / "items").glob("ITEM-*.md")}
    assert {"from-machine-b.md", "second-from-machine-b.md"} <= items
    assert [i for i in j.verify(dep) if i.level == "error"] == []


def test_check_reports_a_merge_that_lost_recorded_content(world):
    from catalyst.check import merge_integrity, run as check_run

    shared.add_item(world["ada"], "ada", "Ada thing")
    a = shared.push(world, "ada", "Ada adds an item")
    wc = world["ada"] / ".criterion"
    shared.git(wc, "checkout", "-q", "criterion")
    shared.git(wc, "merge", "-q", "--no-ff", "--no-commit", a.branch)
    for shard in (wc / "development" / "journal").rglob("*.jsonl"):
        shard.write_text("", encoding="utf-8")  # a bad merge resolution
    shared.git(wc, "add", "-A")
    shared.git(wc, "commit", "-q", "-m", "bad merge")
    lost = merge_integrity(load(world["ada"]))
    assert lost and all("journal line" in p for p in lost)
    assert any(e.startswith("integrity: journal line") for e in check_run(load(world["ada"])).errors)
    assert merge_integrity(load(world["ada"])) == lost  # kept per HEAD
