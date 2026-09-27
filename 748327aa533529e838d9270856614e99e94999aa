# Migration: `IAM/users/`, `IAM/roles/` gain the `templates/` treatment (INV-20)

> Target version: `0.13.0` — this is the migration that produces the
> shape `0.13.0` introduces. Triggered by `SYNCHRONIZE.md`'s
> "Version-specific one-time migrations" (`From 0.12.1`). Applies once,
> the first time a deployment's `version.txt` advances past `0.12.1` to
> `0.13.0` or later, to any project still on the pre-0.13.0 shape where
> `IAM/users/` and `IAM/roles/` have no `templates/` subdirectory.
> Never re-run on a later sync once applied.

## What changed

`0.12.0` (`migrations/0.12.0/uniform-artifact-layout.md`) deliberately
carved `IAM/users/` and `IAM/roles/` out of the uniform `templates/`
treatment: each registry is one JSON array, not a one-file-per-instance
document type, so there was judged to be nothing to version. This
migration reverses that carve-out: both now get the same `templates/`
subdirectory every other artifact type carries (`Rules-of-Rules.md` §15,
`INVARIANTS.md` INV-20) — `README.md`, a `templates-<type>.md` catalog
(Version | File | Timestamp | Notes), and the current
`TEMPLATE-<TYPE>-vN.md`. The versioned file is the registry's *seed
shape* (the array a fresh deployment starts from) rather than a
per-instance document, since `users.json`/`roles.json` remain one JSON
array each — there is exactly one live instance per type, versioned the
same way any other type's template is.

## Preconditions

- Clean git working tree (or an explicit journal checkpoint) before
  starting — every step here is additive (new files only), never a
  delete or a content change to `users.json`/`roles.json` themselves,
  so a clean starting point makes this trivially revertible.
- Resolve the deployment root the normal way (`<app-name>.catalyst`'s
  `agent-source`, or the in-project fallback) before any file operation.

## Steps

1. **`IAM/users/templates/`**: create it. Copy the framework's
   `templates/users.template.json` in as `TEMPLATE-USERS-v1.json`
   (content unchanged — `{"users": []}`). Write `templates-users.md`
   seeded with one `v1` row (today's date, "carried over from the
   pre-0.13.0 layout, where this registry had no `templates/`"). Write
   `IAM/users/templates/README.md`.
2. **`IAM/roles/templates/`**: same treatment. Copy
   `templates/roles.template.json` in as `TEMPLATE-ROLES-v1.json`
   (content unchanged — the default agile-role mapping). Seed
   `templates-roles.md` the same way. Write
   `IAM/roles/templates/README.md`.
3. **Existing registries untouched**: `IAM/users/users.json` and
   `IAM/roles/roles.json` keep their current content exactly — this
   migration adds a seed-shape template alongside them, it does not
   reset or reseed the live registry.
4. **Update the two `README.md` files**: `IAM/users/README.md` and
   `IAM/roles/README.md` currently explain *why* there is no
   `templates/` here — replace that rationale with a pointer to the new
   `templates/` subdirectory, matching the wording pattern every other
   artifact type's `README.md` uses.
5. **Re-sync governing docs**: refresh the deployed `CODE-OF-CONDUCT.md`
   and `rules/Rules-of-Rules.md` against their (now-updated) source
   templates, the same way any other `/sync-framework` pass would — in
   particular §15's "Where every artifact type actually sits" list.
6. **Journal**: append exactly one entry for this migration (`action:
   "migrate"`, `intent` describing the reversal and why, `files`
   covering every touched path by content hash) — per `Rules-of-Rules.md`
   §12.
7. **Version**: update the deployment's own `version.txt` to `0.13.0`
   (or later, if synchronizing further than this one migration in the
   same run).

## Rollback

Every step above only adds files or edits the two `README.md`
explanatory paragraphs — nothing destructive, no renames, no content
change to the live registries. The clean pre-migration git state (or
the journal checkpoint from step 6's `before` hashes) is enough to fully
revert if something goes wrong partway through.
