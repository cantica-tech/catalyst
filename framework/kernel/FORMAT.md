# The catalyst on-disk format

**Format version: `1.0-rc`.**

This document specifies the files a catalyst deployment consists of, as
the tools read and write them: the pointer the product repository tracks,
the working copy it points to, and every file in it that carries meaning.
It is agent-agnostic and module-agnostic. Examples use the fictional
module entity type `ITEM` (folder `items`, `MODULE-SPECIFICATION.md` §4.4),
a rule document with the prefix `br`, and the userid `Ab3xR9pQ`.

The procedures that *produce* these files are specified elsewhere
(`CLI.md`, `CODE-OF-CONDUCT.md`, `Rules-of-Rules.md`); this document says
only what a conforming file looks like, and what `catalyst check` and
`catalyst validate` enforce about it. "Structure" below means the
structural checks `catalyst check` runs; "validate" means the chain
checks `catalyst validate` runs (and `catalyst check` repeats). Their
codes are listed in `CLI.md`.

## Format versions

- **`1.0-rc`** is the release candidate. It is declared **`1.0`** only
  after the multi-user trial finds no format change is needed. Until
  then a format change is still possible, and ships with a migration
  like any other.
- **From `1.0` on**, a breaking change to anything specified here is a
  new major format version (`2.0`), always with a migration
  (`migrations/`). A change that existing readers ignore safely (a new
  optional field, a new optional file) is a minor version (`1.1`).
- A deployment declares its format in the pointer's `format` field. The
  CLI knows which formats it reads (`SUPPORTED_FORMATS`): `catalyst check`
  **warns** when the pointer declares none (a deployment from before
  `1.0-rc`; migration `0.41.0` adds it) and **fails** when it declares one
  the CLI does not read — update the vendored CLI, or migrate the
  deployment. A bare working copy (`--working-copy`) has no pointer and is
  not format-checked.
- **The declared format sets how strict the history checks are.** While
  it is a release candidate, [unrecorded changes](#7-the-journal) are
  warnings; from `1.0` they are errors, as are commits without a trace in
  the hook and `trace` — the same rollout. A pointer may opt in earlier
  with `"strict_journal": true`.

## General conventions

- Text files are UTF-8. Markdown tables are GitHub-flavoured pipe
  tables; a literal `|` inside a cell is written `\|`.
- Every recorded path is relative — to the project root or to the working
  copy, as each section says. No tracked file holds an absolute or
  machine-specific path (INV-1, INV-6).
- Dates are `YYYY-MM-DD`; timestamps are ISO 8601 in UTC,
  `YYYY-MM-DDTHH:MM:SSZ`.
- A **userid** is 8 characters from `[A-Za-z0-9]` with at least one
  uppercase letter, unique among registered users (INV-26).
- Readers ignore JSON fields they do not know; writers that rewrite a
  JSON file keep the fields they do not know.

## 1. The pointer: `<app-name>.catalyst`

One JSON object in a file named `<app-name>.catalyst` at the product
repository's root, committed. It is the only catalyst file the product
repository tracks, besides a shared deployment's `.gitmodules` entry and
gitlink. The directory holding it is the **project root**; if several
`*.catalyst` files exist, the CLI reads the first, in name order, that
parses as a JSON object.

```json
{
  "project_name": "shop",
  "format": "1.0-rc",
  "kernel_version": "0.41.0",
  "module": "example-process",
  "agent": "claude-code",
  "repoed": false,
  "catalyst_repo": null,
  "catalyst_repo_url": null,
  "created_by": "Ada Lovelace",
  "criterion_branch": null,
  "created": "2026-09-28",
  "updated": "2026-09-28",
  "journal_since": "4f1c2a9e0b7d3c5e8a6f9b2d1c0e7a3b5d8f6c4e"
}
```

| Field | Type | Meaning | Checked |
|---|---|---|---|
| `project_name` | string | The project's name; `<app-name>` in the file name. | — |
| `format` | string | The format version this deployment is written in. | `check`: warning if absent, error if not supported. |
| `kernel_version` | string | The kernel version the deployment is at. Pre-0.35.0 name: `framework_version`, still read. | Structure: must equal `.criterion/version.txt` (`version drift`). |
| `module` | string | The active module's id. Its ETDs are loaded from `.criterion/modules/<module>/` (then a sibling checkout `catalyst-<module>`). | A module that cannot be found leaves the checks kernel-only (the check's scope line says so). |
| `agent` | string | The id of the agent that last owned the working copy, e.g. `claude-code`; `unknown` if none was given. `catalyst task` resolves the agent command from it. | — |
| `repoed` | boolean | `true` once the deployment is shared (INV-18). | — |
| `catalyst_repo` | string or null | Informational name of the criterion repository. | — |
| `catalyst_repo_url` | string or null | The criterion repository's URL, when shared. | — |
| `created_by` | string or null | The installing user's name (`ACCESS-CONTROL.md`). Informational. | — |
| `criterion_branch` | string or null | The shared branch; `null` means `criterion`. | — |
| `created`, `updated` | date | When the pointer was written and last changed. | — |
| `journal_since` | string | The baseline for changes made outside catalyst: the product commit after which every commit's changes must be in the journal (`catalyst init` writes `HEAD`); `""` checks the whole history. | `check`: warning if absent (history not checked); unrecorded changes after it reported (§7). |
| `strict_journal` | boolean | Optional, default `false`: `true` makes unrecorded changes errors before format `1.0`. | — |

