# Catalyst Module & ETD Specification

**Version:** 2.0.0  
**Status:** Standard  
**Scope:** Catalyst kernel (`framework/kernel/`)

---

## 1. Overview

This document specifies how a **process module** plugs into the catalyst
kernel: its repository layout, its manifest, its Entity Type Definitions
(ETDs), and the content it contributes to a deployment.

The catalyst framework is the **kernel** plus its **process modules**. The
kernel is process-agnostic: it owns rules, domains, reconciliation cases,
workflows, users and roles, the journal, repoed sync and entity
definitions as a mechanism. A module owns a process domain: its
development-artifact entity types, their templates, definitions, commands,
meta-rules, invariants and migrations. The kernel never names a specific
module or any of its entities (`INVARIANTS.md` INV-30); it only speaks of
"the active module" and `<entity-type>`.

A deployment has one module or several. Its project file's `module` field
names the first; the criterion's `modules/modules.json` records each one, in
install order, and `catalyst module install` adds one beside the others. Two
modules of one deployment share no entity type, folder, definition,
namespace, meta-rule ID or command, give a tier id one meaning, and ground on
the same type (`CLI.md`, `catalyst module install`).

**Modules compose** (`INVARIANTS.md` INV-30). Every module is written to
work alone and beside any other module those rules admit, in either install
order: it never requires, names or assumes another module — its entity
types, ID prefixes, folders, commands or tiers. Its commands, documents and
checks hold whichever modules sit beside it. A module that serves any
project, such as one that builds knowledge bases, is added beside the module
that already governs that project.

---

## 2. Module repository layout

Each production module lives in its own git repository named
`catalyst-<module-id>`, checked out next to the catalyst repository, and is
published as a versioned release; it is never vendored into catalyst or added
as a submodule. Production modules are listed in catalyst's
`framework/modules/catalog.md`. In the catalyst repository,
`framework/modules/` (a sibling of `framework/kernel/`) holds only that catalog
and in-repo samples. In a project deployment, the active module is seeded into
`.criterion/modules/<module-id>/`.

```
catalyst-<module-id>/
├── module.yaml                 # Module manifest (§3)
├── version.txt                 # Module version
├── schemas/                    # One ETD per entity type (§4)
│   └── <entity>.yaml
├── templates/                  # Human-facing document templates
│   └── <entity>.template.md
├── definitions/                # Versioned prose definition per entity type (§6.3)
│   └── <entity>/DEFINITION-<PREFIX>-v1.md
├── rules-of-rules.module.md    # Module meta-rules (§6.1)
├── code-of-conduct.module.md   # Module document types and commands (§6.2)
├── INVARIANTS.module.md        # Module invariants (§6.4)
├── Taskfile.module.yml         # Not read since kernel 0.70.0 (§6.5)
├── migrations/                 # Module migrations + migrations.md index (§6.6)
└── skills/                     # Optional agent skills
    └── <skill-name>/SKILL.md
```

---

## 3. Module manifest (`module.yaml`)

### 3.1 Field reference

