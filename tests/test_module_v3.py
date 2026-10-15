"""Module format v3 (module v3 M3, REQ-000025): one `module.yaml` declares
the types; catalyst generates their templates and definitions; the work
cycle runs on it end to end."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from catalyst import generate
from catalyst.__main__ import main
from catalyst.init import init
from catalyst_fixtures import write
from module_loader import load_module, parse_simple_yaml, v3_entity
from test_catalyst_init import KERNEL, request

V3 = """id: case-process
name: Case Process
version: 1.0.0
description: A small v3 module for tests.
grounding_type: rule
format: 3
entities:
  CASE:
    name: Case
    folder: cases
    grounding: required
    grounding_field: Targets
    fields:
      Targets: { kind: ref-list, to: rule, required: true }
      Domain: { kind: ref, to: domain, required: true }
      Tasks: { kind: ref-list, to: TASK }
    states: [Open, Closed]
    closed: [Closed]
    guards:
      Closed:
        - children_closed: Tasks
    sections:
      - Summary: What the case is about.
      - Notes
    definition: >
      A case: one matter handled
      under the rules it targets.
  TASK:
    name: Task
    folder: tasks
    grounding: { inherited_from: Parent }
    fields:
      Parent: { kind: ref, to: CASE, required: true, backref: Tasks }
    states: [todo, done]
    closed: [done]
    guards:
      done:
        - section_written: Verification
    sections:
      - Verification: How the result was confirmed.
    definition: One unit of work on a case.
