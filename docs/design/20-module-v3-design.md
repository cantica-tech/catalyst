# 20 — `module.yaml` v3 (R4.3 design note for the owner, 2026-10-11)

> **Status: decided (owner, 2026-10-11).** Decisions 1–5 and 7 as recommended (6, the second module, waits for M5):
> one release per step; templates generated; definitions from the YAML; `rr-SE-`/`INV-SE-` with aliases; v2 read until
> 1.0; a tier names its artifact. **M1 released** (kernel 0.55.0, module 2.8.0); **M2 released** (kernel 0.56.0, module
> 2.9.0); **M3, M4 and M5 released** (kernel 0.57.0, module 3.0.0, 2026-10-12; REQ-000025
> and REQ-000026 completed): decision 6 taken as recommended, `sample-process` is the second module and runs end to
> end in the tests. The v3 `module.yaml` is 23.6 KB against 32.9 KB for the v2 files it replaces (46 files instead of
> 68); the ≈ 15 KB of §3.2 is not met without trimming prose, a separate proposal. Two findings from publishing
> catalyst's own deployment: BUG-000007 (the share guard took the renamed meta-rules as lost; fixed in 0.57.0), and a
> criterion shared on git takes the kernel first, then the module, because its gate runs the CLI of its base branch
> (§3.3 did not foresee it; `sync` enforces it since kernel 0.57.1, BUG-000011).
>
> Was: draft for the owner. R4.3 asks for "`module.yaml` v3 plus generic engine verbs; convert
> software-engineering (130 KB → ~17 KB); namespaced module rules; module-declared tiers". `02` §5 drafted v3 against
> module 2.3.1 (2026-10-08). Since then R2 and R4.1–R4.2 built part of it. This note measures where module 2.7.0 and
> kernel 0.54.0 stand, keeps what `02` got right, and lists what is left, in steps, with the decisions to take first.

## 1. Where things stand

### 1.1 The module (2.7.0), what an agent or a deployment reads

| Part | Bytes | Note |
|---|---:|---|
| `templates/` (10) | 25,995 | requirement (6.6 KB) and roadmap (4.9 KB) carry instructional prose |
| `code-of-conduct.module.md` | 13,554 | its §4 is the module's commands, read one at a time |
| `schemas/` (7) + `module.yaml` | 8,729 | the entity types |
| `definitions/` (13, v1 and v2) | 8,349 | frozen once deployed |
| `INVARIANTS.module.md` | 6,010 | SE-L1, then the module's invariants in full |
| `rules-of-rules.module.md` | 3,449 | the module's handbook part (cut by R4.2) |
| `Taskfile.module.yml` | 2,392 | one task per command |
| **Total** | **≈ 68,500** | was ≈ 129,500 at 2.3.1 (`02` §5.4) |

The repository also carries old package zips under `catalyst/` and a `ui/` build (13 files), which no deployment reads.

### 1.2 What `02` §5 asked of the kernel, and what exists

| Capability | Status (kernel 0.54.0) |
|---|---|
| `catalyst new <PREFIX>`: ID, file, index, back-references, journal | **done** (R2) |
| `catalyst status set`: checked against the type's states and transitions | **done**; guards: only `required_when_closed` on a field |
| `catalyst link A.Field B`: both sides | **done** |
| `catalyst list`, `view`, `backlog`, `graph` | **done** (R2, 0.54.0); the backlog is generic, from the types |
| Tiers declared by the module | **missing**: `chore|fix|feature` hard-coded (journal `TIERS`, five CLI options, the commit trace) |
| Derived fields (`children`, `backref`) and derived statuses (FEAT, RM) | **missing**: kept by hand, checked by `validate` |
| Templates generated from fields and sections | **missing**: 10 hand-written templates, which drift from the schemas |
| One file per module (`module.yaml` v3) | **missing**: `module.yaml` + 7 schemas + 13 definition files + templates |
| Module meta-rules and invariants in their own namespace | **partly**: the law is `SE-L1`; meta-rules still borrow kernel numbers (`rr-META-009`, `010`, `021`, `022`, placeholders in the kernel handbook) |
| The module's `kernel_version` enforced | **missing**: written by sync, read by the UI, not checked at init or check |
| Several modules per deployment | out of scope here (R4.9) |

## 2. The format

`02` §5.2 stands, with four corrections from what was built since:

