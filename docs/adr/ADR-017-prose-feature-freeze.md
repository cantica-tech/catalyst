# ADR-017: Prose feature freeze until the R2 verbs exist

**Date:** 2026-10-08  
**Status:** Accepted  
**Author:** Olivier Steck (owner)  
**Affected scope:** kernel

## Context

Kernel versions 0.35 → 0.45 shipped in about a week, and INV-6 was rewritten
seven times. Every new behaviour arrived as more prose an agent must read and
obey: an invariant, a meta-rule, a slash command, an entity type or a guide.
That prose is what costs tokens and what drifts. Roadmap R2 replaces much of it
with CLI verbs (code, tested); adding prose before then only grows what R2 has
to replace.

## Decision

The kernel's prose surface is frozen until the R2 verbs exist (roadmap R1.2):

- **Frozen:** the invariants (`INVARIANTS.md`), the meta-rules
  (`rules-of-rules.template.md`), the §4 slash commands
  (`rules-of-development.template.md`), the entity types (`entities/`,
  `definitions/`) and the kernel's top-level documents.
- **Allowed:** corrections and clarifications to existing text, and new
  behaviour as CLI code with tests (the CLI-first rule).
- **Enforced:** `scripts/check_frozen_surface.py` compares the surface with the
  snapshot `docs/FROZEN-SURFACE.json`; `tests/test_frozen_surface.py` fails on
  any addition or removal. Prose growth inside existing items is already capped
  by the token budgets (R1.1).
- **Exceptions:** an item enters or leaves the surface only with an ADR that
  says why, then `python3 scripts/check_frozen_surface.py --write` in the same
  change.

The freeze lifts per item as R2 delivers the verb that replaces it, and
entirely at the end of R2.

## Consequences

- **Positive:** the surface stops growing while it is being replaced; every
  change to it is visible in review and traced to an ADR.
- **Negative:** a genuinely missing rule waits for R2 or needs an ADR.
- **Trade-offs:** process modules are not covered (they live in their own
  repositories); the same check can be applied to them later.

## Alternatives Considered

1. **Freeze by convention only:** no mechanism; the past week shows it does
   not hold.
2. **Install simplification as R1.2:** a different item (fewer install
   questions); it needs the R2 verbs for real detection, so it moves to R2 as a
   candidate.

## Related

- Roadmap R1.2 (prose feature freeze), R1.1 (token budgets), R2 (code replaces prose)
- `docs/plans/r1-2-install-ux-simplification.md` (R2 candidate, not R1.2)
