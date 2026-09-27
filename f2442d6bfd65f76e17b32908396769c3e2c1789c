# Contributing to catalyst

Thanks for your interest. catalyst is pre-1.0 and changes quickly; please open
an issue to discuss anything larger than a fix before sending a pull request.

## Current focus: beta readiness (feature freeze)

catalyst is working towards a public beta. Until the "rebuild criterion on
git" phase of that roadmap lands, the kernel takes **no new invariants
(`INV-`), meta-rules (`rr-META-`) or entity types**. Changes that make
existing behaviour executable, verifiable or simpler are welcome; changes
that add more rules for an agent to follow are not, for now. A proposal
that seems to need an exception should start as an issue.

## Prerequisites

- git
- Python 3.11+ with `pip install -r requirements-dev.txt` (pytest)
- [go-task](https://taskfile.dev) 3.x (`task`)
- A coding agent to exercise the framework end to end (Claude Code is the
  only one tested so far)

## Branches

- `development` — where work lands; open pull requests against it.
- `main` — integrated from `development` for each version.
- `release` — what has been tagged and packaged.

## Before you open a pull request

```
task check:all   # the same checks CI runs
task test        # pytest
```

## How kernel changes are versioned

The kernel (`framework/kernel/`) is versioned by the root `version.txt`. A
change that alters what gets deployed into a project also needs:

1. a bump in `version.txt`;
2. a migration under `framework/kernel/migrations/<version>/`, plus a row in
   `framework/kernel/migrations/migrations.md` and an entry in
   `framework/kernel/SYNCHRONIZE.md`;
3. a `CHANGELOG.md` entry.

Two hard rules for kernel sources: the kernel names no process module or
module entity (`INVARIANTS.md` INV-30, checked by
`scripts/check_kernel_purity.py`), and it references no downstream product.
Process modules live in their own repositories
(`framework/modules/catalog.md`).

## License

By contributing, you agree that your contributions are licensed under the
Apache License 2.0 (see `LICENSE`).
