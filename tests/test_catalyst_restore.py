"""`catalyst restore` (REQ-000049): an entity's earlier version written back
as a new journaled change, never a rewrite of the journal."""

from __future__ import annotations

import json

from catalyst import history
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from test_catalyst_history import RULE, lived  # noqa: F401 (the fixture)


def _history(project, item):
    dep = load(project)
    return history.history(dep, load_corpus(dep), item)["entries"]


def test_restore_writes_the_earlier_version_back_as_a_new_journaled_change(lived, capsys):  # noqa: F811
    project, item, _sub = lived
    before = _history(project, item)
    first = before[0]["content_after"]
    assert "Done" in before[-1]["content_after"] and first != before[-1]["content_after"]
    capsys.readouterr()
    assert main(["restore", item, "--to", "#1", "--as", "ada", "--intent", "Undo the close", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == item
    after = _history(project, item)
    assert after[: len(before)] == before  # no entry rewritten (L1)
    new = after[-1]
    assert len(after) == len(before) + 1
    assert (new["command"], new["action"], new["intent"]) == ("catalyst restore", "update", ["Undo the close"])
    assert new["content_before"] == before[-1]["content_after"]
    assert "Done" not in new["content_after"] and new["content_after"].split("Subs")[0] == first.split("Subs")[0]
    # its derived field is recomputed from its sources, not taken from the old version
    dep = load(project)
    from catalyst import derived

    assert [d for d in derived.drift(dep, load_corpus(dep)) if d.art.id == item] == []
    assert _sub in new["content_after"]


def test_restore_by_time_takes_the_last_entry_at_or_before_it(lived, capsys):  # noqa: F811
    project, item, _ = lived
    entries = _history(project, item)
    assert main(["restore", item, "--to", "2999-01-01T00:00:00Z", "--as", "ada"]) == 1  # the latest: already there
    assert "already as it stood" in capsys.readouterr().err
    assert main(["restore", item, "--to", "1999-01-01T00:00:00Z", "--as", "ada"]) == 1
    assert "first journal entry is later" in capsys.readouterr().err
    assert len(_history(project, item)) == len(entries)  # nothing written


def test_restore_refuses_what_it_cannot_restore_alone(lived, capsys):  # noqa: F811
    _project, item, _ = lived
    assert main(["restore", "ITEM-999999", "--to", "#1", "--as", "ada"]) == 1
    assert "no artifact or rule" in capsys.readouterr().err
    assert main(["restore", RULE, "--to", "#1", "--as", "ada"]) == 1
    assert "shares its rule document" in capsys.readouterr().err
    assert main(["restore", item, "--to", "#99", "--as", "ada"]) == 1
    assert "is none of them" in capsys.readouterr().err
