# Instantiation Guide

How to stand up this framework in a project — new or existing — so it
creates concrete rules for that particular project.

## 1. New project

> Hard rule: when referring to catalyst, the model SHALL NEVER mention any
> local drive, local folder, or local path. References to catalyst must stay
> scoped to the git repository provided by the environment and the repository
> name itself.
>
> Hard rule: when the catalyst framework is first loaded into memory for a
> project, it MUST be installed immediately into that project using the
> instantiation steps in this guide.
>
> Hard rule: after that first installation, the framework MUST be referred to
> as "catalyst" or "catalyst framework" in all subsequent guidance,
> memory, and discussion, whether or not it has already been loaded before.
> Its module-independent part (`framework/kernel/`) MUST be referred to as
> "the kernel"; the framework is the kernel plus its process modules.
>
> Hard rule: the model SHALL NEVER push anything in this project, catalyst,
> without the user's explicit assent.

1. Decide your rule document(s) and their prefixes based on the project’s
   actual structure (e.g. one document per natural seam in the system — UI
   vs. backend, or per-service in a multi-service repo). Pick a short
   lowercase prefix per document.
2. Before creating the project layout, locate configuration for the
   framework name. Look for a project-local `dev-instructions.yaml` in the
   project where this guide is being run. If it exists, read its `name` value
   and, if present, its optional `layout` tree. If it does not exist, ask
   the user for the project name and use the current project root directory
   name as the default.

   The required format for that file is now:
   ```yaml
   name: "project-name"
   layout:
     project-root:
       - rules:
           - rules-of-rules.md
   ```

   The `name` value is the configurable project name used for the
   instantiated project data. It must be a simple project identifier, not a
   full path or a nested object. The optional `layout` value lets the
   deployment override the default directory structure. If no `layout` is
   provided, the deployment must use the default structure described below.

   After the deployment completes successfully, remove the project-local
   `dev-instructions.yaml` file from the project root. It was only needed as
   temporary bootstrap metadata for discovering the project name and any
   custom layout override, and is no longer needed once the framework has
   been deployed.
