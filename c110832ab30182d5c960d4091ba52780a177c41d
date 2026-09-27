# Proposal: a generic entity/workflow kernel, and cutting the repetition tax

**Status:** draft, for review — not committed, not part of the framework's
own governed structure yet.
**Scope:** the `catalyst` framework itself (`framework/`). Does
not touch any downstream host UI directly, though §6 covers what this would
mean for one built on the framework.

## 0. The ask, restated

Two threads, tightly coupled:

1. **Efficiency** — running catalyst (adding an entity type, syncing a
   deployment, dogfooding) burns tokens on repetitive, mechanical work.
2. **Generality & Modular Prompts** — catalyst should eventually govern *any*
   process, not just the one it grew up around. The existing process-specific
   prompts, slash commands, and workflows need to be treated as a discrete
   **process module**, allowing
   catalyst to seamlessly load and swap other prompt modules for different
   project management types (e.g. Agile Scrum, ITIL service management, legal/compliance,
   product management). The actual artifact types + prompt workflows +
   interdependencies should be a **design-time choice** an architect/admin makes
   per deployment, not something hardcoded into the kernel's source.

These aren't separate problems. The repetition *is*, almost entirely, the
cost of every entity type being hand-authored prose baked into the
framework's own template files instead of data a generic engine reads. Fix
the second and most of the first goes away for free.

## 1. Evidence: what adding one entity type actually costs today

This session added two entity types (call them `ITEM-` and `SUBITEM-`) and
one field-widening change (a sub-item's parent: one type only → either of
two types). Each touched, by hand, every time:

- `rules-of-rules.template.md` — new/amended `rr-META-NNN` section, plus
  edits to the ID-format line, the entity-id-suffix list (§20), the
  "where every artifact type sits" list (§15).
- `rules-of-development.template.md` — the §3 type table, the hard-rule
  bullet list, a type-description bullet, the §4 command bullet *and* its
  procedural block, the §6 ID format string, a §7 closing-item bullet.
- `INVARIANTS.md` — a new `INV-N`.
- A new `templates/<type>.template.md`.
- A new `definitions/<type>/DEFINITION-<TYPE>-v1.md`, plus a
  `definitions/README.md` edit.
- `SYNCHRONIZE.md` — a required-artifacts checklist edit *and* a new
  migration paragraph.
- A new `migrations/<version>/*.md` file, plus a `migrations.md` row.
- `templates/Taskfile.common.template.yml` — a new task.
- `scripts/check_deployment.py` — an entity-type list edit.
- `INSTANTIATION-GUIDE.md`, `INSTANTIATION-CHECKLIST.md`,
  `ARTIFACT-LAYOUT.md` — each got its own tree/checklist edit.
- Three separate top-level READMEs (`README.md`,
  `framework/kernel/README.md`, `templates/README.md`) — each
  separately re-describes the same new type in its own words.
- A new `.claude/commands/create-<type>.md`.

**That's 17+ files, by hand, for one entity type** — and then the *entire
list repeats* against catalyst's own dogfooded `.criterion`, and again
against every deployed project's `.criterion`, and again (if there's a
real product on top, like a host UI) in actual application code.

The framework has shipped 17 migrations since `0.11.0`. The pattern
repeats every time. Concretely, in *this session alone*, the repetition
directly caused real drift bugs I had to catch and fix mid-task:
`definitions/README.md`'s type list silently fell out of sync twice; a
`CODE-OF-CONDUCT.md` paragraph was missing entirely from one dogfood copy;
`Rules-of-Rules.md`'s own "where every type sits" list was missing two
entries. Six files independently claiming to be *the* list of entity
types is not a design, it's a liability — the token cost and the
correctness cost come from the same root cause.

## 2. Root cause

The framework's actual reusable machinery — the ID+userid scheme
(`rr-META-003/020`), the uniform artifact-type layout (`rr-META-015`,
INV-20), IAM/signing (`rr-META-011`), the append-only journal
(`rr-META-012`), criterion sync (`rr-META-013`), plugin activation
(`rr-META-017`) — is **already fully domain-agnostic**. None of it
mentions "rule" or any development-artifact type by name. This part is fine as
it stands and should not change.

What's *not* generic is layered directly on top, hardcoded into the
framework's own prose:

- The **chain invariant** itself (INV-5: "no work without a link to a
  documented rule") is one process's assumption wearing a
  framework-wide invariant's clothes.
- Every entity type's **shape** (its fields, which are required, which
  are lists, what they reference) and **workflow** (status enum,
  transition rules, what blocks closing) exist only as scattered prose
  across the ~17 files in §1 — never as one machine-readable source of
  truth a tool could read, generate from, or validate against.
- Existing **process-specific prompts and commands** (such as slash
  commands defined in `.claude/commands/`, agent skills, and workflow
  prompts) are baked directly into kernel prose rather than being
  isolated into a standalone module.
- Adding a type currently means **editing the framework's own source**
  (`framework/*.template.md`) and cutting a framework
  version + migration. There is no way for a deployed project's own
  architect/admin to add a type without either forking the framework or
  asking an agent to hand-edit framework internals on their behalf — which
  is exactly backwards from "design-time choice per deployment."

