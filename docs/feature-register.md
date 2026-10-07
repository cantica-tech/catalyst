# Feature Register — R1.3

**Date:** 2026-10-07  
**Status:** R1.3 inventory lock — baseline for refactoring R0–R7  
**Source:** Analysis documents `what-is-going-on/01a`, `01b`, `02`

---

## Overview

This register tracks all documented features across the kernel (K-01…K-73), the software-engineering module (SE-01…SE-NN), and plugins (P-01…P-NN). Each entry includes:
- **ID & Name** — Stable identifier and human-readable name
- **Category** — kernel / module / plugin
- **Verdict** — Keep / Merge / Drop (owner decision)
- **Rationale** — Why (impact of the decision)
- **New Home** — Where this capability lands after refactoring (R2–R7)

**Totals:** 73 kernel features, ~30 module features, ~10 plugin features.

---

## Kernel Features (K-01…K-73)

| # | Feature | Verdict | Rationale | New Home (R2–R7) |
|---|---|---|---|---|
| K-01 | Agent entry shims (CLAUDE.md, AGENT.md, SYSTEM.md) | **Keep** | Agent-agnostic access; critical for multi-agent support | Updated shims per agent; `/bootstrap` to reload |
| K-02 | Single install entry (BOOTSTRAP.md) | **Keep** | Convergence point; prevents drift | Shorter brief + generated agent-specific guide (R4) |
| K-03 | Hard rules (BOOTSTRAP §0) | **Keep** | Anti-drift anchor; re-read cheaply | Move to 12-line brief (R4); auto-inject at session start |
| K-04 | Capability detection and fallbacks | **Keep** | Portability; enables varied environments | Formalise in MCP adapter layer (R5) |
| K-05 | Agent-switch handling | **Keep** | Multi-agent governance | CLI verb `catalyst agent switch` (R2); mirror is automated |
| K-06 | Install (`catalyst init`) | **Keep** | One-shot onboarding | Simplified: fewer judgment questions (R1.2); tests-first (R0 ✓) |
| K-07 | Deployment ledger | **Keep** | Work tracking; manual record | Kept as optional supplement to CLI `status`; template (R4) |
| K-08 | Re-ground cadence | **Keep** | Anti-drift discipline | Automated: session grounding (R0 ✓); no manual cadence needed |
| K-09 | Assent gate (before commit/push) | **Keep** | Safety; user control | Stays as git hook; no CLI bypass |
| K-10 | Invariants file | **Keep** | Canonical rules | Auto-deployed and injected (R0 ✓); kept brief |
| K-11 | Module invariants | **Keep** | Module-owned constraints | Auto-composed into deployed copy (R0 ✓) |
| K-12 | Kernel/module split | **Keep** | Portability; reduced coupling | Formalised by R2 (no module-specific code in kernel) |
| K-13 | Module manifest (module.yaml) | **Keep** | Machine-readable contract | Redesigned as v3 (17 KB instead of 130 KB) in R4 |
| K-14 | Entity Type Definition (ETD) | **Keep** | CLI knows all types without naming | Simplified to core fields only (R4) |
| K-15 | Grounding model (required/inherited/none) | **Keep** | Links validate; chain invariant | Kept as-is; enforced by CLI (R2) |
| K-16 | Document composition | **Keep** | One source per doc (kernel + module) | Formalised; keyed in module.yaml (R4) |
| K-17 | Module catalog | **Keep** | Discovery; purity denylist | Moved to CLI (R2): `catalyst catalyzer list` |
| K-18 | Kernel purity check | **Keep** | Enforces module-agnosticism | Stays as CI check; added to tests (R0 ✓) |
| K-19 | Pointer file (.catalyst) | **Keep** | Path-free, agent-agnostic | Simplified to core fields; stored as `.catalyst.toml` (R3) |
| K-20 | Working copy in agent-owned space | **Keep** | Governance ≠ product code | Supported by symlink repair (R0 ✓); no change |
| K-21 | In-project fallback (.criterion/ local) | **Keep** | Portability for agents without owned space | Used when symlinks unavailable |
| K-22 | Shared deployment (repoed, submodule) | **Keep** | Multi-user on git; PR-based governance | Redesigned as locator + drivers (R3); submodule option kept |
| K-23 | /criterion lifecycle | **Merge** | Sub-verbs → `catalyst criterion` CLI verb (R2) | `catalyst criterion create/join/status/push/sync/integrity` |
| K-24 | /project lifecycle | **Merge** | Sub-verbs → `catalyst project` CLI verb (R2) | `catalyst project create/remove/export/import` |
| K-25 | Uniform artifact-type layout | **Keep** | Predictability; templates | Formalised in v2 definitions (R0 ✓) |
| K-26 | Descriptive file naming | **Keep** | Human-findable; validated | Enforced by CLI (R2) |
| K-27 | Rules, rule documents, rules index | **Keep** | No orphan rules; traceability | One file per rule document (R0.9 ✓); index auto-generated (R2) |
| K-28 | Domains and sub-domains | **Keep** | Semantic grouping | Formalised as a taxonomy; auto-validated (R2) |
| K-29 | Rule ID scheme (rr-META-003-yCNjAMXO) | **Keep** | Stable, never-reused, collision-free | Enforced by CLI `catalyst id next-rule` (R0 ✓) |
| K-30 | Rule retirement (🗑 marker) | **Keep** | References don't dangle | Enforced by CLI `catalyst link` (R2) |
| K-31 | Workflow ETD | **Keep** | Entity lifecycle states and transitions | Simplified in v2; `required_when_closed` validated (R0 ✓) |
| K-32 | Backref maintenance (linked artifacts) | **Merge** | → `catalyst link` verb (R2) | Bidirectional refs auto-maintained by CLI |
| K-33 | Reconciliation (RECON-) | **Keep** | Multi-branch conflict resolution | Gate enforced (R0 ✓); redesigned for R3 consensus model |
| K-34 | RECON workflow states | **Keep** | Proposed→Accepted→Closed | Formalised; only `/reconcile close` closes (R0 ✓) |
| K-35 | Role-based access (RECON only) | **Keep** | Write gates on merge, accept, close | Enforced in CLI (R0 ✓) |
| K-36 | IAM: users, roles, permissions | **Keep** | Identity and access control | Journaled writes (R0 ✓); CLI verbs (R2) |
| K-37 | /user-* commands | **Merge** | → `catalyst user` verb group (R2) | `catalyst user add/remove/modify/assign-role/list` |
| K-38 | /role-* commands | **Merge** | → `catalyst role` verb group (R2) | `catalyst role add/modify/list` |
| K-39 | /status command | **Merge** | → `catalyst status` verb (R2) | Shows entity states; RECON gate enforced (R0 ✓) |
| K-40 | Meta-tags | **Drop** | Unused (0 instances in this deployment) | Replace with `tags:` field in all entity types (R4) |
| K-41 | Frozen definitions | **Keep** | v1 + v2; v1 untouched for legacy | v2 used for new definitions (R0 ✓); auto-migration (R3) |
| K-42 | Entity versioning (v1, v2, …) | **Keep** | Backward compatibility during refactors | Supported by ETD `schema_version` (R2 enforces on create) |
| K-43 | Analysis playbook (/run-analysis) | **Keep** | Four-eyes audits + findings booking | Simplified: findings → artifacts, not stored in prose (R2) |
| K-44 | Analysis findings as entities (ANALYSIS-NN) | **Keep** | Grounded audits; traceable | New ANALYSIS entity type in all modules (R4); CLI auto-book |
| K-45 | Entity import/export | **Merge** | → `catalyst entity export/import` (R3) | Supports migration and sharing |
| K-46 | Multi-stage sync | **Keep** | plan → apply flow; reversible | Improved by machine-readable migration index (R2) |
| K-47 | Schema alignment (migrations) | **Keep** | ETD changes tracked; deployments migrated | v0.45→0.46 schema changes in migration (R0 ✓); auto-applied (R3) |
| K-48 | Migrations index (machine-readable) | **Keep** | Tells the tool what changed, when, and why | Linked from SYNCHRONIZE.md (R0 ✓); YAML (R2) |
| K-49 | Journal (hash chain) | **Keep** | Immutable audit trail; verify chain | Core to R3 redesign (drivers, shards) |
| K-50 | Journal entry fields | **Keep** | actor, command, timestamp, body, category, schema_version | Kept per FORMAT 1.0-rc; immutable after write (R3) |
| K-51 | Journal pins (product .git refs) | **Keep** | Anchor points for recovery, audit | Fetched on sync (R0 ✓); used for recovery (R3) |
| K-52 | Criterion repository (backend) | **Keep** | Shared deployment storage; one truth | Redesigned in R3 (drivers: repo, db, journal-remote) |
| K-53 | Criterion push flow | **Keep** | Pull-request-based governance on shared | CI from base branch (R0 ✓); rebase+check+merge (R2) |
| K-54 | Criterion join (clone into agent space) | **Keep** | New contributor onboarding | Updated for new locator (R3) |
| K-55 | /adopt command | **Merge** | → `catalyst journal adopt` (R2) | Retroactively journal a commit |
| K-56 | /lock / /unlock | **Keep** | Prevent concurrent edits during sensitive ops | Upgraded to cross-platform lock (R0 ✓) |
| K-57 | /trace command | **Merge** | → `catalyst journal trace` (R2) | Show commitment chain for a file |
| K-58 | /check command | **Merge** | → `catalyst check` (already CLI, tested R0 ✓) | Verifies chain, schema, governance scope |
| K-59 | /catalyst init` install rollback | **Keep** | Failed init restores pre-existing state | Tested in R0 ✓ |
| K-60 | ID allocation under lock | **Keep** | `id next-rule` never reuses a number | Cross-platform lock (R0 ✓); tested (R0 ✓) |
| K-61 | Plugin system (catalyzer) | **Merge** | Park as v0.x (not a 1.0 headline) | Keep `catalyst-git` as example; adapters via MCP (R5) |
| K-62 | Plugin working contract | **Keep** | README + working-contract.md in plugin repo | Kept as-is; no plugin shipped at 1.0 |
| K-63 | Plugin activation (/catalyzer) | **Merge** | → `catalyst catalyzer activate/deactivate/list` (R2) | UI can also manage plugins (R6) |
| K-64 | CLI architecture (verbs, subverbs, args) | **Keep** | `catalyst <verb> [<subverb>] [args]` | Enhanced with `--json`, structured output (R2) |
| K-65 | CLI `--json` output | **Keep** | Machines read catalysts; adapters consume | Standardised format (R2); all verbs support it |
| K-66 | Version string (X.Y.Z+gSHA) | **Keep** | Tracks build; reproducible | Embedded in pyz (R0 ✓) |
| K-67 | Python floor (3.9) | **Keep** | CI matrix 3.9–3.13; git 2.28+ | Declared (R0 ✓); CI tested (R0 partial, Windows pending) |
| K-68 | Windows portability | **Keep** | No symlinks, no colons in paths, shebangs conditional | Target for 1.0; bundled Python runtime (R7) |
| K-69 | Vendored zipapp (dist/catalyst.pyz) | **Keep** | No pip install needed; portable | Updated to 0.46.0; reproducible build (R0 ✓) |
| K-70 | Stop hook (fail-closed) | **Keep** | Blocks stops on violations; unblocks second attempt (R0.5 ✓) | Session-scoped in R2; blocks only new failures |
| K-71 | SessionStart hook (grounding) | **Keep** | Injects INVARIANTS at session start | Deployed in 0.46.0 (R0 ✓); template provided |
| K-72 | Format version (1.0-rc) | **Keep** | Declared; format check on load | One big migration to 1.0 after beta (R6 trial) |
| K-73 | Documentation: BOOTSTRAP, INVARIANTS, CLI.md, guides | **Keep** | Portable grounding | Shortened in R4 (generated docs); brief auto-injected |

---

## Software-Engineering Module Features (SE-01…SE-NN)

| # | Feature | Verdict | Rationale | New Home |
|---|---|---|---|---|
| SE-01 | Artifact entity types (REQ, BUG, FEAT, STEP, BACKLOG, …) | **Keep** | Core to the module | v2 definitions deployed (R0 ✓); unchanged |
| SE-02 | Grounding type: rules | **Keep** | REQ/BUG must link to a rule or be unjournaled | Enforced by CLI (R2) |
| SE-03 | Severity field (bug-only) | **Keep** | Risk classification; impacts priority | Marked `required` in v2 ETD (R0 ✓) |
| SE-04 | Status workflow (Open→In Progress→Done/Closed) | **Keep** | Lifecycle tracking | Simplified; ETD transitions enforced (R2) |
| SE-05 | Roadmap entity (RM-) | **Keep** | Phased delivery planning | Kept for product roadmaps; not every artifact |
| SE-06 | Roadmap fields (Status, Linked, …) | **Keep** | Planning metadata | v2 schema enforces all fields (R0 ✓) |
| SE-07 | Roadmap automation (linked artifact status roll-up) | **Drop** | Theoretical but never implemented; LLM-driven roll-up too brittle | Manual status; artifacts link to RM items |
| SE-08 | Backlog entity (BACKLOG-) | **Keep** | Unplanned work queue | Separate from roadmap; linked via refs |
| SE-09 | /create-* commands (6 artifact types) | **Merge** | → `catalyst new <PREFIX>` (R2) | One verb with consistent questions |
| SE-10 | /status command (artifact state changes) | **Merge** | → `catalyst status set <ID> <state>` (R2) | Enforces allowed transitions |
| SE-11 | /link command (backref maintenance) | **Merge** | → `catalyst link <ID> to <ID2>` (R2) | Bidirectional refs auto-maintained |
| SE-12 | Four-eyes analysis (/run-analysis) | **Keep** | Dual-agent audits; findings booking | Simplified to book findings as entities (R2) |

---

## Plugin Features (P-01…P-NN)

| # | Feature | Verdict | Rationale | New Home |
|---|---|---|---|---|
| P-01 | Plugin activation (/catalyzer activate) | **Keep** | User control over extensions | Kept for future plugins; none at 1.0 |
| P-02 | Vendor isolation (plugin repo only) | **Keep** | Security; no framework code from plugins | Enforced (R2) |
| P-03 | Work-items plugin (epic/story/task/…) | **Drop** | Parked; not a headline feature at 1.0 | Plugin repos stay frozen; re-activate post-1.0 |
| P-04 | Agile workbench plugin | **Drop** | Same; not a 1.0 requirement | Feature freeze; may ship as post-1.0 plugin |

---

## Summary

- **73 kernel features** — all **Keep** except merges (23 → CLI verbs), drops (1: meta-tags)
- **~12 SE module features** — all **Keep** except drops (1: auto roll-up) and merges (4 → CLI verbs)
- **~4 plugin features** — 2 Keep, 2 Drop (parked)

**No feature is lost:** each capability is tracked to its R2–R7 new home (07 §12 mapping).

---

## Next Steps (R1–R2)

1. **R1.4** — Golden corpus: snapshot 3 deployments as test fixtures
2. **R1.5** — ADR log: start documenting design decisions
3. **R2** — Code replaces prose: implement the 16 target CLI verbs (from 38 command files)
   - Each verb has tests + `--json` output
   - Command files shrink to "run X; judgment Y"
4. **R2.1** — Collapse /` surface from 38 → 16; alias files auto-generated
5. **Token impact:** W1 (reads) −95%, W2 (creates) −80%, W4 (sync) −90% → total ≥80% savings

---

**Approved by:** Owner (2026-10-07)  
**Locked for:** R0–R7 refactoring; no new prose features until R2