3. Pick a root layout, e.g.:
   ```
   <project-root>/.criterion/
     .ledger/
     ACCESS-CONTROL.md
     CODE-OF-CONDUCT.md
     DEPLOYMENT.md
     README.md
     version.txt
     definitions/
       README.md
       <type>.md
     modules/
       <module-id>/         # the active module, seeded from its release (step 4)
         module.yaml
         version.txt
         schemas/
         templates/
         definitions/
         commands/
         migrations/
         skills/
         rules-of-rules.module.md
         code-of-conduct.module.md
         INVARIANTS.module.md
         Taskfile.module.yml
     rules/
       templates/
         README.md
         templates-rule.md
         TEMPLATE-RULE-v1.md
       domains/
         templates/
           README.md
           templates-domain.md
           TEMPLATE-DOMAIN-v1.md
         README.md
         domains.md
         <prefix>-<CODE>-<short-description>.md
       README.md
       Rules-of-Rules.md
       rules.md
       business/
         business-rules.md
         <rule-doc-1>.md
       ui/
         ui-rules.md
         <rule-doc-2>.md
     <folder>/              # one per active-module entity type (step 4)
       templates/
         README.md
         templates-<type>.md
         TEMPLATE-<TYPE>-v1.md
       README.md
       <folder>.md
       <PREFIX-NNNNNN-short-summary>.md
     reconciliations/
       templates/
         README.md
         templates-reconciliation.md
         TEMPLATE-RECONCILIATION-v1.md
       README.md
       reconciliations.md
     workflows/
       templates/
         README.md
         templates-workflow.md
         TEMPLATE-WORKFLOW-v1.md
       README.md
       workflows.md
     IAM/
       users/
         templates/
           README.md
           templates-users.md
           TEMPLATE-USERS-v1.json
         README.md
         users.json
       roles/
         templates/
           README.md
           templates-roles.md
           TEMPLATE-ROLES-v1.json
         README.md
         roles.json
     plugins/
       <type>/
         <name>/            # an activated plugin's own install (its own repo)
     development/
       <folder>/            # active-module entity types the module places here
       meta-tags/
         templates/
           README.md
           templates-meta-tag.md
           TEMPLATE-META-TAG-v1.md
         README.md
         meta-tags.md
       README.md
       journal.jsonl
   ```
   `work-items/` is **not** built here — it's not part of the core
   layout (`Rules-of-Rules.md` §8, INV-22). It only comes into being if
   and when a project-management-type plugin is activated later; see
   `ARTIFACT-LAYOUT.md`'s "Optional, plugin-provided: `work-items/`" for
   the shape it deploys when one is.
   Every artifact-type folder above follows the same shape (`Rules-of-Rules.md`
   §15, `INVARIANTS.md` INV-20): a `templates/` subdirectory (its own
   `README.md`, a `templates-<type>.md` catalog — Version | File |
   Timestamp | Notes — and the current `TEMPLATE-<TYPE>-vN.md`, files
   only, never a subfolder, never edited in place once a newer version
   exists), its own `README.md`, the `<type>.md` instance catalog, and
   free-form space underneath for the actual artifacts (files and
   folders, any depth — e.g. rule documents nested by domain). `IAM/users/`
   and `IAM/roles/` get the same `templates/` treatment as every other
   type, except the versioned file is the registry's *seed shape*
   (`TEMPLATE-USERS-vN.json`/`TEMPLATE-ROLES-vN.json`) rather than a
   per-instance document, since each registry is one JSON array, not
   one-file-per-instance.
   (The working-copy directory is always named `.criterion/`, but it
   is not built inside the target project's own tree: resolve the
   **agent-owned location** first — a location this agent owns (a
   per-project data directory the running agent already maintains, if it
   has one), distinct from the project being governed, computed per
   machine from the agent's own conventions and never written into a
   tracked file — and build the tree there instead. Link it into the
   project as a `.criterion` symlink at the project root, and add
   `/.criterion` to the project's `.gitignore`: that symlink is the one
   path everything uses to reach the working copy. Write
   `<app-name>.catalyst` (from `templates/catalyst-pointer.template.json`)
   at the target project's own root, tracked normally; it holds no path
   — this pointer file is the *only* catalyst artifact the target
   project's own repo ever carries. If the running agent has no such
   owned-space concept, or the platform has no symlinks, fall back to
   building `.criterion/` directly inside the target project as a real
   directory, gitignored the same way — still not committed, but no
   relocation possible without agent support. Either way, `/criterion` (§13,
   opt-in) remains the durable, shareable persistence layer for teams
   that want the working copy to survive and sync across contributors,
   via a dedicated repository, never by committing it into the product's
   own repo. See `Rules-of-Rules.md` §14 for migrating a deployment that
   already exists in the old, purely in-project shape, and
   `migrations/` (this repository) for migrating an existing deployment
   built under an older layout of this section itself to the current
   one. The framework only cares that the chain from every active-module
   artifact to its grounding type (a kernel rule) to a domain stays intact
   — extended upward through epic→story→task only when an agile
   project-management plugin is active (INV-5, INV-22) — not the folder
   names.
   The `domains/` folder nests under `rules/` (`Rules-of-Rules.md` §7) —
   domains exist only to group rules, so they live where rules live, not
   as a top-level sibling. The `<folder>/` entries above stand for the
   active module's entity types: each ETD in the module's `schemas/`
   names its own `folder` (and whether it sits at the root or under
   `development/`), and the module's own meta-rules
   (`rules-of-rules.module.md`, composed in step 4) say what each type is
   for and how its artifacts link to one another and to rules. The kernel
   never names them (INV-30). The
   `reconciliations/` folder also sits at the root, alongside the active
   module's root-level folders — not nested under `work-items/`
   — and holds `RECON-NNNNNN` cases opened by `/criterion push`'s merge
   step or manually (`Rules-of-Rules.md` §16).
   `work-items/` itself is not built at all here — it's plugin-only
   (`Rules-of-Rules.md` §8, INV-22); skip it entirely for a core
   instantiation.)
