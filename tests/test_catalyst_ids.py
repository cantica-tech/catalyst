from __future__ import annotations

import itertools

import pytest

from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst.ids import (
    IdError, generate_userid, highest_number, next_entity_id, next_rule_id,
    resolve_signer,
)
from catalyst_fixtures import USER, USERID, make_project


def setup(tmp_path):
    project = make_project(tmp_path)
    dep = load(project)
    return project, dep, load_corpus(dep)


def test_next_entity_id_is_one_above_highest(tmp_path):
    project, dep, corpus = setup(tmp_path)
    signer = corpus.user(USER)
    assert next_entity_id(dep, corpus, "ITEM", signer) == f"ITEM-000002-{USERID}"
    assert next_entity_id(dep, corpus, "RECON", signer) == f"RECON-000001-{USERID}"


def test_numbers_are_never_reused_after_a_file_disappears(tmp_path):
    """An ID still registered in the index (or cited anywhere in the type's
    folder) keeps its number even when its file is gone."""
    project, dep, corpus = setup(tmp_path)
    index = project / ".criterion" / "items" / "items.md"
    index.write_text(index.read_text(encoding="utf-8") + f"| [ITEM-000007-{USERID}](ITEM-000007-x.md) | X | Done |\n", encoding="utf-8")
    assert highest_number(dep, load_corpus(dep), "ITEM") == 7


def test_unknown_prefix(tmp_path):
    _, dep, corpus = setup(tmp_path)
    with pytest.raises(IdError, match="unknown entity type"):
        next_entity_id(dep, corpus, "NOPE", corpus.user(USER))


def test_next_rule_id_is_per_domain(tmp_path):
    _, dep, corpus = setup(tmp_path)
    assert next_rule_id(dep, corpus, "br", "AUTH", corpus.user(USER)) == f"br-AUTH-000002-{USERID}"


def test_next_rule_id_needs_a_registered_domain(tmp_path):
    _, dep, corpus = setup(tmp_path)
    with pytest.raises(IdError, match="not registered"):
        next_rule_id(dep, corpus, "br", "NOPE", corpus.user(USER))


def test_signer_resolution(tmp_path):
    project, dep, corpus = setup(tmp_path)
    assert resolve_signer(dep, corpus, "ada")["userid"] == USERID
    assert resolve_signer(dep, corpus)["userid"] == USERID      # the only active user
    with pytest.raises(IdError, match="not a registered user"):
        resolve_signer(dep, corpus, "mallory")


def test_signer_is_never_guessed_among_several_users(tmp_path):
    _, dep, corpus = setup(tmp_path)
    corpus.users.append({"name": "Bob", "active": True, "userid": "Bb4xR9pQ"})
    with pytest.raises(IdError, match="pass --as"):
        resolve_signer(dep, corpus)


def test_signer_without_userid_cannot_allocate(tmp_path):
    _, dep, corpus = setup(tmp_path)
    with pytest.raises(IdError, match="no userid"):
        next_entity_id(dep, corpus, "ITEM", {"name": "Bob"})


def test_userid_redraws_without_uppercase_and_on_collision():
    draws = itertools.chain("database", "Ab3xR9pQ", "Zz9yY8xX")
    assert generate_userid({"Ab3xR9pQ"}, rng=lambda alphabet: next(draws)) == "Zz9yY8xX"


def test_userid_shape():
    uid = generate_userid(set())
    assert len(uid) == 8 and uid.isalnum() and any(c.isupper() for c in uid)


def test_cli(tmp_path, capsys):
    project = make_project(tmp_path)
    assert main(["--project", str(project), "id", "next", "SUB"]) == 0
    assert capsys.readouterr().out.strip() == f"SUB-000002-{USERID}"
    assert main(["--project", str(project), "id", "next-rule", "br", "AUTH", "--as", USER]) == 0
    assert capsys.readouterr().out.strip() == f"br-AUTH-000002-{USERID}"
    assert main(["--project", str(project), "id", "next", "NOPE"]) == 1
    assert main(["--project", str(project), "userid", "gen"]) == 0
    assert len(capsys.readouterr().out.strip()) == 8


def test_next_rule_id_counts_rules_only_listed_in_the_index(tmp_path):
    project, dep, _ = setup(tmp_path)
    index = project / ".criterion" / "rules" / "rules.md"
    index.write_text(index.read_text(encoding="utf-8") + f"- `br-AUTH-000007-{USERID}` — removed later\n", encoding="utf-8")
    corpus = load_corpus(dep)
    assert next_rule_id(dep, corpus, "br", "AUTH", corpus.user(USER)) == f"br-AUTH-000008-{USERID}"


def test_ids_seen_only_in_the_journal_are_not_reused(tmp_path):
    project, dep, _ = setup(tmp_path)
    (project / ".criterion" / "development" / "journal.jsonl").write_text(
        f'{{"artifact": "ITEM-000005-{USERID}"}}\n', encoding="utf-8")
    corpus = load_corpus(dep)
    assert next_entity_id(dep, corpus, "ITEM", corpus.user(USER)) == f"ITEM-000006-{USERID}"