The pointer holds no path. `agent-source`, a path written by kernels
before 0.37.0, is still honoured when present and never written.

## 2. The working copy

A directory named `.criterion/`, reached as `<project root>/.criterion`:
a gitignored symlink into agent-owned space, a git submodule (shared), or
an in-project gitignored directory (fallback) — INV-6. It is its own git
repository. Paths in this section are relative to it.

### 2.1 Root files

| Path | Content | Checked |
|---|---|---|
| `version.txt` | The kernel version, one line. | Structure: must exist and equal the pointer's `kernel_version`. |
| `CODE-OF-CONDUCT.md` | The composed rules of development (`MODULE-SPECIFICATION.md` §6). | — (its §4 is what `catalyst spec` reads) |
| `ACCESS-CONTROL.md` | Per-role rights, verbatim from the kernel. | — |
| `DEPLOYMENT.md` | Project, kernel, module and version, installer, sharing — a Markdown bullet list, informational. | — |
| `README.md` | The deployment's landing page. | — |
| `Taskfile.common.yml` | The composed common tasks. | — |
| `composition.json` | The parameters the governing documents were composed with (§2.3). | — |
| `bin/catalyst.pyz` | The vendored CLI. | — |
| `ANALYSIS-PLAYBOOK.md` | The analysis process's phases, prompts and findings format, verbatim from the kernel (`/run-analysis`). | — |
| `definitions/<type>.md` | One frozen definition per kernel and module entity type, plus `definitions/README.md` (INV-23). | Structure: one per type. |
| `modules/<module-id>/` | The whole active module tree, as released. | — |
| `.gitattributes` | Shared deployments: the union-merge block (§8). | — |
| `.github/workflows/catalyst.yml` | Shared deployments: the criterion repository's CI (`CLI.md`). | — |
| `.frozen` | Optional: items `/sync-framework` leaves alone (§9). | — |
| `.ledger/` | The agent's task ledgers; not part of the format. | — |

### 2.2 Entity folders

Every entity type — the kernel's (`rules/`, `rules/domains/`,
`reconciliations/`, `workflows/`, `analyses/`, `development/meta-tags/`,
`IAM/users/`, `IAM/roles/`) and each of the active module's — has one
folder of this shape (INV-20):

```
<folder>/
  README.md                    what the folder holds
  <folder>.md                  the index (§4); rules/ has rules.md, domains/ has domains.md
  templates/
    README.md
    templates-<type>.md        catalog: | Version | File | Timestamp | Notes |
    TEMPLATE-<TYPE>-v1.md      one file per version, never edited once a newer one exists
  <instances>
```

A module type's folder sits at `<location>/<folder>/` when its ETD
declares `location`, else at the working-copy root. The CLI looks there
first, then at the root, then one level down in any non-hidden
directory.

Structure checks: every module folder present has its `<folder>.md`;
`workflows/workflows.md` exists; every path the module's manifest lists
under `required_paths` exists; every `.md` file in an entity folder,
other than a fixed name (an index, `README.md`, an all-uppercase name, a
template or a templates catalog), is named `<id>-<short-summary>.md` and
not a bare ID (INV-7) — except in folders of `naming: free-form` types.

### 2.3 `composition.json`

Written by `catalyst init`; read by `catalyst recompose` so a later sync
composes the documents with the same parameters.

