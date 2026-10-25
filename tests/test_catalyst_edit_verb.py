"""`catalyst edit` (design 31 §2a, §3, §4.2, `fw-STRUCTURE-000021`): an entity's plain fields and sections. No one
edits its ID, Name, Filename, Signed-off-by or Status; references are `link`'s. An admin's edit is made; anyone
else's only on an unlinked entity of theirs, and on a linked one it becomes a proposal for an admin to decide."""

from __future__ import annotations

import json
from pathlib import Path

from catalyst import edit
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst_fixtures import journal_entries
from test_catalyst_proposals import ITEM, project  # noqa: F401 (the fixture)


def _item_file(project):  # noqa: F811
    dep = load(project)
    return load_corpus(dep).artifacts[ITEM][0].file


def test_an_admin_edits_a_section_journaled(project, capsys):  # noqa: F811
    assert main(["edit", ITEM, "--section", "Description=A clearer description.", "--as", "ada",
                 "--intent", "clearer"]) == 0  # fmt: skip
    assert "A clearer description." in _item_file(project).read_text(encoding="utf-8")
    entry = journal_entries(project / ".criterion")[-1]
    assert entry["artifact"] == ITEM and entry["intent"] == ["clearer"]


def test_no_one_edits_what_catalyst_owns(project, capsys):  # noqa: F811
    for name in ("ID", "Status", "Signed-off-by", "Name", "Filename"):
        assert main(["edit", ITEM, "--field", f"{name}=x", "--as", "ada"]) == 1
        assert "never edited" in capsys.readouterr().err
    assert main(["edit", ITEM, "--field", "Targets=x", "--as", "ada"]) == 1
    assert "`catalyst link`" in capsys.readouterr().err


def test_someone_elses_entity_is_not_edited_by_a_contributor(project, capsys):  # noqa: F811
    assert main(["edit", ITEM, "--section", "Description=Mine now.", "--as", "bob"]) == 1
    assert "neither theirs nor assigned to them" in capsys.readouterr().err


def test_a_contributors_edit_of_a_linked_entity_is_a_proposal(project, capsys):  # noqa: F811
    path = _item_file(project)
    path.write_text(path.read_text(encoding="utf-8").replace("Ada Lovelace", "Bob"), encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    assert main(["edit", ITEM, "--section", "Description=Bob's wording.", "--as", "bob", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["id"] == ITEM and out["proposal"].startswith("RECON-")
    assert path.read_text(encoding="utf-8") == before  # nothing lands before an admin decides
    proposed = [p for p in out["touched"] if p.endswith(".proposed")]
    assert proposed and "Bob's wording." in Path(proposed[0]).read_text(encoding="utf-8")


def test_a_contributor_edits_an_unlinked_entity_of_theirs_directly(project, monkeypatch, capsys):  # noqa: F811
    path = _item_file(project)
    path.write_text(path.read_text(encoding="utf-8").replace("Ada Lovelace", "Bob"), encoding="utf-8")
    monkeypatch.setattr(edit, "is_linked", lambda dep, corpus, art: False)
    assert main(["edit", ITEM, "--section", "Description=Direct.", "--as", "bob"]) == 0
    assert "Direct." in path.read_text(encoding="utf-8")


def test_linked_means_any_reference_in_or_out(project):  # noqa: F811
    dep = load(project)
    corpus = load_corpus(dep)
    assert edit.is_linked(dep, corpus, corpus.artifacts[ITEM][0])  # it cites its rule


def test_an_edit_can_be_previewed(project, tmp_path, monkeypatch, capsys):  # noqa: F811
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    before = _item_file(project).read_text(encoding="utf-8")
    assert main(["edit", ITEM, "--section", "Description=Tried.", "--as", "ada", "--preview", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]
    assert _item_file(project).read_text(encoding="utf-8") == before


def test_a_derived_field_is_catalysts(project, capsys):  # noqa: F811
    assert main(["edit", ITEM, "--field", "Subs=x", "--as", "ada"]) == 1
    assert "derived" in capsys.readouterr().err


def test_an_edit_must_change_something(project, capsys):  # noqa: F811
    assert main(["edit", ITEM, "--as", "ada"]) == 1
    assert "nothing to edit" in capsys.readouterr().err
    assert main(["edit", ITEM, "--section", "Description=Same.", "--as", "ada"]) == 0
    capsys.readouterr()
    assert main(["edit", ITEM, "--section", "Description=Same.", "--as", "ada"]) == 1
    assert "already reads so" in capsys.readouterr().err
