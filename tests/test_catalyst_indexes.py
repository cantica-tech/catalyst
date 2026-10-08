from __future__ import annotations

from pathlib import Path

from catalyst.__main__ import main
from catalyst.corpus import Artifact, load_corpus
from catalyst.deployment import load
from catalyst.indexes import regenerate, render
from catalyst_fixtures import USERID, artifact, make_project, write


def regen(project, write_files=True):
    dep = load(project)
    return regenerate(dep, load_corpus(dep), write=write_files)


def test_fixture_indexes_are_already_current(tmp_path):
    assert regen(make_project(tmp_path)) == []


def test_new_artifact_is_added_in_id_order_with_its_columns(tmp_path):
    project = make_project(tmp_path)
    item2 = f"ITEM-000002-{USERID}"
    write(project / ".criterion" / "subs" / "SUB-000002-second.md", artifact(
        f"SUB-000002-{USERID}", "Second sub",
        {"ID": f"`SUB-000002-{USERID}`", "Status": "Done", "Item": f"`{item2}`",
         "Signed-off-by": "ada"}))
    changes = regen(project)
    assert [c.path.name for c in changes] == ["subs.md"]
    rows = (project / ".criterion" / "subs" / "subs.md").read_text(encoding="utf-8").splitlines()
    assert rows[-1] == (f"| [SUB-000002-{USERID}](SUB-000002-second.md) | Second sub | "
                        f"{item2} | Done |")
    assert rows[-2].startswith(f"| [SUB-000001-{USERID}]")


def test_removed_file_keeps_its_row_and_prose_is_kept(tmp_path):
    """Regenerating never drops a row: the ID must stay taken, and validate
    reports the orphan instead."""
    project = make_project(tmp_path)
    index = project / ".criterion" / "items" / "items.md"
    index.write_text(index.read_text(encoding="utf-8") + "\nSee also the roadmap.\n", encoding="utf-8")
    (project / ".criterion" / "items" / "ITEM-000001-first-item.md").unlink()
    regen(project)
    text = index.read_text(encoding="utf-8")
    assert f"| [ITEM-000001-{USERID}](ITEM-000001-first-item.md) | First item | Open |" in text
    assert text.startswith("# Items index")
    assert text.rstrip().endswith("See also the roadmap.")


def test_orphan_row_keeps_its_id_from_being_reused(tmp_path):
    from catalyst.ids import next_entity_id
    project = make_project(tmp_path)
    index = project / ".criterion" / "items" / "items.md"
    index.write_text(index.read_text(encoding="utf-8") + f"| [ITEM-000009-{USERID}](ITEM-000009-gone.md) | Gone | Done |\n", encoding="utf-8")
    regen(project)
    dep = load(project)
    corpus = load_corpus(dep)
    assert next_entity_id(dep, corpus, "ITEM", corpus.user("ada")) == f"ITEM-000010-{USERID}"


def test_hand_written_cells_without_a_field_are_kept(tmp_path):
    project = make_project(tmp_path)
    index = project / ".criterion" / "items" / "items.md"
    index.write_text(index.read_text(encoding="utf-8").replace("| ID | Title | Status |\n|---|---|---|",
                                               "| ID | Title | Status | Notes |\n|---|---|---|---|")
                     .replace("| First item | Open |", "| First item | Open | keep me |"), encoding="utf-8")
    regen(project)
    assert "| First item | Open | keep me |" in index.read_text(encoding="utf-8")


def test_only_the_id_table_is_regenerated(tmp_path):
    project = make_project(tmp_path)
    index = project / ".criterion" / "items" / "items.md"
    legend = "| Status | Meaning |\n|---|---|\n| Open | not started |\n"
    index.write_text(index.read_text(encoding="utf-8").replace("# Items index\n", "# Items index\n\n" + legend), encoding="utf-8")
    assert regen(project) == []
    assert legend in index.read_text(encoding="utf-8")


def test_placeholder_line_removed_once_rows_exist():
    out = render("# Things index\n\n| ID | Title | Status |\n|---|---|---|\n\n*(none yet — add one)*\n",
                 "Things", [])
    assert "*(none yet" in out
    art = Artifact("T-000001-Ab3xR9pQ", "T", Path("T-000001-x.md"), "X", {"Status": "Open"})
    out = render("# Things index\n\n| ID | Title | Status |\n|---|---|---|\n\n*(none yet — add one)*\n",
                 "Things", [art])
    assert "*(none yet" not in out and "| [T-000001-Ab3xR9pQ](T-000001-x.md) | X | Open |" in out


def test_missing_index_is_created_with_default_columns(tmp_path):
    project = make_project(tmp_path)
    (project / ".criterion" / "items" / "items.md").unlink()
    regen(project)
    text = (project / ".criterion" / "items" / "items.md").read_text(encoding="utf-8")
    assert text.startswith("# Items index") and "| ID | Title | Status |" in text


def test_cli_check_mode_changes_nothing(tmp_path, capsys):
    project = make_project(tmp_path)
    index = project / ".criterion" / "items" / "items.md"
    index.write_text(index.read_text(encoding="utf-8").replace("| Open |", "| Stale |"), encoding="utf-8")
    stale = index.read_text(encoding="utf-8")
    assert main(["--project", str(project), "index", "regen", "--check", "--diff"]) == 1
    assert "out of date" in capsys.readouterr().out
    assert index.read_text(encoding="utf-8") == stale
    assert main(["--project", str(project), "index", "regen"]) == 0
    assert main(["--project", str(project), "index", "regen", "--check"]) == 0


def test_empty_index_without_a_table_is_left_alone():
    assert render("# Things index\n\n*(none)*\n", "Things", []) == "# Things index\n\n*(none)*\n"