| Field | Type | Meaning |
|---|---|---|
| `module` | string | The module the documents were composed with. |
| `userid` | string | The userid the `rr-META-` meta-rule IDs are signed with. |
| `rule_docs` | list of strings | The rule documents, e.g. `["business-rules.md"]`. |
| `test_locations` | string | What fills `{{TEST_LOCATIONS}}` in `Rules-of-Rules.md` §2. |
| `rules_dir` | string | The rules directory, `rules`. |

Absent (deployments installed before `catalyst init`), `recompose` reads
the parameters back from `rules/Rules-of-Rules.md`.

## 3. Entity files

A per-file entity type (ETD `naming: id-summary`, the default) stores one
Markdown file per instance, **directly in its folder** (the 1.0-rc CLI
does not read instance files in subfolders), named:

```
<PREFIX>-<NNNNNN>-<short-summary>.md        ITEM-000012-login-form-validation.md
```

The name may also carry the userid after the number
(`ITEM-000012-Ab3xR9pQ-login-form-validation.md`). Only files matching
`<PREFIX>-` + six digits + `-` + anything + `.md` are read as instances.

```markdown
# `ITEM-000012-Ab3xR9pQ` — Login form validation

| Field | Value |
|---|---|
| **ID** | `ITEM-000012-Ab3xR9pQ` |
| **Name** | `login-form-validation` |
| **Status** | Open |
| **Targets** | `br-AUTH-000003-Ab3xR9pQ`, `br-AUTH-000004-Ab3xR9pQ` |
| **Domain** | `AUTH` |
| **Signed-off-by** | Ada Lovelace |

## Description
...
```

- **Title.** The first H1; its title is the text after the first `—`,
  or the whole heading if it has none.
- **Fields.** Every table row whose first cell is bold, `| **Field** |
  value |`, is a field; its value is the second cell (a third cell is a
  note, not part of the value). The first row for a name wins. Field
  names match an ETD field loosely: case, punctuation and a trailing
  plural `s` or `(s)` are ignored (`Target(s)` = `Targets`).
- **The ID.** The `ID` field's first cited value (below); if there is no
  `ID` field, the `<PREFIX>-NNNNNN` the file name starts with. Validate:
  the ID must be `<PREFIX>-NNNNNN-<registered userid>` and the file name
  must start with `<PREFIX>-NNNNNN-` (`id-shape`); an ID defined in two
  files is `duplicate-id`.
- **References.** A reference field cites IDs as backticked tokens
  (`` `br-AUTH-000003-Ab3xR9pQ` ``, several separated by commas); a value
  with no backticks is read as comma-separated bare tokens. Each cited
  value must resolve to a rule, a domain code, an artifact or a row item
  (`dangling-ref`, an error); a value of the wrong type for the ETD's
  `target_type` is `ref-type`, several values in a single `ref` field are
  `cardinality`, a retired rule is `retired-target`, and a missing
  declared back-reference is `backref` (warnings).
- **Empty values.** A value is empty when it is blank, `-`, `—`, `n/a`
  or `none` (any case), or starts with `*(none` (e.g. `*(none yet)*`). An
  empty required field is `required-field`; an empty
  `required_when_closed` field on a closed artifact is
  `closed-incomplete` (errors).
- **Status.** Read from the first run of letters, ignoring `*`, `` ` ``
  and `_`, so `**Closed**`, `` `Closed` `` and `Closed ✅` are all
  `Closed`; compared without regard to case against the ETD's
  `closed_states`. An `enum` value outside `allowed_values` is
  `enum-value` (a warning).
- **Grounding.** A type whose ETD grounding is `required` or `inherited`
  must have at least one resolvable value in its `grounding_field`
  (`ungrounded`, an error — INV-5).
- **Signer.** `Signed-off-by` names a registered user by `name`,
  `git_username` or `userid` (any case, backticks ignored); missing or
  unregistered is `signer` (an error — INV-16).

**Free-form types** (ETD `naming: free-form`, e.g. items kept as rows of a
hand-edited table) store no file per instance: an item is a table row in
any `.md` file of the folder whose first cell is its ID,
`| ITEM-000012-Ab3xR9pQ | ... |` (backticks optional). Such items resolve
as references; they have no generated index and are exempt from INV-7.

## 4. Index files

A per-file type's index is `<folder>/<folder>.md`, generated by
`catalyst index regen` and never edited by hand or merged.

```markdown
# Items index

