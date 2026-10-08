# ADR-001: One file per rule document, not per rule ID

**Date:** 2026-10-07  
**Status:** Accepted  
**Author:** Catalyst Team  
**Affected scope:** kernel

## Context

During the R0 phase, ambiguity existed about how to organize rules in the catalyst framework:
1. **One file per individual rule ID** (e.g., `rr-META-001.md`, `rr-META-002.md`, …) — creates ~100+ files, splits related rules across many files
2. **One file per rule document** (e.g., `Rules-of-Rules.md` contains RR-META-001…006) — keeps related rules grouped in coherent documents

The existing practice already used one file per rule document, but this decision was not formally documented, creating uncertainty about the canonical storage model.

## Decision

**One file per rule document.** Rules are organized by domain/purpose in documents; each rule document is one file. Examples:
- `Rules-of-Rules.md` contains meta-rules (how rules are created, versioned, cited)
- Domain documents contain 1–20 related rules with clear ID numbering (e.g., structure rules, behavior rules, plugin rules)

## Consequences

- **Positive:**
  - Related rules stay together, providing essential context
  - Improved discoverability: new contributors find all rules in a domain in one place
  - Manageable scale: ~10 rule documents vs. ~100+ individual rule files
  - Semantic clarity: each document title reflects its domain/purpose
  - Formalizes existing practice; no migration needed
  - Easier navigation and understanding of rule clusters

- **Negative:**
  - Large documents require careful organization to prevent overwhelming readers
  - Search-and-replace for cross-document rule changes must span multiple documents

- **Trade-offs:**
  - Traded individual file isolation for thematic coherence and reduced fragmentation

## Alternatives Considered

1. **One file per rule ID:** This would create approximately 100+ rule files, making the framework difficult to navigate and losing the semantic relationships between related rules. Rejected as unmaintainable and fragmented.

2. **Hybrid: group documents by type, each containing related rules:** This is what was chosen—documents like `Rules-of-Rules.md` are the canonical form.

## Related

- Source: `docs/plans/r0-decisions-session-scope-and-rule-storage.md`
- Enforced by: `catalyst validate` (checks rule-document structure, ID uniqueness, and domain grouping)
- Related: INV-8 (No orphan rules)
