# ADR-005: Artifacts linked to rules via etd: ID pointers

**Date:** 2026-10-07  
**Status:** Pending (awaiting owner decision)  
**Author:** Catalyst Team  
**Affected scope:** kernel

## Context

As the catalyst framework scaled to support multiple process modules and artifact types, the need arose to create bidirectional traceability between:
- Active-module artifacts (created by users during development work)
- The grounding rules that govern those artifacts (kernel rules defining process constraints)

The framework required a consistent, machine-readable way to link artifacts to rules that:
- Could be embedded in artifact definitions without cluttering them
- Would survive migrations and schema changes
- Could be validated and audited
- Worked across different module implementations

The `etd:` (Entity Type Definition) pointing mechanism emerged as the solution, formalized in the MODULE-SPECIFICATION.md §6 (Artifact Linking).

## Decision

**Artifacts are linked to rules via `etd:` ID pointers in the artifact definition.**

Each artifact type definition includes an `etd:` field pointing to the kernel rule (by rule ID, e.g., `etd: rr-ARTIFACT-001`) that governs that artifact type. This creates an explicit link from the module artifact upward to its kernel grounding.

Examples:
- A bug artifact type definition includes `etd: rr-ARTIFACT-005` (the rule that defines what a bug is)
- A requirement artifact includes `etd: rr-ARTIFACT-003` (the rule governing requirements)

The module's grounding type is declared once in `MODULE-SPECIFICATION.md` (field: `grounding_type`), and individual artifact types either inherit the module's grounding or specify their own.

## Consequences

- **Positive:**
  - Explicit, machine-readable linkage between artifacts and grounding rules
  - Enables impact analysis (which artifacts are affected by a rule change?)
  - Audit trail is complete and verifiable
  - Supports the chain invariant (INV-5)
  - Enables automated validation of artifact-to-rule conformance
  - Works across multiple modules and deployment scenarios

- **Negative:**
  - Requires discipline to maintain the links during rule changes
  - Dead links are possible if rules are deleted without updating artifacts
  - Adds metadata that must be kept in sync with rule document changes

- **Trade-offs:**
  - Traded implicit traceability (assumed through naming conventions) for explicit linkage (verified through IDs)

## Alternatives Considered

1. **Implicit linkage via naming:** Link artifacts to rules by matching name patterns. Rejected: fragile, doesn't survive renames, hard to audit.

2. **Separate linkage registry:** Maintain a separate file mapping artifacts to rules. Rejected: diverges from the artifact definition, creates sync problems.

3. **Runtime rule lookups:** Determine artifact-to-rule mapping at runtime based on artifact type. Rejected: hides the relationship and makes static analysis impossible.

## Related

- Source: INV-5 (Chain invariant), MODULE-SPECIFICATION.md §6 (Artifact Linking)
- Implemented in: Module ETD definitions, artifact templates
- Related: ADR-003 (Rule domains), ADR-004 (Meta-rules)
- Validates: Chain invariant enforcement in `catalyst check`