def test_next_rule_needs_a_registered_domain_even_when_none_exist(tmp_path):
    project, dep, _ = setup(tmp_path)
    (project / ".criterion" / "rules" / "domains" / "domains.md").write_text("# Domains index\n", encoding="utf-8")
    corpus = load_corpus(dep)
    with pytest.raises(IdError, match="not registered"):
        next_rule_id(dep, corpus, "br", "AUTH", corpus.user(USER))


def test_next_rule_id_counts_rules_cited_only_in_a_rule_document(tmp_path):
    """A rule removed from the index but still cited in a document's prose
    (or remembered by the journal) keeps its number."""
    project, dep, _ = setup(tmp_path)
    doc = project / ".criterion" / "rules" / "business" / "br-business-rules.md"
    doc.write_text(doc.read_text(encoding="utf-8") + f"\nSupersedes `xr-AUTH-000011-{USERID}` (removed).\n", encoding="utf-8")
    corpus = load_corpus(dep)
    assert next_rule_id(dep, corpus, "br", "AUTH", corpus.user(USER)) == f"br-AUTH-000012-{USERID}"
    (project / ".criterion" / "development" / "journal.jsonl").write_text(
        f'{{"artifact": "br-AUTH-000020-{USERID}"}}\n', encoding="utf-8")
    assert next_rule_id(dep, corpus, "br", "AUTH", corpus.user(USER)) == f"br-AUTH-000021-{USERID}"


def test_reserved_ids_are_handed_out_once(tmp_path):
    _, dep, corpus = setup(tmp_path)
    signer = corpus.user(USER)
    first = next_entity_id(dep, corpus, "ITEM", signer, reserve=True)
    second = next_entity_id(dep, corpus, "ITEM", signer, reserve=True)
    assert (first, second) == (f"ITEM-000002-{USERID}", f"ITEM-000003-{USERID}")
    r1 = next_rule_id(dep, corpus, "br", "AUTH", signer, reserve=True)
    r2 = next_rule_id(dep, corpus, "br", "AUTH", signer, reserve=True)
    assert (r1, r2) == (f"br-AUTH-000002-{USERID}", f"br-AUTH-000003-{USERID}")
    # the reservations are never written into the working copy
    assert not list((tmp_path / "app" / ".criterion").rglob("ids.json"))


def test_a_stale_lock_is_broken(tmp_path):
    import os
    import time
    from catalyst.ids import id_lock, state_dir
    _, dep, _ = setup(tmp_path)
    lock = state_dir(dep) / "ids.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("12345\n", encoding="utf-8")
    with pytest.raises(IdError, match="held by another process"):
        with id_lock(dep, wait=0.1, stale=60):
            pass
    old = time.time() - 120
    os.utime(lock, (old, old))
    with id_lock(dep, wait=0.1, stale=60):
        assert lock.is_file()
    assert not lock.exists()


def test_parallel_cli_callers_never_get_the_same_id(tmp_path):
    """Parallel sub-agents allocating at once: every caller gets its own ID."""
    import os
    import subprocess
    import sys
    from pathlib import Path
    project = make_project(tmp_path, git=True)
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parent.parent / "scripts"))
    procs = [subprocess.Popen([sys.executable, "-m", "catalyst", "--project", str(project), "id",
                               *(["next", "ITEM"] if i % 2 else ["next-rule", "br", "AUTH"])],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=env)
             for i in range(12)]
    outs = [p.communicate(timeout=120) for p in procs]
    assert all(p.returncode == 0 for p in procs), [e for _, e in outs]
    ids = [o.strip() for o, _ in outs]
    assert len(set(ids)) == 12
    assert sorted(i for i in ids if i.startswith("ITEM")) == [f"ITEM-{n:06d}-{USERID}" for n in range(2, 8)]
    assert sorted(i for i in ids if i.startswith("br")) == [f"br-AUTH-{n:06d}-{USERID}" for n in range(2, 8)]
    # nothing was left in the working copy's tracked tree
    status = subprocess.run(["git", "-C", str(project / ".criterion"), "status", "--porcelain"],
                            capture_output=True, text=True, encoding="utf-8").stdout
    assert status == ""


def test_the_lock_waits_while_windows_reports_it_delete_pending(tmp_path, monkeypatch):
    """Windows: opening a lock file its holder is deleting fails with
    PermissionError; that means busy, so the caller waits and gets the lock."""
    import os
    from catalyst import ids
    from catalyst.deployment import load
    dep = load(make_project(tmp_path, git=True))
    real_open, calls = os.open, []

    def flaky_open(path, *a, **kw):
        calls.append(path)
        if len(calls) == 1:
            raise PermissionError(13, "Permission denied", path)
        return real_open(path, *a, **kw)

    monkeypatch.setattr(ids, "BUSY", (FileExistsError, PermissionError))
    monkeypatch.setattr(ids.os, "open", flaky_open)
    with ids.id_lock(dep, wait=5):
        pass
    assert len(calls) == 2
