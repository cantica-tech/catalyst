# Migration: `Taskfile.common.yml` moves into `.criterion/`, dispatch becomes agent-generic

> Target version: `0.19.0` — this is the migration that produces the
> shape `0.19.0` introduced. Triggered by `SYNCHRONIZE.md`'s
> "Version-specific one-time migrations" (`From 0.18.0`). Applies once,
> the first time a deployment's `version.txt` advances past `0.18.0` to
> `0.19.0` or later. Never re-run on a later sync once applied. Only a
> deployment that ran `/sync-framework` or was first instantiated while
> on exactly `0.18.0` has the old shape at all — anything older simply
> gets the new shape fresh on its next sync, no migration needed.

## What changed

`0.18.0` introduced `Taskfile.common.yml` deployed at the target
project's own root — inconsistent with INV-6 ("the deployment's real
working copy... never inside the developed project's own tree"), since
this file is generated/refreshed framework machinery, not product code,
the same way `rules/`, the development-artifact folders, etc. already
live in `.criterion/` rather than the project tree. (`.claude/commands/*.md`
stays project-root — that's forced by Claude Code's own fixed discovery
path, an external constraint this file has none of.)

At the same time, every task's dispatch hardcoded `{{.CLAUDE}} -p
"/command {{.CLI_ARGS}}"`, even though catalyst is meant to be
agent-agnostic — the `*.catalyst` pointer's own `"agent"` field already
exists for exactly this.

| Old | New |
|---|---|
| `Taskfile.common.yml` at the target project's own root, committed | `Taskfile.common.yml` inside `.criterion/` (agent-owned space), not committed to the product's own repo |
| Every task: `{{.CLAUDE}} -p "/name {{.CLI_ARGS}}"`, `vars: {CLAUDE: '{{.CLAUDE_BIN \| default "claude"}}'}` inside `Taskfile.common.yml` itself | Every task: `{{.AGENT_CMD}} "/name {{.CLI_ARGS}}"`, with no `vars:` block of its own — `AGENT_CMD` is passed in from the project's root `Taskfile.yml` |
| Root `Taskfile.yml`: `includes: common: {taskfile: ./Taskfile.common.yml, flatten: true}` | Root `Taskfile.yml`: `CRITERION_DIR` copied in as a literal from the `*.catalyst` pointer's `agent-source` field (Task resolves `includes.taskfile` paths before dynamic vars, so this can't be `sh:`-computed); `AGENT_ID`/`AGENT_BIN`/`AGENT_CMD` resolved dynamically from the pointer's `agent` field; `includes: common: {taskfile: '{{.CRITERION_DIR}}/Taskfile.common.yml', flatten: true, vars: {AGENT_CMD: '{{.AGENT_CMD}}'}}` |

## Steps

1. Resolve `.criterion`'s real location for this deployment (the
   `*.catalyst` pointer's `agent-source` field — same lookup
   `find_deploy_root`/`resolveCorpusRoot` already use elsewhere).
2. Copy the current `templates/Taskfile.common.template.yml` into
   `.criterion/Taskfile.common.yml` (not the project root) — this is a
   normal template-refresh copy, the same one `/sync-framework` already
   does for this file, just landing in the new location. If `.criterion`
   is itself a repoed working copy (`repoed: true`), commit this file
   there too, in that backing repository.
3. Remove the project-root `Taskfile.common.yml` from the target
   project's own repository (`git rm`) — it's no longer product-owned
   content.
4. Rewrite the project's own root `Taskfile.yml`: replace the static
   `includes: common: {taskfile: ./Taskfile.common.yml, flatten: true}`
   with the `CRITERION_DIR`/`AGENT_ID`/`AGENT_BIN`/`AGENT_CMD` var block
   and dynamic `includes:` from `INSTANTIATION-GUIDE.md` §1 step 5 (or
   `CLAUDE.md`'s "Taskfiles" entry) — copied verbatim, not
   reinterpreted. Leave every other task in this file (the project's own
   operational tasks) untouched; they're project-owned content this
   migration doesn't touch.
5. If this root `Taskfile.yml` also has its own agent-dispatch task
   outside the common set (e.g. a catalyst-development-only `dogfood`
   task, `Rules-of-Rules.md` §13's documented exception, excluded from
   the shared template) — this is the natural moment to also switch its
   own hardcoded `{{.CLAUDE_BIN \| default "claude"}} -p "..."` to
   `{{.AGENT_CMD}} "..."`, since it's the exact same bug in the same
   file family, even though the migration itself doesn't require it.
6. Verify: `task --list` from the project root shows every common task
   (proves the dynamic `includes:` resolved); running one low-risk task
   (e.g. `task commands`) actually dispatches rather than erroring on a
   missing taskfile.
7. Journal the migration (`action: "update"`, `intent` describing the
   relocation, one entry covering every file actually touched) — never
   rewrite the journal itself (INV-17).
8. Report the result.

Past migration docs and their rows in `migrations.md` describe shapes as
they were named at the time and are not rewritten by this migration.
