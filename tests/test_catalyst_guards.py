"""Guards on entering a state (rr-META-021, REQ-000024): `status set`
refuses while a guard fails, `--force` overrides it (journaled), `check`
warns about an artifact already in a guarded state."""

from __future__ import annotations

import pytest

from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst.guards import failures
from catalyst_fixtures import USERID, journal_entries, make_project, write

ITEM, SUB = f"ITEM-000001-{USERID}", f"SUB-000001-{USERID}"


@pytest.fixture
def guarded(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path, git=True)
    schemas = project / ".criterion" / "modules" / "example-process" / "schemas"
    item = schemas / "item.yaml"
    write(
        item,
        item.read_text(encoding="utf-8")
        + "  guards:\n    Done:\n      - nonempty: Subs\n      - children_closed: Subs\n      - section_written: Notes\n",
    )
    sub = schemas / "sub.yaml"
    write(sub, sub.read_text(encoding="utf-8") + "\nworkflow:\n  initial: Open\n  closed_states:\n    - Done\n")
    template = project / ".criterion" / "items" / "templates" / "TEMPLATE-ITEM-v1.md"
    write(template, "# `ITEM-NNNNNN` — {{title}}\n\n## Notes\n\nWhat was noticed.\n")
    item_file = project / ".criterion" / "items" / "ITEM-000001-first-item.md"
    write(item_file, item_file.read_text(encoding="utf-8") + "\n## Notes\n\nWhat was noticed.\n")
    monkeypatch.chdir(project)
    capsys.readouterr()
    return project, item_file


def _why(project):
    dep = load(project)
    corpus = load_corpus(dep)
    return failures(dep, corpus, corpus.artifacts[ITEM][0], "Done")


def test_each_guard_refuses_until_it_holds(guarded, capsys):
    project, item_file = guarded
    assert _why(project) == [f"{SUB} (in `Subs`) is Open, not closed", "`## Notes` is not written"]
    assert main(["status", "set", ITEM, "Done", "--as", "ada"]) == 1
    err = capsys.readouterr().err
    assert "cannot become Done" in err and "is not written" in err and "--force overrides" in err
    assert main(["status", "set", SUB, "Done", "--as", "ada"]) == 0
    item_file.write_text(
        item_file.read_text(encoding="utf-8").replace("What was noticed.", "Checked by hand."), encoding="utf-8"
    )
    assert _why(project) == []
    assert main(["status", "set", ITEM, "Done", "--as", "ada"]) == 0


def test_nonempty_and_force_is_journaled(guarded, capsys):
    project, item_file = guarded
    item_file.write_text(
        item_file.read_text(encoding="utf-8").replace(f"| **Subs** | `{SUB}` |", "| **Subs** | *(none yet)* |"),
        encoding="utf-8",
    )
    assert "`Subs` is empty" in _why(project)
    assert main(["status", "set", ITEM, "Done", "--as", "ada", "--force"]) == 0
    (entry,) = [e for e in journal_entries(project / ".criterion") if e["command"] == "/status"]
    assert entry["intent"][0] == f"{ITEM}: Open -> Done"
    assert entry["intent"][1].startswith("guards overridden with --force: `Subs` is empty")


def test_check_warns_about_work_already_past_a_guard(guarded, capsys):
    _, item_file = guarded
    item_file.write_text(
        item_file.read_text(encoding="utf-8").replace("| **Status** | Open |", "| **Status** | Done |"),
        encoding="utf-8",
    )
    capsys.readouterr()
    main(["validate"])
    out = capsys.readouterr().out
    assert "guard" in out and "is Done, but" in out


def test_view_and_graph_say_what_an_entity_page_shows(guarded):
    """The entity page reads its type's workflow from `graph` and an
    artifact's sections and next states from `view` (roadmap R6.7)."""
    from catalyst.views import graph, view

    project, _ = guarded
    dep = load(project)
    corpus = load_corpus(dep)
    shown = view(dep, corpus, ITEM)
    assert {"heading": "Notes", "text": "What was noticed."} in shown["sections"]
    done = next(n for n in shown["next"] if n["state"] == "Done")
    assert done["blocked_by"] == [f"{SUB} (in `Subs`) is Open, not closed", "`## Notes` is not written"]
    item_type = graph(dep, corpus)["types"]["ITEM"]
    assert item_type["guards"]["Done"][-1] == {"condition": "section_written", "argument": "Notes"}
    assert isinstance(item_type["transitions"], list) and isinstance(item_type["sections"], list)
