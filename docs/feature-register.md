# Feature register (R1.3 inventory lock)

**Status: draft — verdicts proposed, awaiting owner review.** Only rows marked *owner, 2026-10-08* carry an owner
decision; every other verdict is a proposal. All open questions are answered (see the end).
**Date:** 2026-10-08.

## Purpose

Roadmap item R1.3 (`what-is-going-on/06-roadmap-streamline.md`, "Inventory lock") asks for one register that tracks
every feature found by the analysis inventories to its home after the refactor, so that "KISS without losing any
feature" can be checked row by row. The target homes come from `07-ideal-architecture.md` (§4, §5, §7, §8, §12), the
schedule from `06`, owner decisions from `10-questions-and-decisions.md` and the ADR log in `docs/adr/`.

## How to read this file

- **One table per inventory, one row per inventory entry.** No entry is merged away, skipped or added. Each table keeps
  the inventory's own numbering under a prefix so IDs never collide:

  | Prefix | Inventory | Source rows |
  |---|---|---|
  | `K-nn` | kernel features and processes | `01a-kernel-concepts-install.md` §1.1, K-01…K-73 |
  | `PR-nn` | process inventory | `01b-kernel-rules-sync-commands.md` §3, P-01…P-71 (`PR-nn` = `P-nn`) |
  | `CMD-nn` | command inventory | `01b-kernel-rules-sync-commands.md` §4.1–§4.2, #1…#38 (`CMD-nn` = `#nn`) |
  | `SE-nn` | software-engineering module | `02-software-engineering-and-plugins.md` §1.3, SE-01…SE-46 |
  | `PL-nn` | plugins and plugin-like extensions | `02-software-engineering-and-plugins.md` §3.1, P1…P10 (`PL-nn` = `Pn`) |

  The plugin inventory lives in `02` §3.1. (`03-python-usage.md` also uses `P1…P8`, but those are Python portability
  findings, not plugins; they are not part of R1.3.)
- **Feature** is the inventory's own name. **Source** is the file, section and row.
- **Owner** is the component accountable after the refactor: *kernel CLI*, *kernel docs/brief*, *module
  (software-engineering)*, *UI*, *plugin*, or *user/agent shim*.
- **Verdict**:
  - **Keep**: the capability stays, possibly reimplemented in code.
  - **Merge**: it is folded into the feature or verb named in *New home*.
  - **Drop**: the capability survives elsewhere, named in *New home*.
  - **Park**: kept on the shelf until the condition named in *New home*.
- **New home** follows 07. Where 06 and 07 say nothing, it reads "unchanged (no roadmap item)".
- **Roadmap item** cites a 06 ID or "—":
  - R0.1…R0.21, R1.1…R1.6, R3.1…R3.9, R4.1…R4.9 and R5.1…R5.5 are numbered items.
  - "R2 W1"…"R2 W5" are the R2 waves (06 §R2).
  - "R6" and "R7" are phases without numbered items.
  - "(done)" appears only where `11-r0-status.md` records the item as done.
  - "decided (ADR-nnn), impl. R2" marks an owner-accepted decision that has not been implemented yet.
  - R2's un-numbered paragraph on the `commands.yaml` registry (06 §R2, after the wave table) has no ID, so its rows
    show "—" and name it under *New home*.
  - R1.2 is install simplification; R1.6 is the prose feature freeze (ADR-017).

## Totals

| Table | Inventory entries | Register rows | Keep | Merge | Drop | Park |
|---|---:|---:|---:|---:|---:|---:|
| Kernel (01a) | 73 | 73 | 46 | 23 | 2 | 2 |
| Processes (01b §3) | 71 | 71 | 42 | 24 | 1 | 4 |
| Commands (01b §4) | 38 | 38 | 15 | 20 | 2 | 1 |
| Software engineering (02 §1.3) | 46 | 46 | 23 | 22 | 1 | 0 |
| Plugins (02 §3.1) | 10 | 10 | 3 | 3 | 0 | 4 |
| **All** | **238** | **238** | **129** | **92** | **6** | **11** |

---

## 1. Kernel features (01a §1.1)