## 3. Proposed architecture: kernel + profile

Split the framework into two layers:

### 3a. Kernel (stays framework-core, rarely changes)

Everything already domain-agnostic, unchanged: ID+userid scheme, INV-20
uniform layout, IAM/roles/signing, the journal, criterion sync, plugin
activation, `/criterion push`'s vet+merge. Plus one new, deliberately
small primitive:

- **Entity Type Definition (ETD)** — a machine-readable schema, one file
  per type, living in the *deployment*, not the framework:
  `.criterion/schema/entity-types/<TYPE>.yaml`. Declares: id prefix,
  folder, fields (name, kind — `text`/`enum`/`ref`/`ref-list`/`date`),
  cardinality on any `ref`/`ref-list` field, which field(s) are the
  **grounding link** (see below), and a **workflow** block (states,
  which states count as "closed," what a transition requires).
- **Relationship** — declared *on* a `ref`/`ref-list` field: target
  type, optional `backref` name (the field the target type gets for
  free, the way a verifying type's `Items` field would back-populate
  `ITEM.Verified-by`).
- **Grounding type** — the kernel generalizes INV-5 from "must link to a
  rule" to "may declare a grounding type it must link to." A profile
  picks its own grounding type (today's default module's is `rule`; a
  legal profile's might be `policy`, a support-ops profile's might have
  none). A type's ETD says `grounding: required | inherited | none` —
  `inherited` is what a sub-unit-of-work type does (inherits its parent's),
  `none` is what an idea-capture type or `WORKFLOW-` does.

This is genuinely small: one schema format, one generalized invariant,
one place relationships/back-references are declared instead of
re-derived by hand per type.

### 3b. Profile & Prompt Modules (per-deployment, author-owned)

A **profile** is a named bundle containing Entity Type Definitions (ETDs), a chosen grounding type, seed content, and a dedicated **Prompt Module**:

- **Prompt Module concept:** Existing process-specific prompts (entity-creation slash commands such as `/create-item`, release commands, skills stored in `.claude/skills/` or `.claude/commands/`, and procedural instructions) are decoupled from the kernel and packaged as a module (for example `example-process`), while process-agnostic commands such as `/check-rules` stay in the kernel.
- **Pluggable project management types:** By encapsulating prompts into modules, Catalyst can support other modules for different project management types (e.g. Agile Scrum, Kanban, ITIL service management, Product Management, Legal/Compliance tracking, or Physical Engineering).
- **Module structure:** Each project management module bundles its own set of prompt files, slash command definitions (following `.claude/commands/` patterns), agent skills, and ETDs without modifying the Catalyst core kernel.

The framework ships today's process as the **default module/profile**,
authored via ETDs and modular prompts like everything else — dogfooding the new mechanism to
define the old one, rather than keeping two parallel systems.
An architect/admin creates a new type or adapts a process by writing ETD files or attaching a prompt module in their own deployment. No kernel version bump, no migration, no asking an
agent to hand-edit `framework/`. That *is* "design-time
choice, their own way."

### 3c. What a generic engine derives from one ETD and Prompt Module, instead of being hand-written per type

- The human-facing document template (field table + sections) —
  generated once from the ETD, not authored separately.
- `/create-<type>` and workflow prompt behaviors — parameterized by the active prompt module and ETDs. Generic command handlers or modular prompt definitions (like `.claude/commands/` files) read the ETDs and module configuration; no hand-written kernel prose per type or process.
- Validation — orphan/registered/grounding/dangling-reference checks,
  today hand-written per type in `validator.ts`-equivalent logic,
  become one generic pass parameterized by the ETD.
- Back-reference population — a verifying type's `Items` → `ITEM.Verified-by`
  happens automatically because the relationship says so, not because
  someone remembered to write the "append to the other side" step.
- Closing/done criteria — read from the workflow block instead of a
  hand-written §7 bullet.

## 4. Concrete moves that cut token/repetition cost specifically

Some of these are payoffs of §3; a few are independent and can land
first, regardless of the bigger decision:

1. **One canonical entity registry, everything else references it.**
   Collapse the 6 hand-maintained "here's the list of types" copies
   (top-level `README.md`, `framework/kernel/README.md`,
   `templates/README.md`, `INSTANTIATION-GUIDE.md`,
   `INSTANTIATION-CHECKLIST.md`, `ARTIFACT-LAYOUT.md`) into one source
   — under the new model, that's literally "the set of ETD files in the
   active profile" — with the rest either linking to it or generated
   from it. `scripts/check_deployment.py` already validates against the kernel's
   entity types plus the active module's ETDs; extend that pattern to *generate* the docs
   that currently drift, not just check them after the fact.
2. **Scope four-eyes verification to the actual diff.** Today, syncing
   or dogfooding a change re-reads the whole corpus for a second,
   independent pass. When a change is a well-scoped ETD add/edit, the
   independent check only needs to verify that specific schema + its
   generated artifacts, not re-derive the entire deployment's rule
   coverage from scratch. Reserve full blind re-derivation
   (`/dogfood recreate`'s existing mode) for periodic audits.
3. **Leaner journal entries for mechanical changes.** The journal's
   `intent` field is prose because most past changes needed judgment
   calls explained. A schema-driven ETD add is not one of those — a
   structured entry (`{op: "add-entity-type", etd: "ITEM", version:
   "0.30.0"}`) is more honest *and* cheaper than three paragraphs of
   narrative reconstructing what a diff already shows.
4. **Cache what's already been verified.** The journal already tracks
   per-file content hashes before/after. `/check-rules` and `/dogfood`
   could skip re-validating a file whose hash hasn't changed since its
   last clean check, instead of a full-corpus pass every time.
5. **Split session-start cost from task cost.** `INVARIANTS.md` re-injects
   every session (correct — cheap, anti-drift). Heavier guides
   (`INSTANTIATION-GUIDE.md`, `ANALYSIS-PLAYBOOK.md`) should stay
   read-on-demand only, not bundled into routine-session overhead — this
   is likely already true; worth auditing `BOOTSTRAP.md §1`'s actual load
   sequence to confirm nothing heavier than INVARIANTS.md loads by
   default.

## 5. Migration path & phasing (this is itself a framework change — same discipline)

Backward-compatible, phased, each phase independently shippable (a detailed step-by-step plan for the extraction lives in the default module's own repository, listed in `framework/modules/catalog.md`):

- **Phase 0 (no architecture change, ships immediately):** the quick
  wins in §4 that don't depend on ETDs existing — registry
  consolidation for the 6 duplicated doc lists, journal entry
  leaning-out for mechanical ops, hash-based check caching.
- **Phase 1 (module spec & kernel generalization):** define the ETD schema format, `module.yaml` manifest structure, and generalize INV-5 into the grounding-type concept. No existing deployment's behavior changes yet — this only adds the *capability*.
- **Phase 2 (default module extraction):** re-express today's hardcoded
  development-artifact types as the default module's own ETDs, slash
  commands (`/create-<type>`, etc.), and templates, and the process-agnostic
  ones (`WORKFLOW`, `RECON`) as kernel ETDs. A migration (like every
  past one) converts a deployment's existing hardcoded shape into
  module-backed form, byte-for-byte compatible — existing artifacts don't
  move or get renamed.
- **Phase 3 (generic engine & prompt loader):** the agent's own procedures
  (`/create-<type>`, validation, sync) become module/ETD-driven instead of
  reading hardcoded prose. This is where the token savings in §4 items
  2–4 actually land in the agent's real day-to-day behavior.
- **Phase 4 (author tooling & multi-module validation):** a real `/create-entity-type` (or
  equivalent) command so an architect/admin authors a new ETD or module
  conversationally, without hand-writing YAML, and validation against modules for other processes to prove kernel isolation.

Each phase gets its own version bump + migration doc, exactly like every
change so far — this proposal doesn't ask the framework to abandon its
own discipline, just to stop hand-copying the same information into 17
places per change.

## 6. What this means for a host UI (not in scope to build now, flagging the shape)

A host UI's parser typically hardcodes a union of dev-artifact type names
plus one parser function,
one validator branch, one tree section, and one icon per type — the
same repetition pattern as the framework's own docs, just in TypeScript.
An ETD-driven world implies such a host eventually reads a
deployment's own ETDs and parses/validates/displays *any* declared type
generically, rather than needing a code change per type. That's a real
rearchitecture of the host's parser and tree-building — flagged here for sequencing, not proposed as part of
this framework-side plan.

## 7. Risks / honest tradeoffs

- A generic engine is harder to reason about at a glance than
  hand-written prose per type — the framework's current verbosity is
  partly *because* prose is easy to review. Mitigation: the generated
  human-facing template/docs stay the actual review surface; the ETD is
  the source, not a replacement for readable output.
- This is a genuine kernel change (INV-5 generalizes) — needs care that
  every *existing* deployment's behavior is provably unchanged
  post-migration, not just "should be."
- Scope creep risk: "any process" is a big ambition. The default process
  migrating to a real ETD-defined profile (§8) is the proof point — the
  framework should not claim to support a second domain until that
  migration is clean and every existing dogfooded behavior is provably
  unchanged.

## 8. Decisions (confirmed 2026-09-20)

1. **Sequencing:** hold everything — including the §4/Phase 0 quick
   wins — until this whole plan is reviewed and approved as one unit.
   Nothing ships piecemeal ahead of that.
2. **Architecture:** the kernel/profile split (§3) is the direction —
   Entity Type Definitions an architect/admin authors per deployment,
   not framework-hardcoded types.
3. **Profile & Prompt Module status:** today's default process migrates to be a real, ETD-defined profile and prompt module (not a permanently privileged hardcoded default) — Phase 2 in §5 is confirmed scope, not optional. This proves the mechanism against catalyst's own real complexity and avoids the framework permanently carrying two parallel ways of defining a type.
4. **Modular Prompts:** Existing process-specific prompts (slash commands, skills, procedural guidance) are packaged as that default module, establishing the architecture for Catalyst to plug in additional modules for other project management types.

This plan is now considered final pending explicit go-ahead to begin
Phase 0. No implementation work has started.