"""


def v3_module(base: Path) -> Path:
    mod = base / "case-process"
    write(mod / "module.yaml", V3)
    write(mod / "version.txt", "1.0.0\n")
    return mod


def test_the_reader_builds_the_types_a_v2_schema_would():
    data = parse_simple_yaml(V3)
    case = v3_entity("CASE", data["entities"]["CASE"])
    assert [(f.name, f.kind, f.target_type) for f in case.fields] == [
        ("ID", "text", None),
        ("Status", "enum", None),
        ("Targets", "ref-list", "rule"),
        ("Domain", "ref", "domain"),
        ("Tasks", "ref-list", "TASK"),
    ]
    assert case.workflow.initial == "Open" and case.workflow.closed_states == ["Closed"]
    assert case.workflow.guards == {"Closed": [("children_closed", "Tasks")]}
    assert case.sections == [("Summary", "What the case is about."), ("Notes", "")]
    assert case.definition == "A case: one matter handled under the rules it targets."
    task = v3_entity("TASK", data["entities"]["TASK"])
    assert (task.grounding, task.grounding_field) == ("inherited", "Parent")
    assert next(f for f in task.fields if f.name == "Parent").backref == "Tasks"


def test_init_generates_templates_and_definitions_and_the_cycle_runs(tmp_path, monkeypatch, capsys):
    req = request(tmp_path, module_id="case-process", module=v3_module(tmp_path / "mods"))
    init(req)
    root, mod = req.at, req.module
    assert root is not None and mod is not None
    manifest = load_module(module_dir=mod)
    assert manifest is not None and manifest.entity_types["CASE"].generated
    template = (root / "cases" / "templates" / "TEMPLATE-CASE-v1.md").read_text(encoding="utf-8")
    assert "| **Status** | Open |" in template and "## Summary\n\nWhat the case is about." in template
    assert "| **Tasks** | *(none yet)* |" in template
    assert "one matter handled under the rules it targets" in (root / "definitions" / "case.md").read_text(
        encoding="utf-8"
    )
    write(root / "rules" / "domains" / "br-CORE-core.md", "# `CORE` — core\n")
    with (root / "rules" / "domains" / "domains.md").open("a", encoding="utf-8") as fh:
        fh.write("| [`CORE`](br-CORE-core.md) | rules/business-rules.md | 2026-10-11 |\n")
    monkeypatch.chdir(req.project)
    capsys.readouterr()
    assert main(["id", "next-rule", "br", "CORE", "--as", "ada"]) == 0
    rule = capsys.readouterr().out.strip().splitlines()[-1]
    with (root / "rules" / "business-rules.md").open("a", encoding="utf-8") as fh:
        fh.write(f"\n### `{rule}` Cases are handled\n\n✅ working.\n")
    with (root / "rules" / "rules.md").open("a", encoding="utf-8") as fh:
        fh.write(f"- `{rule}` — Cases are handled\n")
    assert (
        main(
            [
                "new",
                "CASE",
                "--title",
                "First",
                "--field",
                f"Targets={rule}",
                "--field",
                "Domain=CORE",
                "--as",
                "ada",
                "--json",
            ]
        )
        == 0
    )
    case = json.loads(capsys.readouterr().out)["id"]
    assert main(["new", "TASK", "--title", "Do it", "--field", f"Parent={case}", "--as", "ada", "--json"]) == 0
    task = json.loads(capsys.readouterr().out)["id"]
    assert main(["status", "set", case, "Closed", "--as", "ada"]) == 1  # the task is open
    assert main(["status", "set", task, "done", "--as", "ada"]) == 1  # its Verification is the template's
    task_file = next((root / "tasks").glob("TASK-*.md"))
    task_file.write_text(
        task_file.read_text(encoding="utf-8").replace("How the result was confirmed.", "Ran it."), encoding="utf-8"
    )
    assert (
        main(
            [
                "journal",
                "append",
                "--command",
                "/x",
                "--action",
                "update",
                "--artifact",
                task,
                "--intent",
                "verified",
                "--file",
                str(task_file),
                "--as",
                "ada",
            ]
        )
        == 0
    )
    assert main(["status", "set", task, "done", "--as", "ada"]) == 0
    assert main(["status", "set", case, "Closed", "--as", "ada"]) == 0
    capsys.readouterr()
    assert main(["check"]) == 0, capsys.readouterr().out


def test_a_shipped_template_still_wins(tmp_path):
    mod = v3_module(tmp_path / "mods")
    write(mod / "templates" / "case.template.md", "# `CASE-NNNNNN` — {{title}}\n\nHand-written.\n")
    write(
        mod / "module.yaml",
        V3 + "templates:\n  - entity_type: CASE\n    template_path: templates/case.template.md\n",
    )
    req = request(tmp_path, module_id="case-process", module=mod)
    init(req)
    assert req.at is not None
    assert "Hand-written." in (req.at / "cases" / "templates" / "TEMPLATE-CASE-v1.md").read_text(encoding="utf-8")


def test_a_generated_type_s_shipped_index_template_is_its_index_not_its_item(tmp_path):
    mod = v3_module(tmp_path / "mods")
    write(mod / "templates" / "cases.template.md", "# Cases index\n\n| ID | Title | Status |\n|---|---|---|\n")
    write(
        mod / "module.yaml",
        V3 + "templates:\n  - entity_type: CASE\n    template_path: templates/cases.template.md\n",
    )
    req = request(tmp_path, module_id="case-process", module=mod)
    init(req)
    assert req.at is not None
    item = (req.at / "cases" / "templates" / "TEMPLATE-CASE-v1.md").read_text(encoding="utf-8")
    assert "| **ID** |" in item and "## Summary" in item
    assert (req.at / "cases" / "cases.md").read_text(encoding="utf-8").startswith("# Cases index")


def test_generated_texts_name_every_field_and_state():
    task = v3_entity("TASK", parse_simple_yaml(V3)["entities"]["TASK"])
    assert generate.type_slug(task) == "task"
    assert "| **Parent** | *(none yet)* |" in generate.template(task)
    assert "States: `todo`, `done`; closed: `done`." in generate.definition(task)


def test_each_v3_type_gets_a_create_command_in_the_catalogue_and_the_taskfile(tmp_path, monkeypatch, capsys):
    req = request(tmp_path, module_id="case-process", module=v3_module(tmp_path / "mods"))
    init(req)
    assert req.at is not None
    monkeypatch.chdir(req.project)
    capsys.readouterr()
    assert main(["spec", "create-case"]) == 0
    spec = capsys.readouterr().out
    assert "catalyst new CASE --title" in spec and "--field Targets=<IDs>" in spec
    assert "entering `Closed` is guarded" in spec
    assert "catalyst new TASK" not in spec  # one part of `/create`, not every type's (ADR-021)
    assert main(["spec", "create", "case"]) == 0
    assert capsys.readouterr().out.replace("/create-case (alias of /create)", "") == spec.replace(
        "/create-case (alias of /create)", ""
    )
    assert main(["spec", "create"]) == 0
    whole = capsys.readouterr().out
    assert "`/create case <title>`" in whole and "`/create task <title>`" in whole and "catalyst new CASE" not in whole
    taskfile = (req.at / "Taskfile.common.yml").read_text(encoding="utf-8")
    assert "\n  create:\n" in taskfile and "create-case:" not in taskfile and "create-task:" not in taskfile
    parity = subprocess.run(
        ["python3", str(KERNEL.parent.parent / "scripts" / "check_command_parity.py"), "--require"],
        cwd=req.project,
        capture_output=True,
        text=True,
        check=False,
        env={**__import__("os").environ, "PYTHONPATH": str(KERNEL.parent.parent / "scripts")},
    )
    assert parity.returncode == 0, parity.stdout + parity.stderr


def test_a_catalogue_entry_with_arguments_is_the_type_s_own_command_and_rows_get_none(tmp_path):
    from catalyst.compose import generated_commands

    mod = v3_module(tmp_path / "mods")
    write(
        mod / "module.yaml",
        V3
        + "  ITEM:\n    name: Item\n    folder: items\n    grounding: none\n    storage: rows\n"
        + "    states: [new, done]\n    closed: [done]\n",
    )
    names = lambda existing: [e.id_prefix for e in generated_commands(mod, existing)]  # noqa: E731
    assert names("") == ["CASE", "TASK"]
    assert names("- `/create-task <CASE-id>` — create a task.") == ["CASE"]
    assert names("When the user enters `/create-case: ...`") == ["TASK"]
    assert names("- `/create-tasks` — something else.") == ["CASE", "TASK"]
