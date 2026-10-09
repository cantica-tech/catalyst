# Catalyst — Claude Code entry

> **Self-governance of this repository is suspended** (owner decision,
> 2026-10-07) while the framework is refactored. Changes to this repository
> are not journaled: do not run `catalyst journal append` for them, and do
> not try to clear the `unjournaled` / `unrecorded-change` errors
> `catalyst check` reports here — they are expected. The Stop hook is
> removed from `.claude/settings.json` for the same reason. Git history and
> commit messages are the record until self-governance is restored.

You are running catalyst as **Claude Code**. Load `BOOTSTRAP.md` from this
repository and follow it top to bottom. It is the single source of truth; this
file only records what Claude Code adds on top.

Installing is always an explicit request (`INVARIANTS.md` INV-2): reading
this repository, or a session in a project that has no `*.catalyst` pointer,
never installs anything. When the user asks, follow `BOOTSTRAP.md` §2; its
mechanical step, under Claude Code, is one command from the target project's
root:

```
python3 <catalyst>/dist/catalyst.pyz init --kernel <catalyst>/framework/kernel \
    --name <name> --module <module-id> --git-username <u> \
    --rule-doc <file>:<prefix> --agent claude-code
```

(from a catalyst checkout, `task catalyst -- --project <target root> init
...` runs the same from source; `task build:cli` builds `dist/catalyst.pyz`).
The criterion goes to `$HOME/.catalyst/projects/<name>/criterion` with its
own runtime, and `catalyst.toml` is the only file added to the project; a
`.criterion` holding only the deployment ledger (`.ledger/`) is moved into
the criterion. Add
`--module-dir <dir>` when the module is not checked out next to the project
or catalyst as `catalyst-<module-id>`, and one `--rule-doc` per rule
document. Then merge `agents/claude-code/settings.template.json` into the
project's `.claude/settings.json` (its hooks), and carry on with the
judgment steps of `BOOTSTRAP.md` §2.

Capabilities you have (use them per `BOOTSTRAP.md §1`):
- **Sub-agents:** use `Agent` calls with `run_in_background: true`, launched in
  the same message so they run in parallel, `subagent_type: general-purpose`,
  and `model: opus` for the long reading passes in `ANALYSIS-PLAYBOOK.md`.
- **Persistent memory:** record the deployment target note there.
- **Slash commands:** one native command file per entry in
  `CODE-OF-CONDUCT.md` §4 (the deployed copy of
  `framework/kernel/rules-of-development.template.md` §4, with the active
  module's `code-of-conduct.module.md` §4 inserted at its end — that's the
  canonical, complete list; never hand-maintain a shortlist elsewhere, it
  drifts out of sync with the real command set). `catalyst init
  --agent claude-code` writes them into `.claude/commands/`: the kernel's from this
  repository's `.claude/commands/` (never `/dogfood`), the module's from its
  `commands/`. For each command:
  - Path: `.claude/commands/<name>.md`, in the **target project's** root
    — not this framework repository. Every alias a command declares gets
    its own file too.
  - Shape: follow
    `framework/kernel/templates/slash-command.template.md` — minimal
    frontmatter (`description`, `argument-hint` only; don't reach for
    less-certain frontmatter fields without verifying the running Claude
    Code version actually supports them first), with a body that reads
    the command's spec with `catalyst spec <name>` (only that command's
    part of the deployed `CODE-OF-CONDUCT.md` §4, the canonical text)
    rather than duplicating its behavior inline, so the command stays
    correct across a `/sync-framework` without needing its own edit.
- **Taskfiles:** `catalyst init` composes `Taskfile.common.yml` **inside
  the criterion** from
  `framework/kernel/templates/Taskfile.common.template.yml` plus the
  module's `Taskfile.module.yml` — one task per entry in
  `CODE-OF-CONDUCT.md` §4, same canonical-list rule as slash commands
  (`scripts/check_command_parity.py` diffs it the same way). Each task is
  a thin `{{.AGENT_CMD}} "/<name> {{.CLI_ARGS}}"` dispatch run from the
  caller's directory. Never create or edit the project's own
  `Taskfile.yml`: `catalyst task <name> -- <args>` runs a common task from
  the project's root, and `catalyst task` lists them.
- **Hooks:** if `.claude/settings.json` is present, its `SessionStart` hook
  re-injects `INVARIANTS.md` and its `Stop` hook runs the deployment validator —
  the enforcement layer of the anti-drift architecture. You do not need to
  simulate these; the harness runs them.

Everything else: `BOOTSTRAP.md`.
