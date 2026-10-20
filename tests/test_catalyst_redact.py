"""Redacting journaled content (roadmap R3.7, decision A5; REQ-000036): a
tombstone entry, the blob out of the pins here and on the shared copy, and
every reader of the journal treating it as redacted."""

from __future__ import annotations

import json
import stat
import subprocess

import pytest

import schema_check
from catalyst import criterion as cr, history, journal as j
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from test_catalyst_history import lived  # noqa: F401 (the fixture)


def _git(repo, *args) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def secret(lived, capsys):  # noqa: F811 (the fixture's name)
    """An item whose second version held a secret, then had it removed."""
    project, item, _ = lived
    dep = load(project)
    art = load_corpus(dep).artifacts[item][0]
    clean = art.file.read_text(encoding="utf-8")
    art.file.write_text(clean + "\napi_key = sk-live-123\n", encoding="utf-8")
    leaked = j.append(dep, j.AppendRequest("/status", "update", item, [], ["oops"], [str(art.file)], "ada"))
    art.file.write_text(clean, encoding="utf-8")
    j.append(load(project), j.AppendRequest("/status", "update", item, [], ["the key removed"], [str(art.file)], "ada"))
    capsys.readouterr()
    return project, item, leaked["files"][0]["after"]


def test_a_redaction_is_an_entry_and_takes_the_blob_out_of_the_pins(secret, capsys):
    project, _, sha = secret
    dep = load(project)
    assert sha in j.pinned(dep.root)
    assert main(["journal", "redact", sha, "--intent", "an API key was journaled", "--as", "ada", "--json"]) == 0
    printed = json.loads(capsys.readouterr().out)
    entry = j.read(load(project))[-1][1]
    assert entry and {k: printed[k] for k in entry} == entry  # the entry it wrote, and where the blob was
    assert printed["paths"] == [".criterion/items/ITEM-000002-second.md"]
    assert schema_check.problems(printed, schema_check.load("journal-entry")) == []
    assert entry and entry["action"] == "redact" and entry["redacted"] == [sha] and entry["files"] == []
    assert entry["intent"] == ["an API key was journaled"] and entry["actor"] == "ada"
    assert schema_check.problems(entry, schema_check.load("journal-entry")) == []
    root = load(project).root
    assert sha not in j.pinned(root) and j.pinned(root)  # the others stay pinned
    assert _git(root, "rev-list", "--count", j.PIN_REF) == "1"  # no older pin commit keeps it reachable
    assert j.pin_all(load(project)) and sha not in j.pinned(root)  # pinning everything again leaves it out
    assert j.redacted_in(root) == {sha} and j.redacted_in(project) == {sha}  # the product repository reads it too


def test_the_readers_treat_it_as_redacted(secret, tmp_path, capsys):
    project, item, sha = secret
    assert main(["journal", "redact", sha, "--intent", "a key", "--as", "ada"]) == 0
    out = capsys.readouterr().out
    assert "redacted 1 blob(s)" in out and "Rotate the secret" in out
    dep = load(project)
    h = history.history(dep, load_corpus(dep), item)
    leaked = next(e for e in h["entries"] if e["after"] == sha)
    assert leaked["redacted"] and leaked["content_after"] is None
    following = next(e for e in h["entries"] if e["before"] == sha)
    assert following["redacted"] and following["content_before"] is None
    assert "sk-live-123" not in json.dumps(h) and "content redacted" in history.render(h)
    # once git has dropped it, verify notes the redaction and reports no missing blob
    obj = dep.root / ".git" / "objects" / sha[:2] / sha[2:]
    if obj.exists():
        obj.chmod(stat.S_IWRITE)  # git writes objects read-only, which Windows refuses to delete
        obj.unlink()
    j._EXISTS.clear()
    issues = j.verify(load(project))
    assert not [i for i in issues if i.code in ("missing-blob", "unpinned") and sha[:10] in i.message]
    assert any(i.code == "redacted" and i.level == "note" for i in issues)
    restored, _ = j.restore(load(project), "2999-01-01T00:00:00Z", tmp_path / "out")
    assert restored and not any("sk-live-123" in (tmp_path / "out" / p).read_text(encoding="utf-8") for p in restored)


def test_the_shared_pins_drop_it_too(secret, tmp_path, capsys):
    project, _, sha = secret
    root = load(project).root
    remote = tmp_path / "pins.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    _git(root, "remote", "add", "origin", str(remote))
    _git(root, "push", "-q", "origin", f"{j.PIN_REF}:{j.PIN_REF}")  # shared before the redaction
    assert main(["journal", "redact", sha, "--intent", "a key", "--as", "ada"]) == 0
    _git(root, "update-ref", j.PIN_REF, _git(str(remote), "rev-parse", j.PIN_REF))  # a clone that kept the old pins
    cr.share_pins(root)
    shared = _git(str(remote), "ls-tree", j.PIN_REF)
    assert sha not in shared and shared  # gone from the shared copy, the others kept
    assert _git(str(remote), "rev-list", "--count", j.PIN_REF) == "1"  # and from its history


def test_what_cannot_be_redacted_is_refused(secret, capsys):
    project, _, sha = secret
    assert main(["journal", "redact", "0" * 40, "--intent", "x", "--as", "ada"]) == 1
    assert "not a blob the journal names" in capsys.readouterr().err
    assert main(["journal", "redact", sha, "--as", "ada"]) == 1
    assert "--intent is required" in capsys.readouterr().err
    assert sha in j.pinned(load(project).root)  # nothing done
