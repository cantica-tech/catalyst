# ADR-011: Store abstraction with in-repo driver (R3 default)

**Date:** 2026-10-07  
**Status:** Pending (awaiting owner decision)  
**Author:** Catalyst Team  
**Affected scope:** kernel

## Context

Currently, all catalyst deployments store their working copy (`.criterion/`) as a directory in a specific location:
- Agent-owned space (local deployments)
- Git submodule (shared deployments)

This works for current use cases, but it creates coupling between the deployment and its storage backend. Future evolution requires:
- Supporting alternative storage backends (cloud storage, databases, etc.)
- Pluggable storage drivers
- Migration between storage backends
- Clear separation between logical deployment and physical storage

The proposal (what-is-going-on/08-criterion-proposals.md, "One truth" design) suggests introducing a store abstraction layer with pluggable drivers.

## Decision

**In R3, introduce a store abstraction with multiple driver implementations.** The initial release targets in-repo (filesystem) storage as the default, but the architecture supports alternative drivers.

**Store drivers:**
- `in-repo` (default for R3): Store working copy in filesystem (current behavior, improved with catalyst.toml)
- `git-submodule`: Store working copy as git submodule (current behavior, now explicit)
- Future drivers: cloud storage, database-backed, distributed, etc. (post-R3)

**The abstraction layer:**
- Sits between catalyst CLI and physical storage
- Defines a consistent API for store operations (read, write, list, delete)
- Allows stores to be created, switched, and migrated programmatically

## Consequences

- **Positive:**
  - Decouples deployment logic from storage details
  - Enables future storage backends without redesign
  - Clear migration path between storage backends
  - Better testability (mock store drivers)
  - Supports innovation in storage without breaking existing deployments
  - Facilitates distributed or cloud-based deployments

- **Negative:**
  - Adds abstraction layer (more code, more to understand)
  - R3 initial implementation uses only filesystem; other drivers deferred
  - Migration tooling needed to move between stores
  - Performance may vary by driver

- **Trade-offs:**
  - Traded immediate simplicity for long-term extensibility and flexibility

## Alternatives Considered

1. **No abstraction, stick with filesystem:** Keep deployment storage tied to filesystem. Rejected: limits future capabilities; fails to support evolution.

2. **Multiple storage backends from day one:** Support cloud, database, etc. in R3. Rejected: too much scope; filesystem is sufficient for R3; others can follow.

3. **Implicit driver selection:** Drivers auto-detected based on `.criterion` content. Rejected: reduces explicitness; `catalyst.toml` should declare the driver.

## Related

- Source: `what-is-going-on/08-criterion-proposals.md` ("One truth" design)
- Related: ADR-009 (LEGACY deployments), ADR-010 (catalyst.toml locator)
- Implements: INV-6 principle (working copy abstraction) at the driver level
- Scheduled: R3 phase (paired with catalyst.toml and store migration CLI)
