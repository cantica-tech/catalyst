# ADR-002: Session-scoped stop hook (block only session edits)

**Date:** 2026-10-07  
**Status:** Accepted  
**Author:** Catalyst Team  
**Affected scope:** kernel

## Context

The stop hook runs `catalyst check` and other validators on every session end. Prior to R0.5, if ANY unjournaled changes existed (from any session, concurrent or historical), the hook would fail and block the session from ending. This created a critical usability problem in multi-session scenarios: one contributor's uncommitted work would block every other contributor's ability to stop their own session.

**Example failure:** Session A has an unjournaled change in `.criterion/rules/`. The stop hook detects it and blocks. Sessions B, C, and D cannot stop even though they made no changes to `.criterion/`.

This design violated the principle of session isolation and caused cascading blocking issues.

## Decision

The stop hook must distinguish between:

- **Pre-existing failures:** Changes that existed when this session started (do not block)
- **New failures:** New unjournaled changes made during this session (block on these)

Only exit 2 (block) if new failures emerged during the session. If failures were present at session start, report them but exit 0 (allow the session to stop).

## Consequences

- **Positive:**
  - Sessions are now independent; one contributor's work does not block another's
  - Parallel development workflows become unblocked
  - Session end is no longer a potential deadlock point
  - Encourages users to commit work before ending sessions while not penalizing them for pre-existing issues

- **Negative:**
  - More complex stop-hook logic (baseline tracking required)
  - Requires session start metadata (baseline state capture)
  - Transitional period may require running stop twice until full implementation lands

- **Trade-offs:**
  - Traded stricter validation for practical parallel-session usability
  - Deferred perfect consistency checking in favor of pragmatic workflow support

## Alternatives Considered

1. **Keep strict validation:** Always fail the stop hook on any unjournaled changes. Rejected: creates deadlock in multi-session environments and violates session autonomy.

2. **Interim solution with advisory lock:** Use an existing `stop_hook_active` flag to allow the stop after one block attempt (prevent infinite loops). Rejected in favor of proper session-scoped implementation.

3. **No validation on stop:** Remove the stop hook entirely. Rejected: loses important validation that detects uncommitted work.

## Related

- Source: `docs/plans/r0-decisions-session-scope-and-rule-storage.md` (R0.5 decision)
- Implementation: `catalyst hook stop` (session-aware baseline tracking)
- Related INVs: INV-6 (Working copy outside product tree), INV-17 (Append-only journal)
