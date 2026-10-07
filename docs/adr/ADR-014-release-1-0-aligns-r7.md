# ADR-014: Release 1.0 aligns R7 (R3.9: multi-user server, R5: UI parity)

**Date:** 2026-10-07  
**Status:** Pending  
**Author:** Catalyst Team  
**Affected scope:** infra

## Context

The catalyst framework has a multi-phase roadmap (R0 through R7) with specific deliverables at each phase. The question arose: when should the framework be released as version 1.0?

The planning document (what-is-going-on/06-roadmap-streamline.md, §R7) indicates that Release 1.0 should align with the completion of R7, which includes:
- **R3.9:** Multi-user server support (the server protocol for shared deployments)
- **R5:** UI parity (web SPA and desktop UI achieve feature parity with CLI)

These represent the maturity checkpoints needed for a production 1.0 release.

## Decision

**Release 1.0 of catalyst aligns with R7 completion.** This means:
- R0–R6 are pre-1.0 phases (version numbers 0.40–0.50 range)
- R7 completion triggers the 1.0 release (first production-ready release)
- 1.0 assumes:
  - R3.9 complete: multi-user server protocol functional
  - R5 complete: UI parity (SPA and desktop UIs match CLI capabilities)
  - R6 complete: Studio brand and identity established
  - R7 complete: second process module shipped, beta trial complete

The release timing is tied to feature completeness, not a calendar date. R7 deliverables determine 1.0 readiness.

## Consequences

- **Positive:**
  - Clear release criterion (R7 completion)
  - Ensures 1.0 is truly production-ready (not premature)
  - Aligns multi-user and UI capabilities for a complete offering
  - Beta trial in R7 validates 1.0 quality
  - Users know what to expect from 1.0

- **Negative:**
  - R7 is still 6+ weeks out (at current planning); 1.0 is not immediate
  - Pre-1.0 versions (0.40–0.50) may confuse users expecting 1.0-level quality
  - Long roadmap to 1.0 may reduce early adopter adoption
  - Features developed in R0–R6 will not carry 1.0 branding until R7

- **Trade-offs:**
  - Traded quick-to-market for ensuring 1.0 is production-ready

## Alternatives Considered

1. **Release 1.0 at R3:** After store abstraction and multi-user server. Rejected: premature; UI is not ready, and second module/beta validation missing.

2. **Release 1.0 at R5:** After UI parity achieved. Rejected: server protocol not yet mature; storage model not finalized.

3. **Release 1.0 at R2:** After code replaces prose. Rejected: far too early; core infrastructure not in place.

## Related

- Source: `what-is-going-on/06-roadmap-streamline.md` (R7 definition, §R7)
- Roadmap phases: R0 (stop bleeding) → R1 (measure) → R2 (code replaces prose) → R3 (one truth) → R4 (slim) → R5 (engine as service) → R6 (studio) → R7 (prove & release 1.0)
- Related: ADR-013 (version ceiling), ADR-015 (three UIs), ADR-016 (VS Code thin client)
- Validation: Beta trial in R7 confirms 1.0 readiness
