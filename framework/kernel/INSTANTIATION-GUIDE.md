# Instantiation Guide

How to stand up this framework in a project — new or existing — so it
creates concrete rules for that particular project.

## 1. New project

> Hard rule: when referring to catalyst, the model SHALL NEVER mention any
> local drive, local folder, or local path. References to catalyst must stay
> scoped to the git repository provided by the environment and the repository
> name itself.
>
> Hard rule: catalyst is installed into a project ONLY when the user
> explicitly asks for it (`catalyst init`, `/project create`, or in plain
> words). Loading or reading catalyst never installs it; at most, offer to.
>
> Hard rule: after that first installation, the framework MUST be referred to
> as "catalyst" or "catalyst framework" in all subsequent guidance,
> memory, and discussion, whether or not it has already been loaded before.
> Its module-independent part (`framework/kernel/`) MUST be referred to as
> "the kernel"; the framework is the kernel plus its process modules.
>
> Hard rule: the model SHALL NEVER push anything in this project, catalyst,
> without the user's explicit assent.

An install is two kinds of work. Everything mechanical — the working copy's
skeleton, the composed governing documents, the seeded module, definitions,
the first user, the journal, the vendored CLI and runtime, the criterion in
`$HOME/.catalyst/projects/<name>/criterion` and `catalyst.toml` — is one
deterministic command, `catalyst init` (step 4, `CLI.md`). What stays with the
agent is judgment: the project's name, its module, its rule documents, its
first user, and, afterwards, its first rules.

1. Decide your rule document(s) and their prefixes based on the project’s
   actual structure (e.g. one document per natural seam in the system — UI
   vs. backend, or per-service in a multi-service repo). Pick a short
   lowercase prefix per document. Each becomes one `--rule-doc
   <file>:<prefix>` (e.g. `business-rules:br`); with none, `catalyst init`
   creates `<name>-rules.md` with prefix `br`.
2. Resolve the project name. Look for a project-local `dev-instructions.yaml`
   in the project where this guide is being run. If it exists, read its
   `name` value; if it does not, ask the user for the project name and use
   the current project root directory name as the default.
   ```yaml
   name: "project-name"
   ```
   The `name` must be a simple project identifier, not a full path or a
   nested object; the pointer becomes `<name>.catalyst`. `catalyst init`
   builds the standard layout (step 3); an optional `layout` key left in an
   older bootstrap file is not applied — tell the user if one is present.
   After the install completes successfully, remove `dev-instructions.yaml`:
   it was only bootstrap metadata.
3. Resolve the rest of `catalyst init`'s inputs:
   - **The active module** (`--module <id>`). There is no default module; if
     the user has not said which one, `catalyst init` without `--module`
     lists the modules checked out next to the project or to catalyst as
     `catalyst-<id>` (production modules: `framework/modules/catalog.md`):
     propose one and ask. For one elsewhere, pass `--module-dir <dir>` (a checkout of the module's
     repository at the release matching this kernel version). Like plugins,
     a module is never sourced from this framework repository.
   - **The first user**, registered as Admin (INV-16): `--user` defaults to
     `git config user.name`; ask for the git username (`--git-username`).
   - **The agent** (`--agent <id>`, e.g. `claude-code`), recorded in the
     pointer's `agent` field; it also places the command files
     (`--commands-dir` overrides).
   - Optionally, **where the project's tests live** (`--test-locations`),
     which fills `{{TEST_LOCATIONS}}` in `Rules-of-Rules.md` §2 — on the
     greenfield path this comes out of the testing decision (§3).
