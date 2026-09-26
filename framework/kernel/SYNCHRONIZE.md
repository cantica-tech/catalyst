# Synchronize Framework With Deployment

This framework must be kept aligned with the deployed project that uses it.
If the deployed framework is missing, outdated, or has an older version than
this framework, synchronize it before continuing with project work.

## Rule

Whenever a project is active, it must check the catalyst framework for
changes, load the latest version into memory, and, if any changes are
present, offer to apply them using this synchronization process.

Synchronization requires exactly one confirmation from the user before it
starts. After that confirmation, all subsequent framework updates for the
files and folders in the deployed framework directory must proceed without
any further authorization from the user. The synchronization process must
apply the changes automatically and repeatedly as needed to keep the
deployed framework aligned.

If the deployed framework does not exist, or if its version is missing or
lower than the current kernel version, apply this synchronization process
immediately.

## Version rule

- Current kernel version: see this repository's own
  `version.txt`.
- The source of truth for the latest kernel version is the `release`
  branch of `git@github.com:oliben67/catalyst.git` (or
  `https://github.com/oliben67/catalyst.git`).
- The deployed framework must have a `version.txt` file.
- If `version.txt` is missing or contains a version lower than this
  framework's own `version.txt`, treat the
  deployment as out of date and synchronize it.

## Slash-command behavior for `/sync-framework`

When the command `/sync-framework [latest|<version>] [--force <scope>]` is entered:

1. If the first argument is `latest`, inspect the `release` branch and resolve
   the newest available tagged release. If a specific version is supplied,
   inspect the `release` branch for the matching tagged release. If that tag
   exists, load that version into memory and use it as the synchronization
   target.
2. If no version argument is provided, synchronize against the currently
   installed local version rather than looking up a remote release.
3. Build a diff between the currently installed deployment and the target
   kernel version before applying changes, and use that diff as the basis
   for the synchronization plan.
4. If the requested version differs from the version currently deployed,
   synchronize the deployment using the already-present deployment state as
   the baseline, preserving any project-local adjustments that are still
   valid.
5. If the requested version is the same as the currently deployed version,
   load that version into memory, discard the old in-memory copy, and perform
   a synchronization against the already-present deployment contents.
6. If a requested version does not exist as a tag, stop and report that the
   requested release is unavailable rather than silently falling back to an
   unrelated version.
7. Before applying any per-item refresh, inspect the project root `.frozen`
   file. If the target item path is listed there, skip it unless the command
   includes `--force <type>`, `--force <item-id>`, or `--force all`.
8. When an item is refreshed successfully, remove its path from `.frozen` so
   the refreshed version is no longer considered frozen.
9. Before the sync is considered complete, normalize the names and markdown
   filenames of any deployed items whose current names are only the bare ID or
   otherwise lack a summary suffix. Rename them to the required format
   **`<id>-<short-summary>`** and their corresponding files to
   **`<id>-<short-summary>.md`** using their existing title/description
   content, then update every index entry, link, and reference that points to
   the old name or old filename. The same normalization is a hard requirement
   for domain files under `rules/domains/`: any file still named only
   `<prefix>-<CODE>.md` (or `<prefix>-<PARENT>.<SUB>.md` for a sub-domain)
   must be renamed to `<prefix>-<CODE>-<short-summary>.md` (or
   `<prefix>-<PARENT>.<SUB>-<short-summary>.md`), using the domain's own
   `Scope` field as the source for the summary, then every reference to the
   old filename updated accordingly.
10. Check `## Version-specific one-time migrations` below — and the
    active module's own `migrations/migrations.md`
    (`MODULE-SPECIFICATION.md` §6.6) — for any entry whose "From" version
    is at or above the project's own `version.txt` value *before* this
    synchronization run started. Run each such entry exactly once, as part
    of this same run, kernel and module entries merged into one sequence in
    version order (a kernel and a module entry with the same target run
    kernel first), reporting flagged items to the user per that entry's
    own steps rather than applying them silently. Do not re-run an entry on
    a project whose pre-sync `version.txt` already reflected a version past
    that entry's "From" version.
11. Never deactivate an already-active plugin as a side effect of applying a
    new kernel version. A plugin stays active across the sync unless its
    entry in the relevant `plugins/<type>/catalog.md` explicitly excludes
    the target kernel version via the `Compatibility` field — a bare `*`,
    or an absent field, is never grounds for deactivation. Only deactivate a
    plugin when that field names a version or range that excludes the
    target version, and report which plugin was deactivated and why.