| ID | Feature | Source | Owner | Verdict | New home | Roadmap item |
|---|---|---|---|---|---|---|
| K-01 | Agent entry shims | 01a §1.1 K-01 | user/agent shim | Merge | Merges into the generated per-agent instruction file (`catalyst adapters write`, 07 §5.1) | R4.5 |
| K-02 | Single install entry | 01a §1.1 K-02 | kernel CLI | Merge | Merges into `catalyst init` (judgment questions only) plus `catalyst brief` (07 §5.2, §8); instantiation docs generated | R4.1, R4.4 |
| K-03 | Hard rules | 01a §1.1 K-03 | kernel docs/brief | Merge | Merges into the 10 laws via generated `brief` (07 §7, §8: BOOTSTRAP §0 → `brief`) | R4.1 |
| K-04 | Capability detection and fallbacks | 01a §1.1 K-04 | user/agent shim | Merge | Merges into generated agent adapters; fallback = instruction file (07 §5.4) | R4.5 |
| K-05 | Agent-switch handling | 01a §1.1 K-05 | kernel CLI | Merge | Merges into `catalyst move` + the agent-neutral store (07 §8); `catalyst agent switch` only until `move` exists (*owner, 2026-10-08*) | R2 W5, R3.5 |
| K-06 | Install (`catalyst init`) | 01a §1.1 K-06 | kernel CLI | Keep | `catalyst init` (07 §5.2, §13: ≤ 3 commands, ≤ 3k tokens); install simplification (R1.2: user from git config, command dir from the agent, found modules listed) | R0.3 (done), R1.2 (done) |
| K-07 | Deployment ledger | 01a §1.1 K-07 | kernel docs/brief | Keep | Survives in the ≤ 3k-token install (*owner, 2026-10-08*) | R0.3 (done) |
| K-08 | Re-ground cadence | 01a §1.1 K-08 | kernel docs/brief | Merge | Merges into `catalyst brief` run by the session-start hook (07 §5.1, §5.2) | R4.1 |
| K-09 | Assent gate | 01a §1.1 K-09 | kernel docs/brief | Keep | Law L3 "Ask before you publish"; `publish` assent token (07 §7) | R4.1, R3.6 |
| K-10 | Invariants file | 01a §1.1 K-10 | kernel docs/brief | Merge | Merges into the 10 laws + generated `brief`; `INVARIANTS.md` becomes generated (07 §7, §8) | R4.1 |
| K-11 | Module invariants | 01a §1.1 K-11 | module (software-engineering) | Merge | Merges into module `guidance.md` (07 §4.2; §7: SE-specific INV retired to module guidance) | R4.3 |
| K-12 | Kernel/module split | 01a §1.1 K-12 | kernel CLI | Keep | L0 content layer (kernel spec vs modules) and law L8 (07 §3, §7) | R4.3 |
| K-13 | Module manifest | 01a §1.1 K-13 | kernel CLI | Keep | `module.yaml` v3 + `guidance.md` (07 §4.2) | R4.3 |
| K-14 | Entity Type Definition (ETD) | 01a §1.1 K-14 | kernel CLI | Merge | Merges into `module.yaml` v3 `Entity` (fields, states, transitions, guards, `derived_status`; 07 §4.2) | R4.3 |
| K-15 | Grounding model | 01a §1.1 K-15 | kernel CLI | Keep | Law L2; module `grounding`; `validate` (07 §7) | R4.3 |
| K-16 | Document composition | 01a §1.1 K-16 | kernel CLI | Merge | Merges into the generated Handbook per module (07 §8, §9); Taskfile/command list from the `commands.yaml` registry | R4.2 |
| K-17 | Module catalog | 01a §1.1 K-17 | kernel CLI | Merge | Merges into `modules/` folders in the core repo + `catalyst module install` (07 §10; plan `docs/plans/r4-9-module-install.md`, *owner, 2026-10-08*) | R4.9 |
| K-18 | Kernel purity check | 01a §1.1 K-18 | kernel CLI | Keep | Law L8, purity check in CI (07 §7); repo-only checks under `catalyst dev …` | R3.8 |
| K-19 | Pointer file | 01a §1.1 K-19 | kernel CLI | Keep | Kept as the only tracked file, renamed `catalyst.toml` (Python floor 3.11): it names the project, resolved by `catalyst where` to `$HOME/.catalyst/projects/<name>/criterion` (ADR-010 revised, *owner, 2026-10-08*); old pointers read-only for one minor (ADR-009) | R3.1, R3.4 |
| K-20 | Working copy in agent-owned space | 01a §1.1 K-20 | kernel CLI | Merge | Moves to `$HOME/.catalyst/projects/<name>/criterion` (the `home` store driver), agent-neutral, no symlink (ADR-010 revised, *owner, 2026-10-08*); legacy read-only | R3.1, R3.2, R3.4 |
| K-21 | In-project fallback | 01a §1.1 K-21 | kernel CLI | Merge | Merges into the default `in-repo` store driver (07 §3 L1; decision A1) | R3.2 |
| K-22 | Shared deployment ("repoed") | 01a §1.1 K-22 | kernel CLI | Merge | Merges into store driver `git-remote` + `publish` (07 §12); R3.6 required, not optional (*owner, 2026-10-08*) | R3.6 |
| K-23 | `/criterion` lifecycle | 01a §1.1 K-23 | kernel CLI | Merge | Merges into `git-remote` driver + `publish` (07 §12); `integrity` becomes a `catalyst check` rule, `protect` a `publish` option (*owner, 2026-10-08*) | R3.6 |
| K-24 | `/project` lifecycle | 01a §1.1 K-24 | kernel CLI | Merge | Merges into `catalyst move` (07 §8, *owner, 2026-10-08*); `project export\|import\|remove` dropped from W5 | R2 W5 |
| K-25 | Uniform artifact-type layout | 01a §1.1 K-25 | kernel CLI | Keep | Generated from `module.yaml` v3 (07 §4.2); `ARTIFACT-LAYOUT` generated | R4.4 |
| K-26 | Descriptive file naming | 01a §1.1 K-26 | kernel CLI | Keep | `catalyst new` writes ID + slug (07 §4.2) | R2 W2 |
| K-27 | Rules, rule documents, rules index | 01a §1.1 K-27 | kernel CLI | Keep | One file per rule document (ADR-001), `validate` enforces it; kernel entity Rule (07 §4.1) | decided (ADR-001), impl. R2 |
| K-28 | Domains and sub-domains | 01a §1.1 K-28 | kernel CLI | Keep | Kernel entity Rule (+ domain) (07 §4.1) | — |
| K-29 | Rule ID scheme | 01a §1.1 K-29 | kernel CLI | Keep | `catalyst id next-rule` (unchanged) | R0.19 (done) |
| K-30 | Rule retirement | 01a §1.1 K-30 | kernel docs/brief | Keep | Handbook (07 §9) | R4.2 |
| K-31 | Rules of rules (`rr-META-NNN`) | 01a §1.1 K-31 | kernel docs/brief | Merge | Merges into the Handbook, IDs on every rule (07 §8, §9) | R4.2 |
| K-32 | Code of conduct (rules of development) | 01a §1.1 K-32 | kernel docs/brief | Merge | Merges into the Handbook (07 §8); §4 command list → `commands.yaml` registry (06 §R2) | R4.2 |
| K-33 | Per-command spec | 01a §1.1 K-33 | kernel CLI | Keep | `catalyst spec <cmd>` ≤ 1.5k tokens (07 §2, §13) | R0.1 (done), R1.1 |
| K-34 | Slash-command files | 01a §1.1 K-34 | user/agent shim | Merge | Merges into generated agent adapters from one registry (07 §5.4) | R4.5 |
| K-35 | Taskfile dispatch | 01a §1.1 K-35 | kernel CLI | Keep | Generated Taskfile snippet from the command list, optional (07 §12); `commands.yaml` registry (06 §R2) | — |
| K-36 | Users registry | 01a §1.1 K-36 | kernel CLI | Keep | `catalyst user …` (07 §12) | R2 W3 |
| K-37 | Roles and access control | 01a §1.1 K-37 | kernel CLI | Keep | `catalyst role …` (07 §12); advisory role check demoted or mechanised | R2 W3, R4.6 |
| K-38 | Signing / identity resolution | 01a §1.1 K-38 | kernel CLI | Keep | `--as` on mutating verbs (07 §5.2) | — |
| K-39 | Journal | 01a §1.1 K-39 | kernel CLI | Keep | Journal shards + lock, law L1 (07 §7, §12) | R3.3 |
| K-40 | Journal pin | 01a §1.1 K-40 | kernel CLI | Keep | Content blobs in the store (07 §12) | R3.2, R3.3 |
| K-41 | Point-in-time restore | 01a §1.1 K-41 | kernel CLI | Keep | `catalyst journal restore` (07 §12) | — |
| K-42 | Unrecorded changes and `/adopt` | 01a §1.1 K-42 | kernel CLI | Keep | `catalyst unrecorded\|adopt`, content-hash based (07 §12); warn at 1.0-rc, error at 1.0 | R0.10 (done), R3.3, R7 |
| K-43 | Traced commits | 01a §1.1 K-43 | kernel CLI | Keep | `commit-msg` hook (07 §3 L4, §5.4) | R0.17 (done) |
| K-44 | Ceremony tiers | 01a §1.1 K-44 | module (software-engineering) | Keep | Module-declared `tiers[]` in `module.yaml` v3; kernel stops hardcoding (07 §4.2) | R4.3 |
| K-45 | `catalyst check` / `validate` | 01a §1.1 K-45 | kernel CLI | Keep | `catalyst check`, check rule ids `C-001…` (07 §7); incremental checks | R3.8 |
| K-46 | End-of-turn hook | 01a §1.1 K-46 | user/agent shim | Keep | Agent stop hook where it exists, else git hooks + CI (07 §5.4); session-scoped | decided (ADR-002), impl. R2; R0.16 (done) |
| K-47 | SessionStart invariant injection | 01a §1.1 K-47 | user/agent shim | Merge | Merges into the session-start hook running `catalyst brief` (07 §5.2) | R0.4 (done), R4.1 |
| K-48 | Index regeneration | 01a §1.1 K-48 | kernel CLI | Keep | Projections written by every verb; law L6 (07 §7) | R2 W2 |
| K-49 | Reconciliation cases `RECON-` | 01a §1.1 K-49 | kernel CLI | Keep | `catalyst reconcile` with role gate in code (07 §12) | R0.7 (done), R2 W2 |
| K-50 | Workflows `WORKFLOW-` | 01a §1.1 K-50 | kernel CLI | Keep | Kernel entity Workflow: a declared state machine, declared by modules (07 §4.1, *owner, 2026-10-08*; ADR-008 rejected) | R4.3 |
| K-51 | Four-eyes analysis `ANALYSIS-` | 01a §1.1 K-51 | kernel CLI | Keep | `catalyst analysis …` + `/run-analysis` wrapper (07 §12) | — |
| K-52 | Meta-tags | 01a §1.1 K-52 | kernel CLI | Drop | Survives as a `tags:` field in any entity (07 §4.1, §8; B4, *owner, 2026-10-08*) | — |
| K-53 | Frozen definitions | 01a §1.1 K-53 | kernel CLI | Keep | Law L7, `catalyst definition migrate` (07 §7) | R0.8 (done), R2 W3 |
| K-54 | `.frozen` / `/freeze` | 01a §1.1 K-54 | kernel CLI | Keep | `catalyst freeze` (07 §12) | R2 W3 |
| K-55 | Plugin gate, provenance, contract, target | 01a §1.1 K-55 | plugin | Park | Until a second real plugin exists (B3, *owner, 2026-10-08*) (07 §8) | R4.7 |
| K-56 | Content-contributing plugins / work items | 01a §1.1 K-56 | plugin | Park | Until a second real plugin exists (B3, *owner, 2026-10-08*); the capability goes to modules as data, several per deployment (07 §4.2, §8) | R4.7 |
| K-57 | `catalyst-git` plugin | 01a §1.1 K-57 | plugin | Keep | Optional extension, not core: `extensions/` (07 §8) | R4.7 |
| K-58 | `/sync-framework` | 01a §1.1 K-58 | kernel CLI | Keep | `catalyst sync plan\|apply` (07 §12) | R2 W4 |
| K-59 | Migrations | 01a §1.1 K-59 | kernel CLI | Keep | Migrations as tested code, keyed by format version (07 §10, §12) | R0.6 (done), R2 W4 |
| K-60 | Recompose / `composition.json` | 01a §1.1 K-60 | kernel CLI | Merge | Merges into `catalyst sync` as a sub-step (06 W4) | R2 W4 |
| K-61 | On-disk format and versions | 01a §1.1 K-61 | kernel CLI | Keep | Format versioned separately from the product (07 §10) | R7 |
| K-62 | `.catalystignore` and nested deployments | 01a §1.1 K-62 | kernel CLI | Keep | One `scope` implementation shared by CLI and UI (07 §12) | R0.10 (done) |
| K-63 | Persistent memory note | 01a §1.1 K-63 | user/agent shim | Drop | Survives as the locator (declared location) + `catalyst open` (06 R3.5) | R3.5 |
| K-64 | Greenfield path | 01a §1.1 K-64 | kernel docs/brief | Keep | Generated instantiation docs (06 R4.4) | R4.4 |
| K-65 | Retrofit path | 01a §1.1 K-65 | kernel docs/brief | Keep | Generated instantiation docs (06 R4.4); `/run-analysis --bootstrap` | R4.4 |
| K-66 | `dev-instructions.yaml` | 01a §1.1 K-66 | kernel CLI | Keep | unchanged (no roadmap item; Keep confirmed, *owner, 2026-10-08*) | — |
| K-67 | `/dogfood` | 01a §1.1 K-67 | user/agent shim | Keep | Catalyst-only; dogfooding resumes after R3 (06 cross-cutting "Governance of catalyst itself") | — |
| K-68 | Beta kit | 01a §1.1 K-68 | kernel docs/brief | Keep | `beta/` rewritten for the new flow (06 R7) | R7 |
| K-69 | Glossary | 01a §1.1 K-69 | kernel docs/brief | Keep | Generated; `catalyst glossary <term>` (07 §5.1, §9) | R4.4 |
| K-70 | Repo-level checkers | 01a §1.1 K-70 | kernel CLI | Merge | Merges into `catalyst dev …` (06 R3.8); command parity ends with the `commands.yaml` registry | R0.15 (done), R3.8 |
| K-71 | `catalyst report` | 01a §1.1 K-71 | kernel CLI | Keep | unchanged (no roadmap item; Keep confirmed, *owner, 2026-10-08*) | — |
| K-72 | Atomic, real-time updates | 01a §1.1 K-72 | kernel docs/brief | Keep | Law L1 (absorbs INV-29); demoted or mechanised (06 R4.6) | R4.6 |
| K-73 | Act without asking | 01a §1.1 K-73 | kernel CLI | Merge | Merges into law L3 as tooling ("the exception rule is tooling, not law", 07 §7) | R4.1 |