<!-- generated: manifest-fields (scripts/gen_docs.py; do not edit by hand) -->

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | Yes | Unique module identifier, lowercase and hyphen-separated. |
| `name` | `string` | Yes | Human-readable name. |
| `version` | `string` | Yes | SemVer version. |
| `description` | `string` | Yes | One-line summary of the process domain. |
| `grounding_type` | `string` | Yes | The kernel entity the module's artifacts ground to (for example `rule`). |
| `kernel_version` | `string` | No | The kernel versions the module works with, as a version specifier (for example `>=0.42.0`, `>=0.52,<1.0`). A release's manifest states it as `kernelVersion`; without it, the kernel that packages the release is assumed. Enforced: `catalyst init` and `catalyst sync` refuse a kernel outside it, and `catalyst check` reports a deployment outside it. |
| `format` | `integer` | No | `3` for a module that declares its types in this file (§3.3); absent, the v2 layout of §2. The kernel reads both until 1.0. |
| `namespace` | `string` | No | The module's own meta-rule and invariant namespace (`SE`): its meta-rules are `rr-<NS>-NNN`, its invariants `INV-<NS>-n` (ADR-019). Composition widens and signs them like `rr-META-`. |
| `aliases` | `map` | No | Old ID → the ID it is now (`rr-META-009: rr-SE-001`). An old ID, short or widened and signed, keeps resolving: `validate` and `view` take it as the rule it now is, and `catalyst why <old>` explains the new one. |
| `tiers` | `list[object]` | No | The module's ceremony tiers (`rr-META-006`), each `id`, `artifact` (the entity type the tier opens, or `none` when it needs no artifact, only its journal entry) and, for a tier with no artifact, `commit` (the commit-subject prefix that marks it, e.g. `chore:`). Every `--tier` and journal entry is checked against them, and `catalyst trace` accepts as ID-less only commits with a no-artifact tier's prefix. Without it: `chore` (no artifact, `chore:`), `fix` and `feature`. |
| `entities` | `map` | Conditional | Format 3: the module's types, by ID prefix, each declared in this file (§3.3): its name, folder, fields, states, guards, `due`, sections and definition. Required unless the module lists `entity_types`. |
| `entity_types` | `list[object]` | Conditional | The module's ETD files (`id`, `schema`). Format 2; required unless the module declares `entities` (format 3). |
| `commands` | `list[object]` | No | Slash commands the module adds (`name`, `description`, `argument_hint`); the command's text is its `code-of-conduct.module.md` §4 entry. `spec_path` is optional and unused. |
| `templates` | `list[object]` | No | Document templates (`entity_type`, `template_path`). |
| `definitions` | `list[object]` | No | Entity definitions (`entity_type`, `path`). |
| `required_paths` | `list[object]` | No | Paths every deployment must carry (`path`, optional `invariant`, optional `seed` template); checked by `scripts/check_deployment.py`. |
| `contributions` | `object` | No | Content composed into a deployment (§6): `rules_of_rules`, `code_of_conduct`, `invariants`, `taskfile`, `migrations`. |
| `skills` | `list[object]` | No | Agent skills (`name`, `spec_path`). |

<!-- end generated: manifest-fields -->

### 3.2 Manifest example

A fictional `example-process` module with one entity type:

```yaml
id: example-process
name: Example Process Module
version: 1.0.0
description: Illustrative module with a single rule-grounded entity type.
grounding_type: rule

entity_types:
  - id: ITEM
    schema: schemas/item.yaml

commands:
  - name: create-item
    description: Create a new item
    argument_hint: "[<rule-id>]"

templates:
  - entity_type: ITEM
    template_path: templates/item.template.md

definitions:
  - entity_type: ITEM
    path: definitions/item/DEFINITION-ITEM-v1.md

contributions:
  rules_of_rules: rules-of-rules.module.md
  code_of_conduct: code-of-conduct.module.md
  invariants: INVARIANTS.module.md
  migrations: migrations/
```

### 3.3 Format 3: one file

With `format: 3`, `module.yaml` declares its types under `entities:`, each
keyed by its prefix, instead of one ETD file per type, and catalyst
generates what the module would otherwise ship (module v3, M3):

- **The type**: `name`, `plural`, `folder`, `location`, `grounding` (with
  `grounding_field`, or `{ inherited_from: <field> }`), `fields` as a map
  (`kind`, `required`, `to` for a reference's target — a list for several —,
  `values` for an enum, `backref`, `required_when_closed`, `hint`), `states`,
  `status_hint`,
  `initial`, `closed`, `guards` (each `section_written`, `nonempty`,
  `children_closed` or `holds: <condition>`), `due` (`<date field>` or
  `<date field> + <n> days`: when an open entity is overdue), `storage: rows`
  for a type kept as table rows, `contributors_create` (default `true`;
  `false` keeps creating it to admins: design 31, `fw-STRUCTURE-000020`). It
  reads into the same type a §4 schema gives.
- **Its template**: the title, the field table `catalyst new` fills (a
  field's `hint`, or `status_hint` for `Status`, is what its cell tells the
  author; otherwise a placeholder for its kind), `Signed-off-by`, then each
  of `sections` (a heading, or `Heading: hint`, the hint a literal block
  when it runs to several paragraphs, lists or tables).
- **Its definition**: `definition:` composed into the frozen definition
  document (§6.3).
- **Its create command**: a part of the kernel's `/create` in the command
  catalogue, `/create <type> <title>` (`/create-<type>`), unless the module's
  `code-of-conduct.module.md` defines it (ADR-021).

A file the module still ships for a type — a template, a definition — wins
over the generated one. For a generated type, a shipped template named
after its folder (`<folder>.template.md`) is its index template, never its
item template. The YAML takes flow lists and maps
(`[Open, Done]`, `{ kind: ref, to: CASE }`) and folded or literal blocks
(`definition: >`).

