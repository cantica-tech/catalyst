#!/usr/bin/env python3
"""Validate Taskfile.common.yml and the active module's commands against
CODE-OF-CONDUCT.md's §4 command list.

§4 is the canonical command set: agents receive it from `catalyst mcp`
(one prompt per §4 command, read at runtime), so no per-agent command file
exists to drift. What can still drift is checked here: the criterion's
`Taskfile.common.yml` (one task per §4 command) and the module manifest
(every command a module registers must be in the composed §4). Both are
resolved via the pointer-file mechanism check_deployment.py implements
(`find_deploy_root`).

Exit 0 = clean (including when no deployment resolves, unless `--require`,
as CI passes), exit 1 = drift found (or nothing to check under `--require`).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from module_loader import load_module

from check_deployment import REQUIRE_FLAG, find_deploy_root, find_project_root

# Taskfile.common.yml utility tasks that are not slash commands: `catalyst`
# passes its arguments to the catalyst CLI (the launcher).
UTILITY_TASKS = {"catalyst"}

SECTION_HEADING_RE = re.compile(r"^## \d+\. ")
SECTION4_RE = re.compile(r"^## 4\. ")
# Only a leading `/name` right after the opening backtick is a real command
# reference — this deliberately excludes indented sub-bullets like
# /catalyzer's `list` / `activate <name> <version>` (no leading slash) and
# any bold prose paragraph mentioning a command name mid-sentence, since
# both are filtered out upstream by the column-0 "- " bullet check below.
COMMAND_TOKEN_RE = re.compile(r"`/([a-z][a-z0-9-]*)")
TASKS_HEADING_RE = re.compile(r"^tasks:\s*$")
TASK_KEY_RE = re.compile(r"^  ([a-z][a-z0-9-]*):")


def extract_section4_commands(coc_text: str) -> set[str] | None:
    """Command names referenced by top-level bullets under CODE-OF-CONDUCT.md's
    '## 4.' heading, up to the next '## N.' heading. Returns None if no
    '## 4.' heading is found at all (reported distinctly from an empty
    section by the caller)."""
    lines = coc_text.splitlines()
    start = end = None
    for i, line in enumerate(lines):
        if SECTION4_RE.match(line):
            start = i
        elif start is not None and SECTION_HEADING_RE.match(line):
            end = i
            break
    if start is None:
        return None

    names: set[str] = set()
    for line in lines[start:end or len(lines)]:
        # Column-0 "- " only: a 2-space-indented sub-bullet (/catalyzer's
        # subcommands) or a bold prose paragraph naming commands mid-sentence
        # (e.g. the work-items-are-plugin-territory callout) must not count.
        if line.startswith("- "):
            names.update(COMMAND_TOKEN_RE.findall(line))
    return names


def extract_taskfile_commands(taskfile_text: str) -> set[str] | None:
    """Top-level task names under Taskfile.common.yml's `tasks:` block.
    Returns None if no `tasks:` block is found at all (reported distinctly
    from an empty block by the caller)."""
    lines = taskfile_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if TASKS_HEADING_RE.match(line):
            start = i
            break
    if start is None:
        return None

    names: set[str] = set()
    for line in lines[start + 1 :]:
        if line.strip() == "":
            continue
        if not line.startswith(" "):
            break
        match = TASK_KEY_RE.match(line)
        if match:
            names.add(match.group(1))
    return names


def check_module_manifest_parity(project_root: Path | None, code_of_conduct: Path) -> list[str]:
    """Every command the project's active module registers (module.yaml
    `commands:`) is in the composed §4. No-op when no module is declared or
    found, or when §4 cannot be read (reported by the Taskfile check)."""
    if project_root is None:
        return []
    module = load_module(project_root)
    if module is None or not module.commands or not code_of_conduct.is_file():
        return []
    coc_names = extract_section4_commands(code_of_conduct.read_text(encoding="utf-8", errors="ignore")) or set()
    return [f"module parity: module '{module.id}' registers /{name} but CODE-OF-CONDUCT.md §4 does not "
            "list it" for name in sorted(set(module.commands) - coc_names)]


def check_taskfile_parity(taskfile: Path, code_of_conduct: Path) -> list[str]:
    if not code_of_conduct.is_file():
        return [f"taskfile parity: {code_of_conduct} is missing"]

    coc_names = extract_section4_commands(
        code_of_conduct.read_text(encoding="utf-8", errors="ignore")
    )
    if coc_names is None:
        return [f"taskfile parity: {code_of_conduct} has no '## 4.' section"]

    if not taskfile.is_file():
        return [f"taskfile parity: {taskfile} is missing"]

    task_names = extract_taskfile_commands(
        taskfile.read_text(encoding="utf-8", errors="ignore")
    )
    if task_names is None:
        return [f"taskfile parity: {taskfile} has no 'tasks:' block"]

    errors: list[str] = []
    for name in sorted(coc_names - task_names):
        errors.append(
            f"taskfile parity: CODE-OF-CONDUCT.md §4 references /{name} but "
            f"{taskfile.name} has no matching task"
        )
    for name in sorted(task_names - coc_names - UTILITY_TASKS):
        errors.append(
            f"taskfile parity: {taskfile.name} has a '{name}' task but it is "
            f"not referenced in CODE-OF-CONDUCT.md §4"
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    """`--require` (CI): no deployment to compare with is a failure, not a
    skip, so the gate can never pass by checking nothing."""
    argv = list(argv or [])
    unknown = [a for a in argv if a != REQUIRE_FLAG]
    if unknown:
        print(f"usage: check_command_parity.py [{REQUIRE_FLAG}] (unknown: {' '.join(unknown)})")
        return 2
    root = find_deploy_root(Path.cwd())
    if root is None:
        if REQUIRE_FLAG in argv:
            print("command parity validation FAILED: no *.catalyst pointer with a reachable working "
                  f"copy or .criterion/ found from {Path.cwd()} ({REQUIRE_FLAG})")
            return 1
        print("no *.catalyst pointer or .criterion/ found; skipping command "
              "parity validation")
        return 0

    # Taskfile.common.yml lives inside the resolved deployment root (INV-6),
    # never the project tree.
    coc = root / "CODE-OF-CONDUCT.md"
    errors = check_taskfile_parity(root / "Taskfile.common.yml", coc)
    errors += check_module_manifest_parity(find_project_root(Path.cwd()), coc)

    if errors:
        print(f"command parity validation FAILED ({len(errors)} issue(s)):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("command parity validation PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