## 2. Processes (01b §3)

| ID | Feature | Source | Owner | Verdict | New home | Roadmap item |
|---|---|---|---|---|---|---|
| PR-01 | Rule conflict check | 01b §3.1 P-01 | kernel docs/brief | Keep | Agent judgment (07 §5.3) via `/check-rules`; rule search instead of reading every rule document (06 R4.2) | R4.2 |
| PR-02 | Rule definition-of-done | 01b §3.1 P-02 | kernel docs/brief | Keep | Handbook (07 §9) | R4.2 |
| PR-03 | Rule ID allocation | 01b §3.1 P-03 | kernel CLI | Keep | `catalyst id next-rule` (unchanged) | R0.19 (done) |
| PR-04 | Descriptive naming + retro-rename | 01b §3.1 P-04 | kernel CLI | Keep | Naming done by `catalyst new` (07 §4.2); sync-time rename inside `catalyst sync` | R2 W2, R2 W4 |
| PR-05 | Rule retirement | 01b §3.1 P-05 | kernel docs/brief | Keep | Handbook (07 §9) | R4.2 |
| PR-06 | Rule storage/indexing | 01b §3.1 P-06 | kernel CLI | Keep | One file per rule document, enforced by `validate` (ADR-001) | decided (ADR-001), impl. R2 |
| PR-07 | Domain creation | 01b §3.1 P-07 | kernel docs/brief | Keep | Handbook (07 §9); kernel entity Rule (+ domain) (07 §4.1) | R4.2 |
| PR-08 | Sub-domain split | 01b §3.1 P-08 | kernel docs/brief | Keep | Handbook (07 §9) | R4.2 |
| PR-09 | ID rename cross-reference sweep | 01b §3.1 P-09 | kernel CLI | Keep | unchanged (no roadmap item; Keep confirmed, *owner, 2026-10-08*) | — |
| PR-10 | Signer resolution | 01b §3.2 P-10 | kernel CLI | Keep | `--as` on mutating verbs (07 §5.2) | — |
| PR-11 | Advisory role check | 01b §3.2 P-11 | kernel CLI | Keep | Demoted or mechanised (06 R4.6) | R4.6 |
| PR-12 | userid generation | 01b §3.2 P-12 | kernel CLI | Keep | Inside `catalyst user …` (07 §12) | R2 W3 |
| PR-13 | User registry CRUD | 01b §3.2 P-13 | kernel CLI | Merge | Merges into `catalyst user …` (07 §8) | R0.2 (done), R2 W3 |
| PR-14 | Last-active-user guard | 01b §3.2 P-14 | kernel CLI | Keep | Guard inside `catalyst user …` (07 §12) | R2 W3 |
| PR-15 | Role registry CRUD | 01b §3.2 P-15 | kernel CLI | Merge | Merges into `catalyst role …` (07 §8) | R0.2 (done), R2 W3 |
| PR-16 | Role-gated reconciliation | 01b §3.2 P-16 | kernel CLI | Keep | `catalyst reconcile` with role gate in code (07 §12) | R0.7 (done), R2 W2 |
| PR-17 | Ceremony tier selection | 01b §3.3 P-17 | module (software-engineering) | Keep | Module-declared tiers (07 §4.2); choice stays agent judgment (07 §5.3) | R4.3 |
| PR-18 | Common ending | 01b §3.3 P-18 | kernel CLI | Merge | Merges into every mutating verb (`new`, `status`, `link` journal and regenerate in one call; 07 §5.2) | R2 W2 |
| PR-19 | Journal append | 01b §3.3 P-19 | kernel CLI | Keep | `catalyst record` / journal shards (07 §5.1, §12) | R3.3 |
| PR-20 | Journal verify | 01b §3.3 P-20 | kernel CLI | Keep | `catalyst journal verify` (07 §12) | — |
| PR-21 | Blob pinning / share | 01b §3.3 P-21 | kernel CLI | Keep | Content blobs in the store (07 §12) | R0.12 (done), R3.2 |
| PR-22 | Point-in-time restore | 01b §3.3 P-22 | kernel CLI | Keep | `catalyst journal restore` (07 §12) | — |
| PR-23 | Journal query | 01b §3.3 P-23 | kernel CLI | Merge | Merges into `catalyst journal show` (06 W1) | R2 W1 |
| PR-24 | Traced commits | 01b §3.3 P-24 | kernel CLI | Keep | `commit-msg` hook (07 §5.4) | R0.17 (done) |
| PR-25 | Hook install | 01b §3.3 P-25 | user/agent shim | Keep | `catalyst hook install --agent <x>` (07 §5.4) | R4.5 |
| PR-26 | Unrecorded-change detection | 01b §3.3 P-26 | kernel CLI | Keep | Content-hash `catalyst unrecorded` (07 §12); warn at 1.0-rc, error at 1.0 | R0.10 (done), R3.3, R7 |
| PR-27 | Adoption of manual changes | 01b §3.3 P-27 | kernel CLI | Keep | `catalyst unrecorded\|adopt` + `/adopt` judgment (07 §12) | — |
| PR-28 | Atomic updates | 01b §3.3 P-28 | kernel docs/brief | Keep | Law L1; demoted or mechanised (06 R4.6) | R4.6 |
| PR-29 | Stop-hook enforcement | 01b §3.3 P-29 | user/agent shim | Keep | Agent stop hook, else git hooks + CI (07 §5.4); session-scoped | decided (ADR-002), impl. R2; R0.16 (done) |
| PR-30 | Spec budget | 01b §3.3 P-30 | kernel CLI | Merge | Merges into the token-budget tests (06 R1.1) | R1.1 |
| PR-31 | Artifact creation (module) | 01b §3.4 P-31 | kernel CLI | Merge | Merges into `catalyst new <PREFIX>` (07 §4.2) | R2 W2 |
| PR-32 | Status change | 01b §3.4 P-32 | kernel CLI | Merge | Merges into `catalyst status <ID> <state>` (07 §4.2) | R0.7 (done), R2 W2 |
| PR-33 | Closing an item | 01b §3.4 P-33 | kernel CLI | Merge | Merges into transition guards in `module.yaml` v3, enforced by `catalyst status` (07 §4.2) | R2 W2, R4.3 |
| PR-34 | Meta-tagging | 01b §3.4 P-34 | kernel CLI | Drop | Survives as a `tags:` field in any entity (07 §8; B4, *owner, 2026-10-08*) | — |
| PR-35 | Index regeneration | 01b §3.4 P-35 | kernel CLI | Keep | Projections written by every verb; law L6 (07 §7) | R2 W2 |
| PR-36 | Chain validation | 01b §3.4 P-36 | kernel CLI | Keep | `catalyst check` / `validate`, rule ids `C-001…` (07 §7) | — |
| PR-37 | Definition freezing | 01b §3.4 P-37 | kernel CLI | Merge | Merges into `catalyst sync` (definitions create-only) (06 W4); law L7 | R0.8 (done), R2 W4 |
| PR-38 | Definition migration | 01b §3.4 P-38 | kernel CLI | Merge | Merges into `catalyst definition migrate` (06 W3) | R2 W3 |
| PR-39 | Freezing items from sync | 01b §3.4 P-39 | kernel CLI | Merge | Merges into `catalyst freeze\|unfreeze` (06 W3; 07 §12) | R2 W3 |
| PR-40 | Workflow authoring | 01b §3.4 P-40 | kernel CLI | Keep | Kernel entity Workflow: a declared state machine, declared by modules (07 §4.1, *owner, 2026-10-08*; ADR-008 rejected) | R4.3 |
| PR-41 | Open a RECON case | 01b §3.5 P-41 | kernel CLI | Keep | `catalyst reconcile` (07 §12) | — |
| PR-42 | Resolve / propose | 01b §3.5 P-42 | kernel CLI | Keep | `/reconcile` judgment + `catalyst reconcile` role gate (07 §12) | R2 W2 |
| PR-43 | Close a resolved case | 01b §3.5 P-43 | kernel CLI | Keep | `/reconcile <id> close` (defined by R0.7) → `catalyst reconcile` (07 §12) | R0.7 (done) |
| PR-44 | Install | 01b §3.6 P-44 | kernel CLI | Keep | `catalyst init` (07 §5.2); install simplification (R1.2: user from git config, command dir from the agent, found modules listed) | R0.3 (done), R1.2 (done) |
| PR-45 | Project remove / export / import | 01b §3.6 P-45 | kernel CLI | Merge | Merges into `catalyst move` (07 §8, *owner, 2026-10-08*) | R2 W5 |
| PR-46 | Pre-pointer migration | 01b §3.6 P-46 | kernel CLI | Park | Until R3.4 decides whether the optional `catalyst migrate` is built | R3.4 |
| PR-47 | Agent switch | 01b §3.6 P-47 | kernel CLI | Merge | Merges into `catalyst move` + agent-neutral store (07 §8); `catalyst agent switch` only until `move` exists (*owner, 2026-10-08*) | R2 W5, R3.5 |
| PR-48 | Share (criterion create/join/push/sync/status/protect) | 01b §3.6 P-48 | kernel CLI | Merge | Merges into store driver `git-remote` + `publish` (07 §12); `protect` becomes a `publish` option, R3.6 required (*owner, 2026-10-08*) | R3.6 |
| PR-49 | Merge-conflict handling | 01b §3.6 P-49 | kernel CLI | Keep | RECON + laws L3/L5, no AI merges (07 §7) | R3.6 |
| PR-50 | Criterion CI | 01b §3.6 P-50 | kernel CLI | Keep | CI gate runs the CLI pinned by hash from the base branch (07 §10) | R0.13 (done), R3.7 |
| PR-51 | Version freshness check | 01b §3.7 P-51 | kernel CLI | Keep | unchanged (no roadmap item; Keep confirmed, *owner, 2026-10-08*) | — |
| PR-52 | `/sync-framework` | 01b §3.7 P-52 | kernel CLI | Merge | Merges into `catalyst sync plan\|apply` + `/sync-framework` wrapper (07 §12) | R2 W4 |
| PR-53 | One-time migrations | 01b §3.7 P-53 | kernel CLI | Keep | Migrations as tested code, keyed by format version (07 §10, §12) | R0.6 (done), R2 W4 |
| PR-54 | Plugin preservation during sync | 01b §3.7 P-54 | kernel CLI | Merge | Merges into `catalyst sync plan\|apply`, which keeps the installed plugins; no `catalog merge` verb (dropped from W4, *owner, 2026-10-08*) | R2 W4 |
| PR-55 | Sync four-eyes verification | 01b §3.7 P-55 | kernel CLI | Keep | Stays for now, alongside `catalyst sync plan\|apply` + `catalyst check` (*owner, 2026-10-08*) | R2 W4 |
| PR-56 | Module recomposition | 01b §3.7 P-56 | kernel CLI | Merge | Merges into `catalyst sync` as a sub-step (06 W4) | R2 W4 |
| PR-57 | Command/task parity | 01b §3.7 P-57 | kernel CLI | Merge | Merges into generation from the `commands.yaml` registry, which ends the parity script (06 §R2) | — |
| PR-58 | Four-eyes code analysis | 01b §3.8 P-58 | kernel CLI | Keep | `catalyst analysis …` + `/run-analysis` wrapper (07 §12) | — |
| PR-59 | Rule/link consistency check | 01b §3.8 P-59 | kernel docs/brief | Keep | `/check-rules` (absorbs `/audit`, 07 §8) | — |
| PR-60 | Change-impact audit | 01b §3.8 P-60 | kernel docs/brief | Merge | Merges into `/check-rules` (07 §8) | — |
| PR-61 | Dogfood | 01b §3.8 P-61 | user/agent shim | Keep | Catalyst-only; resumes after R3 (06 cross-cutting) | — |
| PR-62 | Recreation drift check | 01b §3.8 P-62 | user/agent shim | Keep | unchanged (no roadmap item; Keep confirmed, *owner, 2026-10-08*) | — |
| PR-63 | Roadmap ingest | 01b §3.9 P-63 | kernel CLI | Merge | Merges into `catalyst roadmap …` + `/roadmap` (07 §8, §12); item extraction stays judgment (07 §5.3) | R2 W3 |
| PR-64 | Roadmap full update | 01b §3.9 P-64 | kernel CLI | Merge | Merges into `catalyst roadmap …` (07 §12) | R2 W3 |
| PR-65 | Roadmap delta merge | 01b §3.9 P-65 | kernel CLI | Merge | Merges into `catalyst roadmap …` (07 §12) | R2 W3 |
| PR-66 | Roadmap removal | 01b §3.9 P-66 | kernel CLI | Merge | Merges into `catalyst roadmap …` (07 §12) | R2 W3 |
| PR-67 | Backlog regeneration | 01b §3.9 P-67 | kernel CLI | Merge | Merges into `catalyst backlog` / `catalyst view` with `derived_status` from `module.yaml` (07 §4.2) | R2 W1 |
| PR-68 | Plugin catalog ops | 01b §3.9 P-68 | plugin | Park | Until a second real plugin exists (B3, *owner, 2026-10-08*); catalog commands dropped meanwhile (07 §8) | R4.7 |
| PR-69 | Plugin startup activation | 01b §3.9 P-69 | plugin | Park | Until a second real plugin exists (B3, *owner, 2026-10-08*) (07 §8); the "hard rule" is demoted or mechanised | R4.6, R4.7 |
| PR-70 | Content-contributing activation | 01b §3.9 P-70 | plugin | Park | Until a second real plugin exists (B3, *owner, 2026-10-08*); the capability goes to modules as data (07 §4.2, §8) | R4.7 |
| PR-71 | Release | 01b §3.9 P-71 | user/agent shim | Keep | Maintainers' tool, outside the product (07 §12); signed releases | R7 |