---

## 4. Entity Type Definition (ETD) schema (`<entity>.yaml`)

An ETD specifies one entity type's ID prefix, folder, grounding, fields,
back-references and workflow. The kernel's own entity types use the same
format and live in `framework/kernel/entities/`.

### 4.1 Field reference

<!-- generated: etd-fields (scripts/gen_docs.py; do not edit by hand) -->

| Field | Type | Required | Description |
|---|---|---|---|
| `id_prefix` | `string` | Yes | Uppercase ID prefix. |
| `name` | `string` | Yes | Singular name. |
| `plural_name` | `string` | Yes | Plural name. |
| `folder` | `string` | Yes | The type's folder name. |
| `grounding` | `string` | Yes | `required` (links directly to the grounding type), `inherited` (through a parent entity), or `none`. |
| `grounding_field` | `string` | Conditional | Field holding the grounding link; required unless `grounding` is `none`. |
| `fields` | `list[object]` | Yes | Ordered field definitions. |
| `workflow` | `object` | Yes | Lifecycle states and transitions. |
| `naming` | `string` | No | `id-summary` (default: `<ID>-<short-summary>.md`, INV-7) or `free-form` (files keyed by a free name, exempt from INV-7). |
| `location` | `string` | No | Parent of `folder` inside the working copy, e.g. `development` for `development/<folder>/`. Default: the working-copy root. `catalyst init` creates the folder there and the CLI looks for it there first. |

<!-- end generated: etd-fields -->

### 4.2 Field definitions (`fields[]`)

<!-- generated: etd-field-definitions (scripts/gen_docs.py; do not edit by hand) -->

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | Yes | Exact field name in the artifact file. |
| `kind` | `string` | Yes | `text`, `enum`, `ref`, `ref-list`, `date`, `user`, `user-list`. |
| `required` | `boolean` | Yes | Whether every instance must carry it. |
| `allowed_values` | `list[string]` | Conditional | Values for `enum`. |
| `target_type` | `string` | Conditional | Target entity prefix (or kernel type such as `rule`) for `ref` / `ref-list`. |
| `backref` | `string` | No | The field on the target that lists this entity back. That field is **derived**: catalyst writes it (`catalyst new`, `catalyst link`), `catalyst check` reports it as the `derived` error when it disagrees with its sources, and `catalyst repair derived` rewrites it, journaled. Never edit it by hand. |
| `required_when_closed` | `boolean` | No | For a field that is not `required`: it must be non-empty once the artifact's `Status` is one of the workflow's `closed_states` (e.g. an item may not close without the sub-items recording its work). `catalyst validate` reports a violation as the `closed-incomplete` error (`CLI.md`). Default `false`. |
| `hint` | `string` | No | What the item template's cell tells the artifact's author, in place of the kind's placeholder (format 3; `catalyst new` writes an optional field it is not given as `*(none yet)*`). |

<!-- end generated: etd-field-definitions -->

### 4.3 Workflow (`workflow`)

<!-- generated: etd-workflow (scripts/gen_docs.py; do not edit by hand) -->

| Field | Type | Required | Description |
|---|---|---|---|
| `initial` | `string` | Yes | Status on creation. |
| `states` | `list[string]` | Yes | All valid statuses. |
| `closed_states` | `list[string]` | Yes | Statuses meaning done. |
| `guards` | `map` | No | State → the conditions entering it requires, each one of `children_closed: <field>` (every artifact the field cites is in a closed state), `nonempty: <field>`, `section_written: <heading>` (the section's text differs from the type's template's), `holds: <condition>` (a condition on its fields, e.g. `Classification at least Confidential`: `<Field> is\|is not\|in\|not in\|at least\|at most <value>` or `<Field> is set\|is empty`, ordered by the field's enum values, else as numbers or dates). `catalyst status set` refuses to enter a state while one fails (`--force` overrides it, journaled); `catalyst check` warns about an artifact already in a guarded state that fails one. |
| `transitions` | `list[object]` | No | Allowed `from` → `to` moves. |
| `due` | `string` | No | When an open entity of the type is due: a date field (`Due`), or a date field plus days (`Checked + 30 days`). Past it, `catalyst inbox` lists it as `overdue`, with the role a governing workflow escalates to, and `catalyst check` warns. |

<!-- end generated: etd-workflow -->

