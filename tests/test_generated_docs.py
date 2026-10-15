"""The generated sections of the kernel's reference documents (roadmap
R4.4): the command index in CLI.md and the kernel's entity types in
FORMAT.md match the code, and a stale section is caught."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import gen_docs


def test_every_generated_section_is_up_to_date(capsys):
    assert gen_docs.main(["--check"]) == 0, capsys.readouterr().out


def test_the_index_lists_every_command_with_its_options():
    index = gen_docs.cli_index()
    for row in (
        "`catalyst init`",
        "`catalyst hook start`",
        "`catalyst module install <source>`",
        "`catalyst impact <id>`",
    ):
        assert row in index
    assert "`--quiet`" in index and "`--no-module`" in index


def test_a_stale_section_is_named_and_not_written_by_check(tmp_path, monkeypatch, capsys):
    doc = tmp_path / "CLI.md"
    begin, end = gen_docs.BEGIN.format(name="cli-index"), gen_docs.END.format(name="cli-index")
    doc.write_text(f"# CLI\n\n{begin}\n\nold\n\n{end}\n", encoding="utf-8")
    monkeypatch.setattr(gen_docs, "ROOT", tmp_path)
    monkeypatch.setattr(gen_docs, "SECTIONS", {"cli-index": (doc, gen_docs.cli_index)})
    assert gen_docs.main(["--check"]) == 1
    assert "out of date: CLI.md (cli-index)" in capsys.readouterr().out
    assert "old" in doc.read_text(encoding="utf-8")  # --check writes nothing
    assert gen_docs.main([]) == 0 and "`catalyst init`" in doc.read_text(encoding="utf-8")
    assert gen_docs.main(["--check"]) == 0


def test_a_document_without_its_markers_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="no `<!-- generated: cli-index"):
        gen_docs.render("# no markers\n", "cli-index", "body")
