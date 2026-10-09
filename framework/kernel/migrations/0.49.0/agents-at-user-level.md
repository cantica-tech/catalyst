# Migration 0.49.0: agents wired at user level

> Apply this migration when synchronizing a deployment whose `version.txt`
> is being advanced past `0.48.x` to `0.49.0` or later. See `SYNCHRONIZE.md`
> for the full synchronization procedure. Never re-run on a later sync once
> applied.

Until `0.48.x` `catalyst init` wrote one command file per command of the
composed `CODE-OF-CONDUCT.md` §4 into the project (`.claude/commands/` under
Claude Code), and the install merged catalyst's hooks into the project's
agent settings (`.claude/settings.json`). From `0.49.0` catalyst writes no
file into a project but `catalyst.toml` (INV-6): agents are wired once per
machine, at user level.

## What changed

1. **`catalyst mcp`:** a stdio MCP server. Its prompts are the commands of
   the project's composed §4 (kernel and module, read at runtime); its
   tools are `catalyst` (runs the CLI through the launcher, in the
   project's root, at the project's pinned version) and `command` (a
   command's procedure, for clients without MCP prompts); its instructions
   are the deployment's invariants. Under Claude Code, `/check-rules` is
   `/catalyst:check-rules`.
2. **`catalyst agent install|uninstall|status <agent>`** (`claude-code`,
   `copilot`, `vscode`, `cursor`, `codex`, `gemini`) writes only the
   agent's user-level config: the MCP server and the end-of-turn
   `catalyst hook stop` (plus `catalyst hook start` where the server's
   instructions may not reach the model). `agents/claude-code/plugin` is
   the same wiring as a Claude Code plugin.
3. **`catalyst init`** writes no command files and no hooks; `--commands-dir`
   is gone and `--agent` only records the agent in `catalyst.toml`.
4. **`catalyst sync apply`** retires what older versions wrote: an unedited
   command file in `.claude/commands/` (a released copy, or a generated one
   calling `catalyst spec <name>`) is removed, a locally edited one is
   reported as a conflict and never deleted; catalyst's hooks are removed
   from the project's `.claude/settings.json`, its other settings kept.
5. **Releases** no longer ship `commands/`; a module's text for a command
   is its `code-of-conduct.module.md` §4 entry (`commands[].spec_path` in
   `module.yaml` is optional and unused).

## Steps for every deployment

1. **Wire each machine:** every contributor runs
   `catalyst agent install <agent>` once (`catalyst agent status` checks
   it). Without it, the agent gets no commands and no end-of-turn check.
2. **Synchronize** with `catalyst sync plan|apply --kernel <0.49.0 release>`:
   it retires the project's catalyst command files and hooks. Show the user
   each conflict (an edited command file): keep its local change by moving
   it out of the project, or remove it by hand. Without a sync, remove them
   by hand.
3. **Commit the removal** in the product repository, with the user's
   assent: the deleted command files and the edited `.claude/settings.json`
   (deleted if catalyst's hooks were all it held).
4. **Tools that read `.claude/commands/`** (scripts, CI, docs) read the
   composed `CODE-OF-CONDUCT.md` §4 instead (`catalyst spec`).
5. **Version and journal:** `catalyst sync apply` set the version and
   journaled the sync; `catalyst check`.

## Rollback

Restore the previous CLI and recompose; restore the command files and
hooks from the product repository's history, and
`catalyst agent uninstall <agent>` on each machine.
