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
  branch of `git@github.com:cantica-tech/catalyst.git` (or
  `https://github.com/cantica-tech/catalyst.git`).
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
10. Check `## Version-specific one-time migrations` below (indexed in
    the kernel's `migrations/migrations.md`, which wins if the two ever
    differ) — and the active module's own `migrations/migrations.md`
    (`MODULE-SPECIFICATION.md` §6.6) — for any entry whose "From" version
    is at or above the project's own `version.txt` value *before* this
    synchronization run started. Run each such entry exactly once, as part
    of this same run, kernel and module entries merged into one sequence in
    version order (a kernel and a module entry with the same target run
    kernel first), reporting flagged items to the user per that entry's
    own steps rather than applying them silently. Do not re-run an entry on
    a project whose pre-sync `version.txt` already reflected a version past
    that entry's "From" version.
11. Never delete or overwrite a file the deployment keeps that no kernel or
    module release ships (a plugin catalog from before the plugin system
    was retired, ADR-022, say): it is project-owned state.
12. Never write into the project beyond `catalyst.toml`; a release's
    content reaches the criterion only.
13. At the end of the synchronization run, perform a four-eyes verification
   pass: one sub-agent verifies the deployment against the checklist in
   [`INSTANTIATION-GUIDE.md`](INSTANTIATION-GUIDE.md), and a second
   independent sub-agent repeats the verification from a fresh perspective.
   The sync is not complete until both verifiers approve the deployment. If
   their findings conflict or either verifier reports a violation, stop and
   report the issue rather than treating the sync as complete.

## Synchronization checklist

`catalyst sync plan` lists, and `catalyst sync apply` performs, the
mechanical items below (3, 4's retired command files and hooks, 6, 7's definitions, CLI and
version, 8's journal entry); what remains is the confirmation (2), each
migration's judgment steps, `DEPLOYMENT.md` and the four-eyes verification.
`catalyst migrate` lists those judgment steps and, with `--apply`, adds the
template versions the migrations ask for (`CLI.md`).

1. Check the framework repository on the `release` branch for the latest
   version and changes.
2. Ask for exactly one confirmation before beginning the synchronization.
3. Compare the deployed framework files with the latest framework state.
4. Copy any changed templates, rules, guidance, or structure needed by the
   deployed project. A file the deployment keeps that no release ships is
   project-owned state (item 11 of the slash-command behavior above): never
   overwritten or deleted.
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
   the deployment uses before going further. Then (the three
   recompositions below are one `catalyst recompose` run, `CLI.md`, which
   merges the new templates into the deployed documents without losing
   their local edits):
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
     `templates/Taskfile.common.template.yml`, one task per command of the
     composed §4 (§6.5: a module ships no task; a `Taskfile.module.yml` is
     not read);
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
   - `IAM/identity.json`, the pointer to the deployment's catalyst-users
     configuration (written by `catalyst init` or `catalyst identity
     configure`), and `IAM/signers.jsonl`, the append-only signers ledger
     — never overwritten by synchronization once they exist, same
     project-owned-state treatment as item 11 above (`INVARIANTS.md`
     INV-16, INV-26). The criterion holds no user or role registry:
     people, roles and grants are catalyst-users'. `IAM/users/`,
     `IAM/roles/` and `IAM/groups/` hold only their display templates,
     with the same `templates/` treatment as every other type (INV-20).
     A deployed project that predates them gets them through its
     migration (`0.106.0`), not silently skipped — and if it is left
     without a pointer, prompt to point it at catalyst-users (`catalyst
     identity configure --issuer <url>`) before considering the sync
     complete: nothing can be signed until it is.
   - The journal (`development/journal/`, one shard per actor, machine and
     month; `development/journal.jsonl` in a deployment made before kernel
     0.50 — see `INVARIANTS.md` INV-17). Append-only: a sync appends its own
     entry to a shard, but must never rewrite, reorder, or truncate a single
     existing line, nor move the legacy file's lines into shards. A deployed project that predates
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
   - `bin/catalyst.pyz`, the catalyst CLI (`CLI.md`) — always replaced
     with the target kernel release's `bin/catalyst.pyz` (from catalyst's
     own checkout: `task build:cli`), never project-owned. The template's
     `catalyst` pass-through task is part of `Taskfile.common.yml` below.
   - every documented slash command from the composed `CODE-OF-CONDUCT.md`
     §4 — `rules-of-development.template.md` §4 plus the active module's
     §4 (item 6), the canonical list; this file must never re-enumerate a
     subset of it — reaches the agent as a prompt of the user-level
     `catalyst mcp` server, read at runtime: a sync writes no command
     file. It retires those older versions wrote: an unedited one in
     `.claude/commands/` is removed, a locally edited one reported as a
     conflict (never deleted), and catalyst's hooks leave the project's
     `.claude/settings.json` (its other settings kept). For
     `Taskfile.common.yml` (in the criterion, not the project tree —
     INV-6) against `templates/Taskfile.common.template.yml` and the
     composed §4 (a module ships no task, §6.5): add any task missing
     relative to §4, refresh a task's `desc`/dispatched command only if this
     kernel or module version changed that command's §4 spec.
     The project's own `Taskfile.yml`, if it has one, is never read or
     written by a sync: catalyst never touches it.