4. Seed and compose the active module (`MODULE-SPECIFICATION.md` §6). The
   `<app-name>.catalyst` pointer MUST name it in its `module` field —
   there is no default module; if the user has not said which one, list
   the production modules in `framework/modules/catalog.md` and ask.
   Then:
   - **Seed** the module from its catalogued repository, at the release
     that matches this kernel version (its default branch only if no
     release exists yet), into `.criterion/modules/<module-id>/` — the
     whole module tree, never cherry-picked files. Like plugins, a module
     is never sourced from this framework repository.
   - **Rules-of-Rules:** append the module's `rules-of-rules.module.md`
     to the deployed `rules/Rules-of-Rules.md`, after the kernel's
     sections, under a `### From module <module-id>` heading
     (§6.1). Module rule IDs keep their numbers; a kernel placeholder
     line for an `rr-META-NNN` that moved to the module stays in place.
   - **CODE-OF-CONDUCT:** insert the `## 3.` and `## 4.` sections of the
     module's `code-of-conduct.module.md` at the end of the deployed
     `CODE-OF-CONDUCT.md` §3 and §4 respectively, each under a
     `### From module <module-id>` heading (§6.2). The composed §4
     (kernel plus module) is the canonical command list step 5 deploys.
   - **Invariants:** read the module's `INVARIANTS.module.md` together
     with the kernel's `INVARIANTS.md` (§6.4); both bind the deployment.
   - **Definitions:** the module's `definitions/` join the kernel's in
     step 7 (§6.3).
   - **Taskfile:** append the tasks of the module's `Taskfile.module.yml`
     to the deployed `Taskfile.common.yml` in step 5 (§6.5).
   - **Artifact folders:** build one artifact-type folder per module
     entity type, at the place its ETD names, in step 6, from the
     module's `templates/`.
   - **Migrations:** a fresh deployment starts at the current version, so
     no migration runs now; `/sync-framework` later applies module and
     kernel migrations together in version order (§6.6,
     `SYNCHRONIZE.md`).
   Record the module id and version in `DEPLOYMENT.md`.
5. Ensure the deployed
   framework exposes **every** documented custom slash command from
   the composed `CODE-OF-CONDUCT.md` §4 — `rules-of-development.template.md`
   §4 plus the active module's §4 (step 4) — the canonical list; don't
   re-enumerate a subset of it here or anywhere else, that's exactly how it
   drifts — in the same way the framework defines them, so they are
   available in the deployed environment. Under Claude Code this
   concretely means: one `.claude/commands/<name>.md` file per command,
   created from `templates/slash-command.template.md` (see `CLAUDE.md`'s
   "Slash commands" entry for the exact mechanism). When plugins are
   needed, pull their content directly from each plugin's own repository;
   no plugin may be sourced from this framework repository, and every
   plugin must have its own repository with no exceptions. Also deploy
   `templates/Taskfile.common.template.yml` as `Taskfile.common.yml`
   **inside `.criterion/`** (agent-owned space per INV-6 — never the
   target project's own tree, unlike `.claude/commands/` which stays
   project-root only because Claude Code's own fixed discovery path
   forces it there), with the active module's `Taskfile.module.yml` tasks
   appended to it (step 4) — same canonical composed §4 list, same drift
   concern, see `CLAUDE.md`'s "Taskfiles" entry. Create the project's own root
   `Taskfile.yml` if none exists yet, resolving the deployed agent's CLI
   binary from the `*.catalyst` pointer's `agent` field so every
   dispatched command stays agent-generic, and including
   `.criterion/Taskfile.common.yml` — the project-root `.criterion`
   symlink (INV-6), so the same relative path works on every machine and
   for every agent, and no machine-specific path ever lands in this
   tracked file. The include is `optional: true`, so the project's own
   tasks still run on a clone where `.criterion` isn't set up yet (Task
   follows the symlink transparently):
   ```yaml
   vars:
     # Resolves the deployed agent's CLI binary from the pointer's "agent"
     # field. "claude-code" is the one known id whose CLI binary name
     # differs from the id itself; any other agent id is assumed to
     # already be its own binary name. Falls back to "claude" — today's
     # only known agent — when no pointer/field is found.
     AGENT_ID:
       sh: |
         f=$(ls *.catalyst 2>/dev/null | head -1)
         [ -n "$f" ] && grep -oE '"agent"[[:space:]]*:[[:space:]]*"[^"]*"' "$f" | head -1 | sed -E 's/.*"([^"]*)"$/\1/'
     AGENT_BIN: '{{if eq .AGENT_ID "claude-code"}}claude{{else if .AGENT_ID}}{{.AGENT_ID}}{{else}}claude{{end}}'
     # Full override escape hatch for an agent needing different flags
     # than `<bin> -p "<prompt>"` entirely (e.g. a non-Claude CLI).
     AGENT_CMD: '{{.AGENT_CMD_OVERRIDE | default (printf "%s -p" .AGENT_BIN)}}'

   includes:
     common:
       # The gitignored .criterion symlink (or in-project fallback
       # directory) at the project root — INV-6. Optional, so a clone
       # without it still runs this project's own tasks.
       taskfile: .criterion/Taskfile.common.yml
       optional: true
       flatten: true
       vars:
         AGENT_CMD: '{{.AGENT_CMD}}'
   ```
   Add that project's own operational tasks in this same root
   `Taskfile.yml`, alongside — never inside — the included common tasks.
