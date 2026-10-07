# ADR-009: Existing deployments remain LEGACY; new deployments use locator

**Date:** 2026-10-07  
**Status:** Accepted  
**Author:** Catalyst Team  
**Affected scope:** kernel

## Context

The catalyst framework evolved its deployment model over time. Prior to R3, deployments were stored and managed using:
- A symlink (`.criterion` → agent-owned `.criterion/` directory or git submodule)
- A pointer file (`.catalyst` containing metadata)
- A git submodule (for shared deployments)

This model worked but was complex and hard to reason about. For R3 and beyond, a clearer model was needed that could be versioned, passed around, and understood at a glance.

The planning document (what-is-going-on/06-roadmap-streamline.md, R3.4) distinguishes between LEGACY deployments (using the old model) and new deployments using a clearer locator-based approach.

## Decision

**Existing deployments created before R3 are marked LEGACY and remain supported.** New deployments created at or after R3 use a locator-based model (catalyst.toml or equivalent).

- **LEGACY deployments:** Use symlink + pointer + submodule model; continue to work indefinitely with appropriate adapters and migration paths
- **New deployments:** Use a locator file (e.g., `catalyst.toml`) that clearly specifies the working-copy path, kernel version, module version, and other essential metadata
- **Adaptation:** Existing deployments can be migrated to new model on demand, but LEGACY support ensures no forced upgrades

## Consequences

- **Positive:**
  - Backward compatibility: existing deployments continue to work
  - Clear distinction between old and new models
  - Enables gradual migration (users choose when to upgrade)
  - New model can be cleaner and more discoverable
  - Reduces burden on existing users

- **Negative:**
  - Dual-path support adds complexity to tooling
  - Codebase must handle both LEGACY and new semantics
  - Migration tooling required to move from LEGACY to new
  - Documentation must explain both models during transition period

- **Trade-offs:**
  - Traded code simplicity for user stability and optional upgrade paths

## Alternatives Considered

1. **Forced immediate migration:** All deployments must migrate to new model at R3. Rejected: disruptive to existing users; LEGACY support is more humane.

2. **Deprecate old model but allow it:** Old model stays in source but is no longer documented or tested. Rejected: creates hidden technical debt; explicit LEGACY marking is clearer.

3. **Maintain both indefinitely:** Both models supported equally, forever. Rejected: adds unnecessary ongoing burden; bounded LEGACY support is better.

## Related

- Source: `what-is-going-on/06-roadmap-streamline.md` (R3.4: LEGACY vs. locator decision)
- Related: ADR-010 (catalyst.toml locator), ADR-011 (Store abstraction)
- Migration: 0.46.0/grounded-sessions-and-safe-gates.md step 1 (re-vendor CLI)
