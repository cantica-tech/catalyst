# ADR-006: SE module as canonical process plugin (through R2)

**Date:** 2026-10-07  
**Status:** Pending (awaiting owner decision)  
**Author:** Catalyst Team  
**Affected scope:** SE module

## Context

The catalyst framework was designed to support multiple process modules (plugins that define how work is done). However, the initial rollout focused on a single reference implementation: the Software Engineering (SE) process module, which defines artifact types (bugs, requirements, tests, etc.) and workflows for typical software development.

The question arose: during the R0–R2 phase, should the SE module be treated as the canonical, primary process module? And if so, through which roadmap phase should this status continue?

The planning document (06-roadmap-streamline.md, R1.6 phase) indicates that feature freeze on prose should remain until R2 verbs exist, suggesting the SE module's status remains primary through that phase.

## Decision

**The SE module is designated as the canonical process module through R2.** This means:
- All example deployments use the SE module by default
- The SE module's artifact types and workflows are the reference implementation
- No other process modules are expected to ship during R0–R2
- Documentation and examples primarily feature SE-module workflows
- After R2, alternative modules may be added; the canonical status may transition to multi-module support

This status is revisited at R2 completion to determine whether SE remains primary or the framework shifts to a truly pluggable multi-module architecture.

## Consequences

- **Positive:**
  - Simplifies initial framework adoption (one clear process model)
  - Enables focused refinement of the SE module's design
  - Reduces scope of testing and documentation burden
  - Provides a stable baseline for roadmap planning (R1.6 feature freeze applies to the SE module)
  - Allows SE-specific optimizations to the framework

- **Negative:**
  - Delays multi-module support (other process models cannot ship yet)
  - Creates potential lock-in to SE-module assumptions
  - May require rework when moving to multi-module support in R3+
  - Plugins cannot define their own artifact types until R3

- **Trade-offs:**
  - Traded architectural flexibility for focused, deliverable progress through R2

## Alternatives Considered

1. **Multi-module support from R1:** Ship the framework with plugin support for alternative modules. Rejected: adds scope and delays R1; feature freeze becomes unachievable.

2. **No canonical module:** Framework is agnostic from day one. Rejected: users need a clear, working example; documentation becomes too abstract.

3. **SE module primary through R3:** Extend canonical status through the store-abstraction phase. Rejected: limits R2 deliverables and delays module diversification too long.

## Related

- Source: `what-is-going-on/06-roadmap-streamline.md` (R1.6 feature freeze decision)
- Roadmap: See ADR-014 (Release 1.0 roadmap alignment)
- Related: ADR-007 (Artifact tiers), ADR-008 (Workflow links as narrative)