## 3. Commands (01b §4)

| ID | Feature | Source | Owner | Verdict | New home | Roadmap item |
|---|---|---|---|---|---|---|
| CMD-01 | `/user-add` | 01b §4.1 #1 | kernel CLI | Merge | Merges into `/user` → `catalyst user …` (07 §8) | R0.2 (done), R2 W3 |
| CMD-02 | `/user-remove` | 01b §4.1 #2 | kernel CLI | Merge | Merges into `/user` → `catalyst user …` (07 §8) | R0.2 (done), R2 W3 |
| CMD-03 | `/user-modify` | 01b §4.1 #3 | kernel CLI | Merge | Merges into `/user` → `catalyst user …` (07 §8) | R0.2 (done), R2 W3 |
| CMD-04 | `/user-assign-role` | 01b §4.1 #4 | kernel CLI | Merge | Merges into `/user` → `catalyst user …` (07 §8) | R0.2 (done), R2 W3 |
| CMD-05 | `/user-list` | 01b §4.1 #5 | kernel CLI | Merge | Merges into `catalyst list` (07 §4.2) | R0.2 (done), R2 W1 |
| CMD-06 | `/role-add` | 01b §4.1 #6 | kernel CLI | Merge | Merges into `/role` → `catalyst role …` (07 §8) | R0.2 (done), R2 W3 |
| CMD-07 | `/role-modify` | 01b §4.1 #7 | kernel CLI | Merge | Merges into `/role` → `catalyst role …` (07 §8) | R0.2 (done), R2 W3 |
| CMD-08 | `/meta-tag` | 01b §4.1 #8 | kernel CLI | Drop | Survives as a `tags:` field in any entity (07 §8; B4, *owner, 2026-10-08*) | — |
| CMD-09 | `/list` | 01b §4.1 #9 | kernel CLI | Keep | `catalyst list …` (07 §4.2) | R2 W1 |
| CMD-10 | `/freeze` | 01b §4.1 #10 | kernel CLI | Merge | Merges into `catalyst freeze\|unfreeze` (07 §12) | R2 W3 |
| CMD-11 | `/migrate-definition` | 01b §4.1 #11 | kernel CLI | Merge | Merges into `catalyst definition migrate` (06 W3) | R2 W3 |
| CMD-12 | `/catalyzer` | 01b §4.1 #12 | plugin | Park | Until a second real plugin exists (B3, *owner, 2026-10-08*) (07 §8) | R4.7 |
| CMD-13 | `/criterion` | 01b §4.1 #13 | kernel CLI | Merge | Merges into `publish` + `git-remote` driver (07 §12); `integrity` → `catalyst check` rule, `protect` → `publish` option; "criterion" name retired (*owner, 2026-10-08*) | R3.6 |
| CMD-14 | `/reconcile` | 01b §4.1 #14 | kernel CLI | Keep | `/reconcile` judgment wrapper + `catalyst reconcile` (07 §12) | R0.7 (done), R2 W2 |
| CMD-15 | `/project` | 01b §4.1 #15 | kernel CLI | Merge | Merges into `catalyst move` (07 §8, *owner, 2026-10-08*) | R2 W5 |
| CMD-16 | `/switch-agent` | 01b §4.1 #16 | kernel CLI | Drop | Survives as `catalyst move` + the agent-neutral store (07 §8); `catalyst agent switch` only until `move` exists (*owner, 2026-10-08*) | R2 W5, R3.5 |
| CMD-17 | `/status` | 01b §4.1 #17 | kernel CLI | Keep | `catalyst status <ID> <state>` (07 §4.2) | R0.7 (done), R2 W2 |
| CMD-18 | `/audit` | 01b §4.1 #18 | kernel docs/brief | Merge | Merges into `/check-rules` (07 §8) | — |
| CMD-19 | `/run-analysis` | 01b §4.1 #19 | kernel CLI | Keep | `catalyst analysis …` + `/run-analysis` wrapper (07 §12) | — |
| CMD-20 | `/sync-framework` | 01b §4.1 #20 | kernel CLI | Keep | Wrapper over `catalyst sync plan\|apply` (07 §12) | R2 W4 |
| CMD-21 | `/check-rules` | 01b §4.1 #21 | kernel docs/brief | Keep | `/check-rules` (absorbs `/audit`, 07 §8) | — |
| CMD-22 | `/commands` | 01b §4.1 #22 | kernel CLI | Merge | Merges into `/help`, backed by `catalyst spec` (07 §8) | — |
| CMD-23 | `/journal` | 01b §4.1 #23 | kernel CLI | Keep | Thin wrapper over `catalyst journal show` (06 W1) | R2 W1 |
| CMD-24 | `/journal-restore` | 01b §4.1 #24 | kernel CLI | Merge | Merges into `catalyst journal restore` (07 §12) | — |
| CMD-25 | `/adopt` | 01b §4.1 #25 | kernel CLI | Keep | `/adopt` judgment + `catalyst unrecorded\|adopt` (07 §12) | — |
| CMD-26 | `/help` | 01b §4.1 #26 | kernel CLI | Keep | `/help` (absorbs `/commands`, 07 §8) | — |
| CMD-27 | `/dogfood` | 01b §4.1 #27 | user/agent shim | Keep | Catalyst-only; resumes after R3 (06 cross-cutting) | — |
| CMD-28 | `/create-bug` | 01b §4.2 #28 | module (software-engineering) | Keep | Judgment wrapper over `catalyst new BUG` (07 §4.2) | R2 W2 |
| CMD-29 | `/create-req` | 01b §4.2 #29 | module (software-engineering) | Keep | Judgment wrapper over `catalyst new REQ` (07 §4.2) | R2 W2 |
| CMD-30 | `/create-requirement` | 01b §4.2 #30 | module (software-engineering) | Merge | Merges into `/create-req` as a generated alias (06 §R2) | — |
| CMD-31 | `/create-test` | 01b §4.2 #31 | module (software-engineering) | Keep | Judgment wrapper over `catalyst new TEST` + `catalyst link` (07 §4.2) | R2 W2 |
| CMD-32 | `/create-feature` | 01b §4.2 #32 | module (software-engineering) | Keep | Judgment wrapper over `catalyst new FEAT` (07 §4.2) | R2 W2 |
| CMD-33 | `/create-step` | 01b §4.2 #33 | module (software-engineering) | Keep | Judgment wrapper over `catalyst new STEP` + `catalyst link` (07 §4.2) | R2 W2 |
| CMD-34 | `/roadmap-add` | 01b §4.2 #34 | kernel CLI | Merge | Merges into `/roadmap` → `catalyst roadmap …` (07 §8) | R2 W3 |
| CMD-35 | `/roadmap-update` | 01b §4.2 #35 | kernel CLI | Merge | Merges into `/roadmap` → `catalyst roadmap …` (07 §8) | R2 W3 |
| CMD-36 | `/roadmap-merge` | 01b §4.2 #36 | kernel CLI | Merge | Merges into `/roadmap` → `catalyst roadmap …` (07 §8) | R2 W3 |
| CMD-37 | `/roadmap-remove` | 01b §4.2 #37 | kernel CLI | Merge | Merges into `/roadmap` → `catalyst roadmap …` (07 §8) | R2 W3 |
| CMD-38 | `/show-backlog` | 01b §4.2 #38 | kernel CLI | Merge | Merges into `catalyst backlog` / `catalyst view` (06 W1; 07 §4.2) | R2 W1 |

