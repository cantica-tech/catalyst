# ADR-015: Catalyst has three UIs: CLI (kernel), SPA (R6), desktop (R6)

**Date:** 2026-10-07  
**Status:** Pending (awaiting owner decision)  
**Author:** Catalyst Team  
**Affected scope:** infra

## Context

As the catalyst framework evolved, multiple interfaces for interacting with the system were proposed:
1. **CLI:** Command-line interface (exists; the primary user interface today)
2. **SPA:** Single-page application (web-based interface; planned for R6)
3. **Desktop:** Electron or native desktop application (planned for R6)
4. **VS Code:** Extension-based interface (planned for R6 or R5)

The question arose: which interfaces should be officially supported, and when? The planning document (what-is-going-on/06-roadmap-streamline.md, §R6) clarifies that three primary UIs are planned: CLI, SPA, and desktop.

## Decision

**Catalyst will have three official user interfaces:**

1. **CLI (kernel-level):** Command-line interface using the `catalyst` command. Available now; the primary interface through R6. Remains the reference implementation for all features.

2. **SPA (Web UI, R6):** Single-page application (likely React or Vue) running in a web browser. Provides graphical access to catalyst capabilities. Reaches feature parity with CLI by R6 end.

3. **Desktop (R6):** Native or Electron-based desktop application for macOS, Windows, and Linux. Provides offline-capable, platform-native interface. Reaches feature parity with CLI by R6 end.

Other interfaces (VS Code extension, IDE plugins, etc.) are future or optional; not part of the three official UIs.

## Consequences

- **Positive:**
  - Clear scope for UI development (three distinct targets)
  - CLI remains reference implementation, avoiding specification drift
  - Multiple interfaces serve different user preferences (terminal, browser, desktop)
  - Feature parity ensures consistent behavior across UIs
  - Desktop and SPA reduce terminal-phobia barrier to adoption

- **Negative:**
  - Significant development effort to build and maintain three UIs
  - Feature parity requirement means changes must ship across all three simultaneously
  - Testing burden multiplies (each feature tested in three UIs)
  - Resource allocation becomes complex (UI team vs. core team)
  - Desktop-specific issues (installer, auto-update, etc.) add complexity

- **Trade-offs:**
  - Traded single-interface simplicity for multi-modal user experience

## Alternatives Considered

1. **CLI only:** Stick with command-line interface exclusively. Rejected: limits adoption; some users prefer graphical interfaces.

2. **SPA only (no desktop):** Web interface but no native desktop. Rejected: desktop mode provides value for offline work and platform-native experience.

3. **Unlimited interfaces:** Support CLI, SPA, desktop, VS Code, IDE plugins, etc. Rejected: too much scope; three interfaces is ambitious.

## Related

- Source: `what-is-going-on/06-roadmap-streamline.md` (R6 definition, "Studio & brand")
- Related: ADR-014 (Release 1.0 aligns R7), ADR-016 (VS Code thin client protocol)
- Parity requirement: All three UIs achieve feature parity by R6 end
- Scheduled: SPA and Desktop development in R6 phase
