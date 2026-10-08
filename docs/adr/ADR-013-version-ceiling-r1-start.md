# ADR-013: Version ceiling: kernel 0.46.0, SE module 2.4.0 (R1 start)

**Date:** 2026-10-07  
**Status:** Pending (awaiting owner decision)  
**Author:** Catalyst Team  
**Affected scope:** infra

## Context

At the start of the R1 phase (2026-10-07), the framework and SE module reached specific version milestones:
- **Kernel:** Version 0.46.0
- **SE module:** Version 2.4.0

These versions represent the baseline at which R1 starts. R1 is focused on measurement (token budgets), feature freeze on prose, and creating an inventory lock—not on adding new capabilities.

The `.catalyst` pointer files in deployed projects record these version numbers to ensure reproducibility and clear dependency tracking.

## Decision

**The version ceiling for R1 start is kernel 0.46.0 and SE module 2.4.0.**

This is a versioning decision that:
- Establishes the baseline for R1 work
- Ensures deployments can track which kernel and module versions they are running
- Pins versions at the start of each roadmap phase for clarity
- Allows future phases to increment versions as changes ship

The `.catalyst` pointer's `kernel_version` and module `version` fields record these values in every deployment.

## Consequences

- **Positive:**
  - Clear versioning baseline for the R1 phase
  - Deployments can declare their dependency versions explicitly
  - Enables reproducibility and debugging (know exactly which code is running)
  - Facilitates migration tracking (version → version transitions)
  - Creates clear boundaries between roadmap phases

- **Negative:**
  - Must be updated when releasing new versions (administrative overhead)
  - Misalignment between kernel and module versions can create confusion
  - Version ceiling must be communicated clearly to users

- **Trade-offs:**
  - Traded flexibility (any version combination) for explicitness (pinned baselines)

## Alternatives Considered

1. **Floating versions:** No version ceiling; deployments always use latest. Rejected: loses reproducibility and makes debugging impossible.

2. **Per-feature versioning:** Increment version for each feature shipped. Rejected: too granular; roadmap-phase versioning is clearer.

3. **Semantic versioning ceiling:** Use semver for all decisions (0.46.0 = minor update). Rejected: roadmap phases (R1, R2, etc.) are the primary organizational unit, not semver; versions follow phases.

## Related

- Source: `.catalyst` pointer file structure (tracks kernel_version)
- Used in: Deployment validation, migration planning, release notes
- Related: ADR-014 (Release 1.0 roadmap alignment)
- Tracked: `version.txt` (kernel), module repositories (SE module)
