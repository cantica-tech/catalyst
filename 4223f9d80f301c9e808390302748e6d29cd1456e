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
   <project-root>/.catalyst-proj/
     .ledger/
     CODE-OF-CONDUCT.md
     DEPLOYMENT.md
     README.md
     version.txt
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
     requirements/
       templates/
         README.md
         templates-requirement.md
         TEMPLATE-REQUIREMENT-v1.md
       README.md
       requirements.md
       <requirement-doc-1>.md
       <requirement-doc-2>.md
     features/
       templates/
         README.md
         templates-feature.md
         TEMPLATE-FEATURE-v1.md
       README.md
       features.md
       <FEAT-NNNNNN-short-summary>.md
     IAM/
       users/
         README.md              # no templates/ — one JSON array, not
         users.json              # a per-instance artifact type
       roles/
         README.md              # no templates/ — same reason
         roles.json
     plugins/
       <type>/
         <name>/            # an activated plugin's own install (its own repo)
     development/
       roadmaps/
         templates/
           README.md
           templates-roadmap.md
           TEMPLATE-ROADMAP-v1.md
         README.md
         roadmaps.md
       bugs/
         templates/
           README.md
           templates-bug.md
           TEMPLATE-BUG-v1.md
         README.md
         bugs.md
       house-keeping/
         templates/
           README.md
           templates-house-keeping.md
           TEMPLATE-HOUSE-KEEPING-v1.md
         README.md
         house-keeping.md
       meta-tags/
         templates/
           README.md
           templates-meta-tag.md
           TEMPLATE-META-TAG-v1.md
         README.md
         meta-tags.md
       BACKLOG.md
       README.md
       journal.jsonl
     work-items/
       boards/
         templates/
           README.md
           templates-board.md
           TEMPLATE-BOARD-v1.md
         README.md
         boards.md
       epics/
         templates/
           README.md
           templates-epic.md
           TEMPLATE-EPIC-v1.md
         README.md
         epics.md
       spikes/
         templates/
           README.md
           templates-spike.md
           TEMPLATE-SPIKE-v1.md
         README.md
         spikes.md
       sprints/
         templates/
           README.md
           templates-sprint.md
           TEMPLATE-SPRINT-v1.md
         README.md
         sprints.md
       stories/
         templates/
           README.md
           templates-story.md
           TEMPLATE-STORY-v1.md
         README.md
         stories.md
       tasks/
         templates/
           README.md
           templates-task.md
           TEMPLATE-TASK-v1.md
         README.md
         tasks.md
       tickets/                 # plugin-populated slot, no core template
         README.md
         tickets.md
       workflows/
         templates/
           README.md
           templates-workflow.md
           TEMPLATE-WORKFLOW-v1.md
         README.md
         workflows.md
       README.md
       rules-of-work-items.md
   ```
   Every artifact-type folder above follows the same shape (`Rules-of-Rules.md`
   §15, `INVARIANTS.md` INV-20): a `templates/` subdirectory (its own
   `README.md`, a `templates-<type>.md` catalog — Version | File |
   Timestamp | Notes — and the current `TEMPLATE-<TYPE>-vN.md`, files
   only, never a subfolder, never edited in place once a newer version
   exists), its own `README.md`, the `<type>.md` instance catalog, and
   free-form space underneath for the actual artifacts (files and
   folders, any depth — e.g. rule documents nested by domain). Two
   exceptions: `IAM/users/`, `IAM/roles/` skip `templates/` entirely —
   each is one JSON array, not a one-file-per-instance document type, so
   there's nothing to version — and `tickets/` is a reserved slot with no
   core template, populated by a project-management-type plugin if one
   is activated, otherwise left empty. `boards/` is optional per agile
   flavor (§2 below — Kanban/Scrumban only, mutually exclusive with
   `sprints/`); `workflows/` is optional but flavor-independent — adopt
   it whenever the project wants process-definition documents, not tied
   to which agile flavor is chosen.
   (The working-copy directory is always named `.catalyst-proj/`, but it
   is not built inside the target project's own tree: resolve
   **agent-source** first — a location this agent owns (a per-project
   data directory the running agent already maintains, if it has one),
   distinct from the project being governed — and build the tree there
   instead. Write `<app-name>.catalyst` (from
   `templates/catalyst-pointer.template.json`) at the target project's
   own root, tracked normally, with its `agent-source` field pointing at
   that location — this pointer file is the *only* catalyst artifact the
   target project's own repo ever carries. If the running agent has no
   such owned-space concept, fall back to building `.catalyst-proj/`
   directly inside the target project instead, and add it to that
   project's own `.gitignore` — still not committed, but no relocation
   possible without agent support. Either way, `/thingamabob` (§13,
   opt-in) remains the durable, shareable persistence layer for teams
   that want the working copy to survive and sync across contributors,
   via a dedicated repository, never by committing it into the product's
   own repo. See `Rules-of-Rules.md` §14 for migrating a deployment that
   already exists in the old, purely in-project shape, and
   `migrations/` (this repository) for migrating an existing deployment
   built under an older layout of this section itself to the current
   one. The framework only cares that the chain
   epic→story→task→REQ/BUG/HK→rule stays intact, not the folder names.
   The `domains/` folder nests under `rules/` (`Rules-of-Rules.md` §7) —
   domains exist only to group rules, so they live where rules live, not
   as a top-level sibling. The `features/` folder sits at the root,
   alongside `requirements/`; it holds descriptive, non-rule-linked
   feature entries (see `Rules-of-Rules.md` §9) and is never a
   substitute for `requirements/`. The work-items rule document belongs
   in the `work-items/` layer and should not be duplicated under
   `rules/`.)
5. Copy `rules-of-work-items.template.md` similarly. Ensure the deployed
   framework exposes **every** documented custom slash command from
   `rules-of-development.template.md` §4 — the canonical list; don't
   re-enumerate a subset of it here or anywhere else, that's exactly how it
   drifts — in the same way the framework defines them, so they are
   available in the deployed environment. Under Claude Code this
   concretely means: one `.claude/commands/<name>.md` file per command,
   created from `templates/slash-command.template.md` (see `CLAUDE.md`'s
   "Slash commands" entry for the exact mechanism). When plugins are
   needed, pull their content directly from each plugin's own repository;
   no plugin may be sourced from this framework repository, and every
   plugin must have its own repository with no exceptions.
6. For **every** artifact-type folder (`Rules-of-Rules.md` §15, INV-20):
   create its `templates/` subdirectory, copy the matching
   `templates/*.template.*` from this framework into it as
   `TEMPLATE-<TYPE>-v1.md` (first version — new versions only ever get
   added later, never an in-place edit), write that `templates/`
   folder's own `README.md`, and seed its `templates-<type>.md` catalog
   with one row for `v1` (Version | File | Timestamp | Notes — today's
   date, "initial version"). Then write the artifact-type folder's own
   `README.md` and its `<type>.md` instance catalog (`bugs.md`,
   `requirements.md`, `features.md`, `house-keeping.md`, `meta-tags.md`,
   `boards.md`, `epics.md`, `stories.md`, `tasks.md`, `spikes.md`,
   `sprints.md`, `workflows.md`, `roadmaps.md`, `domains.md`,
   `tickets.md`). Skip `boards/`/`sprints/` per the chosen agile flavor
   (§2); `tickets/` gets its `README.md` and empty `tickets.md` but no
   `templates/` — no core template exists for it (a project-management
   plugin, if activated, owns that).

   Keep requirements templates in the same `requirements/` directory as
   the actual requirements documents so the template and the concrete
   requirement files live together (nested one level deeper now, under
   `requirements/templates/`, but still co-located), and likewise for
   every other type. Domain files nest under `rules/domains/`, which
   gets this same full treatment (its own `templates/`, `README.md`,
   `domains.md`).

   Also copy `templates/backlog.template.md` to `development/BACKLOG.md`
   — a hard requirement (`INVARIANTS.md` INV-14), not optional like the
   artifact templates above; unlike those, it is not hand-edited
   afterward, and it has no `templates/` treatment of its own (it isn't
   an artifact type, INV-20 doesn't apply to it). Also copy
   `templates/roles.template.json` to `IAM/roles/roles.json` (filled in
   with its default agile-role mapping) and `templates/users.template.json`
   to `IAM/users/users.json` (empty array) — both a hard requirement
   (`INVARIANTS.md` INV-16). Neither gets a `templates/` of its own — see
   the two exceptions noted in step 4 above. **Then immediately run `/user-add` for at least one
   person** — unlike every other on-demand artifact, deployment is not
   actually complete with an empty `users.json`: a project must have at
   least one active user (INV-16). Ask the user who that first
   registered user should be and what role they hold if it isn't obvious
   from context. Run `/show-backlog` once immediately after creating
   `BACKLOG.md` so its sections reflect the real, likely still-empty,
   indexes from the start, rather than leaving any template's
   `{{PLACEHOLDER}}` text in place. Also copy
   `templates/journal.template.jsonl` (empty) to
   `development/journal.jsonl` — a hard requirement (`INVARIANTS.md`
   INV-17). From this point on, every command that creates, modifies,
   closes, or retires a rule-linked artifact, rule, domain, or work item,
   or changes a `Status` field, appends one entry to it as its last step
   (`CODE-OF-CONDUCT.md` §9) — including every step of this instantiation
   itself from here onward.
7. Create a root-level `README.md` in the deployed framework directory that
   explains the project's rule-and-workflow structure, the deployment path,
   and the main artifact folders. This README should be created during both
   deployment and synchronization so the deployed framework always has a
   custom, project-specific landing page. In addition, create a `README.md`
   in every major deployed folder (`rules/`, `rules/domains/`,
   `requirements/`, `features/`, `IAM/users/`, `IAM/roles/`,
   `development/`, `development/roadmaps/`, `development/bugs/`,
   `development/house-keeping/`, `development/meta-tags/`, `work-items/`
   and each of its type folders) and in every `templates/` subdirectory
   (INV-20) that briefly explains that folder's purpose and link to it
   from the root README so the structure is discoverable and
   self-documenting.
8. Create a starter requirements document in `requirements/` based on the
   project's rule documents (for example, a description document such as
   `UI-Rules.md` for UI rules or `business-rules.md` for business rules) and
   keep it aligned with the rule IDs or source documents that define the
   expected behavior. Requirements must be concrete and tied to specific
   application areas, screens, flows, or components, because they are the
   basis for tests and for the bugs that will later be raised when the
   behavior is wrong.
9. Create your first rule document(s) with a `## Contents` heading and a
   `## Known Bugs — Quick Index` heading (even if empty) — the rest fills
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

Nothing below the work-items layer changes. Above it:

- Using Scrum → keep everything as templated (`sprints/` included, skip
  `boards/`).
- Using Kanban → skip `sprints/`; use `boards/` (`BOARD-NNNNNN`) instead —
  a WIP-limited `Status` value set on stories/tasks, referencing the
  board in place of sprint membership (`Rules-of-Rules.md` §8,
  `rules-of-work-items.md` §6).
- Using something else entirely → the framework's hard requirement is
  only §1 of `rules-of-development.md` (no development without a
  targeted rule) — everything above that is replaceable with whatever
  process vocabulary your team actually uses, as long as it still
  bottoms out in `REQ-`/`BUG-`/`HK-` docs.

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
   framework skeleton (work-items, requirements, features) around it.
   That rule document stands in for the starter requirements doc in §1
   step 8 — there is no product behavior yet to write requirements
   against.
5. As soon as real application code starts, that work is a normal `REQ-`
   (per `CODE-OF-CONDUCT.md` §1) against a business/UI rule document
   created the usual way — the greenfield path only front-loads the
   tooling layer, it does not replace the rest of the chain.

## 4. Retrofitting an existing project

1. Do **not** try to write every rule up front. Start with
   `Rules-of-Rules.md`, `CODE-OF-CONDUCT.md`,
   `rules-of-work-items.md` (or your project's equivalents) and an empty
   `rules/domains/` directory.
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
5. Once rules exist, retrofit `BUG-`/`REQ-`/`HK-` docs for any
   already-known issues (a "Known Bugs" index is a good source), citing
   the rule IDs from step 4.
6. Add a one-line header to each of your project's rule and process files
   noting which template in this framework they instantiate, e.g.:
   ```
   > Instantiates [the catalyst framework rules template](../../development-framework/rules-of-rules.template.md).
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
resolved `agent-source` (§1) in the persistent memory store, if one is
available, so later sessions can recover which project this framework was
deployed into without having to rediscover it. This is a convenience
cache, not the source of truth: `<app-name>.catalyst` at the project root
is always tracked and always present regardless of memory-tool
availability, and `.catalyst-proj/DEPLOYMENT.md` inside the working copy
carries the fuller deployment/repo record — either can be read fresh each
session with no memory tool at all.

Keep a compact note with at least:

- the framework name (`catalyst framework`)
- the deployed project path
- the resolved `agent-source` path (where `.catalyst-proj/` actually lives)
- the date or context of the instantiation
- any short notes that help identify the project later

When this guide is used again for the same project, check memory first and
reuse the existing note as the default project context. If a prior note
already exists for that project, update it instead of creating a duplicate.
This makes the association durable across sessions and keeps the project's
instantiated ruleset available whenever the guide is used again.

At the end of a successful instantiation via the retrofit path (§4), if the
project currently has no bugs, features, house-keeping items, or other
tracked work items yet, propose running
[`analysis-playbook.md`](analysis-playbook.md) next to help bootstrap the
first round of project-specific rules and evidence — it reads an existing
codebase, so it does not apply after the greenfield path (§3), whose
dev-environment rule document already is the first round of rules.
