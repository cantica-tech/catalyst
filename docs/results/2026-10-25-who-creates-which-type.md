# Results — 2026-10-25: who may create which type (kernel 0.113.0)

| What                                                                                         | Where                                                     |
| -------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Kernel [0.113.0](https://github.com/cantica-tech/catalyst/releases/tag/0.113.0) (REQ-000094) | `cantica-tech/catalyst` (PRs 333, 334); distribution repo |

- **Design 31, phase 2** (`fw-STRUCTURE-000020`): `catalyst new` checks who may create which type. An admin (a `cmd:*`
  grant, or the `Admin` role) creates any type. Anyone else creates only a module's type the module leaves open to
  contributors (`contributors_create` in `module.yaml`, true by default), with a `cmd:create` (or an alias of it) or
  `create:<TYPE>` grant from catalyst-users; the kernel's own types are an admin's. `role_check = "warn"` warns.
- The edit tests' signer is now a verified Admin: since design 29 a corpus user carries no grants, so a raw one is
  no signer.
- **Lint**: PR 333's first run would have failed on an unformatted file; before every push, catalyst now runs the
  standards' own task, the one CI runs (`task --taskfile ../standards/Taskfile.standards.yml --dir .
standards:lint`).
- Checks: the full suite (828); every job of both pull requests passed before merging.

## What's left

- **Design 31's next phases**: a linked entity's edits and retirements through its workflow (tag, type, criterion);
  tags and tag workflows.
- **Design 30's eight open questions**, first among them what makes a person a member of a project.