6. For **every** artifact-type folder (`Rules-of-Rules.md` §15, INV-20):
   create its `templates/` subdirectory, copy the matching
   `templates/*.template.*` — from this framework for a kernel type, from
   the seeded `.criterion/modules/<module-id>/templates/` for an
   active-module type — into it as
   `TEMPLATE-<TYPE>-v1.md` (first version — new versions only ever get
   added later, never an in-place edit), write that `templates/`
   folder's own `README.md`, and seed its `templates-<type>.md` catalog
   with one row for `v1` (Version | File | Timestamp | Notes — today's
   date, "initial version"). Then write the artifact-type folder's own
   `README.md` and its `<type>.md` instance catalog (the kernel's
   `reconciliations.md`, `meta-tags.md`, `domains.md`, `workflows.md`,
   plus one `<folder>.md` per active-module entity type).
   This loop does not include `work-items/` or any of its subtypes
   (`boards.md`/`epics.md`/`stories.md`/`tasks.md`/`spikes.md`/
   `sprints.md`/`tickets.md`) — that folder is
   plugin-only (step 3's note above) and isn't built during core
   instantiation at all. `workflows.md` is core now (`Rules-of-Rules.md`
   §19, INV-24), so it's in the list above, not this exclusion.

   Keep each type's templates in the same folder as its actual
   artifacts so the template and the concrete files live together
   (nested one level deeper, under `<folder>/templates/`, but still
   co-located). Domain files nest under `rules/domains/`, which
   gets this same full treatment (its own `templates/`, `README.md`,
   `domains.md`).

   Also deploy any non-artifact file the active module's meta-rules and
   invariants require at instantiation (for example a generated summary
   document), from the module's own `templates/`, and run whatever
   command the module names to populate it, so no template's
   `{{PLACEHOLDER}}` text is left in place. Also create
   `IAM/users/templates/` and `IAM/roles/templates/` the same way as any
   other type in this loop: copy `templates/users.template.json` in as
   `TEMPLATE-USERS-v1.json` and `templates/roles.template.json` in as
   `TEMPLATE-ROLES-v1.json`, each with its own `README.md` and a
   `templates-users.md`/`templates-roles.md` catalog seeded with a `v1`
   row. Then seed `IAM/roles/roles.json` from `TEMPLATE-ROLES-v1.json`
   (its default agile-role mapping) and `IAM/users/users.json` from
   `TEMPLATE-USERS-v1.json` (empty array) — both a hard requirement
   (`INVARIANTS.md` INV-16). **Then immediately run `/user-add` for at least one
   person** — unlike every other on-demand artifact, deployment is not
   actually complete with an empty `users.json`: a project must have at
   least one active user (INV-16). Ask the user who that first
   registered user should be and what role they hold if it isn't obvious
   from context. Also copy
   `templates/journal.template.jsonl` (empty) to
   `development/journal.jsonl` — a hard requirement (`INVARIANTS.md`
   INV-17). From this point on, every command that creates, modifies,
   closes, or retires a rule-linked artifact, rule, domain, or work item,
   or changes a `Status` field, appends one entry to it as its last step
   (`CODE-OF-CONDUCT.md` §9) — including every step of this instantiation
   itself from here onward.
7. Deploy `framework/kernel/definitions/` and the active module's
   `definitions/` (`INVARIANTS.md` INV-23, `MODULE-SPECIFICATION.md` §6.3) —
   one short prose file per real entity type explaining what it is and
   what it's for, distinct from the `templates/` files' field-and-shape
   definitions. For each type, copy
   only its *latest* `DEFINITION-<TYPE>-vN.md` content into
   `.criterion/definitions/<type>.md` (flat — one file per type, no nested
   subfolder in the deployed copy; the versioned-history subfolders under
   `framework/kernel/definitions/` and the module's `definitions/` are
   source structure only). Also copy `framework/kernel/definitions/README.md` to
   `.criterion/definitions/README.md` so the freeze/versioning convention
   travels with the deployment. **This step never runs again after first
   deploy for a type that already has a deployed definition** — see
   `SYNCHRONIZE.md`'s definitions carve-out; only `/sync-framework` adding a
   brand-new type, or an explicit `/migrate-definition`, ever touches a
   `.criterion/definitions/<type>.md` file after this.
8. Create a root-level `README.md` in the deployed framework directory that
   explains the project's rule-and-workflow structure, the deployment path,
   and the main artifact folders. This README should be created during both
   deployment and synchronization so the deployed framework always has a
   custom, project-specific landing page. In addition, create a `README.md`
   in every major deployed folder (`rules/`, `rules/domains/`,
   `reconciliations/`, `workflows/`, `IAM/users/`, `IAM/roles/`,
   `development/`, `development/meta-tags/`, `modules/<module-id>/`, and
   every active-module `<folder>/`) and in every `templates/` subdirectory
   (INV-20) that briefly explains that folder's purpose and link to it
   from the root README so the structure is discoverable and
   self-documenting. Also copy `framework/kernel/ACCESS-CONTROL.md`
   to `.criterion/ACCESS-CONTROL.md` verbatim (no project-specific
   customization, unlike this README) — a root-level governing reference,
   same treatment as `CODE-OF-CONDUCT.md`/`Rules-of-Rules.md`: created on
   first deploy, refreshed on `/sync-framework` whenever this framework
   version actually changes it, linked from the root README so it's
   discoverable.
9. Create whatever starter artifacts the active module's meta-rules call
   for, based on the project's rule documents (for example, a description
   document such as `UI-Rules.md` for UI rules or `business-rules.md` for
   business rules), and keep them aligned with the rule IDs or source
   documents that define the expected behavior. Starter artifacts must be
   concrete and tied to specific application areas, screens, flows, or
   components, because later work is grounded on them.