| ID | Title | Status |
|---|---|---|
| [ITEM-000012-Ab3xR9pQ](ITEM-000012-login-form-validation.md) | Login form validation | Open |
```

- The **ID table** is the first table whose header has an `ID` column.
  Everything else in the file — prose, other tables, the header's
  columns — is kept as written. A new index gets `| ID | Title | Status |`.
- One row per instance, in ID-number order. `ID` is
  `[<ID>](<file name>)`; `Title` is the instance's title; any other column
  is the instance field of the same (loosely matched) name, references
  rendered bare and joined with `, `. A column with no matching field
  keeps the old row's cell.
- A row whose file is gone is kept, so its number is never reused.
- A `*(none yet)*` placeholder line after the table is removed once the
  table has rows.

A row is read as a registration when its first cell is
`` [<ID>](<file>) `` (the ID optionally backticked). Validate: a
registered ID with no file is `index-orphan` (an error); an instance with
no row, or a row linking another file name, is `index-drift` (a warning,
repaired by `index regen`). `catalyst check` also warns when any index
differs from what `index regen` would write.

## 5. Rules

### 5.1 Rule documents

Every `.md` file under `rules/`, at any depth, is read for rule headings,
except `rules.md`, templates, templates catalogs, and anything under
`rules/domains/` or a `templates/` folder. `Rules-of-Rules.md` is read for
its `rr-META-` rules; every other such file is a **rule document**: it
must contain a `## Contents` heading and a
`## Linked Artifacts — Quick Index` heading, and its file name (or stem)
must appear in `rules/rules.md` (structure, INV-8).

### 5.2 Rule headings and IDs

A rule is defined by a level-2 or level-3 heading whose first element is
its backticked ID, optionally after a section number:

```markdown
### `br-AUTH-000003-Ab3xR9pQ` Session expires after 30 minutes idle
## 12. `rr-META-000012-Ab3xR9pQ` The journal is transaction-log-grade
```

- **ID grammar:** `<doc-prefix>-<DOMAIN>-<NNNNNN>[-<parent>]-<userid>` —
  a lowercase document prefix, an uppercase domain code
  (`[A-Z][A-Z0-9]*`), a six-digit number, an optional parent segment
  (`Rules-of-Rules.md` §3), and the signer's userid last. Structure: the
  number must have six digits and the last segment must be a registered
  userid (INV-26). Sub-domain codes (`PARENT.SUB`, `Rules-of-Rules.md`
  §7) are valid in domain files, but the 1.0-rc tools do not recognise a
  rule heading whose ID uses one — an open item for `1.0`.
- A rule's body runs to the next heading. It is **retired** when its
  heading contains `🗑`, or a line of its body contains both `🗑` and the
  word "status" (`Rules-of-Rules.md` §4).
- A heading containing "owned by the active module" is the kernel's
  placeholder for a module-owned meta-rule, not a definition.
- Validate: a rule ID defined twice is `duplicate-id`; a rule not listed
  in `rules/rules.md` is `rule-unindexed` (errors). `rr-META-` rules in
  `Rules-of-Rules.md` govern themselves and are never listed there.

### 5.3 `rules/rules.md`

Hand-maintained (never generated, never union-merged): a `## Documents`
table (`| Prefix | Document | Domains |`) and a `## Rule IDs` list. A rule
counts as listed when its full ID appears backticked anywhere in the
file: ``- `br-AUTH-000003-Ab3xR9pQ` — Session expires after 30 minutes idle``.
At least one `TEMPLATE-RULE-vN.md` exists, and only in `rules/templates/`
(structure, INV-8).

### 5.4 Domains

- **Domain files:** `rules/domains/<doc-prefix>-<CODE>-<short-summary>.md`
  (sub-domain: `<doc-prefix>-<PARENT>.<SUB>-<short-summary>.md`), shaped by
  `templates/domain.template.md` (`Rules-of-Rules.md` §7). Structure:
  INV-7 naming.
- **Domains index:** `rules/domains/domains.md`, a hand-maintained table
  (`| Code | Document | Defined |`). A row registers a domain when its
  first cell starts with the backticked code, optionally linked:
  ``| [`AUTH`](br-AUTH-authentication.md) | rules/business-rules.md | 2026-09-28 |``.
  Codes are `[A-Z][A-Z0-9_.]*`. A `Domain` reference resolves only to a
  registered code. `catalyst id next-rule` refuses a domain not
  registered here (`META` is always accepted).

