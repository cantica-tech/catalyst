"""Recomposing what catalyst itself generates (ADR-021)."""

from catalyst.compose import _as_generated

OLD_ENTRY = (
    "- `/create-note` — create a new note (`NT-NNNNNN`) immediately, register it in its index and journal it "
    "(generated from the module's `module.yaml`).\n\n"
    "When the user enters `/create-note: ...`, run `catalyst new NT`.\n"
)
NEW_ENTRY = (
    "- `/create note <title>` (`/create-note`) — create a new note (`NT-NNNNNN`) immediately, register it in its "
    "index and journal it (generated from the module's `module.yaml`).\n\n"
    "When the user enters `/create note: ...` or `/create-note: ...`, run `catalyst new NT`.\n"
)


def test_a_generated_entry_is_based_on_what_the_deployment_holds():
    deployed = "## 4. Commands\n\n- `/own` — a hand-written one.\n\n" + OLD_ENTRY
    fresh = "## 4. Commands\n\n- `/own` — a hand-written one.\n\n" + NEW_ENTRY
    base, ours = _as_generated("CODE-OF-CONDUCT.md", fresh, fresh, deployed)
    assert base == deployed and ours == deployed  # the merge then takes the new entry


def test_a_generated_task_the_new_composition_lacks_leaves_the_deployment():
    task = (
        "\n\n  create-note:\n    dir: '{{.USER_WORKING_DIR}}'\n"
        '    desc: "Create a new note (NT) — generated from module.yaml"\n'
        "    cmds:\n      - '{{.AGENT_CMD}} \"/create-note {{.CLI_ARGS}}\"'"
    )
    deployed = "tasks:\n  create:\n    cmds: []" + task + "\n"
    _, ours = _as_generated("Taskfile.common.yml", "", "tasks:\n  create:\n    cmds: []\n", deployed)
    assert ours == "tasks:\n  create:\n    cmds: []\n"
    _, kept = _as_generated("Taskfile.common.yml", "", "tasks:\n  create-note:\n", deployed)
    assert kept == deployed
