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
| `software-engineering` | `git@github.com:cantica-tech/catalyst-software-engineering.git` | `main` |
| `knowledge-base` | `git@github.com:cantica-tech/catalyst-knowledge-base.git` | `main` |

Every module installs alone or beside any other (INV-30). `knowledge-base`
(KBM) builds knowledge bases off any project: it is a criterion's only module,
or it is installed beside the module that already governs the project
(`catalyst module install`), in either order.
