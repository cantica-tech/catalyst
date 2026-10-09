# Catalyst Invariants

The non-negotiable rules of the catalyst framework, extracted into one lean file
so they can be re-read cheaply and survive context compaction. This is the
**canonical** copy; in the `catalyst` repository, `BOOTSTRAP.md` §0 mirrors it and
`INSTANTIATION-GUIDE.md` §1 is the prose origin. If those disagree with this file, this file wins and the
others should be corrected.

Keep this file short. Anything that needs explanation, examples, or rationale
belongs in the guide it came from — not here. A bloated invariants file decays
faster and is the first thing a summarizer mangles.

The active process module adds its own invariants in its
`INVARIANTS.module.md` (`MODULE-SPECIFICATION.md` §6.4), read together with
this file. An invariant that moved to a module keeps its number here as a
one-line placeholder; numbers are never reused.

## Behavioural

- **INV-1 — Repo-scoped references.** Never mention a local drive, folder, or
  path when referring to catalyst. Only the git repository and repository name.
- **INV-2 — Install only when asked.** Loading or reading catalyst never
  installs it. Install into a project only on the user's explicit request
  (`catalyst init`, `/project create`, or asking in plain words), via the
  instantiation procedure; otherwise at most offer to.
- **INV-3 — Name it "catalyst".** Always "catalyst" / "catalyst framework"
  thereafter, in guidance, memory, and discussion. The framework is the
  **kernel** (`framework/kernel/`, everything independent of process
  modules, versioned by the root `version.txt`) plus its **process
  modules** (each versioned in its own repository). Call the
  module-independent part "the kernel", never "the framework core".
- **INV-4 — Assent before push.** Never push anything (project or catalyst)
  without the user's explicit assent. No target-repo commit without assent.
