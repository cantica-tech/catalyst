"""Derived fields are catalyst's (rr-META-015, REQ-000024): a field another
type names as its `backref` is derived from its sources; `check` reports
one that disagrees, `catalyst repair derived` rewrites it, journaled."""

from __future__ import annotations

from catalyst import derived
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst_fixtures import USERID, journal_entries, make_project

SUB = f"SUB-000001-{USERID}"


def _item(project):
    return project / ".criterion" / "items" / "ITEM-000001-first-item.md"


def test_the_derived_fields_are_read_from_the_backrefs(tmp_path):
    dep = load(make_project(tmp_path))
    assert derived.sources(dep) == {("ITEM", "Subs"): [("SUB", "Item")]}
    assert derived.drift(dep, load_corpus(dep)) == []


def test_drift_both_ways_and_a_journaled_repair_that_runs_once(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path, git=True)
    item = _item(project)
    text = item.read_text(encoding="utf-8")
    item.write_text(text.replace(f"| **Subs** | `{SUB}` |", "| **Subs** | `SUB-000009-Zz9zZz9z` |"), encoding="utf-8")
    dep = load(project)
    (d,) = derived.drift(dep, load_corpus(dep))
    assert (d.art.id, d.field, d.missing, d.extra) == (f"ITEM-000001-{USERID}", "Subs", [SUB], ["SUB-000009-Zz9zZz9z"])
    monkeypatch.chdir(project)
    capsys.readouterr()
    assert main(["repair", "derived", "--as", "ada"]) == 0
    out = capsys.readouterr().out
    assert f"added {SUB}; removed SUB-000009-Zz9zZz9z" in out and "1 derived field(s) rewritten" in out
    assert f"| **Subs** | `{SUB}` |" in item.read_text(encoding="utf-8")
    (entry,) = [e for e in journal_entries(project / ".criterion") if e["command"] == "catalyst repair derived"]
    assert entry["tier"] == "chore" and entry["files"][0]["path"].endswith("ITEM-000001-first-item.md")
    assert main(["repair", "derived", "--as", "ada"]) == 0
    assert "every derived field agrees" in capsys.readouterr().out
