# Migrations

One-time migration plans for bringing an existing deployment up to a
kernel version that changed the deployed *shape* — not ordinary
template/rule content updates, which `/sync-framework` already handles
on every run. Each file here is what `SYNCHRONIZE.md`'s "Version-specific
one-time migrations" section (step 10 of its slash-command behavior)
points to, so the detailed procedure lives in one place instead of being
duplicated inline there.

## Naming

`<target-version>/<short-slug>.md` — one directory per version that
introduced a shape change, named for **the version where the migration
is implemented** (the target it brings a deployment up to), not the
version it starts from. A version that changes the shape in more than
one way holds more than one file in its directory.

## Index

See [`migrations.md`](migrations.md) for the full table of kernel
migrations, their from/target versions, and what each one migrates.

## Module migrations

A migration that only reshapes a module's own entity types lives in that
module's repository, under its `migrations/` with its own
`migrations.md` index (`MODULE-SPECIFICATION.md` §6.6), never here.
`/sync-framework` applies the kernel's and the active module's migrations
together, in version order. Where a kernel migration also touched module
entities, it defers to the active module's migration for that version.

## When a migration doesn't apply

A deployment created fresh (via `/project create` or `catalyst init`)
after the "From" version already has the target shape — these plans are
only ever relevant when synchronizing an **older** existing deployment
forward, never for a new install.
