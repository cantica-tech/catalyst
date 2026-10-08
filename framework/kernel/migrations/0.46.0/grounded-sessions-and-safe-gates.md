# Migration 0.46.0: grounded sessions and safe gates

> Apply this migration when synchronizing a deployment whose `version.txt`
> is being advanced past `0.45.x` to `0.46.0` or later. See `SYNCHRONIZE.md`
> for the full synchronization procedure. Never re-run on a later sync once
> applied.

Until `0.45.x` a deployed project's sessions started with no invariants
in context, a crash in the end-of-turn hook let the turn end unchecked, and
the criterion repository's CI ran a checker the pull request under review
could replace. From `0.46.0` these gates hold.

## What changed

1. **Grounded sessions.** `init` copies the kernel's `INVARIANTS.md` (and
   the module's `INVARIANTS.module.md`, when it ships one) into the working
   copy; `catalyst hook start` prints them, registered as the agent's
   session-start hook where the agent supports one (`CLI.md` "Hooks").
2. **Gates fail closed.** `catalyst hook stop` exits `2` on any unexpected
   error, never `1`.
3. **The criterion CI gate runs the base branch's checker**
   (`pull_request_target`, read-only), verified against
   `bin/catalyst.pyz.sha256`, on the pull request checked out as data
   (`CLI.md` "The CI workflow"). `criterion push` refreshes the workflow
   and the hash file catalyst wrote.
4. **Commands.** `/user-*` and `/role-*` journal their writes; roles carry
   `reconciliation` (`/role-add` defaults to `propose`); `/status` refuses
   a `RECON-` case and `/reconcile <id> close` is the only way to close
   one.
5. **CLI hardening.** `--at` takes the `.criterion` directory or its
   parent; a ledger-only `.criterion` is adopted; `id next` reserves under
   a lock; revisions, URLs and branches that look like git options are
   refused; `check` honours `.catalystignore` and nested deployments for
   uncommitted files and ignores OS clutter; `--version` carries the build.

Layout change: `.criterion/INVARIANTS.md` (and `INVARIANTS.module.md`).

## Steps for every deployment

1. **Re-vendor the CLI.** Replace `.criterion/bin/catalyst.pyz` with the
   release's.
2. **Copy the invariants.** The release's `framework/kernel/INVARIANTS.md`
   to `.criterion/INVARIANTS.md`; the active module's
   `INVARIANTS.module.md`, if it has one, to `.criterion/INVARIANTS.module.md`.
3. **Register the session-start hook** where the agent supports one: for
   Claude Code, merge the `SessionStart` entry of
   `agents/claude-code/settings.template.json` into the project's
   `.claude/settings.json` (a product file: commit it with the user's
   assent).
4. **Refresh governing documents and command files**: `catalyst recompose`,
   then rewrite the command files from `CODE-OF-CONDUCT.md` §4 as usual.
5. **Roles.** List every role in `IAM/roles/roles.json` without a
   `reconciliation` field for the user, who sets each level (`full`,
   `propose` or `none`, `Rules-of-Rules.md` §16). Never fill it in
   silently.
6. **Shared deployments.** Nothing to do by hand: the next
   `catalyst criterion push` rewrites `.github/workflows/catalyst.yml` and
   writes `bin/catalyst.pyz.sha256`. The pull request carrying that rewrite
   gets **no check**: its own workflow now triggers on
   `pull_request_target`, which the old base does not define. Run
   `catalyst check` locally before merging it; the run on the shared
   branch after the merge, and every later pull request, are checked.
7. **Version.** Set `.criterion/version.txt` and the pointer's
   `kernel_version`.
8. **Journal and check.** One `catalyst journal append --command
   /sync-framework --action sync --artifact "kernel <version>" --file …`
   entry, then `catalyst check`.

## Rollback

Restore the previous CLI, remove `.criterion/INVARIANTS*.md` and the
session-start hook entry, and restore the previous workflow file in a
shared deployment's criterion repository.
