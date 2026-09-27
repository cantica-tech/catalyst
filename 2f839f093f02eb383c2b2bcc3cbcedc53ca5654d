from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from catalyst import journal as j
from catalyst.__main__ import main
from catalyst.deployment import load
from catalyst_fixtures import USERID, make_project, write


def req(files, **kw):
    base = dict(command="/status", action="update", artifact=f"ITEM-000001-{USERID}",
                targets=[f"br-AUTH-000001-{USERID}"], intent=["close the item"],
                files=files, actor="ada")
    base.update(kw)
    return j.AppendRequest(**base)


def entries(dep):
    return [e for _, e, _ in j.read(dep)]


@pytest.fixture
def project(tmp_path, monkeypatch):
    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)
    return project


def item(project: Path) -> Path:
    return project / ".criterion" / "items" / "ITEM-000001-first-item.md"


def test_append_records_real_hashes_and_pins(project):
    dep = load(project)
    before = j.head_blob(dep.root, "items/ITEM-000001-first-item.md")
    item(project).write_text(item(project).read_text().replace("| Open |", "| Done |"))
    entry = j.append(dep, req([".criterion/items/ITEM-000001-first-item.md"]))
    f = entry["files"][0]
    assert f["path"] == ".criterion/items/ITEM-000001-first-item.md"
    assert f["before"] == before
    assert f["after"] == j.git(dep.root, "hash-object", "items/ITEM-000001-first-item.md")
    assert entry["writer"].startswith("catalyst/")
    assert entry["timestamp"].endswith("Z") and len(entry["timestamp"]) == 20
    assert f["after"] in j.pinned(dep.root)


def test_before_chains_from_the_previous_entry(project):
    dep = load(project)
    path = ".criterion/items/ITEM-000001-first-item.md"
    item(project).write_text(item(project).read_text() + "\nmore\n")
    first = j.append(dep, req([path]))
    item(project).write_text(item(project).read_text() + "\nand more\n")
    second = j.append(dep, req([path]))
    assert second["files"][0]["before"] == first["files"][0]["after"]
    assert [i for i in j.verify(dep) if not i.legacy] == []


def test_project_files_are_hashed_into_the_project_repo(project):
    dep = load(project)
    write(project / "src" / "app.py", "print('hi')\n")
    entry = j.append(dep, req(["src/app.py"], action="create"))
    f = entry["files"][0]
    assert f == {"path": "src/app.py", "before": None,
                 "after": j.git(project, "hash-object", "src/app.py")}
    assert j.blob_exists(project, f["after"])


def test_unchanged_file_is_refused(project):
    dep = load(project)
    with pytest.raises(j.JournalError, match="unchanged"):
        j.append(dep, req([".criterion/items/ITEM-000001-first-item.md"]))
    assert j.append(dep, req([".criterion/items/ITEM-000001-first-item.md"], allow_unchanged=True))


def test_action_and_intent_are_required(project):
    dep = load(project)
    with pytest.raises(j.JournalError, match="action"):
        j.append(dep, req(["src/x"], action="migrate"))
    with pytest.raises(j.JournalError, match="intent"):
        j.append(dep, req(["src/x"], intent=[" "]))


def test_deleted_file_has_null_after(project):
    dep = load(project)
    item(project).unlink()
    entry = j.append(dep, req([".criterion/items/ITEM-000001-first-item.md"], action="retire"))
    assert entry["files"][0]["after"] is None


def test_pins_survive_gc(project):
    dep = load(project)
    write(project / "scratch.txt", "never committed\n")
    sha = j.append(dep, req(["scratch.txt"], action="create"))["files"][0]["after"]
    subprocess.run(["git", "-C", str(project), "gc", "-q", "--prune=now"], check=True)
    assert j.blob_exists(project, sha)


def test_verify_flags_unjournaled_edits_and_chain_breaks(project):
    dep = load(project)
    path = ".criterion/items/ITEM-000001-first-item.md"
    item(project).write_text("v2\n")
    j.append(dep, req([path]))
    item(project).write_text("v3, not journaled\n")
    assert [(i.level, i.code) for i in j.verify(dep)] == [("error", "unjournaled")]
    # a hand-written CLI-looking entry that breaks the chain
    bad = {"timestamp": j.now(), "actor": "ada", "command": "x", "action": "update",
           "artifact": "x", "targets": [], "intent": ["x"], "writer": "catalyst/0",
           "files": [{"path": path, "before": "0" * 40, "after": None}]}
    with j.journal_path(dep).open("a") as fh:
        fh.write(json.dumps(bad) + "\n")
    codes = {i.code for i in j.verify(dep) if i.level == "error"}
    assert {"chain", "missing-blob"} <= codes


def test_legacy_entries_only_warn(project):
    dep = load(project)
    legacy = {"timestamp": "2026-01-01T00:00:00Z", "actor": "Ada", "command": "x", "action": "update",
              "artifact": "x", "targets": [], "intent": ["x"],
              "files": [{"path": "items/ITEM-000001-first-item.md", "before": None, "after": "1" * 40}]}
    j.journal_path(dep).write_text(json.dumps(legacy) + "\n")
    issues = j.verify(dep)
    assert issues and all(i.level == "warning" and i.legacy for i in issues)


