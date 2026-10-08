# Migration 0.47.0: verbs replace procedures

> Apply this migration when synchronizing a deployment whose `version.txt`
> is being advanced past `0.46.x` to `0.47.0` or later. See `SYNCHRONIZE.md`
> for the full synchronization procedure. Never re-run on a later sync once
> applied.

Until `0.46.x` an agent carried out `/list`, `/user-list`, `/journal`,
`/status`, `/user-*`, `/role-*`, `/freeze` and `/migrate-definition` by
reading and editing files as their procedures described. From `0.47.0` the
CLI does the mechanical half (roadmap R2 W1–W3) and those procedures say
which verb to run.

## What changed

1. **Read-only views:** `catalyst list`, `view`, `backlog`, `journal show`.
2. **Writing verbs:** `catalyst new`, `status set`, `link` — the next ID, the
   latest template filled and signed, references checked, back-references
   kept, indexes regenerated, one journal entry.
3. **Administration:** `catalyst user add|remove|modify|assign-role`,
   `role add|modify`, `freeze|unfreeze`, `definition migrate`.
4. **`init` asks less** (0.46.1): `--user` from `git config user.name`,
   `--commands-dir` from `--agent`.

No layout change.

## Steps for every deployment

1. **Re-vendor the CLI.** Replace `.criterion/bin/catalyst.pyz` with the
   release's (the procedures now call verbs only this CLI has).
2. **Recompose:** `catalyst recompose` merges the rewritten §4 procedures
   into the deployed `CODE-OF-CONDUCT.md`. Command files need no change:
   they read their spec with `catalyst spec`.
3. **Version.** Set `.criterion/version.txt` and the pointer's
   `kernel_version`.
4. **Journal and check.** One `catalyst journal append --command
   /sync-framework --action sync --artifact "kernel 0.47.0" --file …` entry,
   then `catalyst check`.

## Rollback

Restore the previous CLI and recompose back to the previous kernel.
