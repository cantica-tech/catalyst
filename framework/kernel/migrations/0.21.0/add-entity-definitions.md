# Migration: entity definitions

> Target version: `0.21.0` — this is the migration that produces the shape
> `0.21.0` introduced. Triggered by `SYNCHRONIZE.md`'s "Version-specific
> one-time migrations" (`From 0.20.0`). Applies once, the first time a
> deployment's `version.txt` advances past `0.20.0` to `0.21.0` or later.
> Never re-run on a later sync once applied.

## What changed

Every real entity type now has a short, versioned prose definition
(`INVARIANTS.md` INV-23, `framework/kernel/definitions/README.md`)
explaining what it is and what it's for — distinct from a `templates/`
file's field-and-shape definition. A deployed project predating this
version has no `definitions/` folder at all.

## Steps

1. Create `.criterion/definitions/` if it doesn't already exist.
2. For each real entity type — the kernel's (`rule`, `domain`, `user`,
   `role`, `reconciliation`, `meta-tag`, `journal`, `ledger`,
   `slash-command`, `templates-catalog`) and the active module's
   (`MODULE-SPECIFICATION.md` §6.3) — if
   `.criterion/definitions/<type>.md` does not already exist, create it
   from the current *latest* `definitions/<type>/DEFINITION-<TYPE>-vN.md`
   of this framework or of the active module. This is the exact same "create if missing,
   never overwrite" logic `SYNCHRONIZE.md`'s definitions carve-out already
   describes for ordinary syncs — this migration just runs it once,
   retroactively, for a deployment old enough to have never run it before.
3. Also create `.criterion/definitions/README.md` from
   `framework/kernel/definitions/README.md` if missing.
4. Do not touch any `definitions/<type>.md` that already exists in the
   deployment (shouldn't happen for a first-time migration, but the rule
   is unconditional per INV-23 regardless of how a file came to exist).
5. Journal the migration (`action: "create"`, one entry summarizing the
   new `definitions/` folder) — never rewrite the journal itself
   (INV-17).
6. Report the result.

Past migration docs and their rows in `migrations.md` describe shapes as
they were named at the time and are not rewritten by this migration.
