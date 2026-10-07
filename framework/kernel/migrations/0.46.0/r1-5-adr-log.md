# R1.5: ADR Log (Architecture Decision Record)

**Objective:** Document key design decisions made during the R0–R1 refactor
window, creating a reference for R2–R7 and post-1.0 evolution.

**Why:** Catalyst has accumulated 40+ design decisions across rules, module
format, product naming, and infrastructure. An ADR log:
- Preserves rationale (why, not just what).
- Guides future contributors (unpack the "why" before changing things).
- Tracks trade-offs and open questions.
- Enables confident deprecation (we'll *know* why something exists).

---

## ADR Format

Each decision: one file, `docs/adr/ADR-<NN>-<slug>.md`, following
[Nygard's ADR format](https://adr.github.io/madr/):

```markdown
# ADR-NN: <Title>

**Date:** YYYY-MM-DD  
**Status:** Accepted | Pending | Superseded by ADR-MM | Rejected  
**Author:** <name>  
**Affected scope:** [kernel|SE module|plugins|catalyst-ui|infra]

## Context

Why the decision was needed. What problem does it solve?

## Decision

What we decided to do (and why this option over alternatives).

## Consequences

- Positive: …
- Negative: …
- Trade-offs: …

## Alternatives Considered

1. Alt A: Why we rejected it.
2. Alt B: Why we rejected it.

## Related

- ADR-XX (related decision)
- Issue: github.com/oliben67/catalyst#123
- Migration: 0.46.0/r0-decisions-*.md
```

---

## Decisions to Log (R1.5 Scope)

### Core Model & Rules

| ADR | Title | Scope | Status | Source |
|-----|-------|-------|--------|--------|
| ADR-01 | One file per rule document, not per rule ID | kernel | **Accepted** | R0.9 decision |
| ADR-02 | Session-scoped stop hook (block only session edits) | kernel | **Accepted** | R0.5 decision |
| ADR-03 | Rule domains define seams; rule documents map to domains | kernel | **Accepted** | what-is-going-on/01a §5 |
| ADR-04 | Meta-rules (rr-\*) govern the rule system itself | kernel | **Accepted** | Rules-of-Rules.md §1 |
| ADR-05 | Artifacts linked to rules via etd: ID pointers | kernel | **Accepted** | INV-5, MODULE-SPECIFICATION.md §6 |

### Module & Process

| ADR | Title | Scope | Status | Source |
|-----|-------|-------|--------|--------|
| ADR-06 | SE module as canonical process plugin (through R2) | SE module | **Pending** | Roadmap R1.2 hardcoding decision |
| ADR-07 | Artifact tiers (Support, Guidance, Enforcement) for severity | SE module | **Accepted** | Rules-of-Rules.md §2 |
| ADR-08 | Workflow links as narrative thread (not state machines) | SE module | **Accepted** | workflow ETD spec |

### Store & Migration

| ADR | Title | Scope | Status | Source |
|-----|-------|-------|--------|--------|
| ADR-09 | Existing deployments remain LEGACY; new deployments use locator | kernel | **Accepted** | what-is-going-on/06 §R3.4 |
| ADR-10 | `catalyst.toml` locator (R3) replaces symlink + pointer + submodule | kernel | **Pending** | what-is-going-on/08 (criteria proposal) |
| ADR-11 | Store abstraction with `in-repo` driver (R3 default) | kernel | **Pending** | 08 § "One truth" design |

### Product & Brand

| ADR | Title | Scope | Status | Source |
|-----|-------|-------|--------|--------|
| ADR-12 | Catalyst is the framework; kernel is the rule engine | infra | **Accepted** | BOOTSTRAP.md hard rule 3 |
| ADR-13 | Version ceiling: kernel 0.46.0, SE module 2.4.0 (R1 start) | infra | **Accepted** | .catalyst pointer |
| ADR-14 | Release 1.0 aligns R7 (R3.9: multi-user server, R5: UI parity) | infra | **Pending** | what-is-going-on/06 §R7 |

### UI & Interaction

| ADR | Title | Scope | Status | Source |
|-----|-------|-------|--------|--------|
| ADR-15 | Catalyst has three UIs: CLI (kernel), SPA (R6), desktop (R6) | infra | **Pending** | what-is-going-on/06 §R6 |
| ADR-16 | VS Code thin client (R6) uses server protocol (R3.9) | infra | **Pending** | 06 §R5–R6 |

---

## Implementation Plan

### Phase 1: Extract Existing Decisions

Read and summarize:
1. `framework/kernel/INVARIANTS.md` (INV-01 through INV-30 → ADRs)
2. `framework/kernel/BOOTSTRAP.md` (hard rules 1–9)
3. `framework/kernel/Rules-of-Rules.md` (meta-rules, §1–3)
4. `framework/kernel/MODULE-SPECIFICATION.md` (artifact linking, §6)
5. `what-is-going-on/10-questions-and-decisions.md` (§"Questions")
6. R0 migration doc (R0.5, R0.9 decisions)

**Output:** 20–25 ADR files.

### Phase 2: Write ADRs

**Directory:** `docs/adr/`

**Template:** Use marker above; one file per decision.

**Priority order** (for initial write-up):
1. Core model (ADR-01 through -05)
2. Store & migration (ADR-09 through -11)
3. Product & brand (ADR-12 through -14)
4. UI & interaction (ADR-15, -16)
5. SE module specifics (ADR-06 through -08)

### Phase 3: Index & Link

**File:** `docs/adr/README.md`

```markdown
# Architecture Decision Records

This folder documents design decisions made in the catalyst refactor (R0–R7).

## Index by Scope

### Kernel

- [ADR-01: One file per rule document](ADR-01-one-file-per-rule-document.md)
- [ADR-02: Session-scoped stop hook](ADR-02-session-scoped-stop-hook.md)
- ...

### SE Module

- [ADR-06: SE module as canonical process](ADR-06-se-module-canonical-process.md)
- ...

### Store & Infrastructure

- [ADR-09: LEGACY deployments, locator for new](ADR-09-legacy-vs-locator.md)
- ...

### UI & Interaction

- [ADR-15: Three UIs architecture](ADR-15-three-uis.md)
- ...

## Status Summary

- **Accepted:** ADR-01, -02, -03, -04, -05, -07, -08, -12, -13
- **Pending** (await R2/R3/R5 decisions): ADR-06, -09, -10, -11, -14, -15, -16
- **Superseded:** (none yet)

## How to Use

1. **Before making a change:** Check if an ADR covers it. Read the "Consequences" section.
2. **When proposing a new design:** Write an ADR first (status: Pending). Link it in PRs.
3. **When a decision changes:** Mark old ADR "Superseded by ADR-NN".
4. **Post-1.0:** Use ADRs to explain why features exist, not just what they do.
```

---

## Integration Points

### Grounded Docs

Once written, ADRs should be linked from:
- `framework/kernel/INVARIANTS.md` (replace INV-NN with ADR-NN references)
- `framework/kernel/BOOTSTRAP.md` (hard rules → ADR references)
- Migration documents (e.g., `0.46.0/r0-decisions-*.md` → ADR-01, -02)
- `what-is-going-on/` analysis (for future readers)

**Effort:** Light — just add backreferences; no rewrites needed.

### CI Token Budget

ADRs are grounded docs (discoverable from BOOTSTRAP). Add to `measure_tokens.py`:

```python
def measure_adr_tokens():
    adr_files = glob("docs/adr/ADR-*.md")
    total = sum(count_tokens(f) for f in adr_files)
    return total
```

**Target:** ≤10k tokens (average 400 tokens per ADR, ~25 ADRs).

---

## Acceptance Criteria

✓ **20–25 ADR files created in docs/adr/**  
✓ **Each ADR covers: context, decision, consequences, alternatives**  
✓ **ADRs linked from INVARIANTS, BOOTSTRAP, migration docs**  
✓ **docs/adr/README.md index created (by scope, status)**  
✓ **ADR token budget measured and thresholds set**  
✓ **R1.5 ADRs marked Pending or Accepted (not all need to be Accepted yet)**  

---

## Rollout

- **Commit to development:** ADR-01 through ADR-25 + README index
- **Testing window:** 1 day (verify links, check token count)
- **Merge to main:** Ready for R2 (use ADRs to document new decisions)

---

## Open Decisions & Future ADRs

### R2–R7 ADRs (To Be Written)

| Phase | Title | When |
|-------|-------|------|
| R2 | CLI verb design (16 verbs, --json schema) | Mid-R2 |
| R3 | Locator spec (catalyst.toml format) | Start-R3 |
| R3 | Store driver API | Start-R3 |
| R5 | Server protocol (R3.9 catalyst serve) | Start-R5 |
| R6 | SPA & desktop UI architecture | Start-R6 |
| Post-1.0 | Plugin isolation & sandboxing | After R7 |

These ADRs will be written during their respective phases; R1.5 is the
baseline infrastructure.

### Questions Parking Lot

From `10-questions-and-decisions.md`, deferred to later phases:
- Module release coupling (SE 2.4.0 ↔ kernel 0.46.0 version strategy) → ADR when R3 multi-module is ready
- RECON close rule (confirmation flow for `/reconcile close`) → ADR when R2 verb spec is finalized
- Plugin architecture (isolation, permissions) → ADR post-1.0

---

## Related

- `what-is-going-on/10-questions-and-decisions.md` (source of decisions)
- `framework/kernel/INVARIANTS.md` (INV rules → ADRs)
- `framework/kernel/BOOTSTRAP.md` (hard rules → ADRs)
- R0 migration docs (R0.5, R0.9 → ADR-01, -02)
