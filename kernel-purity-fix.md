# Kernel purity fix for the failed CI job

## Problem

The job failed during `scripts/check_kernel_purity.py` with:

> `CHANGELOG.md:11: names entity prefix 'BUG'`

This means the scanner found a module-specific entity prefix in a file that should remain module-agnostic.

## Root cause

`check_kernel_purity.py` validates that the kernel and root docs do not mention specific module IDs, entity prefixes, command names, or template names. The `software-engineering` module defines the entity prefix `BUG`, and the changelog contains:

```md
A fix (`BUG-000003-yCNjAMXO`); no layout change, no migration.
```

That reference violates INV-30 because it names a concrete module entity prefix in the kernel-facing documentation.

## Recommended fix

Update the changelog entry to avoid naming the concrete entity prefix. Replace:

```md
A fix (`BUG-000003-yCNjAMXO`); no layout change, no migration.
```

with something like:

```md
A fix to rule shape recognition; no layout change, no migration.
```

or, if a more explicit reference is required:

```md
A fix in the software-engineering module; no layout change, no migration.
```

The key requirement is to avoid exposing a module-specific entity ID prefix such as `BUG-` in kernel/root documentation.

## Why this works

The kernel purity check is designed to keep the core framework generic. References like `BUG-000003...` are valid in module-owned content, but not in kernel-owned documentation or changelog entries that are scanned by the purity guard.

Removing the prefix reference restores compliance and allows the CI job to pass.
