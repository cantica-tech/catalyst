# ADR-012: Catalyst is the framework; kernel is the rule engine

**Date:** 2026-10-07  
**Status:** Pending (awaiting owner decision)  
**Author:** Catalyst Team  
**Affected scope:** infra

## Context

Early in development, terminology around the catalyst project was inconsistent:
- Was "catalyst" the entire system or just a component?
- What was the "framework" vs. the "kernel"?
- How should these terms be used in documentation, commands, and user communication?

Clarifying the terminology was essential for:
- Consistent documentation and user guidance
- Clear boundaries between kernel (rule engine) and modules (process implementations)
- Avoiding confusion about what users were installing or configuring

The BOOTSTRAP.md hard rule 3 establishes the canonical naming convention.

## Decision

**Catalyst is the framework; the kernel is the rule engine within catalyst.**

Precise definitions:
- **Catalyst** (or "catalyst framework"): The complete system, including the kernel rule engine, standard library, process modules, and supporting tools. This is the product name.
- **The kernel**: The module-independent part of catalyst (`framework/kernel/` in the repository), responsible for:
  - Rule engine and rule storage/validation
  - Artifact types, deployment metadata, journal management
  - Core CLI commands (independent of process modules)
  - Versioned separately; versioned by root `version.txt`
- **Process modules** (or just "modules"): Pluggable implementations of specific development processes (e.g., SE module for software engineering)
  - Each module is versioned separately in its own repository
  - Each module declares its `grounding_type` (how its artifacts link to kernel rules)

Usage examples:
- ✓ "Install catalyst" (the framework)
- ✓ "The kernel provides the rule system" (the rule engine)
- ✓ "The SE module implements software engineering" (a process)
- ✗ "Install the kernel" (imprecise; users install catalyst)
- ✗ "The framework core" (avoid; say "the kernel" instead)

## Consequences

- **Positive:**
  - Clear, consistent terminology across documentation
  - Users understand what they are installing (catalyst) and what it contains (kernel + modules)
  - Enables clear communication about kernel updates vs. module updates
  - Boundary between kernel and modules becomes explicit
  - Facilitates documentation and API clarity

- **Negative:**
  - Requires discipline to maintain consistency (easy to slip into old terminology)
  - May require updating existing documentation and examples
  - Users must learn the distinction between catalyst, kernel, and modules

- **Trade-offs:**
  - Traded casual terminology for precise, consistent naming

## Alternatives Considered

1. **"Catalyst kernel":** The system is the "catalyst kernel", modules are plugins. Rejected: "catalyst kernel" is awkward; "kernel" alone is clearer.

2. **"Framework" for everything:** Use "framework" without distinguishing kernel/modules. Rejected: loses clarity about the structure; modules are not really part of the framework.

3. **No distinction:** Call everything "catalyst". Rejected: users need to understand that the kernel and modules are separate pieces with separate versioning.

## Related

- Source: BOOTSTRAP.md hard rule 3 (naming convention)
- Enforced: Documentation style guide, CLI output, command names
- Related: ADR-006 (SE module canonical status), INV-3 (Name it "catalyst")
