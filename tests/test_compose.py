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
    base, ours = _as_generated("CODE-OF-CONDUCT.md", fresh, deployed)
    assert base == deployed and ours == deployed  # the merge then takes the new entry


def test_the_taskfile_has_one_task_per_section_4_command(tmp_path):
    import re

    from catalyst import compose, spec
    from catalyst.modules import command_names
    from test_catalyst_task import KERNEL, _params

    mod = tmp_path / "catalyst-notes"
    mod.mkdir()
    (mod / "code-of-conduct.module.md").write_text(
        "# Notes\n\n## 4. Slash-command entry points\n\n"
        "- `/create note <title>` (`/create-note`) — a note.\n"
        "- `/digest [<since>]` (`/digest-all`) — summarise the notes.\n",
        encoding="utf-8",
    )
    (mod / "Taskfile.module.yml").write_text("tasks:\n  stale-task:\n    cmds: []\n", encoding="utf-8")  # not read
    text = compose.taskfile(KERNEL, mod, _params())
    commands = list(spec.parse(compose.code_of_conduct(KERNEL, mod, _params())).bullets)
    tasks = re.findall(r"^  ([a-z-]+):\n", text, re.M)
    assert tasks == [*commands, "catalyst"] and "digest" in tasks and "stale-task" not in tasks
    assert 'desc: "summarise the notes"' in text and '"/digest {{.CLI_ARGS}}"' in text
    assert command_names(mod) == {"create-note", "digest", "digest-all"}  # a part brings its alias, not /create