## 4. Software-engineering module (02 §1.3)

| ID | Feature | Source | Owner | Verdict | New home | Roadmap item |
|---|---|---|---|---|---|---|
| SE-01 | `BUG-NNNNNN-<userid>` | 02 §1.3.1 SE-01 | module (software-engineering) | Keep | Entity in `module.yaml` v3 (07 §4.2, §12) | R0.8 (done), R4.3 |
| SE-02 | `REQ-NNNNNN-<userid>` | 02 §1.3.1 SE-02 | module (software-engineering) | Keep | Entity in `module.yaml` v3 (07 §12) | R4.3 |
| SE-03 | `HK-NNNNNN-<userid>` | 02 §1.3.1 SE-03 | module (software-engineering) | Keep | Entity in `module.yaml` v3 (07 §12) | R4.3 |
| SE-04 | `TEST-NNNNNN-<userid>` | 02 §1.3.1 SE-04 | module (software-engineering) | Keep | Entity in `module.yaml` v3 (07 §12) | R4.3 |
| SE-05 | `STEP-NNNNNN-<userid>` | 02 §1.3.1 SE-05 | module (software-engineering) | Keep | Entity in `module.yaml` v3 (07 §12) | R0.8 (done), R4.3 |
| SE-06 | `FEAT-NNNNNN-<userid>` | 02 §1.3.1 SE-06 | module (software-engineering) | Keep | Entity in `module.yaml` v3 (07 §12) | R4.3 |
| SE-07 | `RM-NNNNNN-<userid>` rows in `development/roadmaps/<name>.md` | 02 §1.3.1 SE-07 | module (software-engineering) | Keep | Entity in `module.yaml` v3 with `derived_status` (07 §4.2) | R4.3 |
| SE-08 | `development/BACKLOG.md` | 02 §1.3.1 SE-08 | module (software-engineering) | Merge | Merges into `catalyst view` (backlog view from module queries; 07 §4.2) | R2 W1 |
| SE-09 | `/create-req` | 02 §1.3.2 SE-09 | kernel CLI | Merge | Procedure merges into `catalyst new REQ` (07 §4.2); slash wrapper kept as CMD-29 | R2 W2 |
| SE-10 | `/create-requirement` | 02 §1.3.2 SE-10 | module (software-engineering) | Merge | Merges into `/create-req` as a generated alias (06 §R2) | — |
| SE-11 | `/create-bug` | 02 §1.3.2 SE-11 | kernel CLI | Merge | Procedure merges into `catalyst new BUG` (07 §4.2); wrapper kept as CMD-28 | R2 W2 |
| SE-12 | `/create-test` | 02 §1.3.2 SE-12 | kernel CLI | Merge | Procedure merges into `catalyst new TEST` + `catalyst link` (back-refs) (07 §4.2); wrapper kept as CMD-31 | R2 W2 |
| SE-13 | `/create-feature` | 02 §1.3.2 SE-13 | kernel CLI | Merge | Procedure merges into `catalyst new FEAT` + `catalyst link` (07 §4.2); wrapper kept as CMD-32 | R2 W2 |
| SE-14 | `/create-step <REQ\|BUG>` | 02 §1.3.2 SE-14 | kernel CLI | Merge | Procedure merges into `catalyst new STEP` + `catalyst link` (07 §4.2); wrapper kept as CMD-33 | R2 W2 |
| SE-15 | `/show-backlog` | 02 §1.3.2 SE-15 | kernel CLI | Merge | Merges into `catalyst backlog` / `catalyst view` (06 W1; 07 §4.2) | R2 W1 |
| SE-16 | `/roadmap-add <name> <file>` | 02 §1.3.2 SE-16 | kernel CLI | Merge | Merges into `catalyst roadmap …` (07 §8, §12) | R2 W3 |
| SE-17 | `/roadmap-update <name> <file>` | 02 §1.3.2 SE-17 | kernel CLI | Merge | Merges into `catalyst roadmap …` (07 §8, §12) | R2 W3 |
| SE-18 | `/roadmap-merge <name> <file>` | 02 §1.3.2 SE-18 | kernel CLI | Merge | Merges into `catalyst roadmap …` (07 §8, §12) | R2 W3 |
| SE-19 | `/roadmap-remove <name>` | 02 §1.3.2 SE-19 | kernel CLI | Merge | Merges into `catalyst roadmap …` (07 §8, §12) | R2 W3 |
| SE-20 | Ceremony tiers (module part) | 02 §1.3.3 SE-20 | module (software-engineering) | Keep | `tiers[]` in `module.yaml` v3 (07 §4.2) | R4.3 |
| SE-21 | Adoption mapping | 02 §1.3.3 SE-21 | module (software-engineering) | Keep | Module `guidance.md` (07 §4.2); `/adopt` judgment | R4.3 |
| SE-22 | Rule-document quick index | 02 §1.3.3 SE-22 | module (software-engineering) | Keep | unchanged (no roadmap item; Keep confirmed, *owner, 2026-10-08*) | — |
| SE-23 | Closing conditions | 02 §1.3.3 SE-23 | module (software-engineering) | Merge | Merges into transition guards (`children_closed\|nonempty\|section_nonempty`) in `module.yaml` v3, enforced by `catalyst status` (07 §4.2) | R2 W2, R4.3 |
| SE-24 | Dev-artifact ID scheme | 02 §1.3.3 SE-24 | module (software-engineering) | Keep | Entity `prefix` in `module.yaml` v3; IDs issued by `catalyst new` (07 §4.2) | R2 W2, R4.3 |
| SE-25 | FEAT → REQ promotion | 02 §1.3.3 SE-25 | module (software-engineering) | Keep | `catalyst link` + module `guidance.md` (07 §4.2) | R2 W2 |
| SE-26 | RM triage and derived status | 02 §1.3.3 SE-26 | module (software-engineering) | Keep | `Entity.derived_status` in `module.yaml` v3, rendered by `catalyst backlog` / `view` (07 §4.2) | R2 W1, R4.3 |
| SE-27 | Step ownership | 02 §1.3.3 SE-27 | module (software-engineering) | Keep | STEP parent field + `children_closed` guard in `module.yaml` v3 (07 §4.2) | R4.3 |
| SE-28 | Test links and back-refs | 02 §1.3.3 SE-28 | kernel CLI | Merge | Merges into `catalyst link` (writes both sides; 07 §4.2) | R2 W2 |
| SE-29 | Shared-deployment merge policy | 02 §1.3.3 SE-29 | kernel CLI | Keep | Store driver `git-remote` + `publish` (07 §12) | R3.6 |
| SE-30 | Placement | 02 §1.3.3 SE-30 | module (software-engineering) | Keep | Entity `folder` in `module.yaml` v3 (07 §4.2) | R4.3 |
| SE-31 | Signing | 02 §1.3.3 SE-31 | kernel CLI | Merge | Merges into kernel signing K-38 (`--as` + userid suffix) | — |
| SE-32 | Journal shape | 02 §1.3.3 SE-32 | kernel CLI | Merge | Merges into kernel journal K-39 (filled by `catalyst new`/`status`) | R2 W2 |
| SE-33 | Rename propagation | 02 §1.3.3 SE-33 | module (software-engineering) | Keep | unchanged (no roadmap item; Keep confirmed, *owner, 2026-10-08*) | — |
| SE-34 | Required paths | 02 §1.3.3 SE-34 | module (software-engineering) | Keep | unchanged (no roadmap item; Keep confirmed, *owner, 2026-10-08*) | — |
| SE-35 | Severity scale | 02 §1.3.3 SE-35 | module (software-engineering) | Keep | Enum field in `module.yaml` v3 (07 §4.2) | R4.3 |
| SE-36 | Vetting / New domain / New rules sections | 02 §1.3.3 SE-36 | module (software-engineering) | Keep | Entity `sections[]` in `module.yaml` v3 (07 §4.2) | R4.3 |
| SE-37 | Suggested role actions | 02 §1.3.3 SE-37 | module (software-engineering) | Keep | Module `guidance.md` (07 §4.2) | R4.3 |
| SE-38 | 7 ETDs | 02 §1.3.4 SE-38 | module (software-engineering) | Merge | Merges into `module.yaml` v3 (07 §4.2) | R4.3 |
| SE-39 | 10 templates | 02 §1.3.4 SE-39 | module (software-engineering) | Merge | Merges into templates generated from `module.yaml` v3 (07 §4.2) | R4.3 |
| SE-40 | 8 definitions | 02 §1.3.4 SE-40 | module (software-engineering) | Keep | Frozen, versioned definitions; law L7 (07 §7) | R0.8 (done) |
| SE-41 | 7 migrations | 02 §1.3.4 SE-41 | module (software-engineering) | Keep | Migrations as tested code, keyed by format version (07 §10) | R2 W4 |
| SE-42 | 11 Taskfile tasks | 02 §1.3.4 SE-42 | module (software-engineering) | Merge | Merges into the generated Taskfile snippet from the command list (07 §12) | — |
| SE-43 | UI `Backlog` | 02 §1.3.4 SE-43 | UI | Merge | Merges into ETD-driven generic rendering (07 §6, §12) | R6 |
| SE-44 | UI `RoadmapDetails` | 02 §1.3.4 SE-44 | UI | Merge | Merges into ETD-driven generic rendering (07 §6, §12) | R6 |
| SE-45 | Release output | 02 §1.3.4 SE-45 | module (software-engineering) | Merge | Merges into module packs on the signed release feed (07 §10) | R7 |
| SE-46 | Extraction roadmap | 02 §1.3.4 SE-46 | module (software-engineering) | Drop | Planning survives in `06-roadmap-streamline.md` | — |

