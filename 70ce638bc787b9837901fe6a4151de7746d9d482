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
workflows, meta-tags, users and roles, the journal, repoed sync, plugins and
entity definitions as a mechanism. A module owns a process domain: its
development-artifact entity types, their templates, definitions, commands,
meta-rules, invariants and migrations. The kernel never names a specific
module or any of its entities (`INVARIANTS.md` INV-30); it only speaks of
"the active module" and `<entity-type>`.

A deployment activates exactly one module, named by the `module` field of its
`<app-name>.catalyst` pointer.

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
├── commands/                   # Slash-command specs
│   └── <command>.md
├── rules-of-rules.module.md    # Module meta-rules (§6.1)
├── code-of-conduct.module.md   # Module document types and commands (§6.2)
├── INVARIANTS.module.md        # Module invariants (§6.4)
├── Taskfile.module.yml         # Module command tasks (§6.5)
├── migrations/                 # Module migrations + migrations.md index (§6.6)
└── skills/                     # Optional agent skills
    └── <skill-name>/SKILL.md
```

---

## 3. Module manifest (`module.yaml`)

### 3.1 Field reference

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | Yes | Unique module identifier, lowercase and hyphen-separated. |
| `name` | `string` | Yes | Human-readable name. |
| `version` | `string` | Yes | SemVer version. |
| `description` | `string` | Yes | One-line summary of the process domain. |
| `grounding_type` | `string` | Yes | The kernel entity the module's artifacts ground to (for example `rule`). |
| `entity_types` | `list[object]` | Yes | The module's ETD files (`id`, `schema`). |
| `commands` | `list[object]` | No | Slash commands the module adds (`name`, `description`, `argument_hint`, `spec_path`). |
| `templates` | `list[object]` | No | Document templates (`entity_type`, `template_path`). |
| `definitions` | `list[object]` | No | Entity definitions (`entity_type`, `path`). |
| `required_paths` | `list[object]` | No | Paths every deployment must carry (`path`, optional `invariant`, optional `seed` template); checked by `scripts/check_deployment.py`. |
| `contributions` | `object` | No | Content composed into a deployment (§6): `rules_of_rules`, `code_of_conduct`, `invariants`, `taskfile`, `migrations`. |
| `skills` | `list[object]` | No | Agent skills (`name`, `spec_path`). |

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
    spec_path: commands/create-item.md

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
  taskfile: Taskfile.module.yml
  migrations: migrations/
```

---

## 4. Entity Type Definition (ETD) schema (`<entity>.yaml`)

An ETD specifies one entity type's ID prefix, folder, grounding, fields,
back-references and workflow. The kernel's own entity types use the same
format and live in `framework/kernel/entities/`.

### 4.1 Field reference

| Field | Type | Required | Description |
|---|---|---|---|
| `id_prefix` | `string` | Yes | Uppercase ID prefix. |
| `name` | `string` | Yes | Singular name. |
| `plural_name` | `string` | Yes | Plural name. |
| `folder` | `string` | Yes | Folder relative to the working-copy root. |
| `naming` | `string` | No | `id-summary` (default: `<ID>-<short-summary>.md`, INV-7) or `free-form` (files keyed by a free name, exempt from INV-7). |
| `grounding` | `string` | Yes | `required` (links directly to the grounding type), `inherited` (through a parent entity), or `none`. |
| `grounding_field` | `string` | Conditional | Field holding the grounding link; required unless `grounding` is `none`. |
| `fields` | `list[object]` | Yes | Ordered field definitions. |
| `workflow` | `object` | Yes | Lifecycle states and transitions. |

### 4.2 Field definitions (`fields[]`)

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | Yes | Exact field name in the artifact file. |
| `kind` | `string` | Yes | `text`, `enum`, `ref`, `ref-list`, `date`, `user`, `user-list`. |
| `required` | `boolean` | Yes | Whether every instance must carry it. |
| `allowed_values` | `list[string]` | Conditional | Values for `enum`. |
| `target_type` | `string` | Conditional | Target entity prefix (or kernel type such as `rule`) for `ref` / `ref-list`. |
| `backref` | `string` | Optional | The field on the target that lists this entity back. |

### 4.3 Workflow (`workflow`)

| Field | Type | Required | Description |
|---|---|---|---|
| `initial` | `string` | Yes | Status on creation. |
| `states` | `list[string]` | Yes | All valid statuses. |
| `closed_states` | `list[string]` | Yes | Statuses meaning done. |
| `transitions` | `list[object]` | No | Allowed `from` → `to` moves. |

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
matching section of the deployed `CODE-OF-CONDUCT.md`. Every command bullet in
the module's §4 must match an entry in `module.yaml`'s `commands`; the deployed
§4 (kernel plus module) is the canonical command list that command files and
Taskfile tasks are checked against (`scripts/check_command_parity.py`).

### 6.3 Definitions (`definitions/`)

`definitions/<entity>/DEFINITION-<PREFIX>-vN.md`, deployed and frozen exactly
like the kernel's own definitions (INV-23).

### 6.4 Invariants (`INVARIANTS.module.md`)

Module invariants, read together with the kernel's `INVARIANTS.md`. An
invariant that moved from the kernel keeps its `INV-N` number; the kernel never
reuses it.

### 6.5 Taskfile tasks (`Taskfile.module.yml`)

A `tasks:` block with one thin dispatch task per module command, in the same
shape as the kernel's `templates/Taskfile.common.template.yml`. Its tasks are
appended to the deployed `Taskfile.common.yml`.

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