* **Field kinds keep today's names** (`ref`, `ref-list`, `enum`, `text`, `date`, `user`), plus two derived kinds:
  `children` (the entities whose field points here: a requirement's steps) and `backref` (another type's references to
  this one: a requirement's tests). Derived fields are written by the CLI and never by hand.
* **Guards** on transitions: `children_closed: <field>`, `nonempty: <field>`, `section_nonempty: <heading>`. They
  replace `required_when_closed` and the closing prose in the module's handbook part.
* **Table-row storage** (`storage: rows`) replaces `naming: free-form` for roadmap items, which the graph already
  serves with their cells (0.54.0).
* **No `views:` block yet.** The generic backlog covers today's need; a query language waits for a second module that
  needs one.

```yaml
id: software-engineering
version: 3.0.0
format: 3
kernel: ">=0.55.0"                       # enforced at init, check and sync
grounding: { type: rule, field: Targets, domain_field: Domain }

tiers:
  - { id: chore,   artifact: none, commit: "chore:" }
  - { id: fix,     artifact: BUG }
  - { id: feature, artifact: REQ }

entities:
  REQ:
    name: Requirement
    folder: requirements
    grounding: required
    definition: >
      New or changed behaviour, vetted against every rule document; it always targets or proposes rules.
    fields:
      Targets: { kind: ref-list, to: rule, required: true }
      Domain:  { kind: ref, to: domain, required: true }
      Feature: { kind: ref, to: FEAT, backref: Requirements }
      Steps:   { kind: children, of: STEP, via: Parent }
      Tests:   { kind: backref, from: TEST.Requirements }
    sections: [Vetted against existing rules, Summary, Functional requirements, Test plan]
    states: [Draft, Proposed, Vetted, Active, Completed, Abandoned]
    initial: Draft
    closed: [Completed, Abandoned]
    transitions:
      - { from: Active, to: Completed, guard: { children_closed: Steps } }
  # BUG, HK, TEST, STEP, FEAT, RM in the same shape
commands:                                 # only what is not new/status/link
  - { name: roadmap-ingest, args: "<name> <file> [--delta]" }
guidance: guidance.md                     # the judgment only a person can supply
```

## 3. What changes, by party

### 3.1 The kernel

1. **Read v3** beside v2: `format: 3` selects the reader. A deployment on module 2.7.0 keeps working unchanged.
2. **Tiers from the module.** `TIERS` and the CLI choices come from the active module. The kernel keeps one built-in
   meaning: a tier with `artifact: none` needs no artifact (the chore). The commit trace takes the prefix from it.
3. **Derived fields and guards.** `new`, `link` and `status set` maintain `children` and `backref` fields and check
   the guards. `validate` reports a hand-edited derived field.
4. **Templates rendered** from fields and sections, for a v3 type. The ID table and empty sections come from the YAML;
   a section may carry a one-line hint.
5. **Definitions from the YAML.** The `definition:` text is composed into `definitions/<type>/DEFINITION-<TYPE>-vN.md`
   at deployment, frozen as today (a change is a new version through `definition migrate`).
6. **Module namespace.** The module's meta-rules become `rr-SE-NNN` in its guidance and its invariants `INV-SE-n`; the
   kernel handbook's four placeholders go; `catalyst why` resolves both old and new IDs (old ones as aliases).
7. **`kernel:` enforced** at init, check and sync: refused outside the range, with the version to move to.
8. **Commands from the module.** A command per type's `new` (`/create-req` …) is generated from the type, not written:
   the catalogue (`catalyst spec`, the MCP prompts, the Taskfile) composes it from the YAML plus `guidance.md`.

### 3.2 The software-engineering module (3.0.0)

| Today | Under v3 |
|---|---|
| `module.yaml`, 7 schemas, 13 definition files | one `module.yaml`, ≈ 9 KB |
| 10 templates (26 KB) | none; instructional prose worth keeping moves to `guidance.md` |
| `code-of-conduct.module.md` (13.5 KB) | `guidance.md`, ≈ 4 KB: tier choice, vetting, severity, roadmap ingest |
| `rules-of-rules.module.md` (3.4 KB) | folded into `guidance.md` as `rr-SE-001…` |
| `INVARIANTS.module.md` (6 KB) | SE-L1 and ≈ 1 KB of `INV-SE-n`: most become guards |
| `Taskfile.module.yml` (2.4 KB) | generated |
| `catalyst/`, `ui/` (build output) | removed from the repository |
| **≈ 68.5 KB** | **≈ 14–15 KB** |

### 3.3 Deployments

A sync to module 3.0.0 recomposes the handbook and the catalogue, generates the commands, and composes definitions:
the deployed definition files that already exist stay (frozen), and an unchanged type keeps its version. Existing
artifacts are untouched; derived fields that disagree with the CLI's are reported by `check`, and `catalyst repair
derived` rewrites them, journaled. Migration `0.55.0/module-v3.md`.

### 3.4 Clients that read `graph`

None needed for the switch: a client reading `graph` already receives `types`. A client that maps one module's kinds
by name keeps doing so until it draws any module's types from `graph` alone.

## 4. Steps

| Step | Content | Release |
|---|---|---|
| M1 | Tiers from the module (v2 `module.yaml` gains `tiers:`; default the three of today); `kernel:` enforced | kernel 0.55.0, module 2.8.0 |
| M2 | Derived fields (`children`, `backref`) and guards; `catalyst repair derived` | kernel 0.56.0 |
| M3 | The v3 reader, rendered templates, definitions from the YAML, generated create commands | kernel 0.57.0 |
| M4 | Module namespace (`rr-SE-`, `INV-SE-`), aliases in `why` | with M3 |
| M5 | software-engineering 3.0.0 in v3; `sample-process` rewritten in v3 as a CI fixture that runs init → new → status → view → check | module 3.0.0, kernel 0.57.0 |

Each step ships on its own, keeps v2 working, and gives a measurable cut. M1 alone removes the kernel's last
software-engineering vocabulary from code (the tiers).

## 5. Decisions for the owner

1. **Steps and order** (§4): M1 → M5, each its own release (recommended), or v3 in one release.
2. **Templates generated** (recommended), with the requirement and roadmap templates' instructional prose moved to
   `guidance.md`; or keep hand-written templates as overrides a module may ship.
3. **Definitions from the YAML** (recommended), composed and frozen at deployment as today; or keep definition files
   in the module.
4. **Namespace**: `rr-SE-NNN` and `INV-SE-n` (recommended), with the old `rr-META-009/010/021/022` as aliases in `why`
   and the kernel placeholders removed; or keep borrowing kernel numbers.
5. **v2 compatibility**: the kernel reads v2 and v3 until 1.0 (recommended), or for one minor only.
6. **The second module**: rewrite `sample-process` as the CI fixture (recommended; today only a loader test reads it,
   and nothing runs it end to end), or
   draft a real one (legal review, `02` §4.4) as a pilot.
7. **Tier semantics**: a tier names the artifact it needs and a commit prefix; the kernel keeps only "a tier with no
   artifact is a chore" (recommended); or tiers stay kernel vocabulary and modules only rename them.
