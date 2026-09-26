# Migration: `WORKFLOW-` moves from plugin-territory to core (INV-24)

> Target version: `0.23.0` — this is the migration that produces the
> shape `0.23.0` introduces. Triggered by `SYNCHRONIZE.md`'s
> "Version-specific one-time migrations" (`From 0.22.0`). Applies once,
> the first time a deployment's `version.txt` advances past `0.22.0` to
> `0.23.0` or later. Never re-run on a later sync once applied.

## What changed

The mirror image of `migrations/0.16.0/work-items-to-plugin.md` — applied
to just the one type it originally moved out, in reverse. `WORKFLOW-NNNNNN`
(a process-definition document, never itself work) is no longer part of
the plugin-territory `work-items/` schema (`Rules-of-Rules.md` §8). It's
core now: its own always-present top-level `workflows/` folder, full
INV-20 treatment, no plugin required (`Rules-of-Rules.md` §19,
`INVARIANTS.md` INV-24). `RECON-` reconciliation cases may optionally
name one (a new `Workflow` field, `INVARIANTS.md` INV-21) to guide their
resolution.

**No deployment has ever had `work-items/workflows/` populated** — no
concrete project-management plugin has ever existed to create one — so
this migration is pure addition, never a data-migration case.

## Steps

1. Create `workflows/` if it doesn't already exist: `templates/`
   (`README.md`, `templates-workflow.md` seeded with a `v1` row,
   `TEMPLATE-WORKFLOW-v1.md` copied from this framework's
   `templates/workflow.template.md`), the folder's own `README.md`, and
   an empty `workflows.md` index (empty is fine, same as reconciliations
   on a fresh deployment).
2. Create `definitions/workflow.md` if it doesn't already exist, from
   this framework's current latest `definitions/workflow/
   DEFINITION-WORKFLOW-vN.md` (INV-23's "create if missing" logic,
   applied to a type introduced after the project's last sync).
3. **Re-sync governing docs**: refresh the deployed `CODE-OF-CONDUCT.md`
   and `rules/Rules-of-Rules.md` against their updated source templates,
   the same way any other `/sync-framework` pass would — in particular
   §15's "Where every artifact type actually sits" (adds `workflows/`),
   §8 (drops `WORKFLOW-` from the plugin schema), the new §19 (workflow
   entity), and §16's new optional `Workflow` field on reconciliation.
4. If this deployment happens to have an activated project-management
   plugin with its own `work-items/workflows/` content (only possible if
   a concrete plugin was built and populated one since this migration
   was written — none existed at the time it was authored): confirm
   with the user before migrating any real `WORKFLOW-` instances into
   the new core `workflows/` location, rather than silently moving them.
5. Journal (`action: "create"`, `intent` describing the new core type,
   `files` covering every created path by content hash) — never rewrite
   the journal itself (INV-17).
6. Update the deployment's own `version.txt` to `0.23.0` (or later, if
   synchronizing further than this one migration in the same run).

## Rollback

Steps 1-3 are pure additions (new folder, new file, refreshed governing
docs) — safe to simply delete `workflows/` and `definitions/workflow.md`
and revert the governing-doc refresh if this needs undoing, since
nothing pre-existing was touched. Step 4 only applies in the
(currently impossible) case of a real plugin having populated
`work-items/workflows/` — treat any such move with the same
confirmation tier as any other hard-to-reverse action.