## 6. Users and roles

`IAM/users/users.json`:

```json
{
  "users": [
    {"name": "Ada Lovelace", "git_username": "ada", "roles": ["Admin"],
     "registered": "2026-09-28", "active": true, "notes": "", "userid": "Ab3xR9pQ"}
  ]
}
```

`name`, `roles` (role names from `roles.json`), `registered` (date),
`active` (boolean), `notes` and `userid` are always present;
`git_username` is optional. A user is never deleted, only set
`"active": false`. Structure: the file exists and is valid JSON, at least
one user is active (INV-16), every userid is well-formed and unique
(INV-26).

`IAM/roles/roles.json`:

```json
{
  "roles": [
    {"name": "Admin", "actions": ["/user-add", "/freeze"], "reconciliation": "full"}
  ]
}
```

`reconciliation` is `full`, `propose` or `none` (INV-21). Structure: the
file exists. Role checks are advisory (`Rules-of-Rules.md` §11).

## 7. The journal

`development/journal.jsonl`: one JSON object per line, append-only,
never edited, deleted or reordered (INV-17). Empty is valid.

```json
{"timestamp": "2026-09-28T10:00:00Z", "actor": "ada", "command": "/create-item", "action": "create", "artifact": "ITEM-000012-Ab3xR9pQ", "targets": ["br-AUTH-000003-Ab3xR9pQ"], "intent": ["Validate the login form as br-AUTH-000003 requires."], "files": [{"path": ".criterion/items/ITEM-000012-login-form-validation.md", "before": null, "after": "3b18e512dba79e4c8300dd08aeb37f8e728b8dad"}, {"path": "src/login.py", "before": "9f87015fb23e4f7322f05d868f516b97b75ba037", "after": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"}], "writer": "catalyst/0.41.0", "tier": "feature"}
```

| Field | Type | Meaning |
|---|---|---|
| `timestamp` | string | UTC, `YYYY-MM-DDTHH:MM:SSZ`; non-decreasing down the file. |
| `actor` | string | The signer: a registered user's `git_username`, else `name`. |
| `command` | string | The command, e.g. `/create-item`; for a tiered change outside any command, the tier (`chore`). |
| `action` | string | `create`, `update`, `close`, `retire`, `status-change` or `sync`. |
| `artifact` | string | The artifact or rule ID, or a short description when there is none. |
| `targets` | list of strings | Rule or artifact IDs the change serves; `[]` states that it serves none. |
| `intent` | list of strings | One or more statements of the goal (at least one, non-empty). |
| `files` | list of objects | Per touched file: `path`, `before`, `after`. |
| `files[].path` | string | Relative to the **project root**: a working-copy file is `.criterion/<path>` and hashed into the working copy's repository; any other path into the project's. |
| `files[].before`, `files[].after` | string or null | The file's git blob SHA-1 (40 lowercase hex) before and after; `null` when it did not exist (create) or no longer exists (delete). |
| `writer` | string | `catalyst/<version>` on every CLI-written entry. |
| `tier` | string | Optional: `chore`, `fix` or `feature`. |
| `origin` | string | Optional: `manual` on an entry `catalyst journal adopt` wrote for a commit made outside catalyst. |
| `commit` | string | With `origin`: the adopted product commit's full sha. |
| `files[].superseded` | bool | Optional, on an adopted entry: the file was journaled again after the commit, so this records history only — excluded from the hash chain, the file's last state and restore. |

- **Pinning.** Every blob an entry references is kept reachable under the
  ref **`refs/catalyst/journal`** of the repository it was hashed into: a
  commit chain whose trees hold each blob under its own hash.
- **Legacy entries** (no `writer`: bare working-copy-relative paths,
  `<repo>:path` prefixes, absolute paths) are normalised on read and never
  rewritten.
- Structure: the file exists; every line is a JSON object with the eight
  required fields; every `files[]` entry has a `path` and 40-hex-or-null
  hashes. `catalyst journal verify` (part of `check`) adds: timestamps in
  order, each file's `before` equal to its previous `after`, every blob
  present, every CLI-written blob pinned, and no journaled file changed
  since its last entry — errors on CLI-written entries, warnings on legacy
  ones. `catalyst check` also warns about a product file git shows as
  changed that the journal has never recorded.
