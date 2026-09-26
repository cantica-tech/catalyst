# Process module catalog

Production process modules, each in its own repository. A module is checked
out next to catalyst as `catalyst-<id>/` (see
[`../kernel/MODULE-SPECIFICATION.md`](../kernel/MODULE-SPECIFICATION.md)).
`scripts/check_kernel_purity.py` reads this table to learn which entity
types, folders and commands the kernel must never name (INV-30).

In-repo samples under `framework/modules/` (such as `sample-process`) are not
listed here.

| Id | Repository | Default branch |
|---|---|---|
| `software-engineering` | `git@github.com:oliben67/catalyst-software-engineering.git` | `main` |
