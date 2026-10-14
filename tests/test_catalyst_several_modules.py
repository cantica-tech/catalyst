"""Several modules in one deployment (roadmap R4.9, N3; REQ-000029): a
module installed beside another is loaded, composed, checked and synced
with it, and what two modules must not share is refused."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from catalyst import laws, modules, tiers
from catalyst.__main__ import main
from catalyst.check import run as run_checks
from catalyst.deployment import load, load_working_copy
from catalyst_fixtures import journal_entries, write
from test_catalyst_init import KERNEL
from test_catalyst_sync import _deployment, _release

NOTES_YAML = """id: notes-process
name: Notes
version: 1.0.0
description: A second module, for the tests.
grounding_type: rule
format: 3
namespace: NT

tiers:
  - id: chore
    artifact: none
    commit: "chore:"
  - id: note
    artifact: NOTE

entities:
  NOTE:
    name: Note
    folder: notes
    grounding: none
    fields:
      Owner: {kind: user}
    states: [Open, Closed]
    closed: [Closed]
    sections:
      - Text: What it says.
    definition: A note.
"""


def notes_module(base: Path, yaml: str = NOTES_YAML, files: dict[str, str] | None = None) -> Path:
    mod = base / "notes-process"
    write(mod / "module.yaml", yaml)
    write(mod / "version.txt", "1.0.0\n")
    write(mod / "rules-of-rules.module.md", "# notes meta-rules\n\n## 1. `rr-NT-001` Notes\n\nNotes are notes.\n")
    write(
        mod / "INVARIANTS.module.md",
        f"# Notes laws\n\n## The law\n\n- **NT-L1 — Notes are short.** A note says one thing.\n\n{laws.MARKER}\n",
    )
    for name, text in (files or {}).items():
        write(mod / name, text)
    return mod


def _install(project: Path, source) -> int:
    return main(["--project", str(project), "module", "install", str(source), "--kernel", str(KERNEL)])


def _two(tmp_path: Path) -> tuple[Path, Path]:
    """A deployment with the example module, and the notes module beside it."""
    project, _ = _deployment(tmp_path)
    assert _install(project, notes_module(tmp_path)) == 0
    return project, project / ".criterion"


def _errors(project: Path) -> list[str]:
    """`check`'s errors, minus the one the fixture leaves (it edits the
    project file after the install without journaling it)."""
    return [e for e in run_checks(load(project)).errors if "app.catalyst changed" not in e]


def _files(root: Path) -> dict[str, str]:
    """Every file under `root` but `.git`, and its hash (`.git` is never
    entered: git may repack it while the walk runs)."""
    from test_catalyst_module_install import _files as listed

    return listed(root, skip=(".git",))


def test_a_second_module_installs_beside_the_first(tmp_path):
    project, root = _two(tmp_path)
    dep = load(project)
    assert [m.id for m in dep.installed()] == ["example-process", "notes-process"]
    assert dep.module is not None and dep.module.id == "example-process"  # the one the project file names
    assert json.loads(next(project.glob("*.catalyst")).read_text(encoding="utf-8"))["module"] == "example-process"
    assert {"ITEM", "SUB", "NOTE"} <= set(dep.etds)
    assert [e["id"] for e in modules.read_record(root)] == ["example-process", "notes-process"]  # install order
    assert [f.state for f in modules.verify(root)] == ["ok", "ok"]
    assert (root / "notes" / "notes.md").is_file() and (root / "definitions" / "note.md").is_file()
    assert _errors(project) == [] and run_checks(dep).scope == "modules example-process, notes-process"
    assert journal_entries(root)[-1]["artifact"] == "module notes-process 1.0.0"
    # a bare working copy (the CI gate) loads both too
    assert [m.id for m in load_working_copy(root).installed()] == ["example-process", "notes-process"]


def test_each_modules_part_is_composed_in_install_order(tmp_path):
    _, root = _two(tmp_path)
    coc = (root / "CODE-OF-CONDUCT.md").read_text(encoding="utf-8")
    first, second = coc.index("### From module example-process"), coc.index("### From module notes-process")
    assert 0 < first < second and "`/create-note`" in coc and "`/create-item`" in coc
    handbook = (root / "rules" / "Rules-of-Rules.md").read_text(encoding="utf-8")
    assert handbook.index("### From module example-process") < handbook.index("### From module notes-process")
    assert "`rr-NT-000001-" in handbook  # the second module's meta-rule, widened and signed
    taskfile = (root / "Taskfile.common.yml").read_text(encoding="utf-8")
    assert "From module notes-process" in taskfile and "create-note:" in taskfile
    # its laws: in the session brief and explained by `why`, from its own folder
    assert not (root / "INVARIANTS.module.md").exists()  # the example module has none: the root file is the first's
    assert "NT-L1" in laws.session_brief(root)
    assert "Notes are short" in (laws.why(root, "NT-L1") or "")


def test_artifacts_and_tiers_of_both_modules(tmp_path, capsys):
    project, _ = _two(tmp_path)
    assert tiers.ids(load(project)) == ["chore", "fix", "feature", "note"]  # the union, in install order
    capsys.readouterr()
    assert main(["--project", str(project), "new", "NOTE", "--title", "A note", "--tier", "note"]) == 0
    note = capsys.readouterr().out.split()[0]
    assert note.startswith("NOTE-000001-")
    assert main(["--project", str(project), "status", "set", note, "Closed", "--tier", "note"]) == 0
    assert _errors(project) == []
    assert main(["--project", str(project), "module", "list"]) == 0
    listed = capsys.readouterr().out
    assert "example-process 0.2.0" in listed and "notes-process 1.0.0" in listed


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (lambda y: y.replace("NOTE:", "ITEM:").replace("artifact: NOTE", "artifact: ITEM"), "its type ITEM is also"),
        (lambda y: y.replace("folder: notes", "folder: items"), "its folder items (type NOTE) is also"),
        (lambda y: y.replace("grounding_type: rule", "grounding_type: policy"), "it grounds on `policy`"),
        (lambda y: y.replace("id: note\n", "id: fix\n"), "its tier `fix` means something else"),
        (lambda y: y.replace("id: notes-process", "id: example-process"), "it is already installed"),
    ],
)
def test_what_two_modules_must_not_share_is_refused(tmp_path, capsys, change, said):
    project, _ = _deployment(tmp_path)
    before = _files(project / ".criterion")
    assert _install(project, notes_module(tmp_path, change(NOTES_YAML))) == 1
    assert said in capsys.readouterr().err
    assert _files(project / ".criterion") == before  # nothing written


def test_a_shared_command_meta_rule_or_namespace_is_refused(tmp_path, capsys):
    project, root = _two(tmp_path)
    before = _files(root)

    def refused(base: str, yaml: str = NOTES_YAML, files: dict[str, str] | None = None) -> str:
        other = yaml.replace("id: notes-process", "id: other-process").replace("NOTE", "MEMO").replace("notes", "memos")
        other = other.replace("id: note\n", "id: memo\n")  # its own tier: only what is under test is shared
        assert _install(project, notes_module(tmp_path / base, other, files).rename(tmp_path / base / "other")) == 1
        assert _files(root) == before
        return capsys.readouterr().err

    assert "its namespace NT is also the namespace of the module notes-process" in refused("a")
    free = NOTES_YAML.replace("namespace: NT", "namespace: OT")
    assert "its meta-rule rr-NT-001 is also a meta-rule of the module notes-process" in refused("b", free)
    part = "# part\n\n## 4. Slash-command entry points\n\n- `/create-item` — another way.\n"
    own = {"rules-of-rules.module.md": "# other\n\n## 1. `rr-OT-001` Memos\n\nMemos.\n"}
    said = refused("c", free, {**own, "code-of-conduct.module.md": part})
    assert "its command /create-item is also a command of the module example-process" in said


def test_one_module_is_upgraded_and_the_other_left_alone(tmp_path, capsys):
    project, root = _two(tmp_path)
    kernel = _release(tmp_path, (root / "version.txt").read_text(encoding="utf-8").strip())
    example = modules.tree_hash(root / "modules" / "example-process")
    newer = tmp_path / "newer" / "notes-process"
    shutil.copytree(tmp_path / "notes-process", newer)
    write(newer / "version.txt", "1.1.0\n")
    write(newer / "module.yaml", NOTES_YAML.replace("version: 1.0.0", "version: 1.1.0"))
    write(newer / "guidance.md", "# Guidance\n")
    args = ["--project", str(project), "module", "upgrade", "notes-process", str(newer), "--kernel", str(kernel)]
    assert main(args) == 0
    records = {e["id"]: e for e in modules.read_record(root)}
    assert records["notes-process"]["version"] == "1.1.0" and records["example-process"]["sha256"] == example
    assert modules.tree_hash(root / "modules" / "example-process") == example
    assert [f.state for f in modules.verify(root)] == ["ok", "ok"]
    coc = (root / "CODE-OF-CONDUCT.md").read_text(encoding="utf-8")
    assert "### From module example-process" in coc and "### From module notes-process" in coc
    assert _errors(project) == []
    # a module that is not installed is not synced in
    stranger = notes_module(tmp_path / "x", NOTES_YAML.replace("id: notes-process", "id: stranger"))
    capsys.readouterr()
    sync = ["--project", str(project), "sync", "plan", "--kernel", str(kernel), "--base-kernel", str(kernel)]
    assert main([*sync, "--module", str(stranger)]) == 1
    assert "stranger is not installed here (installed: example-process, notes-process)" in capsys.readouterr().err


def test_a_kernel_sync_recomposes_with_every_module(tmp_path):
    project, root = _two(tmp_path)
    base = _release(tmp_path, (root / "version.txt").read_text(encoding="utf-8").strip())
    new = _release(tmp_path, "9.9.9")
    rod = new / "rules-of-development.template.md"
    rod.write_text(rod.read_text(encoding="utf-8") + "\n<!-- a change in 9.9.9 -->\n", encoding="utf-8")
    args = ["--project", str(project), "sync", "apply", "--kernel", str(new), "--base-kernel", str(base)]
    assert main(args) == 0
    coc = (root / "CODE-OF-CONDUCT.md").read_text(encoding="utf-8")
    assert "a change in 9.9.9" in coc
    assert coc.index("### From module example-process") < coc.index("### From module notes-process")
    assert [f.state for f in modules.verify(root)] == ["ok", "ok"]
    assert main([*args[:3], "plan", *args[4:]]) == 0


def test_recompose_by_hand_keeps_every_modules_part(tmp_path):
    """`catalyst recompose` names one module's old and new directories; the
    modules installed beside it stay in the composed documents."""
    project, root = _two(tmp_path)
    notes = root / "modules" / "notes-process"
    newer = tmp_path / "newer" / "notes-process"
    shutil.copytree(notes, newer)
    write(newer / "rules-of-rules.module.md", "# notes meta-rules\n\n## 1. `rr-NT-001` Notes\n\nNotes are brief.\n")
    args = ["--project", str(project), "recompose", "--base-kernel", str(KERNEL), "--kernel", str(KERNEL)]
    assert main([*args, "--base-module", str(notes), "--module-dir", str(newer)]) == 0
    handbook = (root / "rules" / "Rules-of-Rules.md").read_text(encoding="utf-8")
    assert "Notes are brief." in handbook and "### From module example-process" in handbook
    assert "Items are items." in handbook
