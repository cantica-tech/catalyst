# Catalyst — generic agent entry

You are running catalyst as a **generic tool-using agent**. Load `BOOTSTRAP.md`
from this repository and follow it top to bottom. It is the single source of
truth; this file only records the generic-agent posture.

This path is **untested**: only Claude Code (`CLAUDE.md`) is supported and
tested today. The documents are written to work without Claude Code's
features, and the `catalyst` CLI (`framework/kernel/CLI.md`) runs from any
shell, so its mechanical steps behave the same under any agent — but expect
rough edges, and report them.

Assume nothing beyond repo file read/write. Work through `BOOTSTRAP.md §1` and
pick a fallback for every capability you cannot confirm:
- No parallel sub-agents → run analysis passes sequentially, context-isolated.
- No persistent memory tool → no problem: `<app-name>.catalyst` (project
  root, always tracked) and `.criterion/DEPLOYMENT.md` (inside the
  working copy) are the durable record regardless — read them fresh each
  session instead of relying on a memory-tool cache.
- No slash-command UI → expose the framework commands as named procedures you
  recognize when the user types the same token in plain text.

Install only when the user asks (INV-2): `catalyst init` from the project
root, per `BOOTSTRAP.md` §2, with no `--at` if you have no owned space of your
own (the in-project fallback) and no `--commands-dir`.

Everything else: `BOOTSTRAP.md`.