8. Update the deployed framework's `version.txt` to the latest released
   version once synchronization is complete, journal the sync with
   `catalyst journal append --command /sync-framework --action sync`, and
   run `catalyst check`: every error is resolved (or recorded for the user)
   before the sync is reported complete.

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

Each kernel migration, generated from `migrations/migrations.md`; its file
holds the full procedure. A version with no row needs no migration of the
kernel's: `catalyst sync apply` re-vendors the CLI and recomposes, and the
CHANGELOG says what the version changes. A version whose entity shapes
changed in the active module has that module's migration instead.

<!-- generated: migrations (scripts/gen_docs.py; do not edit by hand) -->

| From | To | Migration | What it migrates |
|---|---|---|---|
| `0.10.1` | `0.11.0` | [`0.11.0/agent-owned-working-copy.md`](migrations/0.11.0/agent-owned-working-copy.md) | `.catalyst-proj/` moves out of the target project's own tree into agent-owned space; `<app-name>.catalyst` pointer introduced (`Rules-of-Rules.md` §14, INV-6 revised). |
| `0.11.0` | `0.12.0` | [`0.12.0/uniform-artifact-layout.md`](migrations/0.12.0/uniform-artifact-layout.md) | Every artifact-type folder gains a versioned, catalogued `templates/`; `domains/` nests under `rules/`; `IAM/` replaces bare `development/users.json`/`roles.json`; `boards/`/`workflows/`/`tickets/` added to `work-items/`; artifact IDs widen from 4 to 6 digits (`Rules-of-Rules.md` §15, INV-20). |
| `0.12.1` | `0.13.0` | [`0.13.0/iam-registry-templates.md`](migrations/0.13.0/iam-registry-templates.md) | `IAM/users/` and `IAM/roles/` gain the same `templates/` treatment as every other artifact type — `TEMPLATE-USERS-vN.json`/`TEMPLATE-ROLES-vN.json` version the registry's seed shape (`Rules-of-Rules.md` §15, INV-20). Reverses the exception `0.12.0` introduced for these two. |
| `0.13.0` | `0.14.0` | [`0.14.0/rename-catalyst-proj-to-criterion.md`](migrations/0.14.0/rename-catalyst-proj-to-criterion.md) | `.catalyst-proj/` and the whole repoed-sync mechanism (`thingamabob` command/branch/field) renamed to "criterion" (`Rules-of-Rules.md` §13/§14, INV-6/INV-18 revised). |
| `0.14.0` | `0.15.0` | [`0.15.0/add-reconciliation-entity.md`](migrations/0.15.0/add-reconciliation-entity.md) | New `RECON-NNNNNN` type (`reconciliations/`, INV-20 template treatment) recording two entity versions `/criterion push`'s merge step couldn't reconcile; resolved via new `/reconcile` command (`Rules-of-Rules.md` §16, INV-21; §13/INV-18's merge step revised). |
| `0.15.0` | `0.16.0` | [`0.16.0/work-items-to-plugin.md`](migrations/0.16.0/work-items-to-plugin.md) | `work-items/` removed from the core layout; only deploys via an activated project-management-type content-contributing plugin (new capability, `Rules-of-Rules.md` §17, INV-22). Chain invariant (INV-5) revised to be conditional on one being active. No concrete plugin exists yet. |
| `0.18.0` | `0.19.0` | [`0.19.0/taskfile-into-criterion.md`](migrations/0.19.0/taskfile-into-criterion.md) | `Taskfile.common.yml` moves from the target project's own root into `.criterion/` (agent-owned space, INV-6); dispatch becomes agent-generic (`{{.AGENT_CMD}}`, resolved from the `*.catalyst` pointer's `agent` field, instead of a hardcoded `claude -p`). |
| `0.20.0` | `0.21.0` | [`0.21.0/add-entity-definitions.md`](migrations/0.21.0/add-entity-definitions.md) | New `definitions/<type>.md` per real entity type — short, versioned prose explaining what it is and what it's for, frozen once deployed and only movable forward via `/migrate-definition` (INV-23). |
| `0.21.0` | `0.22.0` | [`0.22.0/role-gated-reconciliation.md`](migrations/0.22.0/role-gated-reconciliation.md) | Every role in `IAM/roles/roles.json` gains a `reconciliation` field (`full`/`propose`/`none`), genuinely enforced by `/reconcile` — the one deliberate exception to the framework's advisory-only role principle (INV-21). |
| `0.22.0` | `0.23.0` | [`0.23.0/promote-workflow-to-core.md`](migrations/0.23.0/promote-workflow-to-core.md) | `WORKFLOW-` moves out of plugin-territory `work-items/` into its own always-present top-level `workflows/` folder (INV-24); `RECON-` cases may optionally name one to guide their resolution. |
| `0.24.0` | `0.25.0` | [`0.25.0/add-access-control-doc.md`](migrations/0.25.0/add-access-control-doc.md) | New root-level `ACCESS-CONTROL.md` — per-role read/write rights and when the agent may auto-sign as the `*.catalyst` pointer's `created_by` identity. |
| `0.25.1` | `0.26.0` | [`0.26.0/userid-and-entity-id-suffix.md`](migrations/0.26.0/userid-and-entity-id-suffix.md) | Every registered user gains a `userid`; every rule, active-module artifact, `WORKFLOW-` and `RECON-` ID carries its creator's `userid` as a suffix; rule IDs widen from 3-digit to 6-digit before the suffix (`Rules-of-Rules.md` §3/§11/§20, INV-26). |
| `0.26.0` | `0.27.0` | [`0.27.0/add-entity-name-field.md`](migrations/0.27.0/add-entity-name-field.md) | Base `entity` definition introduced and `Name` field added across every entity type and template, kernel and active module (`definitions/entity/`, `Rules-of-Rules.md` §3). |
| `0.31.0` | `0.32.0` | [`0.32.0/atomic-artifact-updates.md`](migrations/0.32.0/atomic-artifact-updates.md) | New behavioural meta-rule: every catalyst artifact is updated as the work it describes actually happens, at the smallest atomic unit practical, not batched retroactively — delayed updating requires an explicit statement before work begins (`Rules-of-Rules.md` §23, INV-29). Purely behavioural, no schema change. |
| `0.32.1` | `0.33.0` | [`0.33.0/process-modules-and-etds.md`](migrations/0.33.0/process-modules-and-etds.md) | Decouple process domains into Catalyst Process Modules and ETD schemas (`modules/<module-id>/`); the then-existing development-artifact types bundled as a default fallback module (`MODULE-SPECIFICATION.md`). |
| `0.34.0` | `0.35.0` | [`0.35.0/rename-framework-core-to-kernel.md`](migrations/0.35.0/rename-framework-core-to-kernel.md) | The module-independent part of the framework is named the kernel: files move to `framework/kernel/`, the pointer's `framework_version` becomes `kernel_version`, `/sync-framework` becomes `/sync-kernel` (alias kept), module manifests declare `kernelVersion`, and the kernel ships as `kernel-v<version>.zip` (INV-3). |
| `0.35.0` | `0.35.1` | [`0.35.1/keep-sync-framework.md`](migrations/0.35.1/keep-sync-framework.md) | `/sync-framework` keeps its name, since it synchronizes the whole framework; the `/sync-kernel` command from 0.35.0 is withdrawn. |
| `0.35.2` | `0.36.0` | [`0.36.0/module-agnostic-kernel.md`](migrations/0.36.0/module-agnostic-kernel.md) | The kernel carries no module entity: `RECON-`/`WORKFLOW-` are kernel entities (ETDs in `framework/kernel/entities/`); every module template, definition, meta-rule, invariant, command, task and migration comes from the active module and is composed per `MODULE-SPECIFICATION.md` §6. The pointer must name its `module` (no default); deployed `CODE-OF-CONDUCT.md` §3/§4, `Rules-of-Rules.md`, `Taskfile.common.yml` and `definitions/` are recomposed from kernel plus module (INV-30). |
| `0.36.0` | `0.37.0` | [`0.37.0/computed-working-copy-location.md`](migrations/0.37.0/computed-working-copy-location.md) | The pointer carries no path: `agent-source` is dropped, the agent-owned location is computed per machine by the running agent, and the project reaches the working copy through a gitignored `.criterion` symlink at its root. The root `Taskfile.yml` includes `.criterion/Taskfile.common.yml` with `optional: true` and no `CRITERION_DIR` (INV-6 revised). |
| `0.37.0` | `0.38.0` | [`0.38.0/catalyst-cli.md`](migrations/0.38.0/catalyst-cli.md) | Mechanical steps (IDs, userids, journal, indexes, chain validation) become the `catalyst` CLI, vendored at `.criterion/bin/catalyst.pyz` with a `catalyst` task and, where the agent supports it, a `catalyst hook stop` end-of-turn hook (`CLI.md`). Journal paths are project-root-relative, CLI-written entries carry `writer`, and journaled blobs are pinned under `refs/catalyst/journal`; old entries are never rewritten. |
| `0.38.0` | `0.39.0` | [`0.39.0/criterion-on-git.md`](migrations/0.39.0/criterion-on-git.md) | A shared deployment's working copy becomes the product repository's `.criterion` git submodule, pointing at the criterion repository; contributors land changes through pull requests (`catalyst criterion push`), checked in CI and optionally required by branch protection (INV-6, INV-18 revised). Per-user `<name>.criterion` branches, AI-assisted merging, push scoping and the `Signed-off-by` identity migration are withdrawn; ID numbers are unique per type and signer. A local-only deployment only bumps its version. |
| `0.39.0` | `0.40.0` | [`0.40.0/explicit-install-and-tiers.md`](migrations/0.40.0/explicit-install-and-tiers.md) | Installing is only ever an explicit request, carried out by `catalyst init` (INV-2 revised). Journal entries may carry a ceremony `tier` (`chore` needs no artifact and no target; `fix`, `feature`), whose requirements the active module defines. Command files read only their own spec (`catalyst spec`). ETDs may declare `location` and per-field `required_when_closed`, checked as `closed-incomplete`. Deployed governing documents, command files, CLI and module are refreshed; closed-incomplete artifacts are listed for the user, never backfilled. |
| `0.40.0` | `0.41.0` | [`0.41.0/traced-commits-and-format.md`](migrations/0.41.0/traced-commits-and-format.md) | Every product commit cites an artifact or rule ID that resolves in the deployment, or is a `chore:` (INV-5 at commit granularity): `catalyst hook commit-msg` (installed with `catalyst hook install`, on the user's assent) and `catalyst trace` in CI. The on-disk format is specified in `FORMAT.md`; the pointer declares `"format": "1.0-rc"`, which `catalyst check` verifies. Existing history is not checked. |
| `0.41.0` | `0.42.0` | [`0.42.0/changes-outside-catalyst.md`](migrations/0.42.0/changes-outside-catalyst.md) | A product commit after the pointer's new `journal_since` baseline that changes a file to a state no journal entry records is an unrecorded change, written outside catalyst: `catalyst unrecorded`, `check`, `trace` and the commit-msg hook report it, as a warning while the format is `1.0-rc` and an error from `1.0` (or with `strict_journal`). `/adopt` accepts it into the journal (`catalyst journal adopt`, `origin: manual`) or reverts it; a contested one is a `RECON-` case (`Trigger: unrecorded-change`). |
| `0.43.0` | `0.44.0` | [`0.44.0/four-eyes-analysis.md`](migrations/0.44.0/four-eyes-analysis.md) | Four-eyes analysis of existing code: the `ANALYSIS-` kernel entity (`analyses/`), `catalyst analysis` (two blind passes, diff, reconciliation accounting for every finding, a human decision per domain, rule and defect), `/run-analysis [<path>...] [--bootstrap\|--incremental]`, and `.criterion/ANALYSIS-PLAYBOOK.md` deployed (it never was). |
| `0.44.1` | `0.45.0` | [`0.45.0/workspace-scope.md`](migrations/0.45.0/workspace-scope.md) | What a deployment governs: its tree minus nested deployments and `.catalystignore` opt-outs, applied to unrecorded changes, `trace`, `analysis` and `init`; the commit-msg hook routes each staged file to its owning deployment (reinstall it after re-vendoring the CLI); `criterion create`/`join` for a project in a repository subfolder. No layout change. |
| `0.45.0` | `0.46.0` | [`0.46.0/grounded-sessions-and-safe-gates.md`](migrations/0.46.0/grounded-sessions-and-safe-gates.md) | Grounded sessions and safe gates: `init` copies the invariants into the working copy and `catalyst hook start` prints them at session start; `hook stop` fails closed; the criterion CI gate runs the base branch's hash-verified checker; IAM commands journal, roles carry `reconciliation`, `/status` refuses `RECON-` cases; CLI hardening. Layout: `.criterion/INVARIANTS.md`. |
| `0.46.1` | `0.47.0` | [`0.47.0/verbs-replace-procedures.md`](migrations/0.47.0/verbs-replace-procedures.md) | Verbs replace procedures (roadmap R2 W1–W3): `catalyst list`, `view`, `backlog`, `journal show`; `new`, `status set`, `link`; `user`, `role`, `freeze`/`unfreeze`, `definition migrate`. The §4 procedures of `/list`, `/user-*`, `/role-*`, `/journal`, `/status`, `/freeze` and `/migrate-definition` call them. Re-vendor the CLI, recompose. No layout change. |
| `0.47.0` | `0.48.0` | [`0.48.0/criterion-in-catalyst-home.md`](migrations/0.48.0/criterion-in-catalyst-home.md) | The criterion in catalyst's home store (ADR-010, INV-6): `catalyst.toml` is the project's only file, the criterion is `$HOME/.catalyst/projects/<name>/criterion` with its own runtime (`catalyst runtime install`, the launcher, Python 3.11+), `catalyst move --to-home` moves a legacy deployment, sharing clones the criterion (`catalyst criterion join`); `catalyst sync plan|apply`. Legacy deployments are read in 0.48.x. |
| `0.48.0` | `0.49.0` | [`0.49.0/agents-at-user-level.md`](migrations/0.49.0/agents-at-user-level.md) | Agents wired at user level: catalyst writes no file into a project but `catalyst.toml`; `catalyst mcp` serves the composed §4 commands as prompts (tools `catalyst`, `command`; the invariants as instructions); `catalyst agent install\|uninstall\|status <agent>` writes the agent's user-level config; `init` writes no command files or hooks (`--commands-dir` gone); `catalyst sync apply` retires the project's unedited command files and catalyst's hooks. |
| `0.49.0` | `0.50.0` | [`0.50.0/journal-shards.md`](migrations/0.50.0/journal-shards.md) | The journal in shards (`development/journal/<actor>@<machine>/<YYYY-MM>.jsonl`), appended under the criterion's journal lock and read in causal order; `development/journal.jsonl` is read, never written. Unrecorded changes are decided by content hashes, never by commit or entry times. `catalyst share` (any driver; `create`, `join`); publishing exits `3` without `--yes` (INV-4); `check` verifies merges. Nothing is converted; contributors to a shared criterion upgrade together. |
| `0.51.0` | `0.52.0` | [`0.52.0/the-handbook.md`](migrations/0.52.0/the-handbook.md) | The ten laws (`INVARIANTS.md` opens with them; a session loads only them; `catalyst why`); `Rules-of-Rules.md` becomes the deduplicated handbook and `CODE-OF-CONDUCT.md` the command catalogue; `/share` replaces `/criterion`; `/project`, `/switch-agent` removed, `/catalyzer` parked; `catalyst reconcile` enforces the reconciliation role gate. |
| `0.68.1` | `0.69.0` | [`0.69.0/one-create-command.md`](migrations/0.69.0/one-create-command.md) | One `/create <type>`: each module type is a part, read alone by `catalyst spec create <type>`; the old `/create-<type>` names stay aliases, one `create` task replaces theirs. Meta-tags dropped (B4): `sync apply` removes an empty `development/meta-tags/` and `definitions/meta-tag.md`. |
| `0.80.0` | `0.81.0` | [`0.81.0/proposals.md`](migrations/0.81.0/proposals.md) | Proposals (design 26): `catalyst propose <ID> --from <file>` opens a reconciliation case with `Trigger: proposal`, its base and the proposed content beside it; `reconcile … accept` writes it to the entity. The reconciliation template gains the `proposal` trigger (a new template version, a judgment step). |
| `0.82.0` | `0.83.0` | [`0.83.0/rule-strength.md`](migrations/0.83.0/rule-strength.md) | Rule strength (decision S): a rule's `**Strength**` line (`must`, `should`, `may`; `must` when none); `check`'s `rule-strength` error; `view`, `list` and `graph` carry it; a breach reported by it. The rule template gains the line (a new template version, a judgment step). |
| `0.83.0` | `0.84.0` | [`0.84.0/single-pass-analysis.md`](migrations/0.84.0/single-pass-analysis.md) | Configurable four-eyes analysis (decision B5): `catalyst analysis start --passes 1\|2`, `catalyst.toml` `analysis_passes`; two stays the default; a single-pass analysis is recorded as such, refuses pass B, and verifies and decides each finding. The analysis template gains `Passes` (a new template version, a judgment step). |
| `0.92.0` | `0.93.0` | [`0.93.0/roles-grant-commands.md`](migrations/0.93.0/roles-grant-commands.md) | Roles grant commands (decision D5): a writing verb refuses a signer none of whose roles grants its command (`/command` actions, `*`, the `Admin` role); `--as` refuses a deactivated user; `role_check = "warn"` warns instead. The roles template gains grants. Judgment: grant each non-Admin role its commands. |
| `0.103.0` | `0.104.0` | [`0.104.0/workflow-governance.md`](migrations/0.104.0/workflow-governance.md) | Workflow governance (REQ-000084): conditions on field values in guards (`holds`), gates (`when`) and workflows; a type's `due` date, `overdue` in the inbox; a `WORKFLOW-` that `Governs` a type, its Transitions enforced while `Active`. The workflow template gains `Governs`, `Escalates to` and Transitions (a new template version). |
| `0.104.0` | `0.105.0` | [`0.105.0/identity-providers.md`](migrations/0.105.0/identity-providers.md) | Identity providers (REQ-000086, design 28): `catalyst.toml` `identity = "oidc"` makes an OIDC provider's accounts sign, verified (`catalyst identity login`); an append-only signers ledger `IAM/signers.jsonl`; roles through `provider_role`; `catalyst serve --identity-issuer` accepts the provider's tokens. `local`, the default, is unchanged. Judgment, optional: map the roles, then configure the provider. |
| `0.105.2` | `0.106.0` | [`0.106.0/users-outside-catalyst.md`](migrations/0.106.0/users-outside-catalyst.md) | Users, groups and roles outside catalyst (REQ-000087, design 29): `IAM/identity.json` points at catalyst-users; the signer is the identity it verifies (with no one logged in, the machine's system account); grants decide what each may do; `user` and `role` refuse; `local` goes. Mechanical: the pointer from `catalyst.toml`, the roles kept as a display template, `users.json`/`roles.json` retired, the groups templates. Judgment: point a `local` deployment at catalyst-users, provision its roles, import its people. |
| `0.108.0` | `0.109.0` | [`0.109.0/criterion-admin-role.md`](migrations/0.109.0/criterion-admin-role.md) | The Criterion Admin, shown (REQ-000091) and `catalyst serve --criterion` (REQ-000090). Mechanical: the roles template gets the kernel's `Criterion Admin` as its next version, once. Judgment: restart a `catalyst serve` server with `--criterion <project_name>`. |
| `0.115.0` | `0.116.0` | [`0.116.0/landing.md`](migrations/0.116.0/landing.md) | Landing, phase 1 (REQ-000099, design 33): every journal entry says how its change was made, `via` (`agent`, `person`, `server`); a criterion declares how its changes land, `IAM/landing.json`, the kernel's `standard` policy when absent; `catalyst landing init\|show`, `check` validates it. Mechanical: nothing. Judgment: choose the landing policy with the user. |
| `0.119.2` | `0.120.0` | [`0.120.0/identity-pointer-issuer.md`](migrations/0.120.0/identity-pointer-issuer.md) | One shape for the identity pointer (BUG-000057): `IAM/identity.json` names its provider by its `issuer`, never `url` + `realm`; tokens kept per provider as one provider is named, so a login carries across shapes and loopback spellings; the signers ledger compares issuers the same way, never rewritten. Mechanical: `catalyst migrate --apply` writes the issuer. Judgment: none. |
| `0.120.0` | `0.121.0` | [`0.121.0/exit-codes.md`](migrations/0.121.0/exit-codes.md) | No deployment exits `4`, `2` is a usage error only (REQ-000110, fw-STRUCTURE-000025); `id next --peek` (REQ-000111); module releases only in the distribution repository (REQ-000112). Mechanical: none. Judgment: a caller that tested `2` for "no deployment" tests `4`. |

<!-- end generated: migrations -->
