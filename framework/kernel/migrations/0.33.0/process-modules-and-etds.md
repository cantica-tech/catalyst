# Migration 0.33.0: Process Modules & Entity Type Definitions (ETDs)

> Apply this migration when synchronizing a deployed framework whose
> `version.txt` is being advanced to `0.33.0` or later. See
> `SYNCHRONIZE.md` for the full synchronization procedure.

This migration introduces **Catalyst Process Modules** and **Entity Type
Definitions (ETDs)**, splitting framework core engine mechanics from
specific domain concepts.

## What changed

1. **Module Architecture (`MODULE-SPECIFICATION.md`):** Process workflows are
   now encapsulated into pluggable modules residing under
   `modules/<module-id>/`.
2. **Bundled Module:** The development-artifact entity types that existed
   at the time, their document templates, and their slash commands were
   packaged into one process module, bundled with the framework as the
   default.
3. **Project Pointer (`*.catalyst`):** Added an optional
   `"module": "<module-id>"` field to project pointers. If omitted, the
   engine fell back to the bundled module. (Kernel `0.36.0` removes that
   fallback: the pointer must name its module —
   `migrations/0.36.0/module-agnostic-kernel.md`.)

## Steps for deployed projects

1. **Copy Module Specifications:** Seed `.criterion/modules/<module-id>/`
   from the module that holds the deployment's existing entity types.
2. **Update Project Pointer:** Add `"module": "<module-id>"` to
   `<app-name>.catalyst`.
3. **Module migration:** Apply the active module's migration for this
   version, if any (`MODULE-SPECIFICATION.md` §6.6).
4. **Update Version File:** Update `.criterion/version.txt` to `0.33.0`.
