# Architecture Decision Records (ADR)

This directory contains the architecture decision records (ADRs) for the catalyst framework. Each ADR documents a significant design decision: its context, the decision made, consequences, and alternatives considered.

## Format

ADRs follow [Nygard's ADR format](https://adr.github.io/madr/). See [TEMPLATE.md](TEMPLATE.md) for the standard structure.

## Index

### Core Model & Rules

| # | Title | Status | Scope |
|---|-------|--------|-------|
| [ADR-001](ADR-001-one-file-per-rule-document.md) | One file per rule document, not per rule ID | ✅ Accepted | kernel |
| [ADR-002](ADR-002-session-scoped-stop-hook.md) | Session-scoped stop hook (block only session edits) | ✅ Accepted | kernel |
| [ADR-003](ADR-003-rule-domains-define-seams.md) | Rule domains define seams; rule documents map to domains | ⏳ Pending | kernel |
| [ADR-004](ADR-004-meta-rules-govern-rule-system.md) | Meta-rules (rr-\*) govern the rule system itself | ⏳ Pending | kernel |
| [ADR-005](ADR-005-artifacts-linked-via-etd-pointers.md) | Artifacts linked to rules via etd: ID pointers | ⏳ Pending | kernel |
| [ADR-017](ADR-017-prose-feature-freeze.md) | Prose feature freeze until the R2 verbs exist (R1.6) | ✅ Accepted | kernel |

### Module & Process

| # | Title | Status | Scope |
|---|-------|--------|-------|
| [ADR-006](ADR-006-se-module-canonical-through-r2.md) | SE module as canonical process plugin (through R2) | ⏳ Pending | SE module |
| [ADR-007](ADR-007-artifact-tiers-severity.md) | Artifact tiers (Support, Guidance, Enforcement) for severity | ⏳ Pending | SE module |
| [ADR-008](ADR-008-workflow-narrative-thread.md) | Workflow links as narrative thread (not state machines) | ❌ Rejected: workflows are declared state machines | SE module |

### Store & Migration

| # | Title | Status | Scope |
|---|-------|--------|-------|
| [ADR-009](ADR-009-legacy-deployments-vs-locator.md) | Existing deployments remain LEGACY; new deployments use locator | ⏳ Pending | kernel |
| [ADR-010](ADR-010-catalyst-toml-locator.md) | Locator `.catalyst/catalyst.toml` (vs. catalyst.json, .criterion symlink) | ✅ Accepted | kernel |
| [ADR-011](ADR-011-store-abstraction-in-repo-driver.md) | Store abstraction in repo driver (vs. inline) | ⏳ Pending | kernel |

### Naming & Versioning

| # | Title | Status | Scope |
|---|-------|--------|-------|
| [ADR-012](ADR-012-catalyst-framework-kernel-naming.md) | Naming: catalyst framework (repo), kernel (framework/kernel), modules (SE, plugins) | ⏳ Pending | infra |
| [ADR-013](ADR-013-version-ceiling-r1-start.md) | Version ceiling: R1 starts at 0.46.0; 1.0.0 after R7 complete | ⏳ Pending | infra |
| [ADR-014](ADR-014-release-1-0-aligns-r7.md) | Release 1.0.0 aligns with R7 completion (production-ready) | ⏳ Pending | infra |

### User Interfaces (R5–R6)

| # | Title | Status | Scope |
|---|-------|--------|-------|
| [ADR-015](ADR-015-three-uis-cli-spa-desktop.md) | Three official UIs: CLI (kernel, now), SPA (R6), Desktop (R6) | ⏳ Pending | infra |
| [ADR-016](ADR-016-vscode-thin-client.md) | VS Code thin client (R6) uses server protocol (R3.9) | ⏳ Pending | infra |

## Status Legend

- ⏳ **Pending:** Drafted, awaiting the owner's decision
- ✅ **Accepted:** Decided by the owner
- 🔄 **Superseded:** Replaced by another ADR (see ADR-XX)
- ❌ **Rejected:** Decided against; preserved for historical context

## Usage

When making a significant architectural decision or design choice:

1. Read related ADRs to understand existing decisions and trade-offs
2. Consult the [TEMPLATE.md](TEMPLATE.md) for the standard format
3. Create a new `ADR-NNN-slug.md` file
4. Update this README with an entry in the appropriate section
5. Link the ADR from commit messages, migration documents, and related code

## Future ADRs (R2–R7)

See [PARKING.md](PARKING.md) for decisions planned in future phases (R2–R7) and post-1.0 evolution.

## See Also

- [PARKING.md](PARKING.md) — Future ADRs for R2–R7 phases
- [TEMPLATE.md](TEMPLATE.md) — ADR format template
- `framework/kernel/INVARIANTS.md` — Invariants and hard rules
- `framework/kernel/BOOTSTRAP.md` — Installation and setup decisions
