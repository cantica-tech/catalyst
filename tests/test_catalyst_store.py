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
    with pytest.raises(store.ShareError, match="criterion create"):
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