10. Create your first rule document(s) with a `## Contents` heading and the
   `## Linked Artifacts — Quick Index` heading (even if empty;
   `Rules-of-Rules.md` §6) — the rest fills
   in as domains/rules get added, each per `Rules-of-Rules.md` §6, so the
   framework produces rules that are specific to this project. This is a hard
   requirement: every rule must be stored as its own markdown file under the
   rule type directory it belongs to, appear in the corresponding type index,
   and be listed in the global `rules.md` index. In addition, every rule and
   development artifact name must follow the descriptive format
   **`<id>-<short-summary>`**, and the corresponding markdown filename must
   follow **`<id>-<short-summary>.md`**; bare IDs or bare-ID filenames are no
   longer acceptable. Existing deployed items must be renamed during deployment
   or synchronization to meet this rule. There must be exactly one *current*
   `TEMPLATE-RULE-vN.md` file, in `rules/templates/` (INV-8, INV-20), and
   none inside the rule-type directories. No rule may be orphaned by
   missing a type, a local index entry, or a global index entry. This
   same descriptive-naming requirement is a hard requirement for domain
   files: every file under `rules/domains/` must be named
   `<prefix>-<CODE>-<short-summary>.md` (or
   `<prefix>-<PARENT>.<SUB>-<short-summary>.md` for a sub-domain), never the
   bare `<prefix>-<CODE>.md` — see `Rules-of-Rules.md` §7.
