# ADR-003: Rule domains define seams; rule documents map to domains

**Date:** 2026-10-07  
**Status:** Pending (awaiting owner decision)  
**Author:** Catalyst Team  
**Affected scope:** kernel

## Context

The catalyst framework organizes rules into documents, but the mapping between rule documents and semantic domains needed clarification. Without this explicit mapping, it was unclear:
- Which rules formed a coherent domain
- How new rules should be added to existing domains
- What constitutes a "seam" (boundary) between domains
- How modules and plugins should extend rule coverage

The framework's analysis in `what-is-going-on/01a §5` and the existing practice in rule documents like `Rules-of-Rules.md` showed that domains were already the organizing principle—they just needed formalization.

## Decision

**Rule domains define seams; rule documents map directly to domains.**

- **Domains** are semantic groupings that represent distinct areas of concern (e.g., meta-rules, structure rules, behavior rules, plugin rules, storage rules)
- **Rule documents** are files in the rules hierarchy (e.g., `rules/rules-of-rules.md`, `rules/structure/...`, `rules/behavior/...`)
- **Seams** are the boundaries between domains where one domain's rules end and another's begin; seams mark places where extensions or alternative implementations may be plugged in
- Each rule document covers one domain and contains 1–20 related rules with clear, sequential IDs

## Consequences

- **Positive:**
  - Clear organizational structure for the rule system
  - Seams provide natural extension points for plugins and process modules
  - Easier to reason about impact analysis (changes in one domain are isolated)
  - Provides foundation for automated rule organization validation
  - Enables module-specific rule additions at well-defined boundaries

- **Negative:**
  - Requires discipline to avoid domain creep or overly-broad rule documents
  - Seams must be carefully designed to be extensible but not fragile
  - Cross-domain rules become edge cases that need explicit justification

- **Trade-offs:**
  - Traded flexibility (any-to-any rule relationships) for structure (hierarchical, domain-based organization)

## Alternatives Considered

1. **Flat rule namespace:** All rules in one file with no domain structure. Rejected: loses semantic organization and makes seams invisible.

2. **Deeply hierarchical domains:** Nested domain structure (domain → sub-domain → sub-sub-domain). Rejected: adds complexity without clear benefit for current scale (~100 rules).

3. **Dynamic seams:** Seams defined at runtime based on plugin declarations. Rejected: reduces predictability and increases coupling.

## Related

- Source: `what-is-going-on/01a §5` (kernel concepts and install analysis)
- Enforced by: catalyst rule validators
- Related: ADR-001 (One file per rule document), ADR-004 (Meta-rules govern the rule system)
