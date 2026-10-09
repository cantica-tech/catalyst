# ADR-004: Meta-rules (rr-*) govern the rule system itself

**Date:** 2026-10-07  
**Status:** Pending (awaiting owner decision)  
**Author:** Catalyst Team  
**Affected scope:** kernel

## Context

As the catalyst framework's rule system grew, questions arose about how rules themselves should be governed:

- Who creates new rules?
- How are rule IDs assigned?
- What makes a rule valid?
- How are rules versioned or deprecated?
- What constraints apply to rule references?

Rather than having these be implicit conventions, they needed to be explicit, documented rules. This led to the concept of **meta-rules**—rules that govern the rule system itself.

## Decision

**Meta-rules (rr-\* prefix, located in `Rules-of-Rules.md`) govern the rule system itself.**

Meta-rules include:

- How rules are created, numbered, and named (rr-META-001, rr-META-002, etc.)
- Requirements for rule documents (formatting, ID sequences, domain coverage)
- Rules about how other rules can reference each other
- Rules about rule versioning, deprecation, and supersession
- Rules about who can create rules and when
- Rules about rule documentation and evidence requirements

These meta-rules are themselves rules and must comply with the rule system's own requirements.

## Consequences

- **Positive:**
  - The rule system becomes self-describing and self-governing
  - New rule creation is guided by explicit standards
  - Consistency is enforced through meta-rules, not informal conventions
  - Disputes about rule validity can be resolved by reference to meta-rules
  - Enables automated validation of rule compliance

- **Negative:**
  - Adds a layer of indirection (rules about rules)
  - Meta-rules changes require careful consideration (they affect all rules)
  - Risk of meta-rules becoming too prescriptive or too loose

- **Trade-offs:**
  - Traded simplicity (just write rules) for rigor (rules must follow meta-rules)

## Alternatives Considered

1. **Implicit conventions:** Rules follow unstated conventions established through practice. Rejected: leads to inconsistency and makes onboarding difficult.

2. **External governance:** Rule governance defined in separate policy documents outside the rule system. Rejected: violates the principle that rules should be self-governing.

3. **Centralized rule authority:** One person or committee approves all rules. Rejected: does not scale and requires explicit delegation rules anyway.

## Related

- Source: Analysis from framework discussions; formalized in migration planning
- Implemented in: `Rules-of-Rules.md` (meta-rules section)
- Related: ADR-003 (Rule domains define seams), INV-8 (No orphan rules)
