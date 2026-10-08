# ADR-007: Artifact tiers (Support, Guidance, Enforcement) for severity

**Date:** 2026-10-07  
**Status:** Pending (awaiting owner decision)  
**Author:** Catalyst Team  
**Affected scope:** SE module

## Context

The catalyst framework needs a way to classify how strictly different artifact types and rules must be followed. Some rules are fundamental to the system's integrity (must be enforced), some are best practices that should be followed (guidance), and some are helpful but optional (support).

The planning document references this in `Rules-of-Rules.md §2`, indicating that artifact tiers represent a severity or binding-ness hierarchy for different parts of the process model.

## Decision

**Artifacts are classified into three tiers based on enforcement severity:**

1. **Enforcement (strict):** Violations are flagged as errors and block operations (e.g., missing `Signed-off-by`, chain invariant violations, required fields)
2. **Guidance (recommended):** Violations are flagged as warnings; operations proceed but the issue is noted (e.g., artifact not linked to a rule, incomplete ADR, stale version)
3. **Support (optional):** Suggestions that help users but do not block or warn (e.g., recommended fields, quality metrics, style suggestions)

Each artifact type definition specifies its tier, determining how catalyst validators will treat violations.

## Consequences

- **Positive:**
  - Clear hierarchy enables different levels of rigor for different artifacts
  - Allows gradual hardening (start at Support, move to Guidance, then Enforcement over time)
  - Users understand the consequences of each violation
  - Enables adaptive workflows (strict rules for production, relaxed for drafts)
  - Supports progressive onboarding (new contributors see support suggestions, not blocked)

- **Negative:**
  - Adds classification burden (each artifact must be assigned a tier)
  - Risk of misclassification (treating Enforcement as Guidance, or vice versa)
  - Tier transitions may break existing workflows

- **Trade-offs:**
  - Traded simplicity (all rules treated equally) for nuance (tiers allow flexibility)

## Alternatives Considered

1. **Binary enforcement:** All rules are either enforced or not. Rejected: too rigid; some rules should warn but not block.

2. **Per-rule enforcement:** Each rule has its own enforcement level. Rejected: too granular; creates configuration burden.

3. **Contextual enforcement:** Enforcement level determined at runtime based on deployment stage. Rejected: too complex; static classification is clearer.

## Related

- Source: `Rules-of-Rules.md §2` (artifact tiers specification)
- Implemented in: SE module artifact definitions (bug, requirement, test, etc.)
- Related: ADR-005 (etd: pointers for artifact-to-rule linking)
- Enforced by: `catalyst validate` (reads tier from artifact definition)