## 5. Plugins (02 §3.1)

| ID | Feature | Source | Owner | Verdict | New home | Roadmap item |
|---|---|---|---|---|---|---|
| PL-01 | catalyst-git | 02 §3.1 P1 | plugin | Keep | Optional extension, not core: `extensions/` (07 §8) | R4.7 |
| PL-02 | agile (project-management) | 02 §3.1 P2 | plugin | Park | Until a second real plugin exists (B3, *owner, 2026-10-08*); the capability goes to modules as data (07 §8) | R4.7 |
| PL-03 | `project-management/` type slot | 02 §3.1 P3 | plugin | Park | Until a second real plugin exists (B3, *owner, 2026-10-08*) (07 §8) | R4.7 |
| PL-04 | Process modules | 02 §3.1 P4 | module (software-engineering) | Keep | Modules as data (`module.yaml` + `guidance.md`), folders in the core repo, several per deployment (07 §4.2, §10); installed by `catalyst module install` (*owner, 2026-10-08*) | R4.3, R4.9 |
| PL-05 | `sample-process` | 02 §3.1 P5 | module (software-engineering) | Merge | Merges into the second reference module used as a CI fixture (07 §13; 06 R7) | R7 |
| PL-06 | SE module UI bundle | 02 §3.1 P6 | UI | Merge | Merges into ETD-driven generic rendering (07 §6, §12) | R6 |
| PL-07 | `sample-process/ui` | 02 §3.1 P7 | UI | Merge | Merges into ETD-driven generic rendering (07 §6, §12) | R6 |
| PL-08 | Agent adapter | 02 §3.1 P8 | user/agent shim | Keep | Generated agent adapters (`catalyst adapters write`, 07 §5.4) | R4.5 |
| PL-09 | `/register-catalyzer`, `/modify-catalyzer`, `/delete-catalyzer` | 02 §3.1 P9 | plugin | Park | Until a second real plugin exists (B3, *owner, 2026-10-08*) (07 §8: "3 personal commands parked") | R4.7 |
| PL-10 | `/catalyzer` | 02 §3.1 P10 | plugin | Park | Until a second real plugin exists (B3, *owner, 2026-10-08*) (07 §8) | R4.7 |

