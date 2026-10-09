# Templates

This folder contains the reusable document templates that seed the deployed catalyst framework.

## What lives here

- **Development-artifact templates are not here.** The active process
  module ships the templates for its own entity types (its `templates/`,
  referenced from its `module.yaml`; `MODULE-SPECIFICATION.md` §2–§3) and
  they are deployed alongside the kernel's. This folder holds only the
  kernel's own templates, such as [`meta-tag.template.md`](meta-tag.template.md)
  — the lightweight annotation governed by `CODE-OF-CONDUCT.md` for every
  artifact type.
- **Work-item templates are not here anymore.** They moved to
  `plugins/_prototyping/project-management/agile/templates/` — `work-items/`
  is plugin-territory, not core (`Rules-of-Rules.md` §8, INV-22); see
  that directory's own `README.md`. `workflow.template.md` is the one
  exception — it moved back here, see below.
- Rule and domain scaffolding templates used when a project is instantiated
  — `domain.template.md` deploys nested under `rules/domains/`, not as a
  top-level sibling (domains exist only to group rules).
- [`reconciliation.template.md`](reconciliation.template.md) — a
  top-level, non-rule-linked type for `RECON-NNNNNN` cases: two
  diverging versions of some other entity — such as a conflict that
  stopped `/criterion push` — awaiting a human decision. Never a
  unit of work; see `Rules-of-Rules.md` §16.
- [`workflow.template.md`](workflow.template.md) — a top-level,
  non-rule-linked type for `WORKFLOW-NNNNNN` process-definition
  documents: a repeatable multi-step procedure, never itself work. Core
  (unlike the rest of the work-items schema), so other core entities can
  reference one without requiring any plugin — `RECON-` reconciliation
  is the first; see `Rules-of-Rules.md` §19, `INVARIANTS.md` INV-24.
- [`templates-catalog.template.md`](templates-catalog.template.md) — the
  generic catalog every artifact type's `templates/templates-<type>.md`
  is seeded from (`INVARIANTS.md` INV-20): Version | File | Timestamp |
  Notes, one row per template version. This is where the hard rule's
  "timestamped" requirement is actually satisfied — the template files
  themselves carry no date, this table does.
- [`roles.template.json`](roles.template.json) — copy to
  `IAM/roles/roles.json` on first deploy (`INVARIANTS.md` INV-16), filled
  in with its default agile-role mapping (phrased generically; the active
  module's own commands can be listed via `/role-modify`). JSON, not markdown, because it's
  managed by `/role-add`/`/role-modify` rather than hand-edited.
- [`users.template.json`](users.template.json) — copy to
  `IAM/users/users.json` on first deploy (`INVARIANTS.md` INV-16), empty
  array. Managed only by
  `/user-add`/`/user-remove`/`/user-modify`/`/user-assign-role`/`/user-list`
  — see `Rules-of-Rules.md` §11. **Hard requirement:** deployment isn't
  complete until `/user-add` has registered at least one active user.
  `IAM/users/` and `IAM/roles/` each get the same `templates/` treatment
  as every other artifact type (`INVARIANTS.md` INV-20).
- [`journal.template.jsonl`](journal.template.jsonl) — an empty file,
  copied to `development/journal.jsonl` on first deploy (`INVARIANTS.md`
  INV-17). Append-only, one JSON object per line, transaction-log-grade
  (exact before/after `git hash-object -w` content pointers per touched
  file, not just prose) — see `Rules-of-Rules.md` §12 for the full schema
  and the `/journal-restore` point-in-time reconstruction mechanism.
- [`catalyst-pointer.template.json`](catalyst-pointer.template.json) —
  copy to `<app-name>.catalyst` **at the target project's own root**
  (`INVARIANTS.md` INV-6), the one exception to "everything else deploys
  under `.criterion/`": this file is the only catalyst artifact the
  target project's own repo ever tracks. It holds no path: the real
  working copy lives in agent-owned space, computed per machine by the
  running agent and reached through the gitignored `.criterion` symlink
  at the project root — or is the in-project `.criterion/` directory
  (gitignored) when the agent has no owned space (INV-6). Pre-0.37.0
  pointers may still carry `agent-source`; tools honor it until
  migrated. Managed by `/project create`/`remove`/`export`/`import` — see
  `Rules-of-Rules.md` §14. `catalyst criterion create` sets `repoed`,
  `catalyst_repo_url` and `criterion_branch` (the shared branch, default
  `criterion`) when the deployment becomes shared (§13); `catalyst_repo`
  and `created_by` are informational.

## How to use this folder

Copy the appropriate template into the matching deployed folder and rename it to the project-specific filename convention used by the framework.

## Related docs

- [../README.md](../README.md)
- [../INSTANTIATION-GUIDE.md](../INSTANTIATION-GUIDE.md)