12. Never treat a deployed project's `plugins/<type>/catalog.md` or any
    installed plugin directory under `plugins/<type>/<name>/` as framework
    template content to overwrite wholesale. Once a project has registered
    or activated any plugin, that catalog and those directories are
    project-owned state, not framework state: synchronization may only
    merge into a `catalog.md` — adding rows for newly available plugins
    not yet present there, and refreshing the pinned `Release`/`Tag`/
    `Compatibility` columns of a row that already exists — and must never
    delete an existing row, blank the file, or delete or replace an
    installed plugin's directory contents as a side effect of the sync.
    If a plugin's row or directory would otherwise be missing, that is a
    `/catalyzer activate`/`download` action for the user to take
    afterward; `/sync-framework` must never perform or silently correct it.
13. At the end of the synchronization run, perform a four-eyes verification
   pass: one sub-agent verifies the deployment against the checklist in
   [`INSTANTIATION-GUIDE.md`](INSTANTIATION-GUIDE.md), and a second
   independent sub-agent repeats the verification from a fresh perspective.
   The sync is not complete until both verifiers approve the deployment. If
   their findings conflict or either verifier reports a violation, stop and
   report the issue rather than treating the sync as complete.

## Synchronization checklist

1. Check the framework repository on the `release` branch for the latest
   version and changes.
2. Ask for exactly one confirmation before beginning the synchronization.
3. Compare the deployed framework files with the latest framework state.
4. Copy any changed templates, rules, guidance, or structure needed by the
   deployed project, including plugin content pulled directly from each
   plugin's own repository when plugin updates are required. No plugin may be
   sourced from this repository; every plugin must have its own repository.
   A deployed project's own `plugins/<type>/catalog.md` and installed plugin
   directories are project-owned state, not framework template content —
   merge into them (see item 12 of the slash-command behavior above), never
   overwrite or delete them wholesale.
5. Ensure the deployed project contains a custom root-level `README.md` that
   describes the deployed framework's structure and the project's artifact
   layout. Also ensure it contains `ACCESS-CONTROL.md`, copied verbatim
   from `framework/kernel/ACCESS-CONTROL.md` (no project-specific
   customization, unlike the README) — create it if missing, and refresh
   it if this kernel version actually changed its content, same
   treatment as `CODE-OF-CONDUCT.md`/`Rules-of-Rules.md`.
6. Refresh and recompose the active module (`MODULE-SPECIFICATION.md`
   §6). The `<app-name>.catalyst` pointer must name it in its `module`
   field — there is no default module; if the field is missing, stop and
   ask the user which catalogued module (`framework/modules/catalog.md`)
   the deployment uses before going further. Then:
   - refresh `.criterion/modules/<module-id>/` from the module's
     catalogued repository, at the release matching the target kernel
     version (whole tree, never cherry-picked files), creating it if
     missing;
   - recompose the deployed `rules/Rules-of-Rules.md` from
     `rules-of-rules.template.md` plus the module's
     `rules-of-rules.module.md`, appended after the kernel's sections
     under `### From module <module-id>` (§6.1);
   - recompose the deployed `CODE-OF-CONDUCT.md` §3 and §4 from
     `rules-of-development.template.md` plus the `## 3.`/`## 4.`
     sections of the module's `code-of-conduct.module.md`, each inserted
     at the end of the matching kernel section under
     `### From module <module-id>` (§6.2);
   - read the module's `INVARIANTS.module.md` together with the kernel's
     `INVARIANTS.md` (§6.4);
   - recompose `Taskfile.common.yml` from
     `templates/Taskfile.common.template.yml` plus the module's
     `Taskfile.module.yml` tasks (§6.5);
   - apply the module's migrations with the kernel's, in version order
     (item 10 of the slash-command behavior above, §6.6).
   Composition is additive: module content never replaces kernel content,
   and project-local adjustments outside the composed blocks are
   preserved like any other synced file. Record the module id and
   version in `DEPLOYMENT.md`.