## 2. Choosing your agile flavor

`work-items/` is plugin-only (§1 step 3, `Rules-of-Rules.md` §8) — this
choice only matters if and when a project-management-type plugin is
activated. Nothing below the work-items layer changes regardless.
Above it, once such a plugin is active:

- Using Scrum → keep everything as templated (`sprints/` included, skip
  `boards/`).
- Using Kanban → skip `sprints/`; use `boards/` (`BOARD-NNNNNN`) instead —
  a WIP-limited `Status` value set on stories/tasks, referencing the
  board in place of sprint membership (the schema's own
  `rules-of-work-items.template.md` §6).
- Using something else entirely → the framework's hard requirement is
  only §1 of `rules-of-development.md` (no development without a
  targeted rule) — everything above that is replaceable with whatever
  process vocabulary your team actually uses, as long as it still
  bottoms out in the active module's development artifacts. Without any
  project-management plugin active, this is the default — the chain
  simply starts at the active module's artifacts (INV-5).

## 3. Greenfield path — no existing code or practices

Use this path when the target project has no code yet (or only a bare
scaffold) and therefore has no practices to retrofit rules from — the
mirror image of §4. Instead of extracting rules from what already
exists, this path establishes the foundational tooling, stack, and dev-
environment decisions **as rules, before the first line of application
code is written**, so the codebase is born governed rather than governed
after the fact.

1. Pick (or confirm with the user) a dedicated rule document for these
   decisions — e.g. `dev-environment-rules.md` with a short prefix such
   as `env` or `dx` — separate from the application's business/UI rule
   documents, since these rules govern the toolchain and workflow, not
   product behavior. Add it to the rule document list from §1 step 1.
