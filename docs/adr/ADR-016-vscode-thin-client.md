# ADR-016: VS Code thin client (R6) uses server protocol (R3.9)

**Date:** 2026-10-07  
**Status:** Pending  
**Author:** Catalyst Team  
**Affected scope:** infra

## Context

The catalyst team is considering a VS Code extension as a potential interface for accessing catalyst within the editor. However, the design question is: should this be a thick client (running the full catalyst CLI) or a thin client (talking to a remote catalyst server)?

The planning document (what-is-going-on/06-roadmap-streamline.md, §R5–R6) and the multi-user server proposal (what-is-going-on/08-criterion-proposals.md) suggest that a thin client architecture should be used, where the VS Code extension communicates with a catalyst server rather than running catalyst embedded.

## Decision

**The VS Code thin client (R6) communicates with a catalyst server using the server protocol developed in R3.9.**

Architecture:
- **VS Code extension (thin client):** Lightweight UI component; communicates with a remote catalyst server
- **Catalyst server:** Runs separately (locally or remotely); implements the server protocol from R3.9
- **Server protocol:** RPC-based (likely JSON-RPC or gRPC) for commands, artifact access, and subscription to changes
- **Authentication:** Uses the session/deployment authentication model (who is calling the server?)
- **Offline support:** Limited when the server is unreachable (graceful degradation)

Benefits of thin client:
- Reduces VS Code extension complexity (network client, not full app)
- Allows the same server to be used by CLI, SPA, desktop, and VS Code
- Simplifies version management (server version drives feature set)
- Enables shared access (multiple clients using the same deployment)

## Consequences

- **Positive:**
  - Code reuse: all UIs use the same server protocol
  - Simplified extension development (thin client is easier than embedding catalyst)
  - Natural multi-user support (server can handle multiple clients)
  - Decouples VS Code from catalyst versioning (upgrade server independently from extension)
  - VS Code extension becomes a lightweight consumption layer

- **Negative:**
  - Requires R3.9 multi-user server protocol (dependencies on earlier phases)
  - Network latency between editor and server may feel sluggish
  - Server must be running for VS Code integration to work
  - More complex deployment (server + extension, not just extension)
  - Debugging/troubleshooting requires understanding client-server interaction

- **Trade-offs:**
  - Traded self-contained extension for architectural consistency (all UIs are thin clients)

## Alternatives Considered

1. **Thick client:** Embed full catalyst CLI in the VS Code extension. Rejected: duplicates code, makes extension large, difficult to keep in sync with CLI changes.

2. **Hybrid client:** Extension can run CLI or talk to server (both modes). Rejected: too complex; maintains two code paths.

3. **Native IDE integration:** Implement catalyst directly as IDE language server. Rejected: creates tight coupling; server protocol approach is cleaner.

## Related

- Source: `what-is-going-on/06-roadmap-streamline.md` (R5–R6: UI development) and 08-criterion-proposals.md (server protocol design)
- Depends on: ADR-014 (Release 1.0 roadmap), R3.9 multi-user server (server protocol implementation)
- Related: ADR-015 (Three UIs — CLI, SPA, desktop), ADR-011 (Store abstraction)
- Scheduled: R5 (server protocol) → R6 (VS Code thin client)
