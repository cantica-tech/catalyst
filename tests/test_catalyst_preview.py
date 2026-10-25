"""A writing verb's `--preview` and `--forewarned` (design 31 §3): the admins' forewarning. `--preview` is `catalyst
try` of the same change; `--forewarned` tries it first, makes it anyway, and records what it would add to `check` in
its journal entry."""

from __future__ import annotations

import json

from catalyst.__main__ import _preview_and_forewarned, _writing_verb, main
from catalyst_fixtures import journal_entries
from test_catalyst_guards import ITEM, guarded  # noqa: F401 (the fixture)

PAST_THE_GUARD = ["status", "set", ITEM, "Done", "--as", "ada", "--force", "--intent", "done despite its guards"]


def test_the_writing_verb_is_found_after_the_global_options():
    assert _writing_verb(["--project", "p", "status", "set", "X", "Done"]) == 2
    assert _writing_verb(["--working-copy=w", "new", "ITEM"]) == 1
    assert _writing_verb(["check"]) is None and _writing_verb(["share", "push"]) is None


def test_preview_is_try_and_forewarned_is_set_apart():
    assert _preview_and_forewarned(["new", "ITEM", "--preview", "--json"]) == (["try", "--json", "new", "ITEM"], None)
    assert _preview_and_forewarned(["--project", "p", "rename", "X", "--forewarned"]) == (
        ["--project", "p", "rename", "X"],
        ["rename", "X"],
    )
    assert _preview_and_forewarned(["check", "--preview"]) == (["check", "--preview"], None)  # not a writing verb


def test_preview_writes_nothing_and_says_what_the_change_adds(guarded, tmp_path, monkeypatch, capsys):  # noqa: F811
    project, item_file = guarded
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    before, entries = item_file.read_text(encoding="utf-8"), len(journal_entries(project / ".criterion"))
    assert main([*PAST_THE_GUARD, "--preview", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] and report["check"]["added"], report
    assert item_file.read_text(encoding="utf-8") == before
    assert len(journal_entries(project / ".criterion")) == entries


def test_forewarned_makes_the_change_and_records_what_it_adds(guarded, tmp_path, monkeypatch, capsys):  # noqa: F811
    project, item_file = guarded
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    assert main([*PAST_THE_GUARD, "--forewarned"]) == 0
    assert "forewarned, made anyway" in capsys.readouterr().err
    assert "| **Status** | Done |" in item_file.read_text(encoding="utf-8")
    (entry,) = [e for e in journal_entries(project / ".criterion") if e["command"] == "/status"]
    assert entry["intent"][0] == "done despite its guards"
    assert any(i.startswith("forewarned: ") and "finding(s) added" in i for i in entry["intent"]), entry["intent"]


def test_forewarned_records_nothing_when_nothing_is_added(guarded, tmp_path, monkeypatch, capsys):  # noqa: F811
    project, _ = guarded
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    rename = ["rename", ITEM, "--title", "Renamed", "--as", "ada", "--intent", "a better title", "--forewarned"]
    assert main(rename) == 0
    entry = [e for e in journal_entries(project / ".criterion") if e["artifact"] == ITEM][-1]
    assert not any(i.startswith("forewarned") for i in entry["intent"])
