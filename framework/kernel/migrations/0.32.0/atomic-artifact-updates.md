# Migration: atomic, real-time artifact updates

> Target version: `0.32.0` — this is the migration that produces the
> shape `0.32.0` introduces. Triggered by `SYNCHRONIZE.md`'s
> "Version-specific one-time migrations" (`From 0.31.0`). Applies once,
> the first time a deployment's `version.txt` advances past `0.31.0` to
> `0.32.0` or later. Never re-run on a later sync once applied.

## What changed

New behavioural meta-rule (`Rules-of-Rules.md` rr-META-023,
`INVARIANTS.md` INV-29): every catalyst artifact — a development
artifact's own record, a `Status` field, a journal entry — is updated
**as the work it describes actually happens**, at the smallest atomic
unit practical, not reconstructed retroactively in one batch after the
fact. One active-module entity's own definition already said this
narrowly for its opening; this generalizes the same posture to every
artifact update, by the agent or by a user narrating their own manual
work.

Delayed, batched updating remains permitted, but only when explicitly
stated **before** the work begins — never a silent default chosen for
convenience after work is already underway or done.

Purely behavioural — no artifact's fields, shape, or existing content
change. Nothing here to retroactively backfill.

| Old | New |
|---|---|
| Real-time, atomic updating was only explicitly required for one entity type's own opening. | Generalized to every artifact update (development artifacts, `Status` fields, journal entries), with an explicit "must be stated before work starts" exception for delayed/batched updating. |

## Steps

1. **Re-sync `CODE-OF-CONDUCT.md`/`Rules-of-Rules.md`** (the ordinary
   template-refresh path, composed with the active module's
   contributions) so the deployed copies carry the new rr-META-023
   section and its INV-29 cross-references.
2. **No retroactive changes to any existing artifact.** This is a
   behavioural rule governing how future updates happen, not a schema
   or field change — no existing artifact file needs editing because of
   this migration.
3. Journal the migration (`action: "create"`, `intent` describing the
   new behavioural invariant, `files` covering every path actually
   touched by content hash) — never rewrite the journal itself
   (INV-17).
4. Report the result.

## Rollback

Pure documentation addition — safe to revert `Rules-of-Rules.md`/
`INVARIANTS.md`/`CODE-OF-CONDUCT.md` to their prior content if this
needs undoing. Nothing else was touched.

Past migration docs and their rows in `migrations.md` describe shapes as
they were named at the time and are not rewritten by this migration.