7. Ensure the deployed project contains the required artifacts:
   - one artifact-type folder per active-module entity type, at the
     place its ETD names, with its `templates/` (from the seeded module's
     `templates/`), its `<folder>.md` index (created even when empty) and
     its individual artifact files, if any. A type the module added since
     the project's last sync gets its folder and index created, not
     silently skipped; synchronization never overwrites or deletes an
     existing artifact file.
   - any non-artifact file the active module's meta-rules or invariants
     require (created from the module's `templates/` if missing, and
     refreshed only by the command the module names for it)
   - `meta-tags/meta-tags.md`
   - `IAM/roles/roles.json` (from `templates/roles.template.json` on
     first deploy; entries added/changed by `/role-add`/`/role-modify` —
     never overwritten by synchronization once it exists, same
     project-owned-state treatment as an installed plugin directory) and
     `IAM/users/users.json` (from `templates/users.template.json` on
     first deploy; entries added/updated by
     `/user-add`/`-remove`/`-modify`/`-assign-role` — see `INVARIANTS.md`
     INV-16). A deployed project that predates this requirement gets both
     created from their templates on its next sync, not silently skipped
     — and if that leaves `users.json` with zero active users, prompt to
     run `/user-add` before considering the sync complete (INV-16's hard
     "at least one active user" requirement applies regardless of how the
     file came to exist).
   - `development/journal.jsonl` (from `templates/journal.template.jsonl`
     on first deploy — see `INVARIANTS.md` INV-17). Append-only: a sync
     may create this file if missing, but must never rewrite, reorder, or
     truncate a single existing line. A deployed project that predates
     this requirement gets it created empty on its next sync — synchronizing
     does not retroactively fabricate entries for history that predates
     the journal's own existence.
   - `definitions/<type>.md` for every real entity type, kernel and
     active module (from `framework/kernel/definitions/<type>/
     DEFINITION-<TYPE>-vN.md` or the module's `definitions/<type>/
     DEFINITION-<TYPE>-vN.md`, `MODULE-SPECIFICATION.md` §6.3; latest
     version only — see `definitions/README.md` and
     `INVARIANTS.md` INV-23). **Frozen once deployed**: a sync creates `.criterion/definitions/<type>.md` only for
     a type that doesn't already have one there (e.g. a type this framework
     version or the active module introduced since the project's last sync) — it never
     overwrites or touches an existing `definitions/<type>.md`, no matter
     how much newer the framework's own copy has become. This is stronger
     than every other "don't overwrite" item above: those still get
     refreshed when the kernel version actually changed their spec;
     a deployed definition never does, by design (a project's understanding
     of what an entity type *is* must not shift silently underneath it).
     The only sanctioned way to move a deployed definition forward is the
     explicit `/migrate-definition <entity-type> <version>` command, and
     only to a version that actually exists in this framework's (or the
     active module's) `definitions/<entity-type>/` folder — see
     `rules-of-development.template.md` §4. A deployed project that predates this mechanism
     entirely gets every type's `definitions/<type>.md` created (at
     whatever version is current in this framework) the first time it
     syncs past the version that introduced it — see "Version-specific
     one-time migrations" below.
   - `version.txt`
   - every documented slash command from the composed `CODE-OF-CONDUCT.md`
     §4 — `rules-of-development.template.md` §4 plus the active module's
     §4 (item 6), the canonical list; this file must never re-enumerate a
     subset of it — must be available in the deployed environment after
     synchronization. Under Claude Code: create any
     `.claude/commands/<name>.md` missing relative to that list (following
     `templates/slash-command.template.md`), and refresh an existing one
     only if this kernel or module version actually changed that
     command's spec in the composed §4 — an unchanged command's file
     is project-owned content like any other synced file, not something to
     overwrite wholesale on every sync. Same treatment for
     `Taskfile.common.yml` (deployed inside `.criterion/`, not the project
     tree — INV-6) against `templates/Taskfile.common.template.yml` plus
     the module's `Taskfile.module.yml`: add any task missing relative to
     §4, refresh a task's `desc`/dispatched command only if this kernel or
     module version changed that command's §4 spec.
     The project's own root `Taskfile.yml` (its `includes:` plus its
     project-specific tasks) is project-owned content, never overwritten by
     a sync.
8. Update the deployed framework's `version.txt` to the latest released
   version once synchronization is complete.

## Version-specific one-time migrations

Some kernel versions introduce a one-time reclassification or cleanup
step for content a project deployed *before* that version, distinct from
the ordinary template/rule copying above. Each entry below runs **exactly
once** — the first time a deployed project's `version.txt` is advanced past
the entry's "From" version — never again on later syncs, even if the
project re-syncs to a still-later version afterward. The kernel's entries
are listed below and indexed in `migrations/migrations.md` (this
repository); the active module's entries live in its own
`migrations/migrations.md` and run interleaved with these, in version
order (`MODULE-SPECIFICATION.md` §6.6). Where a kernel version also
changed the active module's entity shapes, its entry below says so and
defers to the module's migration for that version.

### From `0.3.1`: module-owned audit

An entity-only migration for this version moved to the active module's
`migrations/` (`MODULE-SPECIFICATION.md` §6.6). Apply the active module's
migration for this version, if any; the kernel has nothing to do here.

### From `0.10.1`: agent-owned working copy + `<app-name>.catalyst` pointer

Target version `0.11.0`. Full procedure:
`migrations/0.11.0/agent-owned-working-copy.md` (this repository) — not
duplicated here.

### From `0.11.0`: uniform artifact-type layout

Target version `0.12.0`. Full procedure:
`migrations/0.12.0/uniform-artifact-layout.md` (this repository) — not
duplicated here. Touches most of the deployed tree (nested `templates/`,
`domains/` relocation, `IAM/`, new `work-items/` types, 6-digit IDs), so
treat it as its own careful pass rather than folding it into an ordinary
template/rule sync.

### From `0.12.1`: IAM registry templates

Target version `0.13.0`. Full procedure:
`migrations/0.13.0/iam-registry-templates.md` (this repository) — not
duplicated here. Adds `templates/` under `IAM/users/` and `IAM/roles/`
(reversing the exception `0.12.0` carved out for them); additive only,
no existing file's content changes except the two `README.md`
explanatory paragraphs.

### From `0.13.0`: rename to "criterion"

Target version `0.14.0`. Full procedure:
`migrations/0.14.0/rename-catalyst-proj-to-criterion.md` (this
repository) — not duplicated here. Renames the working-copy directory
and the whole repoed-sync mechanism (`.catalyst-proj/` → `.criterion/`,
`thingamabob` command/branch/field → `criterion`); if the deployment is
repoed, also renames the backing repository and its canonical branch —
externally-visible and hard-to-reverse, confirm with the user before
that part.

### From `0.14.0`: add the `RECON-` reconciliation entity

Target version `0.15.0`. Full procedure:
`migrations/0.15.0/add-reconciliation-entity.md` (this repository) —
not duplicated here. Additive only: a new `reconciliations/` artifact
type and `/reconcile` command; revises `/criterion push`'s
merge-conflict step to open a `RECON-` instead of an ephemeral,
unrecorded sub-agent proposal.

### From `0.15.0`: `work-items/` moves from core to plugin-territory

Target version `0.16.0`. Full procedure:
`migrations/0.16.0/work-items-to-plugin.md` (this repository) — not
duplicated here. Removes `work-items/` from the core layout — it only
deploys via an activated project-management-type content-contributing
plugin now (new capability, INV-22). **Requires an explicit decision
about any existing `work-items/` content before proceeding** — this is
not a purely mechanical sync, since no concrete plugin currently exists
to take over managing it.

### From `0.18.0`: `Taskfile.common.yml` moves into `.criterion/`

Target version `0.19.0`. Full procedure:
`migrations/0.19.0/taskfile-into-criterion.md` (this repository) — not
duplicated here. `Taskfile.common.yml` relocates from the target
project's own root into `.criterion/` (agent-owned space, INV-6), and
its dispatch becomes agent-generic (`{{.AGENT_CMD}}` instead of a
hardcoded `claude -p`) — only a deployment that ran `/sync-framework` or
was first instantiated while on exactly `0.18.0` needs this; anything
older simply gets the new shape fresh, no migration involved.

### From `0.19.0`: module-owned shape change

Target version `0.20.0`. No kernel change. Apply the active module's
migration for this version, if any (`MODULE-SPECIFICATION.md` §6.6).

### From `0.20.0`: entity definitions

Target version `0.21.0`. Full procedure:
`migrations/0.21.0/add-entity-definitions.md` (this repository) — not
duplicated here. A deployment with no `definitions/` folder yet gets one
created, with every real entity type's (kernel and active module) current
latest `definitions/<type>/
DEFINITION-<TYPE>-vN.md` copied in as `.criterion/definitions/<type>.md` —
the same "create if missing" logic ordinary synchronization now applies
to this folder going forward (INV-23), just run once, retroactively.

### From `0.21.0`: role-gated reconciliation

Target version `0.22.0`. Full procedure:
`migrations/0.22.0/role-gated-reconciliation.md` (this repository) — not
duplicated here. Every existing role in `IAM/roles/roles.json` gains a
`reconciliation` field (`full`/`propose`/`none`) — matched against this
framework's default roles by name where recognized, defaulting to
`propose` for a custom role rather than guessing `full`. `/reconcile`
begins enforcing it from this point on; no `RECON-` case already in
flight is retroactively affected.

### From `0.22.0`: `WORKFLOW-` promoted to core

Target version `0.23.0`. Full procedure:
`migrations/0.23.0/promote-workflow-to-core.md` (this repository) — not
duplicated here. Creates the always-present `workflows/` folder (full
INV-20 treatment, empty catalog is fine) and `definitions/workflow.md`
for any deployment that doesn't have them yet — pure addition, since no
deployment has ever had `work-items/workflows/` populated (no concrete
project-management plugin has ever existed).

### From `0.24.0`: add `ACCESS-CONTROL.md`

Target version `0.25.0`. Full procedure:
`migrations/0.25.0/add-access-control-doc.md` (this repository) — not
duplicated here. Creates the root-level `ACCESS-CONTROL.md` (copied
verbatim, no project customization) for any deployment that doesn't have
it yet, and links it from the root README.

### From `0.25.1`: userid field + entity-ID signer suffix

Target version `0.26.0`. Full procedure:
`migrations/0.26.0/userid-and-entity-id-suffix.md` (this repository) — not
duplicated here. Every registered user gains a `userid`; every entity ID —
kernel and active module — gains a creator/signer `userid` suffix; rule
sequence IDs widen to 6 digits.

### From `0.26.0`: add `Name` field to development entities

Target version `0.27.0`. Full procedure:
`migrations/0.27.0/add-entity-name-field.md` (this repository) — not
duplicated here. Base `entity` definition introduced and `Name` field
added across every entity type and template, kernel and active module
(`definitions/entity/`, `Rules-of-Rules.md` §3).

### From `0.28.0`, `0.29.0` and `0.30.0`: module-owned shape changes

Target versions `0.29.0`, `0.30.0` and `0.31.0`. No kernel change. Apply
the active module's migration for each of these versions, if any, in
version order (`MODULE-SPECIFICATION.md` §6.6).

### From `0.31.0`: atomic, real-time artifact updates

Target version `0.32.0`. Full procedure:
`migrations/0.32.0/atomic-artifact-updates.md` (this repository) — not
duplicated here. New behavioural meta-rule: every catalyst artifact is
updated as the work it describes actually happens, not batched
retroactively, unless delayed updating is explicitly stated before work
begins. Purely behavioural — no schema change, nothing to backfill.

### From `0.32.1`: process modules and ETDs

Target version `0.33.0`. Full procedure:
`migrations/0.33.0/process-modules-and-etds.md` (this repository) — not
duplicated here. Introduces process modules and Entity Type Definitions;
the active module is seeded into `.criterion/modules/<module-id>/` and
named in the pointer's `module` field.

### From `0.34.0`: the kernel

Target version `0.35.0`. Full procedure:
`migrations/0.35.0/rename-framework-core-to-kernel.md` (this repository) —
not duplicated here. The module-independent part of the framework is
named the kernel; the pointer's `framework_version` becomes
`kernel_version`.

### From `0.35.0`: keep `/sync-framework`

Target version `0.35.1`. Full procedure:
`migrations/0.35.1/keep-sync-framework.md` (this repository) — not
duplicated here. Withdraws `/sync-kernel`; `/sync-framework` keeps its
name.

### From `0.35.2`: module-agnostic kernel

Target version `0.36.0`. Full procedure:
`migrations/0.36.0/module-agnostic-kernel.md` (this repository) — not
duplicated here. The kernel no longer carries any module entity; every
module template, definition, meta-rule, invariant, command, task and
migration comes from the active module and is composed per
`MODULE-SPECIFICATION.md` §6. The pointer must name its module.

## Expected outcome

After synchronization, the deployed framework should reflect the current
framework's rules, templates, and file structure, and its version should be
at least this framework's own `version.txt`.
