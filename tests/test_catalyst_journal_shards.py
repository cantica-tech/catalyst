"""The journal's shards, its lock and content-based recording (roadmap R3.3):
one file per actor, machine and month; appends serialised; order and
"recorded" decided by content, never by clocks."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time

import pytest

from catalyst import journal as j, unrecorded as u
from catalyst.check import run as check_run
from catalyst.deployment import load
from catalyst_fixtures import make_project, write
from test_catalyst_journal import req


def git(repo, *args, env=None) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, encoding="utf-8", env=env
    ).stdout.strip()


@pytest.fixture
def project(tmp_path, monkeypatch):
    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)
    return project


def test_an_append_goes_to_its_actors_shard_and_never_to_the_legacy_file(project):
    dep = load(project)
    write(project / "src" / "a.py", "a\n")
    entry = j.append(dep, req(["src/a.py"], action="create", actor="Ada Lovelace"))
    machine = j.machine()
    shard = dep.root / "development" / "journal" / f"ada-lovelace@{machine}" / f"{entry['timestamp'][:7]}.jsonl"
    assert json.loads(shard.read_text(encoding="utf-8")) == entry
    assert (dep.root / j.LEGACY).read_text(encoding="utf-8") == ""  # the fixture's pre-0.50 file, untouched
    assert j.machine() == machine and len(machine) == 6  # created once
    assert j.sources(dep) == [dep.root / j.LEGACY, shard]
    assert [e for _, e, _ in j.read(dep)] == [entry]
    assert j.read(dep)[0][0] == f"journal/ada-lovelace@{machine}/{entry['timestamp'][:7]}.jsonl:1"


def test_shards_merge_in_causal_order_whatever_the_clocks_say(project):
    """Bob's clock is an hour behind: his edit, made after Ada's, carries an
    earlier timestamp. The chain, not the clock, decides the order."""
    dep = load(project)
    write(project / "src" / "f.py", "ada\n")
    j.append(dep, req(["src/f.py"], action="create", actor="ada", timestamp="2026-10-09T12:00:00Z"))
    write(project / "src" / "f.py", "bob\n")
    j.append(dep, req(["src/f.py"], actor="bob", timestamp="2026-10-09T11:00:00Z"))
    assert [e["actor"] for _, e, _ in j.read(dep)] == ["ada", "bob"]
    assert [i for i in j.verify(dep) if i.code in ("chain", "unjournaled")] == []
    assert j.last_after(dep)["src/f.py"] == j.git(project, "hash-object", "src/f.py")


def test_concurrent_appends_are_serialised(project):
    """Eight processes journal at once: every entry lands whole, the chain of
    the file they all name stays intact."""
    write(project / "shared.txt", "same\n")
    for i in range(8):
        write(project / f"f{i}.txt", f"{i}\n")
    code = (
        "import sys\n"
        "from catalyst import journal as j\n"
        "from catalyst.deployment import load\n"
        "i = sys.argv[1]\n"
        "j.append(load('.'), j.AppendRequest(command='/x', action='create', artifact='x', targets=[],"
        " intent=['parallel'], files=[f'f{i}.txt', 'shared.txt'], actor=f'agent{i}', allow_unchanged=True))\n"
    )
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
    procs = [subprocess.Popen([sys.executable, "-c", code, str(i)], cwd=project, env=env) for i in range(8)]
    assert [p.wait(timeout=120) for p in procs] == [0] * 8
    dep = load(project)
    rows = j.read(dep)
    assert len(rows) == 8 and all(e is not None for _, e, _ in rows)
    shared = [f for _, e, _ in rows for f in e["files"] if f["path"] == "shared.txt"]
    assert shared[0]["before"] is None and all(f["before"] == shared[0]["after"] for f in shared[1:])
    assert [i for i in j.verify(dep) if i.level == "error"] == []


def test_an_append_waits_for_the_journal_lock(project):
    dep = load(project)
    write(project / "src" / "a.py", "a\n")
    released = threading.Event()

    def hold():
        with j.journal_lock(dep):
            time.sleep(0.3)
            released.set()

    holder = threading.Thread(target=hold)
    holder.start()
    time.sleep(0.05)
    j.append(dep, req(["src/a.py"], action="create"))
    assert released.is_set()
    holder.join()


def test_a_commit_made_before_it_is_journaled_is_recorded(tmp_path, monkeypatch):
    """Committing first and journaling second, or a committer clock far
    ahead, changes nothing: the commit's result is in the journal."""
    from test_catalyst_unrecorded import fresh_project

    project = fresh_project(tmp_path, monkeypatch)
    write(project / "src" / "late.py", "x = 1\n")
    git(project, "add", "src/late.py")
    future = dict(os.environ, GIT_COMMITTER_DATE="@4000000000 +0000", GIT_AUTHOR_DATE="@4000000000 +0000")
    git(project, "commit", "-qm", "chore: committed first", env=future)
    assert [c.subject for c in u.since_baseline(load(project))] == ["chore: committed first"]
    j.append(load(project), req(["src/late.py"], action="create", allow_unchanged=True))  # already committed
    assert u.since_baseline(load(project)) == []
    assert not [e for e in check_run(load(project)).errors if "unrecorded" in e]


def test_ids_and_the_structure_check_read_every_shard(project):
    from catalyst.corpus import load_corpus
    from catalyst.ids import highest_number
    from check_deployment import check_journal_exists

    dep = load(project)
    write(project / "src" / "a.py", "a\n")
    j.append(dep, req(["src/a.py"], action="create", artifact="ITEM-000042-AbCd1234"))
    assert highest_number(dep, load_corpus(dep), "ITEM") == 42
    assert check_journal_exists(dep.root) == []
    shard = j.sources(dep)[-1]
    shard.write_text(shard.read_text(encoding="utf-8") + "{not json\n", encoding="utf-8")
    name = shard.relative_to(dep.root / "development").as_posix()
    assert any(f"{name}:2 is not valid JSON" in e for e in check_journal_exists(dep.root))