These tables are generated from `schemas/entity-type-definition.schema.json`
(and §3.1's from `schemas/module-manifest.schema.json`), the schemas the
modules are checked against: what they say is what is validated (R4.4).

### 4.4 ETD example (`schemas/item.yaml`)

```yaml
id_prefix: ITEM
name: Item
plural_name: Items
folder: items
grounding: required
grounding_field: Targets

fields:
  - name: ID
    kind: text
    required: true
  - name: Status
    kind: enum
    required: true
    allowed_values: [Open, Done]
  - name: Targets
    kind: ref-list
    required: true
    target_type: rule
  - name: Domain
    kind: ref
    required: true
    target_type: domain

workflow:
  initial: Open
  states: [Open, Done]
  closed_states: [Done]
  transitions:
    - from: Open
      to: Done
```

### 4.5 Fixed documents

A file whose name is all uppercase (for example a generated `SUMMARY.md`)
is a fixed document, not an entity instance, and is exempt from INV-7's
`<ID>-<short-summary>.md` naming check.

---

## 5. Grounding model

1. **Generalized grounding (INV-5).** Every module artifact must link to the
   module's `grounding_type`, directly or through a parent, as its ETD's
   `grounding` says. Kernel entities (rules, domains) are what modules ground
   to.
2. **No default module.** The kernel has no built-in module. A deployment's
   pointer must name its `module`; tools that find none run kernel-only checks.

---

## 6. Module contributions and composition

A module contributes content that is composed with the kernel's own when a
deployment is instantiated or synchronized (`INSTANTIATION-GUIDE.md`,
`SYNCHRONIZE.md`). Composition is additive: module content is appended under a
`### From module <module-id>` heading and never replaces kernel content.

### 6.1 Meta-rules (`rules-of-rules.module.md`)

Module meta-rule sections (`## N. \`rr-...\` ...`), appended to the deployed
`rules/Rules-of-Rules.md` after the kernel's sections. Rule IDs stay stable:
a section that moved from the kernel keeps its original ID. Module text that
extends a kernel meta-rule, rather than replacing it, goes in an
``## Addendum to §N (`rr-META-NNN`)`` section that names the kernel rule it
extends.

### 6.2 Document types and commands (`code-of-conduct.module.md`)

Two sections, `## 3. Standard document types` and
`## 4. Slash-command entry points`. Each is inserted at the end of the
matching section of the deployed `CODE-OF-CONDUCT.md`. The deployed §4
(kernel plus modules) is the one command registry: the `catalyst mcp`
server's prompts are read from it and the criterion's Taskfile is generated
from it (§6.5). A bullet's head names the command, then its aliases in
parentheses. A module adds a type to the kernel's `/create` as a part: a
bullet `/create <type> <title>` (`/create-<type>`), and procedures that name
`/create <type>` or the alias, so `catalyst spec create <type>` reads that
part alone (ADR-021). `module.yaml`'s `commands`, when present, must match
§4's names (`scripts/check_command_parity.py`).

### 6.3 Definitions (`definitions/`)

`definitions/<entity>/DEFINITION-<PREFIX>-vN.md`, deployed and frozen exactly
like the kernel's own definitions (INV-23).

### 6.4 Invariants (`INVARIANTS.module.md`)

Module invariants, read together with the kernel's `INVARIANTS.md`. An
invariant that moved from the kernel keeps its `INV-N` number; the kernel never
reuses it.

### 6.5 Taskfile tasks

The criterion's `Taskfile.common.yml` holds one thin dispatch task per
command of the deployed §4, kernel and modules alike, generated from it
(kernel 0.70.0): a module ships no task. A `Taskfile.module.yml` an older
module ships is not read. `catalyst task` runs the tasks from the project's
root; they never reach the project's own `Taskfile.yml`.

### 6.6 Migrations (`migrations/`)

One-time migrations for the module's entity shapes, indexed in
`migrations/migrations.md` with the same columns as the kernel index. The
`From`/`Target` columns name kernel versions. `/sync-framework` applies kernel
and module migrations together, in version order.

---

## 7. Kernel purity

The kernel, catalyst's own tooling (`scripts/`) and its root documents never
name a specific module, its entity ID prefixes, folders, commands, templates
or definitions (INV-30). `scripts/check_kernel_purity.py` derives that list
from the manifests of the modules in `framework/modules/catalog.md` and fails
on any match.