---

## Open questions for the owner

None. The 2026-10-08 answers are below.

## Decided (owner, 2026-10-08)

- **ADR status:** `docs/adr/README.md` shows every ADR the owner has not decided as Pending, matching the files.
- **Plugin catalog merge (PR-54):** dropped from 06 W4; sync keeps installed plugins itself.
- **Sync four-eyes (PR-55):** stays for now.
- **Ledger (K-07):** survives the ≤ 3k-token install.
- **R1.2** is install simplification; the prose feature freeze is R1.6 (ADR-017).
- **Locator (K-19, K-20):** revised the same day: the tracked `catalyst.toml` (renamed from `<name>.catalyst`) names the project; the criterion lives at `$HOME/.catalyst/projects/<name>/criterion` (ADR-010).
- **`/project` and agent switch (K-05, K-24, PR-45, PR-47, CMD-15, CMD-16):** follow 07: `catalyst move` added to R2 W5; `agent switch` only until `move` exists.
- **Sharing (K-22, K-23, PR-48, CMD-13):** R3.6 required; `integrity` becomes a `catalyst check` rule, `protect` a `publish` option.
- **Workflow (K-50, PR-40):** a declared state machine (07 §4.1); ADR-008 rejected.
- **Module install (K-17, PL-04):** roadmap item R4.9, plan `docs/plans/r4-9-module-install.md`; several modules per deployment, `install` adds one beside the others.
- **Unmentioned rows (K-66, K-71, PR-09, PR-51, PR-62, SE-22, SE-33, SE-34):** Keep confirmed.
- **B3 / B4 (`10`):** accepted: plugins parked until R4.7, meta-tags become a `tags:` field.
