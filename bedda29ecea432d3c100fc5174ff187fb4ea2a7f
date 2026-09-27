# Catalyst — Claude Code entry

You are running catalyst as **Claude Code**. Load `BOOTSTRAP.md` from this
repository and follow it top to bottom. It is the single source of truth; this
file only records what Claude Code adds on top.

Capabilities you have (use them per `BOOTSTRAP.md §1`):
- **Sub-agents:** use `Agent` calls with `run_in_background: true`, launched in
  the same message so they run in parallel, `subagent_type: general-purpose`,
  and `model: opus` for the long reading passes in `ANALYSIS-PLAYBOOK.md`.
- **Persistent memory:** record the deployment target note there.
- **Slash commands:** create one native command file per entry in
  `CODE-OF-CONDUCT.md` §4 (the deployed copy of
  `framework/kernel/rules-of-development.template.md` §4, with the active
  module's `code-of-conduct.module.md` §4 inserted at its end — that's the
  canonical, complete list; never hand-maintain a shortlist elsewhere, it
  drifts out of sync with the real command set). For each command:
  - Path: `.claude/commands/<name>.md`, in the **target project's** root
    — not this framework repository. Every alias a command declares gets
    its own file too.
  - Shape: follow
    `framework/kernel/templates/slash-command.template.md` — minimal
    frontmatter (`description`, `argument-hint` only; don't reach for
    less-certain frontmatter fields without verifying the running Claude
    Code version actually supports them first), with a body that points
    back to the deployed `CODE-OF-CONDUCT.md` §4 as the canonical spec
    rather than duplicating its behavior inline, so the command stays
    correct across a `/sync-framework` without needing its own edit.
  - This is part of the instantiation procedure itself
    (`INSTANTIATION-GUIDE.md` §1 step 5, `INSTANTIATION-CHECKLIST.md`'s
    Discoverability section) — not an optional add-on once everything else
    is deployed.
- **Taskfiles:** deploy
  `framework/kernel/templates/Taskfile.common.template.yml` as
  `Taskfile.common.yml` **inside `.criterion/`** (agent-owned space per
  INV-6 — never the target project's own tree, unlike `.claude/commands/`
  which stays project-root only because Claude Code's own fixed discovery
  path forces it there) — one task per entry in `CODE-OF-CONDUCT.md` §4,
  same canonical-list rule as slash commands (`scripts/
  check_command_parity.py` diffs it the same way). catalyst is
  agent-agnostic, so each task is a thin `{{.AGENT_CMD}} "/<name>
  {{.CLI_ARGS}}"` dispatch, never a hardcoded `claude -p` and never a
  duplicated command behavior inline in the task — `AGENT_CMD` is passed
  in from the project's own root `Taskfile.yml`, resolved from the
  `*.catalyst` pointer's `agent` field. Also ensure the project has its
  own root `Taskfile.yml` pointing the include at `.criterion`'s
  location, copied in from the pointer's `agent-source` field as a
  **literal** var (not `sh:`-computed — Task resolves an
  `includes.taskfile` path before
  dynamic vars are evaluated, so a dynamic value there silently fails;
  confirmed by hand): `includes: common: {taskfile: '{{.CRITERION_DIR}}/
  Taskfile.common.yml', flatten: true, vars: {AGENT_CMD: ...}}` (the
  `flatten` keeps task names bare — `task check-rules`, not
  `task common:check-rules`; see `INSTANTIATION-GUIDE.md` §1 step 5 for
  the exact var block) plus that project's project-specific operations
  (install/lint/test/build/...). Same instantiation-procedure status as
  slash commands above — part of `INSTANTIATION-GUIDE.md` §1 step 5 and
  `INSTANTIATION-CHECKLIST.md`'s Discoverability section, not optional.
- **Hooks:** if `.claude/settings.json` is present, its `SessionStart` hook
  re-injects `INVARIANTS.md` and its `Stop` hook runs the deployment validator —
  the enforcement layer of the anti-drift architecture. You do not need to
  simulate these; the harness runs them.

Everything else: `BOOTSTRAP.md`.
