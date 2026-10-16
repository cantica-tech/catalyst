# ADR-022: Remove the plugin system from the kernel (R4.7)

**Date:** 2026-10-16  
**Status:** Accepted  
**Author:** Olivier Steck (owner: "reviewed recommendations: apply all", 2026-10-16)  
**Affected scope:** kernel

## Context

Decision B3 (2026-10-08) parked the plugin system "until a second real plugin exists": its invariants were marked
parked and the templates stopped naming it, but `framework/kernel/plugins/` (the catalog, the activation checklist,
the working-contract template, the `project-management` prototypes), the `catalyst-git` submodule, two check scripts
and a CI workflow stayed. No CLI verb reads any of it. Since then, modules took over what content-contributing
plugins were for: several modules per deployment (R4.9), each declaring its types as data (module format 3), and
agents are wired at user level (`catalyst agent install`). The feature register's R1.3 review left ten rows waiting
on this (K-55, K-56, PR-68, PR-69, PR-70, CMD-12, PL-02, PL-03, PL-09, PL-10).

## Decision

The plugin system leaves the kernel now:

1. `framework/kernel/plugins/` is removed, with the `catalyst-git` submodule, `scripts/check_plugins.py`,
   `scripts/check_plugin_contracts.py`, their tests, the `plugin-rules` workflow and its Taskfile tasks.
2. The plugin invariants (INV-10 to INV-13, INV-22) and meta-rules (§8 agile work items, §17 content-contributing
   plugins) are **retired in place**: their numbers stay, never reused (L7), and say so.
3. **`catalyst-git` stays an optional extension** in its own repository (`oliben67/catalyst-git`). Nothing in the
   kernel loads, activates or checks it.
4. Work items (epics, stories, tasks) are a module's types when a process needs them, not a plugin's.

## Consequences

- **Positive:** one way to add capability (a module); a smaller kernel and repository; no checks guarding files
  nothing reads.
- **Negative:** a deployment that copied a plugin catalog keeps it as an ordinary file that nothing reads.
- **Trade-offs:** `catalyst-git`'s continuous audit is no longer one command away; it is installed from its own
  repository when wanted.

## Alternatives Considered

1. **Keep it parked until a second plugin exists** (B3 as written): the files and checks keep costing attention for
   a capability nothing uses.
2. **Turn `catalyst-git` into a module:** it watches a repository rather than declaring types; a module is the
   wrong shape for it.

## Related

- ADR-017 (prose freeze: the invariant and meta-rule numbers stay); decision B3 in `10-questions-and-decisions`
- `docs/feature-register.md`, *Decided (owner, 2026-10-16)*