4. **Run `catalyst init`** from the project root (or pass `--project
   <root>`), with `--kernel <framework/kernel>` of the catalyst checkout or
   kernel release when running the zipapp. It refuses if the project
   already has a `*.catalyst` pointer or a `.criterion` (one holding only
   the install ledger, `.ledger/`, is adopted), or if the target location
   is not empty. In order, it:
   - composes `CODE-OF-CONDUCT.md` (the kernel's
     `rules-of-development.template.md` with the module's
     `code-of-conduct.module.md` §3/§4 inserted under
     `### From module <module-id>`), `rules/Rules-of-Rules.md` (the kernel's
     `rules-of-rules.template.md` with the module's
     `rules-of-rules.module.md` appended), `ACCESS-CONTROL.md` (verbatim) and
     `Taskfile.common.yml` (the kernel's tasks, then the module's), resolving
     `{{RULES_DIR}}`, `{{RULE_DOCS_LIST}}` and `{{TEST_LOCATIONS}}` and
     signing meta-rule IDs with the first user's userid
     (`MODULE-SPECIFICATION.md` §6);
   - seeds the whole module into `modules/<module-id>/` (never cherry-picked
     files);
   - creates every entity folder with the uniform shape (INV-20): its
     `templates/` (`README.md`, the `templates-<type>.md` catalog with a `v1`
     row, `TEMPLATE-<TYPE>-v1.md`), its `README.md` and its `<folder>.md`
     index — the kernel's `rules/` (with `rules.md` listing the rule
     documents, and each rule document seeded with `## Contents` and
     `## Linked Artifacts — Quick Index`), `rules/domains/`,
     `reconciliations/`, `workflows/` and `development/meta-tags/`, plus one
     per module entity type at the place its ETD names (`location`), and
     every path the module's manifest requires;
   - copies the latest definition of every kernel and module type to
     `definitions/<type>.md`, with `definitions/README.md` — frozen from
     then on (INV-23, step 7 below);
   - writes `IAM/users/` and `IAM/roles/` with their templates, registers
     the first user with a fresh userid as Admin, and seeds `roles.json`
     from the kernel's default role mapping (INV-16, INV-26);
   - writes an empty `development/journal.jsonl`, `version.txt`,
     `DEPLOYMENT.md` (project, kernel, module and version, installer) and a
     root `README.md`, copies `ANALYSIS-PLAYBOOK.md` and `INVARIANTS.md`,
     and vendors the CLI at `bin/catalyst.pyz` (`INVARIANTS.md` is what the
     session-start hook of step 5 re-injects);
   - builds the criterion at `$HOME/.catalyst/projects/<name>/criterion`
     (refusing a name already used on this machine) with its runtime in
     `.venv`, and writes `catalyst.toml` at the project root — no path in
     it, the only file catalyst adds to the project; its `journal_since` is
     the project's `HEAD`, or `""` with no commit yet — the baseline after
     which changes made outside catalyst are detected;
   - with `--commands-dir`, writes one command file per command of the
     composed `CODE-OF-CONDUCT.md` §4 (the kernel's and the module's);
   - initialises the working copy's own git history, and journals the
     install as its first entry.

   It commits nothing in the project repository. From here on,
   `catalyst <args>` means `python3 .criterion/bin/catalyst.pyz <args>`.
   `work-items/` is **not** built — it only comes into being if a
   project-management-type plugin is activated later (`Rules-of-Rules.md`
   §8, INV-22; `ARTIFACT-LAYOUT.md`).

   The resulting working copy (the module's folders vary by module):
   ```
   <agent-owned location>/.criterion/     # reached as <project root>/.criterion
     .git/                  # the working copy's own history
     ACCESS-CONTROL.md
     ANALYSIS-PLAYBOOK.md
     CODE-OF-CONDUCT.md
     DEPLOYMENT.md
     INVARIANTS.md
     README.md
     Taskfile.common.yml
     version.txt
     bin/
       catalyst.pyz
     definitions/
       README.md
       <type>.md
     modules/
       <module-id>/         # the whole module tree
     rules/
       templates/           # README.md, templates-rule.md, TEMPLATE-RULE-v1.md
       domains/
         templates/
         README.md
         domains.md
       README.md
       Rules-of-Rules.md
       rules.md
       <rule-doc>.md        # one per --rule-doc
     <folder>/              # a module entity type with no `location`
       templates/
       README.md
       <folder>.md
     reconciliations/       # templates/, README.md, reconciliations.md
     workflows/             # templates/, README.md, workflows.md
     IAM/
       users/               # templates/, README.md, users.json
       roles/               # templates/, README.md, roles.json
     development/
       <folder>/            # a module entity type with `location: development`
       meta-tags/           # templates/, README.md, meta-tags.md
       journal.jsonl
   ```
   The framework only cares that the chain from every active-module
   artifact to its grounding type (a kernel rule) to a domain stays intact
   (INV-5), not the folder names. The module's meta-rules
   (`rules-of-rules.module.md`, composed above) say what each of its types
   is for; the kernel never names them (INV-30). `plugins/<type>/<name>/`
   appears when a plugin is activated; `.ledger/` holds the agent's install
   ledger (`BOOTSTRAP.md` §3).
5. **Wire the agent and the project's tasks.** Register the agent's hooks
   the way its shim says (`CLI.md` "Hooks"), where it supports them:
   `catalyst hook start` at session start, so every later session starts
   grounded, and `catalyst hook stop` at the end of each turn. For Claude
   Code, merge `agents/claude-code/settings.template.json` (both hooks) into
   the project's `.claude/settings.json`. An agent without command files instead
   exposes each command of the composed `CODE-OF-CONDUCT.md` §4 as a named
   procedure and lists them in the deployed `README.md` (`BOOTSTRAP.md` §1)
   — the composed §4 is the canonical list; never re-enumerate a subset of
   it anywhere else. Never create or edit the project's own `Taskfile.yml`
   (or any other file of the project but `catalyst.toml`): the composed
   `Taskfile.common.yml` stays in the criterion and runs on its own, from
   the project's root, with `catalyst task <command> -- <arguments>`
   (`catalyst task` alone lists them).

   **Offer the commit-msg hook.** Every product commit must cite an
   artifact or rule ID, or start `chore:` (INV-5, `CODE-OF-CONDUCT.md` §9).
   Offer to run `catalyst hook install`, which writes the project
   repository's `.git/hooks/commit-msg`; run it only on the user's assent,
   and if it refuses because a `commit-msg` hook already exists, show the
   user both and let them merge. If the project has CI, offer a step that
   runs `catalyst trace` on the commits each push or pull request adds
   (`--pattern-only` while the deployment is local-only, since CI has no
   working copy; `CLI.md` has the GitHub Actions snippet). Commits made
   before either existed are not checked.
   When plugins are needed, pull their content directly from each plugin's
   own repository; no plugin may be sourced from this framework repository.
6. **Populate what the module requires.** If a document the module's
   meta-rules or invariants require at instantiation (for example a
   generated summary) still carries template `{{PLACEHOLDER}}` text, run
   the command the module names to populate it. Additional users are added
   with `/user-add`.
7. **Definitions stay frozen.** `catalyst init` copied only the *latest*
   `DEFINITION-<TYPE>-vN.md` of each kernel and module type into
   `.criterion/definitions/<type>.md` (flat; the versioned subfolders are
   source structure only). This never runs again for a type that already
   has a deployed definition — see `SYNCHRONIZE.md`'s definitions
   carve-out; only `/sync-framework` adding a brand-new type, or an explicit
   `/migrate-definition`, ever touches one after this (INV-23).
8. **Customise the landing page.** The root `README.md` `catalyst init`
   writes is a stub: extend it with the project's rule-and-workflow
   structure and links to each folder's `README.md`, so the structure is
   discoverable. `ACCESS-CONTROL.md` stays verbatim (refreshed only by
   `/sync-framework`).
9. Create whatever starter artifacts the active module's meta-rules call
   for, based on the project's rule documents (for example, a description
   document such as `UI-Rules.md` for UI rules or `business-rules.md` for
   business rules), and keep them aligned with the rule IDs or source
   documents that define the expected behavior. Starter artifacts must be
   concrete and tied to specific application areas, screens, flows, or
   components, because later work is grounded on them. Every one is
   journaled with `catalyst journal append` (`CODE-OF-CONDUCT.md` §9), like
   every later change.