- **INV-25 — Act without asking, except where it breaks something
  fundamental.** Creating, reading, or updating an entity proceeds by
  default, without pausing for the user's authorization — routine,
  reversible, purely-local writes are not gated behind a confirmation
  prompt. The agent still stops (or refuses) when acting would violate a
  documented `rules-of-rules` provision or a fundamental invariant (this
  file) — INV-4's push gate, an INV-16 violation, or anything the
  framework's own text already calls hard-to-reverse, externally-visible,
  or destructive keep their existing gates untouched. Not a relaxation of
  any of those; it only removes confirmation pauses that were advisory in
  the first place (e.g. `rr-META-011`'s role-mismatch check).
- **INV-29 — Atomic, real-time artifact updates.** Catalyst's own
  artifacts (an artifact's own record, a `Status` field, a journal entry) are
  updated as the work they describe actually happens, at the smallest
  atomic unit practical — never reconstructed retroactively in one batch
  once work is already underway or done. Delayed, batched updating is
  permitted only when explicitly stated **before** the work begins, by
  whoever is doing it (agent or human); absent that explicit statement
  beforehand, real-time atomic updating is the default, not a
  convenience-driven choice made after the fact
  (`Rules-of-Rules.md` rr-META-023).

## Structural

- **INV-5 — Chain invariant.** No work without a traceable link down to a
  documented grounding artifact: an active-module artifact grounds to the
  module's grounding type (a kernel rule) → domain. The active module
  declares its `grounding_type` (`MODULE-SPECIFICATION.md` §5) and each of
  its ETDs specifies `grounding` as `required` (linking directly to the
  grounding type), `inherited` (inheriting its parent's link), or `none`.
  Every document, domain, and rule has a stable, permanent, never-reused
  ID. Extended upward through `epic → story → task →` when an agile
  project-management plugin is active (INV-22) — `work-items/` doesn't
  exist otherwise, so the chain can't reach through it; without one
  active, the module's grounded artifacts chain directly to their
  grounding → domain. The module's own chain specifics live in its
  `INVARIANTS.module.md` (`MODULE-SPECIFICATION.md` §6.4). At commit
  granularity: every product commit cites an artifact or rule ID that
  resolves in the deployment, or its subject starts `chore:`; merges are
  not checked (`catalyst hook commit-msg`, `catalyst trace`, `CLI.md`).
- **INV-6 — The criterion lives in catalyst's space; one tracked file.**
  A project's criterion (its working copy) is
  `$HOME/.catalyst/projects/<name>/criterion` (`CATALYST_HOME` overrides
  `$HOME/.catalyst`); a VS Code workspace's meta criterion is
  `$HOME/.catalyst/workspaces/<name>/criterion`. Nothing of it sits in the
  project: the project tracks only `catalyst.toml` (project root), which
  names the project and pins versions and never holds a path. catalyst
  creates or edits no other project file — no Taskfile, no code artifact.
  It is found
  the same way by every agent, the UI, hooks and CI (`catalyst where`), and
  runs from its own `.venv` (`catalyst runtime install`). Shared (INV-18),
  the criterion is its own git repository with a remote. Legacy
  deployments — `<app-name>.catalyst` with a `.criterion` symlink, directory
  or submodule, or a pre-0.37.0 `agent-source` — are read for one minor and
  moved with `catalyst move`.
- **INV-7 — Descriptive naming.** Every rule, dev-artifact, and domain file is
  `<id>-<short-summary>.md` (sub-domain: `<prefix>-<PARENT>.<SUB>-<summary>.md`).
  Bare-ID filenames are invalid.
- **INV-8 — No orphan rules.** Every rule lives in its type directory, appears in
  its local type index, and appears in the global `rules.md`. Exactly one
  *current* `TEMPLATE-RULE-vN.md` (the highest `N`), in `rules/templates/`
  (INV-20) — never at the `rules/` root directly.
- **INV-9** — owned by the active module (`MODULE-SPECIFICATION.md` §6.4);
  never reused.
- **INV-14** — owned by the active module (`MODULE-SPECIFICATION.md` §6.4);
  never reused.
- **INV-15** — owned by the active module (`MODULE-SPECIFICATION.md` §6.4);
  never reused.
- **INV-16 — At least one active user; advisory role signing.**
  `IAM/users/users.json` and `IAM/roles/roles.json` always exist, and
  `users.json` must contain **at least one user with `"active": true`** —
  a hard requirement, not optional-if-empty like an artifact index. Every
  active-module artifact, rule-linked artifact, and work item carries a
  `Signed-off-by` field. Role checks against `roles.json` are advisory — a
  mismatch proceeds anyway, noted rather than paused for (INV-25), never
  a hard block, since catalyst cannot verify who is actually typing.
  `/user-remove` never deletes a user's entry; it sets `"active": false`,
  and refuses if doing so would leave zero active users — this specific
  case isn't advisory, since it would break this invariant's own hard
  requirement (INV-25's fundamental-invariant exception).
- **INV-17 — Append-only, replayable journal.** `development/journal.jsonl`
  always exists (empty is fine). Every command that creates, modifies,
  closes, or retires a rule-linked artifact, rule, domain, or work item, or
  changes a `Status` field, appends exactly one entry — timestamp, actor,
  command, action, artifact ID, `targets` (rule IDs, when applicable), one
  or more `intent` statements (the goal driving the change, not just a
  label), and, per touched file, its content hash immediately before and
  immediately after (`git hash-object -w`, written to the object store so
  it's retrievable independent of any commit; `null` for create/delete).
  This makes the journal transaction-log-grade: replaying entries up to
  any timestamp and materializing each file's last `after` hash as of
  that point reconstructs the exact tree state then, via `/journal-restore`
  into a side directory — never overwriting the live tree outright.
  Entries are immutable once written: never edited, deleted, or reordered.
  A product commit after the pointer's `journal_since` whose changes no
  entry records was made outside catalyst: it is detected, and adopted
  into the journal or reverted, never silently left (`/adopt`).
  Complements — does not duplicate — the `catalyst-git` plugin's
  continuous compliance auditing of a *deployed project*; this journal is
  core, applies to catalyst's own deployment too, and records history
  rather than flagging violations.
- **INV-18 — Shared deployments on git.** A deployment is shared
  (`repoed: true`) once `catalyst criterion create <url>` publishes its
  working copy to a criterion repository and makes `.criterion` a
  submodule of the product repository; every product commit then pins
  the rules in force. Contributors land changes only through pull
  requests against the shared branch (`criterion_branch`):
  `catalyst criterion push` commits, rebases (the journal and generated
  indexes merge by union), runs `catalyst check` and
  `catalyst criterion integrity`, and pushes a topic branch; the same
  two checks run in the criterion repository's CI, and
  `catalyst criterion protect` makes them required. A real conflict
  stops the push with nothing pushed; the agent never applies a merge —
  it may record a proposed resolution as a `RECON-` case for a human to
  accept (INV-21). Identity is self-declared: branch protection and
  pull-request review are the real controls. `Rules-of-Rules.md` §13.
- **INV-19 — Project lifecycle commands.** `/project create <name>`
  installs a fresh deployment: a working copy in agent-owned space (or
  the in-project fallback) plus its `<app-name>.catalyst` pointer.
  `/project remove <name>` un-links the pointer locally only — the
  working copy, this agent's memory note, and any `criterion` repo are
  all left untouched (never delete, retire in place). `/project remove
  <name> force` additionally deletes the local working copy and this
  agent's memory note for the project — confirm explicitly first; never
  touches a `criterion` repo, which is a separate, externally-hosted
  artifact out of scope for a local removal. `/project export <name>
  [file]` bundles every file under the working copy into one JSON
  export. `/project import <file>` installs from a bundle, refusing if a
  deployment already exists here; `/project import <file> force`
  overwrites an existing one instead — confirm explicitly first.
- **INV-20 — Uniform artifact-type layout.** Every artifact-type
  directory carries a versioned, catalogued `templates/` subdirectory
  (`README.md`, `templates-<type>.md` catalog with a Timestamp column,
  `TEMPLATE-<TYPE>-vN.md` — files only, never a subfolder, never edited
  in place once a newer version exists) and its own `README.md`; the
  artifact-type root itself accepts files and folders at any depth for
  the actual artifacts. Artifact types, their storage directories, and
  relationships are defined by Entity Type Definitions (ETDs) in the active
  module manifest (`MODULE-SPECIFICATION.md`). Domains nest under
  `rules/domains/` (they exist only to group rules). `IAM/users/`, `IAM/roles/`
  replace bare `development/users.json`/`roles.json`, and carry the same `templates/`
  treatment as every other type — `TEMPLATE-USERS-vN.json`/
  `TEMPLATE-ROLES-vN.json` version the registry's seed shape, since each
  registry is one JSON file (`{"users": [...]}`, `{"roles": [...]}`)
  rather than one-file-per-instance.
  `work-items/` is not part of this core set — see INV-22.
- **INV-21 — Reconciliation entity for diverging versions.** A
  `RECON-NNNNNN` (`reconciliations/`, top-level, full INV-20 template
  treatment) is the durable record of two entity versions that
  disagree — a conflict that stopped `/criterion push` (INV-18), a
  rights-mismatch against `IAM/roles/roles.json`, or a manually opened
  one — and of the human decision that settles it. Like `WORKFLOW-`, it is never itself work: no `Targets` rule
  field; its chain runs sideways via an `Entity` field naming the
  disputed artifact. Never file-versioned per round — each round of
  back-and-forth is a new row in the same file's `Revisions` section,
  edited in place and journaled like any other artifact (INV-17). Resolved via
  `/reconcile <id> accept|accept-with-edits|reject|propose <text>|close`,
  moving `Status` through `Open`/`Under Review`/`Resolved-*`/`Closed` —
  who can resolve one is genuinely gated by the actor's role
  (`reconciliation: full|propose|none` in `IAM/roles/roles.json`), the
  one deliberate exception to `rr-META-011`'s advisory-only principle:
  `propose` may only move a case to `Under Review`, `none` is refused
  outright, and only `full` can reach a `Resolved-*` status — see
  `Rules-of-Rules.md` §16. May optionally name a `Workflow` field (a
  `WORKFLOW-NNNNNN`, INV-24) to guide its resolution — read before
  choosing a verb, when present.
- **INV-22 — Content-contributing plugins.** A plugin's
  `working-contract.md` may carry an optional `## Contributes` section
  naming artifact-type folder(s) (full INV-20 treatment) and/or
  slash-command file(s) it deploys into the target project.
  `/catalyzer activate` materializes this content — the same mechanism
  instantiation uses to copy core templates in;
  `/catalyzer deactivate` removes exactly what was added, never
  artifact instances the deployment already created with it. Two
  content-contributing plugins that would deploy the same artifact-type
  folder must not both be active. `work-items/` (`BOARD-`/`EPIC-`/
  `SPRINT-`/`STORY-`/`TASK-`/`SPIKE-`/`TICKET-`) is the
  first type moved to this model — no longer core (INV-20), it only
  exists once a project-management-type plugin extending the schema at
  `plugins/_prototyping/project-management/agile/` is activated; none
  exists yet. The chain invariant (INV-5) is conditional on this: the
  `epic → story → task →` prefix applies only when such a plugin is
  active. Plugins under `plugins/_prototyping/` are exempt from INV-11's
  separate-repository requirement until they graduate out of it.
- **INV-23 — Frozen entity definitions.** Every real entity type has a
  short, versioned prose definition (`definitions/README.md`) explaining
  what it is and what it's for, deployed to `.criterion/definitions/
  <type>.md`. Once deployed, that file is frozen forever: `/sync-framework`
  only ever creates a missing one (a type introduced since the project's
  last sync), never overwrites an existing one, no matter how far the
  framework's own copy has moved on. The only sanctioned way to move a
  deployed definition forward is `/migrate-definition <entity-type>
  <version>`, and only to a version number that actually exists in this
  framework's `definitions/<entity-type>/` folder.
- **INV-24 — Workflow entity for guided procedures.** `WORKFLOW-NNNNNN`
  (`templates/workflow.template.md`) is a process-definition document —
  a repeatable multi-step procedure, `Status` `Active`/`Deprecated`,
  never itself work. Core, not plugin-gated: its own top-level
  `workflows/` folder, sibling of `reconciliations/`, always present,
  full INV-20 treatment, no `/create-workflow` command (authored ad hoc,
  same posture as `RECON-`). Other core entities may optionally
  reference one by ID to guide their own process — `RECON-`
  reconciliation is the first (INV-21, `Rules-of-Rules.md` §16/§19).
- **INV-26 — Signed entity IDs.** Every registered user
  (`IAM/users/users.json`) carries a `userid`: 8 characters,
  case-sensitive alphanumeric, containing at least one uppercase
  letter, drawn cryptographically at `/user-add` time and regenerated
  on collision against every existing `userid` in the registry
  (`Rules-of-Rules.md` rr-META-011). From that point on, every rule,
  `WORKFLOW-`, and `RECON-` ID, and every ID of an active-module entity
  type (`<PREFIX>-NNNNNN`), carries its creator/signer's `userid` as a
  trailing `-XXXXXXXX` suffix, assigned once at creation and never changed
  thereafter
  (`Rules-of-Rules.md` rr-META-020). A rule ID's sequence number is
  6-digit, not 3 (`Rules-of-Rules.md` rr-META-003) — zero-padded
  before the suffix is appended, never after. A rule's suffix is its
  signer's, named like any other with `catalyst id next-rule --as
  <signer>` (`CLI.md`); domains have no numeric ID and are out of scope
  for this suffix entirely. A user must have a
  `userid` before any entity it signs can be assigned its suffix —
  this ordering is not optional.
- **INV-27** — owned by the active module (`MODULE-SPECIFICATION.md` §6.4);
  never reused.
- **INV-28** — owned by the active module (`MODULE-SPECIFICATION.md` §6.4);
  never reused.
- **INV-30 — The kernel is module-agnostic.** The kernel
  (`framework/kernel/`), catalyst's tooling (`scripts/`) and root documents
  never name a specific process module or any of its entity ID prefixes,
  folders, commands, templates or definitions; only generic references
  ("the active module", `<entity-type>`). Module content lives in the
  module's own repository and is composed into deployments
  (`MODULE-SPECIFICATION.md` §6). Enforced by
  `scripts/check_kernel_purity.py`, which derives its denylist from the
  modules in `framework/modules/catalog.md`.

## Plugins

- **INV-10 — Activation gate.** A plugin is not loaded unless activated via
  `/catalyzer`, and only if it carries `README.md` + `working-contract.md`.
- **INV-11 — Plugin provenance.** Every plugin has its own repository; no plugin
  is sourced from the framework repository.
- **INV-12 — Contract is canonical + stable.** Every plugin's
  `working-contract.md` carries the six metadata fields (Name, Description,
  UUID, Version, Active, Type). The UUID is generated once and never changes.
  `Version` matches the plugin's own `version.txt` and its catalog pin. The
  framework reads `Active` at startup to decide what loads.
- **INV-13 — Operate on the deployment, not on catalyst.** A plugin's runtime
  target (monitoring, auditing, mutation) is the *deployed project's* repository,
  resolved at activation time — never the catalyst framework's own repository and
  never the plugin's own installation directory under `plugins/<type>/<name>/`.
