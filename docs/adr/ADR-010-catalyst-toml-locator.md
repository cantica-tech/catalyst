# ADR-010: catalyst.toml locator (R3) replaces symlink + pointer + submodule

**Date:** 2026-10-07  
**Status:** Accepted (owner, 2026-10-08: the file lives at `.catalyst/catalyst.toml`)  
**Author:** Catalyst Team  
**Affected scope:** kernel

## Context

The current deployment model uses three mechanisms to locate and manage the working copy:
1. `.criterion` symlink (points to agent-owned directory or git submodule)
2. `.catalyst` pointer file (JSON, contains metadata)
3. `.gitmodules` submodule entries (for shared deployments)

This works but is complex:
- Three different technologies to understand
- Hard to version or store in version control
- Not immediately discoverable (reading `.catalyst` requires parsing JSON)
- Symlinks are platform-specific (don't work on all Windows configurations)

The proposal (what-is-going-on/08-criterion-proposals.md) suggests a clearer model using a single `catalyst.toml` file that serves as the locator for the entire deployment.

## Decision

**In R3, introduce `catalyst.toml` as the canonical locator file that replaces the symlink + pointer + submodule model.**

The `catalyst.toml` file:
- Resides at `.catalyst/catalyst.toml` in the product repository (tracked in git); the `.catalyst/` folder keeps the project root clean and gives later files a home
- Contains all deployment metadata (kernel version, module version, working-copy path, deployment mode, etc.)
- Is human-readable (TOML format)
- Serves as the single source of truth for the deployment configuration
- Eliminates the need for symlinks on platforms where they are problematic
- Works equally well for local and shared (submodule-based) deployments

Example structure:
```toml
[deployment]
kernel_version = "0.46.0"
module_id = "SE"
module_version = "2.4.0"
mode = "local"  # or "shared"
working_copy = ".criterion"  # relative path or "submodule"
```

## Consequences

- **Positive:**
  - Single file replaces three technologies
  - Human-readable and version-controllable
  - Platform-agnostic (no symlink issues)
  - Enables clearer semantics (deployment state is explicit)
  - Easier to version and migrate (one thing to update)
  - Supports clear validation and documentation

- **Negative:**
  - Requires migration of existing deployments (though LEGACY support eases this)
  - Tooling must be updated to read `catalyst.toml`
  - TOML parsing required (vs. simple symlink following)
  - Introduces a new file format to learn

- **Trade-offs:**
  - Traded distributed, implicit configuration for centralized, explicit configuration

## Alternatives Considered

1. **Enhance `.catalyst` JSON:** Use `.catalyst` for all metadata, remove symlink. Rejected: doesn't solve platform issues, and TOML is more human-friendly than JSON for config.

2. **Extend `.gitmodules`:** Use `.gitmodules` for all metadata. Rejected: `.gitmodules` is not the right place for general deployment config; creates git coupling.

3. **Multiple separate files:** Keep symlink, pointer, and `.gitmodules` as separate layers. Rejected: remains complex; does not simplify the model.

## Related

- Source: `what-is-going-on/08-criterion-proposals.md` ("One truth" design)
- Related: ADR-009 (LEGACY deployments), ADR-011 (Store abstraction)
- Replaces: INV-6 (Working copy outside product tree) — will be updated in R3
- Scheduled: R3 phase (3-4 weeks after R2 complete)
