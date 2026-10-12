# ADR-019: A module's own meta-rule and invariant namespace

**Date:** 2026-10-11  
**Status:** Accepted  
**Author:** Olivier Steck (owner)  
**Affected scope:** kernel, SE module

## Context

Before modules could declare anything of their own, the kernel lent the active module four meta-rule numbers:
`rr-META-009`, `-010`, `-021` and `-022` stayed in the kernel handbook as "owned by the active module"
placeholders, and the software-engineering module wrote its meta-rules under those numbers. A second module could not
pick numbers without colliding with the kernel's next meta-rule or with the first module (note `02` §4.4, G-05).
Module v3 (`what-is-going-on/20-module-v3-design.md`, step M4) gives a module its own namespace; the owner decided it
on 2026-10-11 (decision 4).

## Decision

Lift the prose freeze (ADR-017) for this change only:

- **The kernel handbook drops its four placeholders.** The numbers 9, 10, 21 and 22 are retired from the kernel's
  sequence and never reused; the handbook says so in its opening.
- **A module declares `namespace:`** in `module.yaml` (`SE` for software engineering) and writes its meta-rules as
  `rr-<NS>-NNN` and its invariants as `INV-<NS>-n`. Composition widens and signs them like the kernel's; `catalyst id
  next-rule` takes the namespace as a meta domain; `validate` treats them as self-governing like `rr-META-`.
- **Old IDs keep resolving.** A module lists `aliases:` (old ID → new ID), and `catalyst why <old>` explains the new
  one.

The snapshot `docs/FROZEN-SURFACE.json` is rewritten for these four meta-rules; the freeze otherwise stands.

## Consequences

- **Positive:** a second module can be written without touching the kernel's numbers; the kernel handbook no longer
  carries entries for content it does not have.
- **Negative:** deployed text and journal entries that cite `rr-META-009` and the others keep doing so; they resolve
  through the aliases, not by their own heading.
- **Trade-offs:** the kernel's own invariant placeholders in `INVARIANTS.md` are untouched by this ADR.

## Alternatives Considered

1. **Keep borrowing kernel numbers:** no change for the software-engineering module, but every new module would
   collide; rejected by the owner.

## Related

- ADR-017 (prose feature freeze), ADR-018 (the handbook)
- `what-is-going-on/20-module-v3-design.md`; catalyst `REQ-000025-yCNjAMXO`
