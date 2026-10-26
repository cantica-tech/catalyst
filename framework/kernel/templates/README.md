# Templates

This folder contains the reusable document templates that seed the deployed catalyst framework.

## What lives here

- **Development-artifact templates are not here.** The active process
  module ships the templates for its own entity types (its `templates/`,
  referenced from its `module.yaml`; `MODULE-SPECIFICATION.md` §2–§3) and
  they are deployed alongside the kernel's. This folder holds only the
  kernel's own templates, such as [`rule.template.md`](rule.template.md).
- **Work-item templates are not here.** Work items are a module's types
  when it declares them (ADR-022); the module ships their templates.
  `workflow.template.md` is a kernel type and stays here, see below.
- Rule and domain scaffolding templates used when a project is instantiated
  — `domain.template.md` deploys nested under `rules/domains/`, not as a
  top-level sibling (domains exist only to group rules).
- [`reconciliation.template.md`](reconciliation.template.md) — a
  top-level, non-rule-linked type for `RECON-NNNNNN` cases: two
  diverging versions of some other entity — such as a conflict that
  stopped a push (`/share push`) — awaiting a human decision. Never a
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
- [`roles.template.json`](roles.template.json) — deployed as
  `IAM/roles/templates/TEMPLATE-ROLES-v1.json`: the default roles (phrased
  generically), their names and ids, for display. Their `actions` and
  `reconciliation` are what `catalyst-users roles provision` writes into
  the provider once, as each role's `cmd:<command>` and `reconcile:<level>`
  grants; in the criterion they grant nothing (`INVARIANTS.md` INV-16).
- [`users.template.json`](users.template.json) and
  [`groups.template.json`](groups.template.json) — deployed as
  `IAM/users/templates/TEMPLATE-USERS-v1.json` and
  `IAM/groups/templates/TEMPLATE-GROUPS-v1.json`: how users and groups are
  shown. They hold no person and grant nothing: people and groups are
  catalyst-users' (`Rules-of-Rules.md` §11). `IAM/users/`, `IAM/roles/`
  and `IAM/groups/` each get the same `templates/` treatment as every other
  artifact type (`INVARIANTS.md` INV-20).
- `landing.<policy>.template.json` (`standard`, `open`, `reviewed`,
  `host`) — the kernel's landing policies (design 33): `catalyst landing
  init --policy <policy>` writes one as `IAM/landing.json`, then it is the
  project's own; without the file, `standard` applies.
- The project file, `catalyst.toml` — the only catalyst file a project
  tracks — has no template: `catalyst init` writes it (`FORMAT.md` §1,
  INV-6); `catalyst share create` adds the sharing fields.

## How to use this folder

Copy the appropriate template into the matching deployed folder and rename it to the project-specific filename convention used by the framework.

## Related docs

- [../README.md](../README.md)
- [../INSTANTIATION-GUIDE.md](../INSTANTIATION-GUIDE.md)