def test_normalise_legacy_paths(project):
    dep = load(project)
    assert j.normalise(dep, "criterion:rules/rules.md") == ".criterion/rules/rules.md"
    assert j.normalise(dep, "app:src/x.py") == "src/x.py"
    assert j.normalise(dep, "other-repo:LICENSE") == "other-repo:LICENSE"
    assert j.normalise(dep, "items/items.md") == ".criterion/items/items.md"
    assert j.normalise(dep, "app.catalyst") == "app.catalyst"


def test_canonical_path_through_symlink(tmp_path, monkeypatch):
    project = make_project(tmp_path)
    real = tmp_path / "agent-space" / ".criterion"
    real.parent.mkdir()
    shutil.move(str(project / ".criterion"), str(real))
    (project / ".criterion").symlink_to(real)
    dep = load(project)
    monkeypatch.chdir(project)
    assert j.canonical(dep, ".criterion/items/items.md") == ".criterion/items/items.md"
    assert j.canonical(dep, str(real / "items" / "items.md")) == ".criterion/items/items.md"
    with pytest.raises(j.JournalError, match="outside"):
        j.canonical(dep, str(tmp_path / "elsewhere.txt"))


def test_restore_materialises_state_at_a_time(project, tmp_path):
    dep = load(project)
    path = ".criterion/items/ITEM-000001-first-item.md"
    item(project).write_text("version one\n")
    t1 = j.append(dep, req([path], timestamp="2026-05-01T00:00:00Z"))["timestamp"]
    item(project).write_text("version two\n")
    j.append(dep, req([path], timestamp="2026-06-01T00:00:00Z"))
    restored, missing = j.restore(dep, t1, tmp_path / "side")
    assert missing == [] and restored == [path]
    assert (tmp_path / "side" / path).read_text() == "version one\n"
    with pytest.raises(j.JournalError, match="not an empty directory"):
        j.restore(dep, t1, tmp_path / "side")


def test_cli_append_verify_pin(project, capsys):
    item(project).write_text("changed\n")
    assert main(["journal", "append", "--command", "/status", "--action", "status-change",
                 "--artifact", f"ITEM-000001-{USERID}", "--intent", "mark done",
                 "--file", ".criterion/items/ITEM-000001-first-item.md", "--json"]) == 0
    entry = json.loads(capsys.readouterr().out)
    assert entry["actor"] == "ada"
    assert main(["journal", "verify"]) == 0
    assert main(["journal", "pin"]) == 0
    assert main(["journal", "append", "--command", "x", "--action", "bogus", "--artifact", "x",
                 "--intent", "x", "--file", "app.catalyst"]) == 1


def test_cli_entries_keep_their_canonical_paths(project):
    """A project file whose name also exists in the working copy (README.md
    in both) must not be re-read as the working-copy file."""
    dep = load(project)
    write(project / ".criterion" / "README.md", "working copy readme\n")
    write(project / "README.md", "project readme\n")
    entry = j.append(dep, req(["README.md"], action="create"))
    assert entry["files"][0]["path"] == "README.md"
    assert [i for i in j.verify(dep) if not i.legacy] == []
    assert j.last_after(dep)["README.md"] == entry["files"][0]["after"]


def test_duplicate_file_is_recorded_once(project):
    dep = load(project)
    item(project).write_text("changed\n")
    entry = j.append(dep, req([".criterion/items/ITEM-000001-first-item.md",
                               str(item(project))]))
    assert len(entry["files"]) == 1
    assert [i for i in j.verify(dep) if not i.legacy] == []


def test_timestamps_compare_as_times_not_strings(project, tmp_path):
    dep = load(project)
    path = ".criterion/items/ITEM-000001-first-item.md"
    item(project).write_text("at ten\n")
    j.append(dep, req([path], timestamp="2026-09-27T10:00:00Z"))
    item(project).write_text("half a second later\n")
    j.append(dep, req([path], timestamp="2026-09-27T10:00:00.500Z"))
    assert [i.code for i in j.verify(dep) if not i.legacy] == []
    j.restore(dep, "2026-09-27T12:00:00+02:00", tmp_path / "side")    # == 10:00:00Z
    assert (tmp_path / "side" / path).read_text() == "at ten\n"
    with pytest.raises(j.JournalError, match="ISO 8601"):
        j.restore(dep, "yesterday", tmp_path / "other")


def test_restore_never_writes_outside_the_side_directory(project, tmp_path):
    dep = load(project)
    write(project / "src" / "x.py", "x\n")
    entry = j.append(dep, req(["src/x.py"], action="create"))
    evil = dict(entry, writer="catalyst/0", timestamp=j.now())
    evil["files"] = [{"path": "../escaped.txt", "before": None, "after": entry["files"][0]["after"]}]
    with j.journal_path(dep).open("a") as fh:
        fh.write(json.dumps(evil) + "\n")
    restored, missing = j.restore(dep, j.now(), tmp_path / "side")
    assert "../escaped.txt" in missing and not (tmp_path / "escaped.txt").exists()


def test_before_hash_in_a_subdirectory_project(tmp_path, monkeypatch):
    """The project root need not be the git top level (monorepo)."""
    mono = tmp_path / "mono"
    mono.mkdir()
    project = make_project(mono)            # mono/app
    from catalyst_fixtures import git_init
    git_init(mono)                          # one repository above the project
    monkeypatch.chdir(project)
    dep = load(project)
    committed = j.git(mono, "rev-parse", "HEAD:app/app.catalyst")
    (project / "app.catalyst").write_text((project / "app.catalyst").read_text() + " ")
    assert j.append(dep, req(["app.catalyst"]))["files"][0]["before"] == committed
