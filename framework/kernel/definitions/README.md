# Entity definitions

This folder holds one short, versioned prose definition per catalyst entity
type — what the type *is* and what it's for, distinct from the
`templates/*.template.md` files (which define an artifact's *fields and
shape*, not its meaning). Deployed once into a project at
`.criterion/definitions/<type>.md` and then left alone (`INVARIANTS.md`
INV-23): see `INSTANTIATION-GUIDE.md` §1 for the deploy step and
`SYNCHRONIZE.md` for the freeze rule.

## Layout

```
definitions/
  <type>/
    DEFINITION-<TYPE>-v1.md
    DEFINITION-<TYPE>-v2.md   # once the definition is revised
```

One subfolder per entity type, one file per version. This mirrors
`INVARIANTS.md` INV-20's existing `TEMPLATE-<TYPE>-vN.md` convention, applied
to definitions instead of instance templates.

## Versioning rule

- **Files are never edited once superseded.** A definition file, once a
  newer version exists for that type, is permanent history — fix a typo or
  reword the description by adding `DEFINITION-<TYPE>-v(N+1).md` alongside
  the old one, never by changing v1 (or vN) in place.
- **Numbering starts at 1** and increases by exactly one per revision, per
  type — independent of this repository's own root `version.txt` (the
  kernel version).
- **A deployed definition is frozen at whatever version it was deployed
  with.** `/sync-framework` only ever *creates* a missing
  `.criterion/definitions/<type>.md` (for an entity type introduced after
  the project's last sync) — it never overwrites one that's already
  present, no matter how far the framework's own copy has moved on. The
  only sanctioned way to move a deployed definition forward is the explicit
  `/migrate-definition <entity-type> <version>` command, and only to a
  version number that actually exists in this folder.

## Entity types covered

`entity` (base entity definition extended by all other entity definitions),
`rule`, `domain`, `user`, `role`, `reconciliation`, `meta-tag`, `journal`,
`ledger`, `slash-command`, `templates-catalog`, `workflow` — every real,
deployed kernel entity type. The active process module ships the
definitions of its own entity types in its `definitions/` folder, with the
same layout and freeze rule (`MODULE-SPECIFICATION.md` §6.3).
(`section.template.md` under `templates/` is vestigial and unused — it
has no definition here.)