10. Write your first rules into the seeded rule document(s), each per
   `Rules-of-Rules.md` §6 and in the domain it belongs to (`rules/domains/`,
   §7), so the framework produces rules that are specific to this project.
   This is a hard requirement: every rule is listed in its document's
   `## Contents` and in the global `rules.md` index (INV-8), and every rule,
   development-artifact and domain file follows the descriptive format
   **`<id>-<short-summary>.md`** — bare IDs are not acceptable (INV-7); a
   domain file is `<prefix>-<CODE>-<short-summary>.md` (or
   `<prefix>-<PARENT>.<SUB>-<short-summary>.md` for a sub-domain,
   `Rules-of-Rules.md` §7). There is exactly one *current*
   `TEMPLATE-RULE-vN.md`, in `rules/templates/` (INV-8, INV-20). Allocate
   each rule ID with `catalyst id next-rule <doc-prefix> <DOMAIN> --as
   <signer>`.
11. Finish with `catalyst check`. Resolve every error before calling the
   install done; warnings may remain, and are reported to the user. Present
   the deployed tree; nothing is committed or pushed without the user's
   assent (INV-4).

## 2. Choosing your agile flavor

`work-items/` is plugin-only (§1 step 4, `Rules-of-Rules.md` §8) — this
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
  only §1 of `CODE-OF-CONDUCT.md` (no development without a
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
   product behavior. Add it to the rule document list from §1 step 1, so
   `catalyst init` seeds it (`--rule-doc dev-environment-rules:env`), and
   run the install (§1 steps 2–5) before step 2 below: its domains and
   rules need the working copy to exist.
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
     for every rule created afterward, including application rules (pass
     it as `--test-locations` if already decided at install, else edit it
     into the deployed `Rules-of-Rules.md` §2).
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
   and rules, continue with §1 steps 6 onward. That rule document stands
   in for the starter artifacts in §1 step 9 — there is no product
   behavior yet to ground them on.
5. As soon as real application code starts, that work is a normal
   active-module artifact (per `CODE-OF-CONDUCT.md` §1) against a
   business/UI rule document
   created the usual way — the greenfield path only front-loads the
   tooling layer, it does not replace the rest of the chain.

## 4. Retrofitting an existing project

1. Do **not** try to write every rule up front. Start with what
   `catalyst init` gives you (§1): `Rules-of-Rules.md`,
   `CODE-OF-CONDUCT.md` and an empty `rules/domains/` directory.
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
   bullets get `NNNNNN` (`catalyst id next-rule`); enumerated sub-cases inside one bullet get
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
- the criterion's location (`catalyst where`)
- the date or context of the instantiation
- any short notes that help identify the project later

When this guide is used again for the same project, check memory first and
reuse the existing note as the default project context. If a prior note
already exists for that project, update it instead of creating a duplicate.
When switching agents, update this persistent memory note alongside
`catalyst.toml` (`agent`, `updated`).
This makes the association durable across sessions and keeps the project's
instantiated ruleset available whenever the guide is used again.

At the end of a successful instantiation via the retrofit path (§4), if the
project currently has no active-module artifacts or other tracked work
items yet, propose running
[`ANALYSIS-PLAYBOOK.md`](ANALYSIS-PLAYBOOK.md) (`/run-analysis`) next to help bootstrap the
first round of project-specific rules and evidence — it reads an existing
codebase, so it does not apply after the greenfield path (§3), whose
dev-environment rule document already is the first round of rules.
