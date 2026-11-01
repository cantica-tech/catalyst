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


def test_release_writes_the_generated_sections_before_it_packages():
    """`SYNCHRONIZE.md`'s migrations table was missed by the 0.120.0 and 0.121.0 releases: `task release` only checked
    the generated sections. It now writes them (journaled, as any write of gen_docs is), checks them again, and only
    then packages."""
    lines = (Path(__file__).resolve().parent.parent / "Taskfile.yml").read_text(encoding="utf-8").splitlines()
    start = lines.index("  release:")
    steps = []
    for line in lines[start + 1 :]:
        if line.strip() and not line.startswith("    "):
            break  # the next task, at the task level
        if line.startswith("      - "):
            steps.append(line.strip()[2:])
    assert "python3 scripts/gen_docs.py" in steps, steps
    write = steps.index("python3 scripts/gen_docs.py")
    assert steps[write + 1] == "python3 scripts/gen_docs.py --check", steps
    package = steps.index("python3 scripts/package_release.py")
    assert package > write + 1, steps
    assert steps.index("task: check:journaled") < write, steps


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


def test_what_it_rewrites_in_a_governed_checkout_is_journaled(tmp_path, monkeypatch, capsys):
    """BUG-000060: a rewritten section is journaled at once in a checkout catalyst governs, before any later check
    can return; a failed entry fails the run; --no-journal and --check journal nothing."""
    import subprocess

    doc = tmp_path / "CLI.md"
    begin, end = gen_docs.BEGIN.format(name="cli-index"), gen_docs.END.format(name="cli-index")
    stale = f"# CLI\n\n{begin}\n\nold\n\n{end}\n"
    (tmp_path / "catalyst.toml").write_text('project_name = "x"\n', encoding="utf-8")
    monkeypatch.setattr(gen_docs, "ROOT", tmp_path)
    monkeypatch.setattr(gen_docs, "SECTIONS", {"cli-index": (doc, gen_docs.cli_index)})
    calls: list[list[str]] = []
    code = {"rc": 0}
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **kw: calls.append(cmd) or subprocess.CompletedProcess(cmd, code["rc"])
    )
    doc.write_text(stale, encoding="utf-8")
    assert gen_docs.main(["--target", "REQ-000001-Ab3xR9pQ", "--tier", "feature"]) == 0
    (call,) = calls
    assert call[call.index("journal") + 1] == "append" and call[call.index("--file") + 1] == "CLI.md"
    assert call[call.index("--target") + 1] == "REQ-000001-Ab3xR9pQ" and call[call.index("--tier") + 1] == "feature"
    doc.write_text(stale, encoding="utf-8")
    assert gen_docs.main([]) == 0 and calls[-1][calls[-1].index("--tier") + 1] == "chore"
    doc.write_text(stale, encoding="utf-8")
    code["rc"] = 1
    assert gen_docs.main([]) == 1 and "not journaled" in capsys.readouterr().out
    doc.write_text(stale, encoding="utf-8")
    calls.clear()
    assert gen_docs.main(["--no-journal"]) == 0 and gen_docs.main(["--check"]) == 0 and calls == []


def test_a_document_without_its_markers_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="no `<!-- generated: cli-index"):
        gen_docs.render("# no markers\n", "cli-index", "body")


def test_the_options_reference_gives_each_argument_its_help():
    """R4.4 phase 1: every command's arguments, generated from the parser."""
    ref = gen_docs.cli_options()
    assert "| `catalyst status set` | `<id>` |" in ref
    assert "`--through`" in ref and "reach a later status through the states between" in ref
    assert "one of `check`, `chain`" in ref.lower()  # choices, from the parser
    assert ref.count("(repeatable) (repeatable)") == 0


def test_the_prose_may_name_only_options_the_cli_has():
    assert gen_docs.flag_drift("Run `catalyst check --strict`; `--base-*` names both bases.") == []
    assert gen_docs.flag_drift("`git commit --no-verify` skips the hook.") == []  # another tool's flag
    assert gen_docs.flag_drift("Pass `--frobnicate` to `catalyst check`.") == ["--frobnicate"]
    assert gen_docs.flag_drift("`--nothing-*` stands for options no command has.") == ["--nothing-*"]


def test_the_project_file_keys_come_from_the_registry(monkeypatch):
    """R4.4 phase 3: FORMAT.md's catalyst.toml table, from project_file.KEYS; a key the code reads must be there."""
    import project_file

    table = gen_docs.project_keys()
    assert "| `role_check` | string |" in table and "| `workspace` | string |" in table
    assert "- `framework_version`:" in table  # a legacy key, read and never written
    assert gen_docs.key_drift() == []
    monkeypatch.setattr(project_file, "KEYS", tuple(k for k in project_file.KEYS if k[0] != "role_check"))
    assert gen_docs.key_drift() == ["role_check"]  # read by the code, no longer listed


def test_the_module_specification_tables_come_from_the_schemas():
    manifest = gen_docs.manifest_fields()
    assert "| `entities` | `map` | Conditional |" in manifest and "| `tiers` | `list[object]` | No |" in manifest
    assert "| `hint` | `string` | No |" in gen_docs.etd_field_definitions()
    assert "| `guards` | `map` | No |" in gen_docs.etd_workflow()


def test_the_migrations_table_comes_from_the_index():
    """R4.4 phase 4: SYNCHRONIZE.md lists every kernel migration the index has, the latest included."""
    table = gen_docs.migrations()
    assert (
        "| `0.92.0` | `0.93.0` | [`0.93.0/roles-grant-commands.md`](migrations/0.93.0/roles-grant-commands.md) |"
        in table
    )
    assert table.count("\n| `") >= 37


def test_the_invariants_name_only_commands_and_scripts_that_exist(tmp_path, monkeypatch):
    """R4.4 phase 5: an "enforced by" cell naming a command the CLI lacks fails the check."""
    assert gen_docs.invariant_drift() == []
    kernel = tmp_path / "kernel"
    kernel.mkdir()
    text = (gen_docs.KERNEL / "INVARIANTS.md").read_text(encoding="utf-8")
    text = text.replace("| `check` (structure) |", "| `check` (structure), `catalyst frobnicate`, `nope.py` |", 1)
    (kernel / "INVARIANTS.md").write_text(text, encoding="utf-8")
    monkeypatch.setattr(gen_docs, "KERNEL", kernel)
    drift = gen_docs.invariant_drift()
    assert any("`catalyst frobnicate`, which is no command" in d for d in drift)
    assert any("nope.py, which is no script" in d for d in drift)
