# ADR-008: Workflow links as narrative thread (not state machines)

**Date:** 2026-10-07  
**Status:** Accepted  
**Author:** Catalyst Team  
**Affected scope:** SE module

## Context

Early discussions about how workflows should be represented in catalyst considered two models:
1. **Workflow as state machine:** Strict state definitions with allowed transitions (e.g., bug status goes from Open → In-Progress → Closed, with explicit rules about what can transition to what)
2. **Workflow as narrative thread:** A sequence of status changes that tells a story about the artifact's lifecycle, with looser constraints

The state-machine model is traditional in issue-tracking systems, but it creates brittleness: any unexpected status transition becomes an error, and real-world work often doesn't fit rigid states.

The planning document references this decision in the workflow ETD specification, indicating the framework chose the narrative approach.

## Decision

**Workflows are narrative threads, not state machines.** An artifact's status changes tell the story of its lifecycle:
- Status changes are logged chronologically in the artifact record
- Constraints exist (e.g., cannot revert a closed bug to open without a reason), but they are permissive rather than prohibitive
- The sequence of statuses is the narrative; tools help ensure logical progression but do not block it
- Artifacts accumulate a history of status changes, creating an audit trail

## Consequences

- **Positive:**
  - Handles real-world complexity (work doesn't always follow ideal workflows)
  - Non-blocking: users are not frustrated by strict state machines
  - Natural audit trail (history of status changes is the narrative)
  - Easier to migrate artifacts between states (fewer constraints)
  - Supports ad-hoc workflows and exceptions
  - Scales better as team practices evolve

- **Negative:**
  - Less structure; requires discipline from users to maintain logical flow
  - Harder to enforce business rules (e.g., "all bugs must be tested before close")
  - Potential for messy or contradictory status sequences
  - Requires more sophisticated analysis to understand workflow health

- **Trade-offs:**
  - Traded rigid state guarantees for flexible, narrative-based workflows

## Alternatives Considered

1. **Strict state machine:** Enforce all transitions, block invalid ones. Rejected: too rigid; real work doesn't follow predicted paths.

2. **Hybrid: permissive with warnings:** Warn on unusual transitions but allow them. Rejected: middle ground loses clarity without gaining sufficient flexibility.

3. **No constraints on status:** Any status can transition to any other. Rejected: loses all workflow structure and makes reporting unreliable.

## Related

- Source: Workflow ETD specification in SE module
- Implemented in: Status transition rules (advisory, not mandatory)
- Related: ADR-007 (Artifact tiers; narrative applies at Guidance tier)
- Enforced by: Workflow analysis and audit trail in `catalyst trace`