2. Work through the foundational decision areas with the user, one
   domain per area, creating each `rules/domains/<prefix>-<CODE>-<short-description>.md`
   file per §7 before writing rule bullets under it. Typical areas
   (skip any that don't apply to the project, add any it needs):
   - **Runtime/language** — language, version, package manager.
   - **Dependency policy** — what may be added and how (lockfiles,
     approval, vetting).
   - **Code style** — linter, formatter, and their configs.
   - **Testing** — test framework, coverage tool, and where tests live.
     This also fills in `{{TEST_LOCATIONS}}` in `Rules-of-Rules.md` §2
     for every rule created afterward, including application rules.
   - **CI/CD** — pipeline provider, what gates a merge.
   - **Local dev environment** — how a new contributor gets running
     (devcontainer, Docker Compose, Nix, a setup script — whatever the
     project uses), and any required environment variables/secrets
     handling.
   - **Repo/module layout** — the directory conventions the codebase
     will follow.
3. For each decision, write the rule *and* implement it in the same
   pass: create the actual config file (`package.json`, `.eslintrc`, the
   CI workflow, the devcontainer, etc.) as part of satisfying
   `Rules-of-Rules.md` §2 (gathered/implemented/tested/documented). A
   tooling rule's "tested" bar is that the tool actually runs clean
   against the (still-empty) scaffold — e.g. the linter exits zero, the
   CI workflow runs green — not a unit test.
4. Once the dev-environment rule document has its first pass of domains
   and rules, continue with §1 steps 2 onward to deploy the rest of the
   framework skeleton (the active module's artifact folders,
   reconciliations) around it. That rule document stands in for the
   starter artifacts in §1 step 9 — there is no product behavior yet to
   ground them on.
5. As soon as real application code starts, that work is a normal
   active-module artifact (per `CODE-OF-CONDUCT.md` §1) against a
   business/UI rule document
   created the usual way — the greenfield path only front-loads the
   tooling layer, it does not replace the rest of the chain.

## 4. Retrofitting an existing project

1. Do **not** try to write every rule up front. Start with
   `Rules-of-Rules.md`, `CODE-OF-CONDUCT.md` (or your project's
   equivalents) and an empty `rules/domains/` directory.
2. Gather rules incrementally — per functional area, as you touch it, or
   via a dedicated audit pass (parallel research agents/subagents
   covering one rule category each, cross-checked against the codebase
   and test suite, is one effective way to bootstrap a first pass quickly
   — but the resulting rules still need the §1 conflict check and the
   gathered/implemented/tested/documented bar from §2 before they count
   as real, not just an audit report). If the project already has
   established practices, merge them into the new ruleset and preserve
   what is still valuable rather than discarding it. If conflicts arise,
   pause and ask the user questions so the final rule reflects the
   project’s intent rather than an arbitrary choice.
3. As each functional domain is identified, create its
   `rules/domains/<prefix>-<CODE>-<short-description>.md` file per §7 before adding rule bullets
   under it.
4. Retrofit IDs onto existing prose bullets (if a rules doc already
   exists in some other form) in document order, per §3 — top-level
   bullets get `NNN`; enumerated sub-cases inside one bullet get
   `-1`/`-2`/... suffixes rather than new top-level IDs.
5. Once rules exist, retrofit active-module artifacts for any
   already-known issues and pending work (an existing known-issues index
   is a good source), citing the rule IDs from step 4.
6. Add a one-line header to each of your project's rule and process files
   noting which template in this framework they instantiate, e.g.:
   ```
   > Instantiates [the catalyst framework rules template](../../framework/kernel/rules-of-rules.template.md).
   ```
   This keeps the project's concrete process traceable back to the
   generic framework as the framework itself evolves.

## 5. Keeping the two in sync

When a process rule changes in a project (e.g. this repo adds a new
`rr-META-NNN`), evaluate whether it's project-specific or a generally
useful addition to this framework. If general, port it back into the
`.template.md` files here so the next project instantiation starts from
the improved version. When the project already has existing practices,
merge them into the framework rather than treating the framework as a
replacement for what is already there. If a conflict cannot be resolved
from the existing context, stop and ask the user targeted questions
before continuing.

## 6. Remember the deployment target across sessions

After a successful instantiation, record the project root path and the
resolved working-copy location (§1) in the persistent memory store, if one is
available, so later sessions can recover which project this framework was
deployed into without having to rediscover it. This is a convenience
cache, not the source of truth: `<app-name>.catalyst` at the project root
is always tracked and always present regardless of memory-tool
availability, and `.criterion/DEPLOYMENT.md` inside the working copy
carries the fuller deployment/repo record — either can be read fresh each
session with no memory tool at all.

Keep a compact note with at least:

- the framework name (`catalyst framework`)
- the deployed project path
- the resolved working-copy location (where the `.criterion` symlink
  points on this machine)
- the date or context of the instantiation
- any short notes that help identify the project later

When this guide is used again for the same project, check memory first and
reuse the existing note as the default project context. If a prior note
already exists for that project, update it instead of creating a duplicate.
When switching agents, update this persistent memory note alongside `<app-name>.catalyst`
(`agent`, `updated`) and the `.criterion` symlink.
This makes the association durable across sessions and keeps the project's
instantiated ruleset available whenever the guide is used again.

At the end of a successful instantiation via the retrofit path (§4), if the
project currently has no active-module artifacts or other tracked work
items yet, propose running
[`analysis-playbook.md`](analysis-playbook.md) next to help bootstrap the
first round of project-specific rules and evidence — it reads an existing
codebase, so it does not apply after the greenfield path (§3), whose
dev-environment rule document already is the first round of rules.
