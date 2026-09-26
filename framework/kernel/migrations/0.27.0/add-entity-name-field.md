# Migration: `Name` field in development entities

> Target version: `0.27.0` — this is the migration that produces the
> shape `0.27.0` introduces. Triggered by `SYNCHRONIZE.md`'s
> "Version-specific one-time migrations" (`From 0.26.0`). Applies once,
> the first time a deployment's `version.txt` advances past `0.26.0` to
> `0.27.0` or later. Never re-run on a later sync once applied.

## What changed

- Every entity type — the kernel's (`reconciliation`, `workflow`,
  `domain`, `rule`, `entity`) and the active module's — carries an explicit `Name` field summarizing the entity's purpose,
  extending the base `entity` definition (`definitions/entity/DEFINITION-ENTITY-v1.md`).
- For markdown artifact files with metadata field tables (`RECON-`,
  `WORKFLOW-`, and every active-module artifact type), a `**Name**` row is
  present in the field table.
- For `domain` files, a `**Name:**` metadata line is present.
- `Rules-of-Rules.md` §3 is updated to enforce the `Name` field requirement across all rules and development entities.

## Preconditions

- Clean git working tree (or an explicit journal checkpoint).
- Resolve the deployment root the normal way.

## Steps

1. **Templates & Definitions**: Copy updated `templates/*.template.md` and ensure `.criterion/definitions/entity.md` is created/seeded if not already present.
2. **Rules of Rules**: Update `.criterion/rules/Rules-of-Rules.md` §3 (Name format) to include the entity `Name` field mandate.
3. **Existing Dev Artifacts**: For existing files in `reconciliations/`,
   `workflows/`, `rules/domains/`, and every active-module artifact
   folder, ensure each metadata table or header contains an explicit `Name` field. If missing, populate `Name` from the existing title, slug, or summary of the item.
4. **Module**: apply the active module's migration for this version, if
   any (`MODULE-SPECIFICATION.md` §6.6).
5. **Journal**: Append a journal entry recording the `sync` action for version `0.27.0`.
6. **Version**: Update the deployment's own `version.txt` to `0.27.0`.
7. **Verify**: Run `scripts/check_deployment.py` to ensure deployment validity.
