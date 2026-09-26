# Migration: add `RECON-` reconciliation entity (INV-21)

> Target version: `0.15.0` — this is the migration that produces the
> shape `0.15.0` introduces. Triggered by `SYNCHRONIZE.md`'s
> "Version-specific one-time migrations" (`From 0.14.0`). Applies once,
> the first time a deployment's `version.txt` advances past `0.14.0` to
> `0.15.0` or later, to any project that predates `reconciliations/`.
> Never re-run on a later sync once applied.

## What changed

A new top-level, non-rule-linked artifact type: `RECON-NNNNNN`
(`reconciliations/`, full INV-20 template treatment), the durable
record of two entity versions that `/criterion push`'s merge step
(INV-18) couldn't cleanly reconcile — a git-level conflict, a
vetting-flagged semantic clash, or a rights-mismatch against
`IAM/roles/roles.json` (INV-16's advisory role check) — or a manually
opened one. Never itself work, same carve-out as `WORKFLOW-`: no
`Targets` rule field, chains sideways via an `Entity` field instead.
Resolved via the new `/reconcile <id> accept|accept-with-edits|reject`
command. Full spec: `rules-of-rules.template.md` §16 (INV-21).

`rr-META-013`/INV-18's own merge-conflict step is also revised: an
irreconcilable conflict now opens a `RECON-` instead of stopping at an
ephemeral sub-agent proposal with nothing durable to show for it.

## Preconditions

- Clean git working tree (or an explicit journal checkpoint) before
  starting — every step here is additive (new files/directory only),
  never a delete or a content change to any existing artifact, so a
  clean starting point makes this trivially revertible.
- Resolve the deployment root the normal way (`<app-name>.catalyst`'s
  `agent-source`, or the in-project fallback) before any file operation.

## Steps

1. **`reconciliations/`**: create it (top-level, sibling to the active
   module's root-level artifact folders). Add `reconciliations/templates/`
   (`TEMPLATE-RECONCILIATION-v1.md` from
   `templates/reconciliation.template.md`, `templates-reconciliation.md`
   seeded with a `v1` row — today's date, "initial version" — and its
   own `README.md`). Write `reconciliations/README.md` and an empty
   `reconciliations/reconciliations.md` index (no `RECON-` yet on an
   existing deployment just migrating up — nothing to backfill).
2. **`/reconcile` command**: add `.claude/commands/reconcile.md` from
   `templates/slash-command.template.md`'s shape, same as any other
   deployed command.
3. **Roles**: add `/reconcile` to whichever role(s) this deployment's
   `IAM/roles/roles.json` maps `/criterion push`'s unrestricted-merge
   privilege to (the framework default template puts both on `Admin`).
   Advisory only (INV-16) — this doesn't hard-gate anything, it just
   keeps the role mapping honest.
4. **Re-sync governing docs**: refresh the deployed `CODE-OF-CONDUCT.md`
   and `rules/Rules-of-Rules.md` against their (now-updated) source
   templates, the same way any other `/sync-framework` pass would — in
   particular §15's "Where every artifact type actually sits" list
   (new `reconciliations/` bullet) and §13's merge-conflict step
   (rights-mismatch folded in as a third trigger kind).
5. **Journal**: append exactly one entry for this migration (`action:
   "migrate"`, `intent` describing the new entity type and the §13
   revision, `files` covering every touched/created path by content
   hash) — per `Rules-of-Rules.md` §12.
6. **Version**: update the deployment's own `version.txt` to `0.15.0`
   (or later, if synchronizing further than this one migration in the
   same run).

## Rollback

Every step above only adds files or a new directory, plus edits to the
governing docs' own prose (§15's list, §13's merge step) — nothing
destructive, no renames, no content change to any existing `RECON-`-
unrelated artifact (there are none pre-migration by definition). The
clean pre-migration git state (or the journal checkpoint from step 5's
`before` hashes) is enough to fully revert if something goes wrong
partway through.