- **Unrecorded changes.** A non-merge product commit after the pointer's
  `journal_since` that changes a file to a blob that was not its latest
  journaled `after` as of the commit (a hand revert included), and was not
  adopted for that commit, is an unrecorded change (`catalyst unrecorded`; `check`,
  `trace` and the commit-msg hook report it): a warning while the format
  is a release candidate, an error from `1.0` or under `strict_journal`.
  `.criterion` is never a product file. `catalyst journal adopt` records
  it (`origin`, `commit`); rejecting it means reverting the commit.

## 8. `.gitattributes` (shared deployments)

`catalyst criterion create` and `push` keep one block in the working
copy's `.gitattributes`: the header line, then one union line per file
that is append-only or regenerated — the journal and every per-file
type's index:

```
# catalyst: append-only and regenerated files merge by union (catalyst criterion)
development/journal.jsonl merge=union
items/items.md merge=union
reconciliations/reconciliations.md merge=union
workflows/workflows.md merge=union
```

The block is rewritten whole; every other line is the team's and kept.
`rules/rules.md` and `domains.md` are hand-maintained and deliberately not
listed, so concurrent edits to them conflict. Not checked by `check`;
`criterion integrity` verifies after a merge that nothing recorded was
lost.

## 9. `.frozen`

An optional plain-text file in the working copy's root or the project
root: one path per line, working-copy-relative (a leading `.criterion/`
is accepted); blank lines and lines starting with `#` are ignored. A
listed item is skipped by `/sync-framework` and `catalyst recompose`
unless forced (`SYNCHRONIZE.md`, `/freeze`). Not checked.

## 10. Entity Type Definitions

An ETD is a YAML file in the module (`schemas/<entity>.yaml`, listed in
`module.yaml`) or the kernel (`entities/`). Its fields — `id_prefix`,
`name`, `plural_name`, `folder`, `location`, `naming`, `grounding`,
`grounding_field`, `fields[]` (`name`, `kind`, `required`,
`allowed_values`, `target_type`, `backref`, `required_when_closed`) and
`workflow` (`initial`, `states`, `closed_states`, `transitions`) — are
specified in `MODULE-SPECIFICATION.md` §4, and machine-readably in
[`schemas/entity-type-definition.schema.json`](schemas/entity-type-definition.schema.json).
The ETDs are the format of each module entity file: §3 above is how the
CLI reads any type an ETD declares.

## 11. What the product repository carries

- `<app-name>.catalyst` (§1).
- `/.criterion` in `.gitignore` (local-only), or `.gitmodules` plus the
  `.criterion` gitlink (shared).
- Commit messages that trace: every product commit cites an artifact or
  rule ID that resolves in the deployment, or its subject starts with
  `chore:` or `chore(<scope>):` (INV-5; `catalyst hook commit-msg`,
  `catalyst trace`, `CLI.md`). A commit message is not a file of the
  format, but the trace convention is part of it.
- Commits whose product changes the journal records (§7), after the
  pointer's `journal_since`; a change made outside catalyst is adopted
  or reverted.
- Optionally, `.catalystignore` files, in any directory: what is not
  governed by catalyst. Empty (blank lines and `#` comments aside): that
  directory and everything below it. Otherwise one path per line,
  relative to the file's directory — a file, or a directory and
  everything below it; `/`-separated, no wildcards, a leading `/` or
  `./` ignored. A directory with its own `<app-name>.catalyst` is a
  separate, nested deployment, outside its parent's scope (`CLI.md`,
  "What a deployment governs").

## Related docs

- [`CLI.md`](CLI.md) — the commands that read and write these files, and every check code.
- [`MODULE-SPECIFICATION.md`](MODULE-SPECIFICATION.md) — modules, manifests and ETDs.
- [`ARTIFACT-LAYOUT.md`](ARTIFACT-LAYOUT.md) — the working copy's tree at a glance.
- [`rules-of-rules.template.md`](rules-of-rules.template.md) §3, §7, §12, §13 — rule IDs, domains, the journal, shared deployments.
- [`migrations/0.41.0/traced-commits-and-format.md`](migrations/0.41.0/traced-commits-and-format.md) — adding `format` to an existing pointer.
- [`migrations/0.42.0/changes-outside-catalyst.md`](migrations/0.42.0/changes-outside-catalyst.md) — adding `journal_since` to an existing pointer.
