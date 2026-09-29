# Migration 0.36.0: module-agnostic kernel

> Apply this migration when synchronizing a deployment whose `version.txt`
> is being advanced past `0.35.2` to `0.36.0` or later. See `SYNCHRONIZE.md`
> for the full synchronization procedure. Never re-run on a later sync once
> applied.

The kernel no longer carries any module entity. Everything a process module
owns now comes from the active module and is composed into the deployment
per `MODULE-SPECIFICATION.md` §6; the kernel only ever speaks of "the active
module" and `<entity-type>` (`INVARIANTS.md` INV-30).

## What changed

1. **Kernel entities.** Reconciliation cases (`RECON-`, `reconciliations/`)
   and workflows (`WORKFLOW-`, `workflows/`) are kernel entities. Their ETDs
   live in `framework/kernel/entities/`, next to their kernel templates and
   definitions. Nothing about their deployed shape changes.
2. **Module content leaves the kernel.** The active module's templates,
   definitions, meta-rules, invariants, commands, Taskfile tasks and
   entity-only migrations are no longer shipped in `framework/kernel/`.
   They come from the module's own repository (`templates/`,
   `definitions/`, `rules-of-rules.module.md`, `code-of-conduct.module.md`,
   `INVARIANTS.module.md`, `Taskfile.module.yml`, `migrations/`) and are
   composed per `MODULE-SPECIFICATION.md` §6.1–§6.6.
3. **Stable numbers.** A meta-rule section (`rr-META-NNN`) or invariant
   (`INV-N`) that moved to the module keeps its number; the kernel leaves a
   one-line placeholder in its place and never reuses the number.
4. **Generic chain invariant.** INV-5 now reads: an active-module artifact
   grounds to the module's grounding type (a kernel rule), which belongs to
   a domain.
5. **Composed command list.** The deployed `CODE-OF-CONDUCT.md` §4 is the
   kernel's §4 plus the module's §4; it stays the one canonical list that
   command files and `Taskfile.common.yml` tasks are checked against.
6. **No default module.** The `<app-name>.catalyst` pointer must name its
   module in the `module` field. The fallback `0.33.0` introduced (an
   omitted field meaning the bundled module) is withdrawn.
7. **Entity-only migrations moved.** Kernel migrations that only reshaped
   module entity types (and the inline `From 0.3.1` audit that used to sit
   in `SYNCHRONIZE.md`) moved to the module's `migrations/` with their
   index rows; kernel migrations that also touched module entities now
   defer to the active module's migration for that version.
8. **Rule-document heading.** The quick-index heading every rule document
   carries is now `## Linked Artifacts — Quick Index` (was named after one
   module's defect entity). The active module says which of its artifact
   types it lists there.

## Steps for deployed projects

1. **Pointer.** If `<app-name>.catalyst` has no `module` field, set it to
   the id of the module whose entity types this deployment already uses
   (the one seeded under `.criterion/modules/` by `0.33.0`). If that is
   unclear, stop and ask the user, listing `framework/modules/catalog.md`.
2. **Module.** Seed or refresh `.criterion/modules/<module-id>/` from the
   module's catalogued repository, at the release matching this kernel
   version — the whole module tree, replacing any copy seeded from an older
   bundled layout.
3. **Rules-of-Rules.** Recompose `.criterion/rules/Rules-of-Rules.md` from
   `framework/kernel/rules-of-rules.template.md` plus the module's
   `rules-of-rules.module.md`, appended after the kernel's sections under
   `### From module <module-id>` (§6.1). Keep every rule ID; sections that
   moved to the module now appear in the module block, with the kernel's
   placeholder lines left where they were.
4. **CODE-OF-CONDUCT.** Recompose `.criterion/CODE-OF-CONDUCT.md` §3 and §4
   from `framework/kernel/rules-of-development.template.md` plus the
   `## 3.`/`## 4.` sections of the module's `code-of-conduct.module.md`,
   each inserted at the end of the matching kernel section under
   `### From module <module-id>` (§6.2). Preserve project-local additions
   outside those blocks.
5. **Invariants.** Read the module's `INVARIANTS.module.md` together with
   `INVARIANTS.md` from now on (§6.4); nothing to copy into the deployment
   beyond the seeded module.
6. **Taskfile.** Recompose `.criterion/Taskfile.common.yml` from
   `framework/kernel/templates/Taskfile.common.template.yml` plus the
   module's `Taskfile.module.yml` tasks (§6.5). Every task still maps to one
   entry of the composed §4. The project's own root `Taskfile.yml` is not
   touched.
7. **Command files.** Check `.claude/commands/` (or the agent's fallback,
   `BOOTSTRAP.md` §1) against the composed §4: create any missing file from
   `framework/kernel/templates/slash-command.template.md`; leave existing
   files alone unless their spec changed.
8. **Definitions.** Leave every existing `.criterion/definitions/<type>.md`
   untouched (INV-23). Create one only for a type — kernel or module — that
   has none yet, from the latest `DEFINITION-<TYPE>-vN.md` in
   `framework/kernel/definitions/` or the module's `definitions/` (§6.3).
9. **Module migrations.** Apply the active module's migrations whose "From"
   version is at or above this deployment's pre-sync `version.txt`,
   interleaved with the kernel's in version order (§6.6). A migration this
   deployment already ran when it was still indexed in the kernel is not
   run again.
10. **Rule-document heading.** In every rule document under `rules/`,
   rename the old quick-index heading to `## Linked Artifacts — Quick Index`,
   keeping its entries.
11. **Verify.** Run `scripts/check_deployment.py` and resolve every reported
    issue.
12. **Journal.** Append one entry (`action: "sync"`, `intent`
    describing the recomposition, `files` covering every touched path by
    content hash) — never rewrite the journal itself (INV-17).
13. **Version.** Set `.criterion/version.txt` and the pointer's
    `kernel_version` to `0.36.0`, and record the module id and version in
    `.criterion/DEPLOYMENT.md`.

## Rollback

Steps 1–8 only recompose governing documents, add files, or refresh the
seeded module; no artifact instance is renamed or deleted. The clean
pre-migration git state (or the journal checkpoint from step 11's `before`
hashes) is enough to revert. Module migrations run in step 9 carry their
own rollback notes.
