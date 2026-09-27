# Rules of Development — template

> Copy to `CODE-OF-CONDUCT.md` in the project root and resolve every
> `{{PLACEHOLDER}}`. See [`INSTANTIATION-GUIDE.md`](INSTANTIATION-GUIDE.md).

Standards for how development work — bugs, requirements, house-keeping, and
meta-tags — gets proposed, tracked, and closed. Subordinate to
[`{{RULES_DIR}}/Rules-of-Rules.md`]({{RULES_DIR}}/Rules-of-Rules.md):
that file governs the rules themselves; this file governs the work items
that reference those rules.

---

## 1. No development without a targeted rule

**No bug, requirement, house-keeping work, or meta-tag may start without
citing one or more existing rule IDs in its `Targets` field when the tag is
used to annotate a rule-linked artifact.** If no rule currently covers the
behavior in question:

1. Define the rule(s) first, as a normal edit to the relevant rule
document.
2. That definition must satisfy `Rules-of-Rules.md` §1 (conflict check)
and follow the ID scheme in §3.
3. Only then open the `BUG-`/`REQ-`/`HK-` item, citing the new ID(s).

House-keeping is the one category where "no rule applies" is a legitimate
answer (pure repo hygiene with no bearing on any documented behavior or
process) — but it must be stated explicitly, not left blank.

## 2. Users, roles, and signing

`IAM/users/users.json` is a JSON array of registered users
(`{name, roles, registered, active, notes}`, plus `git_username` once a
repoed deployment resolves it — `Rules-of-Rules.md` §13), managed only by
`/user-add`/`/user-remove`/`/user-modify`/`/user-assign-role`/`/user-list`
— see §4. Once a user has a `git_username`, every `Signed-off-by`/journal
`actor` written for them uses that, never `name`. Each user has one or
more roles drawn from
`IAM/roles/roles.json`, a JSON array of `{name, actions}` objects
mapping each role to the actions/commands it's expected to perform.
`roles.json` is seeded with a default agile-role mapping
(`templates/roles.template.json`) and then extended via `/role-add`
(new role) or `/role-modify` (change an existing role's actions).

**This is JSON, not hand-edited markdown, precisely because it's managed
exclusively by commands** — the same reasoning that keeps
`development/BACKLOG.md` machine-only, just with structured data instead
of a regenerated document.

**Hard requirement: `IAM/users/users.json` must always have at least
one entry with `"active": true`.** A project with nobody registered has
nobody to sign work. `/user-remove` must refuse or warn (per its own
spec) rather than silently drop the last active user to zero.

**Beyond that one hard requirement, this role model is advisory, not an
access-control system.** Catalyst has no way to verify who is actually
typing, so a role mismatch is a prompt for confirmation, never a silent
block:

1. Before an artifact-creating or work-item-status-changing command
   completes, resolve who is signing it: the user established earlier
   this session, or ask if not yet established (don't guess from git
   config — confirm with the user).
2. Look up that name in `IAM/users/users.json`. If unregistered, say so
   and ask whether to proceed anyway or register them first via
   `/user-add`.
3. Look up their role(s) in `IAM/roles/roles.json` and check whether the
   action being performed is one that role covers. If it isn't, say so
   and ask for confirmation before continuing — never refuse outright.
4. Once confirmed (or if the role already covers the action), fill the
   artifact's `Signed-off-by` field with the user's name and proceed.

Every dev-artifact, feature entry, roadmap item, and work item carries a
`Signed-off-by` field for this reason (see each type's template). It
records who actually signed the artifact, which may differ from who typed
the command on their behalf.

## 3. Standard document types

| Type | Folder | Template | ID prefix |
|---|---|---|---|
| Bug | `bugs/` | `templates/bug.template.md` | `BUG-NNNNNN` |
| Requirement | `requirements/` | `templates/requirements.template.md` | `REQ-NNNNNN` |
| House-keeping | `house-keeping/` | `templates/house-keeping.template.md` | `HK-NNNNNN` |
| Meta-tag | `meta-tags/` | `templates/meta-tag.template.md` | `TAG-<KEY>-<ARTEFACT-ID>` |

Feature entries (`FEAT-NNNNNN`, folder `features/`, template
`templates/features.template.md` → `TEMPLATE-FEATURE.md`) are a related
but **separate, non-rule-linked** scheme — see `Rules-of-Rules.md` §9.
They document possible future work, are not one of the four
development-artifact types above, and are exempt from this document's
rules (no `Targets`, no `Domain`, never "done" against a rule). When a
new feature actually needs to be developed, open a `REQ-NNNNNN`
requirement — never a `BUG-NNNNNN` — to track it.

Roadmap items (`RM-NNNNNN`, table rows inside `development/roadmaps/<name>.md`
files — one file per named roadmap, template `templates/roadmap.template.md`,
index `development/roadmaps/roadmaps.md`) sit one level above feature
entries — see `Rules-of-Rules.md` §10. They are populated by
`/roadmap-add`/`/roadmap-update`/`/roadmap-merge` from an external source
file rather than created one at a time, and are exempt from this document's
rules the same way feature entries are (no `Targets`, no `Domain`, never
"done" against a rule). Formalizing a roadmap item means opening a
`FEAT-NNNNNN` for it via `/create-feature`, citing the `RM-NNNNNN` ID in the
feature's `Roadmap` field.

### Hard rule: individual files and indexes

- **This is a hard requirement.** Bugs, requirements, house-keeping items, and
  meta-tags must each be stored as their own individual markdown file in the
  corresponding folder, not only as free-form notes or grouped content.
- **This is also a hard requirement.** Every item must be listed in the
  corresponding type index file so the repository has an authoritative catalog
  of the concrete documents that exist.
- Each item directory must also contain an index file named after the item type:
  - `bugs/bugs.md` for the bug index.
  - `requirements/requirements.md` for the requirements index.
  - `house-keeping/house-keeping.md` for the house-keeping index.
  - `meta-tags/meta-tags.md` for the meta-tag index.
- These index files are the canonical indexes for their directory and must be kept up to date.
- **This is a hard requirement.** `development/BACKLOG.md` always
  exists — seeded from `templates/backlog.template.md` on first deploy —
  as the go-to document for developers to review work to be done and
  current status. It is not hand-maintained: `/show-backlog` regenerates
  it in full every time it runs, so it never drifts from the real
  indexes — including every `development/roadmaps/<name>.md`. See
  `INVARIANTS.md` INV-14.
- **This is also a hard requirement.** `development/roadmaps/` and its
  `roadmaps.md` index always exist (empty is fine — individual named
  roadmaps are created only via `/roadmap-add`). Within any
  `development/roadmaps/<name>.md` that does exist, only the
  `/roadmap-add`/`-update`/`-merge`/`-remove` commands and `/show-backlog`
  (Status/Linked refresh) ever change it; hand-editing anything but a
  row's Notes column is pointless, the same way hand-editing `BACKLOG.md`
  is. See `INVARIANTS.md` INV-15.
- **This is a hard requirement, stricter than the others above.**
  `IAM/users/users.json` and `IAM/roles/roles.json` always exist, and
  `users.json` must contain **at least one entry with `"active": true`** —
  not "empty is fine," since a project with nobody registered has nobody
  to sign work. Both files are managed only by the `/user-*`/`/role-*`
  commands (§2, §4), never hand-edited. See `INVARIANTS.md` INV-16.
- **This is a hard requirement.** `development/journal.jsonl` always
  exists (empty is fine). Once a line is appended it is never edited,
  deleted, or reordered — stricter than every other "never hand-edited"
  rule above, since even the commands that write to it only ever append.
  See `INVARIANTS.md` INV-17 and §9.

- **Bug**: an existing ✅ rule doesn't actually hold in the running system,
  or formalizes an already-known ⚠️/❌ rule into trackable, closeable work.
  Never introduces a new rule by itself.
- **Requirement**: an explicit, tracked requirement that captures
  user/business behavior that must be implemented and tested — this is the
  artifact to open when a new feature needs to be developed, never a bug.
  It must be vetted against every existing rule document (`Rules-of-Rules.md`
  §1 conflict check) before it's opened, it always carries a `Domain`, and it
  always answers — targets and/or proposes — one or more rules (and, if
  needed, a new domain — see `Rules-of-Rules.md` §6/§7) inline in the
  requirement doc so rule and requirement are reviewed together. None of
  those three are optional.
- **House-keeping**: dev-support tooling/process, not product behavior.
  Still targets a rule where one exists — most commonly a `rr-META-*`
  process rule.
- **Meta-tag**: a lightweight annotation attached to an existing artifact.
  It stores one key/value pair whose key is one of `comment`, `version`, or
  `link-to`, and it is saved under the name `tag-<key>-<artefact-id>`.

## 4. Slash-command entry points

The framework exposes the following custom slash commands:

- `/create-bug` — create a new bug artifact immediately, register it in
  `bugs/bugs.md`, and track it in the same workflow as any other bug.
- `/create-req` or `/create-requirement` — create a new requirement artifact
  immediately, register it in `requirements/requirements.md`, and track it in
  the same workflow.
- `/create-feature` — create a new feature entry immediately and register it
  in `features/features.md`. Unlike `/create-bug`/`/create-req`, this never
  prompts for a rule target or domain — features are not rule-linked (see
  `Rules-of-Rules.md` §9).
- `/roadmap-add <name> <file>` — ingest a new named roadmap from a local
  file, creating `development/roadmaps/<name>.md` from
  `templates/roadmap.template.md` and registering it in
  `development/roadmaps/roadmaps.md` (see `Rules-of-Rules.md` §10).
  Refuses if `<name>` already exists — use `/roadmap-update` or
  `/roadmap-merge` instead.
- `/roadmap-remove <name>` — delete `development/roadmaps/<name>.md` and
  its `roadmaps.md` entry if no row is linked to a `FEAT-`/`REQ-`;
  otherwise retire it in place (never hard-deletes a linked roadmap).
- `/roadmap-update <name> <file>` — re-ingest `<file>` as the new full,
  authoritative version of an existing named roadmap: add new rows,
  update matched rows, flag (never delete) rows missing from the new
  file.
- `/roadmap-merge <name> <update file>` — fold a partial delta file into
  an existing named roadmap: add/update only the rows the delta
  mentions, without flagging anything as missing.
- `/user-add <name> <role>` — register a new user in
  `IAM/users/users.json` with an initial role from
  `IAM/roles/roles.json`. Refuses if `<name>` is already registered —
  use `/user-modify`/`/user-assign-role` instead.
- `/user-remove <name>` — set `<name>`'s `active` field to `false` in
  `IAM/users/users.json`. Never deletes the entry (see §2). Refuses or
  warns if this would leave zero active users (hard rule, §2).
- `/user-modify <name> <field> <value>` — edit `<name>`'s `notes` or
  `active` field. Refuses for `roles` (use `/user-assign-role`) and for
  identity/audit fields (`name`, `registered`).
- `/user-assign-role <name> <role>` — add `<role>` to `<name>`'s `roles`
  array (additive; doesn't remove their other roles).
- `/user-list [--role <role>] [--active-only]` — list registered users,
  optionally filtered.
- `/role-add <role> <actions>` — add a new role entry to
  `IAM/roles/roles.json`. Refuses if `<role>` already exists — use
  `/role-modify` instead.
- `/role-modify <role> <actions>` — replace an existing role's `actions`.
  Refuses if `<role>` doesn't exist — use `/role-add` instead.
- `/create-epic` — create a new epic work item and register it in
  `epics/epics.md`.
- `/create-story` — create a new story work item and register it in
  `stories/stories.md`.
- `/create-task` — create a new task work item and register it in
  `tasks/tasks.md`.
- `/create-spike` — create a new spike work item and register it in
  `spikes/spikes.md`.
- `/create-sprint` — create a new sprint container and register it in
  `sprints/sprints.md`. Scrum flavor only (`rules-of-work-items.md` §2).
- `/create-board` — create a new board container and register it in
  `boards/boards.md`. Kanban/Scrumban flavor only — the structural
  counterpart to `/create-sprint`.
- `/create-workflow` — create a new process-definition document and
  register it in `workflows/workflows.md`. Not a unit of work: no parent
  epic/story link, `Status` is `Active`/`Deprecated`.
- `/meta-tag` — create a new meta-tag artifact, save it as
  `tag-<key>-<artefact-id>`, register it in `meta-tags/meta-tags.md`, and
  link it to the specified artifact.
- `/list <type> [--filter ...]` — list artifacts, work items, rules, or
  templates of the requested type. Use `all` to list everything. Each
  `--filter` is a property filter expressed as `key=value` or
  `key="value*"`; filters apply across the selected collection. If the
  requested type is `template`, the command requires an additional
  `--type <template-type>` argument to identify which template family to
  inspect.
- `/freeze <item-id|item-path|type|template-name>` — protect the resolved
  item from `/sync-framework` by recording its file path in a root-level
  `.frozen` file. The command accepts one of four argument forms: an item
  ID, an item path, a type, or a template name.
- `/catalyzer <subcommand>` — manage plugin installation and activation through
  the framework interface. Every subcommand resolves plugins against the
  registry file `plugins/<type>/catalog.md` (currently only
  `plugins/repository/catalog.md`, since the repository type is the only
  plugin type defined at this time), which is the sole source of truth for
  which plugins are registered, their git repository URL, the release/tag
  that ships with the current catalyst release, and their framework-version
  compatibility. Each catalog entry has a `Compatibility` field: a bare `*`
  means the plugin is compatible with every framework version — the default
  for a registered plugin, and never grounds for `/sync-framework` to
  deactivate it. A future convention allows specific version constraints in
  that field instead, expressed with the same range syntax used in a
  dependency lock file, to mark a plugin as excluded from named framework
  versions. Supported subcommands:
  - `list` — list all available plugins by type, read from each type's
    `catalog.md`, including each plugin's repository URL, pinned
    release/tag, and compatibility.
  - `activate <name> <version|latest>` — download or update the plugin to the
    specified version (or `latest`) and activate it. This command requires a
    version argument.
  - `download <name> <version|latest>` — download the plugin into the
    framework without activating it. The plugin remains installed and inactive
    until it is explicitly activated.
  - `deactivate <name>` — deactivate a plugin by its registered name, remove
    it from memory, and mark it inactive.
  - `upgrade <name|latest>` — upgrade an already installed plugin to a
    specified version or to the latest available version.
  - `downgrade <name> <version>` — downgrade an already installed plugin to
    the specified version.
  Plugins are not loaded into memory unless they are explicitly activated via
  this command, and on framework startup the framework must scan the installed
  plugin list and activate only those marked active. This is a hard rule.
  The framework defines the interface and lifecycle contract; the plugin itself
  owns its implementation details, operational guidance, and domain-specific
  behavior. Each plugin must live in its own repository, with no exceptions,
  and during framework deployment or synchronization plugins must be pulled
  directly from that plugin repository rather than from this repository.
- `/thingamabob create <name> <git-info>` — bootstrap a repoed deployment
  (`Rules-of-Rules.md` §13, `INVARIANTS.md` INV-18): register or create
  the dedicated repo (confirm explicitly first if `<git-info>` already
  has *unrelated* content — a different deployment's own state, not a
  rejoin of this one), then ask which branch this actor will push to and
  record it as `thingamabob_branch` in `<app-name>.catalyst`, then push
  local `.catalyst-proj/` as the first commit on its `thingamabob`
  branch. Also resolves the current actor's `git_username` and migrates
  their prior `Signed-off-by` occurrences to it (never the journal — see
  §9/§13). Called again against the same repo with a different `<name>`,
  branches instead of refusing: a new branch off `thingamabob`, named
  `<name>` in its branch-safe form.
- `/thingamabob get <repo> <username>` — join an already-repoed
  deployment: download `<repo>`'s `thingamabob` branch and check out
  `<username>.catalyst-proj` (branch-safe form) from it as this user's
  local `.catalyst-proj/`. `<username>` is this user's `git_username`,
  same identity-migration treatment as `create`. Also asks which branch
  to push to and records `thingamabob_branch`, same as `create`.
- `/thingamabob push [--force]` — refuses if not yet repoed (point to
  `/thingamabob create`), or asks for and records `thingamabob_branch`
  first if this deployment predates that field. If `thingamabob_branch`
  is a real contributor branch (the default —
  `<git_username>.catalyst-proj`, or the branch-safe form of `name`):
  vet the pushed state against `thingamabob` (`/check-rules` + a
  four-eyes sub-agent pass), AI-merge where a plain merge can't resolve
  it, update both branches, and refresh the local `.catalyst-proj/` to
  match; `--force` skips vetting for this one push and overwrites
  `thingamabob` directly anyway — refused for anyone but the repo's
  `created_by` user. If `thingamabob_branch` **is** `thingamabob`
  itself (single-maintainer mode, e.g. catalyst's own self-dogfooding):
  every push overwrites `thingamabob` directly, no vetting, no merge —
  the normal behavior in this mode, not a `--force`-only shortcut —
  still refused for anyone but `created_by`. After a `/dogfood` run that
  ends clean or ends with fixes applied and reverified, offer this
  command (`create` if not yet repoed, `push` otherwise) as the natural
  next step — never run it automatically.
- `/project create <project name>` — install a fresh catalyst deployment
  here (`Rules-of-Rules.md` §14): resolve `agent-source`, build the
  working copy there, and write `<app-name>.catalyst` at this project's
  root. Refuses if a deployment already exists here.
- `/project remove <project name> [force]` — un-link the local
  `<app-name>.catalyst` pointer; the working copy, memory note, and any
  `thingamabob` repo are left untouched (retire in place). `force`
  additionally deletes the working copy at `agent-source` and this
  agent's memory note for the project — confirm explicitly first; never
  touches a `thingamabob` repo.
- `/project export <project name> [export filename]` — bundle every file
  under the working copy, plus its pointer fields (minus
  `agent-source`), into one JSON export. Default filename:
  `<project name>-catalyst-export-<UTC timestamp>.json`.
- `/project import <export filename> [force]` — install a bundle into
  the current project. Refuses if a deployment already exists here,
  unless `force` is given, in which case it overwrites the existing one
  — confirm explicitly first.
- `/status` — update an artifact or work item's `Status` field.
- `/audit <file-name>` — analyze the change-impact of the specified file by
  checking the current repository state, the file's role in the framework,
  and the rules or artifacts that depend on it, then return a concise impact
  summary.
- `/run-analysis` — open and execute the analysis playbook from
  `ANALYSIS-PLAYBOOK.md` in the project root, following its steps and
  returning the resulting analysis summary.
- `/sync-framework [latest|<version>]` — synchronize the deployed framework
  with the requested framework version. If the argument is `latest`, use the
  newest framework version available from the framework source. If no argument
  is provided, synchronize against the currently installed local version.
- `/check-rules` — verify that rules, domains, and artifact links remain
  consistent and do not conflict.
- `/commands list [--filter ...]` — list every slash command available in
  this deployment (name, one-line purpose), sourced from this document's
  §4. `/help` with no argument delegates here for its command listing
  rather than re-describing it.
- `/show-backlog` — summarize open work, blockers, and missing links,
  refresh `development/BACKLOG.md` with the result, and refresh every
  active `development/roadmaps/<name>.md`'s Status/Linked columns from
  the `FEAT-`/`REQ-` each row is linked to.
- `/journal [--since <date>] [--artifact <id>] [--actor <name>] [--rule
  <id>]` — read-only: filter and report `development/journal.jsonl`
  entries. Never writes to the journal (see §9).
- `/journal-restore <timestamp>` — read-only: reconstruct the tree as it
  stood at `<timestamp>` into a side directory, from the journal's
  before/after file hashes (`Rules-of-Rules.md` §12). Never overwrites the
  live working tree.
- `/help` — return help documentation for the framework or for a specific
  command when provided.

When the user enters `/create-bug: ...`, create a new bug artifact immediately,
register it in `bugs/bugs.md`, and track it in the same workflow as any other
bug. If the domain cannot be inferred from context, prompt for the domain and
rule before creating the artifact.

When the user enters `/create-req:` or `/create-requirement: ...`, create a
new requirement artifact immediately, register it in
`requirements/requirements.md`, and track it in the same workflow. If the
domain or target rule cannot be inferred, prompt for both before creating the
artifact.

When the user enters `/create-feature: ...`, create a new feature entry
immediately using `templates/features.template.md`, register it in
`features/features.md`, and track it as idea/roadmap content, not
rule-linked development work. Do not prompt for a domain or rule target —
neither field exists on this artifact type. If this feature formalizes an
existing roadmap row (in any `development/roadmaps/<name>.md`), cite that
row's `RM-NNNNNN` ID in the new feature's `Roadmap` field and set the row's
`Status` to `Triaged` and `Linked` to the new `FEAT-NNNNNN`. If the user later
asks to start building a registered feature, create a `REQ-NNNNNN`
requirement instead (prompting for domain/target rule as usual), and link
it back to the `FEAT-NNNNNN` entry's `Requirement(s)` field.

When the user enters `/roadmap-add <name> <file>: ...`, refuse with a clear
message if `development/roadmaps/<name>.md` already exists (point to
`/roadmap-update`/`/roadmap-merge`). Otherwise read `<file>` from the
local filesystem, identify its distinct items, and create
`development/roadmaps/<name>.md` from `templates/roadmap.template.md` with
one `RM-NNNNNN` row per item (`Status: Not triaged`, `Linked: *(none)*`),
IDs continuing the global sequence across every existing named roadmap —
never reused, never guessed. Register the new roadmap in
`development/roadmaps/roadmaps.md`, then report the roadmap name and the
IDs assigned.

When the user enters `/roadmap-remove <name>`, refuse with a clear message
if `development/roadmaps/<name>.md` does not exist. If every row's `Linked`
field is empty, delete the file and its `roadmaps.md` entry outright and
report that. If any row has a non-empty `Linked` field, do **not** delete
anything — instead add a `Retired` field (today's date) to the file, mark
its `roadmaps.md` entry `retired`, leave every row and `RM-NNNNNN` ID exactly
as they are, and tell the user it was retired rather than removed because
removing it would break a live `FEAT-`/`REQ-` cross-reference.

When the user enters `/roadmap-update <name> <file>: ...`, refuse with a
clear message if `development/roadmaps/<name>.md` does not exist (point to
`/roadmap-add`). Otherwise treat `<file>` as the new full, authoritative
version of this roadmap: add a new `RM-NNNNNN` row for each item not already
present, update the `Title`/`Notes` of any row that matches an item in
`<file>` by title/description similarity (ask the user rather than
guessing when a match is ambiguous), and flag — in `Notes`, never by
deleting — any existing row whose item no longer appears in `<file>`.
Update the file's `Source` and `Last updated` fields, then report a short
summary of what was added/updated/flagged.

When the user enters `/roadmap-merge <name> <update file>: ...`, refuse
with a clear message if `development/roadmaps/<name>.md` does not exist
(point to `/roadmap-add`). Otherwise treat `<update file>` as a partial
delta, not the full roadmap: apply the same add/update matching rule as
`/roadmap-update` for only the items `<update file>` actually contains,
but do not compare against or flag any row it doesn't mention, and do not
change the `Source` field — only `Last updated`. Report a short summary of
what was added/updated.

When the user enters `/user-add <name> <role>: ...`, refuse with a clear
message if `<name>` already has an entry in `IAM/users/users.json`
(point to `/user-modify`/`/user-assign-role`). If `IAM/users/users.json`
or `IAM/roles/roles.json` doesn't exist yet, create them from
`templates/users.template.json` and `templates/roles.template.json`
first. If `<role>` isn't one of the roles listed in
`IAM/roles/roles.json`, ask whether to use an existing role or run
`/role-add` for `<role>` first. Otherwise append a new entry (`registered`:
today, `active: true`, `roles: [<role>]`) and report it. If this is the
project's first registered user, note that the hard "at least one active
user" requirement (§2) is now satisfied.

When the user enters `/user-remove <name>`, refuse with a clear message if
`<name>` has no entry in `IAM/users/users.json`. If `<name>` is the only
`active: true` entry, warn that this would leave the project with zero
active users (hard rule, §2) and ask for confirmation, or suggest
`/user-add` for a replacement first. Otherwise set that entry's `active`
field to `false` — never delete it, since existing `Signed-off-by`
references on already-signed artifacts must stay resolvable. Report the
result.

When the user enters `/user-modify <name> <field> <value>: ...`, refuse
with a clear message if `<name>` has no entry in `IAM/users/users.json`
(point to `/user-add`). Refuse if `<field>` is `roles` (point to
`/user-assign-role`) or `name`/`registered` (identity/audit fields, never
edited in place). Refuse if `<field>` is `active` set to `false` (point to
`/user-remove`, which also checks the "at least one active user" rule).
Otherwise update `<field>` to `<value>` and report the result.

When the user enters `/user-assign-role <name> <role>: ...`, refuse with a
clear message if `<name>` has no entry in `IAM/users/users.json` (point
to `/user-add`). If `<role>` isn't one of the roles listed in
`IAM/roles/roles.json`, ask whether to use an existing role or run
`/role-add` for `<role>` first. If `<name>`'s `roles` array already
contains `<role>`, say so and make no change. Otherwise append `<role>` to
that array and report the result.

When the user enters `/user-list [--role <role>] [--active-only]`, read
`IAM/users/users.json`. If it doesn't exist, say so rather than
inventing users. Apply `--role`/`--active-only` filters if given, and
report the matching entries. If none match, say so rather than inventing
matches.

When the user enters `/role-add <role> <actions>: ...`, refuse with a
clear message if `<role>` already has an entry in
`IAM/roles/roles.json` (point to `/role-modify`). If
`IAM/roles/roles.json` doesn't exist yet, create it from
`templates/roles.template.json` first. Otherwise append a new entry
(`name: <role>`, `actions: <actions>`) and report it.

When the user enters `/role-modify <role> <actions>: ...`, refuse with a
clear message if `<role>` has no entry in `IAM/roles/roles.json` (point
to `/role-add`). Otherwise replace that entry's `actions` and report the
result. This never retroactively changes a `Signed-off-by` value already
recorded on an existing artifact.

When the user enters `/create-epic`, `/create-story`, `/create-task`,
`/create-spike`, or `/create-sprint`, create the corresponding work-item
artifact immediately, register it in the matching index file under the
appropriate work-items folder, and preserve the required linkage to its parent
or target artifact.

When the user enters `/create-board`, create a new `BOARD-NNNNNN` with
`Status: Active`, register it in `boards/boards.md`. Stories/tasks
reference it in place of sprint membership — never both at once for the
same item.

When the user enters `/create-workflow`, create a new `WORKFLOW-NNNNNN`
documenting the procedure described, `Status: Active`, register it in
`workflows/workflows.md`. It carries no parent epic/story link and is
never itself "done" — only ever `Active` or `Deprecated`.

When the user enters `/meta-tag <artefact-id>`, create a new meta-tag artifact
immediately, save it as `tag-<key>-<artefact-id>`, register it in
`meta-tags/meta-tags.md`, and link it to the specified artifact. If the key
is not supplied explicitly, prompt for it.

When the user enters `/list <type> [--filter ...]`, inspect the relevant
catalogs and return the matching items. If `type` is `all`, inspect every
supported collection and apply the same filters there. If `type` is
`template`, require `--type <template-type>` and list the matching templates
for that family. If no items match, return an empty result rather than
inventing matches.

When the user enters `/freeze <item-id|item-path|type|template-name>`, resolve
the item to its backing file path, append that path to the root-level
`.frozen` file if it is not already present, and report success. The item is
then protected from automatic framework synchronization until it is
explicitly removed from `.frozen` or re-synchronized with an override.

Every `/catalyzer` subcommand resolves plugin identity, repository URL, and
version information exclusively from the `catalog.md` registry of the
relevant plugin type (e.g. `plugins/repository/catalog.md`); a plugin
name with no matching entry in the registry is unregistered, and any
subcommand invoked against it must be refused with a message that the plugin
is not registered. When the user enters `/catalyzer list`, read every plugin
type's `catalog.md` and return the available plugins grouped by type,
each with its registered repository URL, pinned release/tag, and
compatibility. When the user
enters `/catalyzer activate <name> <version|latest>`, look up `<name>` in the
registry to resolve its repository URL, then download or update the plugin
into the framework at `plugins/<type>/` from that repository if it is not
already present, then load it into memory: read that plugin's own
`working-contract.md` and fulfill its Operational-loop section — starting
whatever persistent sub-agent or process it describes — always targeting
the deployed project's own repository root (the project this activation is
happening within), never the catalyst framework's own repository or the
plugin's installation directory. The command requires a version
argument; if the user supplies `latest`, resolve the newest available version
for that plugin from its repository rather than from the pinned tag in the
registry. If a plugin with the same name is already loaded, replace it in
memory with the new instance. When the user enters
`/catalyzer download <name> <version|latest>`, resolve `<name>` against the
registry the same way, then download the plugin into the framework without
activating it; the installed plugin remains inactive until it is explicitly
activated later. A plugin is considered invalid for activation unless its root
directory contains both a `README.md` file and a `working-contract.md` file;
if either file is missing, refuse activation and report the missing
requirement. When the user enters `/catalyzer deactivate <name>`, leave the
plugin installed in the framework but mark it inactive and flush it from
memory. When the user enters `/catalyzer upgrade <name|latest>`, resolve the
plugin's repository URL from the registry, then update the plugin to the
requested version or to the latest available version from that repository.
When the user enters `/catalyzer downgrade <name> <version>`, resolve the
plugin's repository URL from the registry, then downgrade the plugin to the
specified version. Plugins must remain inactive until they are explicitly
activated, and only the repository plugin type exists at this time. On
framework startup, the framework must scan the installed plugins and activate
each one whose `active` metadata flag is true the same way `/catalyzer
activate` loads a plugin into memory (see above). This is a hard rule.

When the user enters `/thingamabob create <name> <git-info>: ...`: if
`.catalyst-proj/DEPLOYMENT.md` doesn't yet show `repoed: true`, this is the first-call
bootstrap — check whether `<git-info>` already exists: if it does,
inspect its content before registering it as-is — if it's genuinely this
same deployment's own prior state (a real rejoin), proceed; if it holds
*unrelated* content (a different project's own `.catalyst-proj/`
deployment), that's not a rejoin, stop and confirm explicitly with the
user before doing anything, the same tier of confirmation as creating a
new repo; if `<git-info>` doesn't exist yet, create it there under
`<name>` — this is an externally-visible, hard-to-reverse action, so
confirm with the user before creating it, distinct from the general
push-assent already implied by invoking this command. Write `repoed:
true`, `catalyst_repo: <name>`, `catalyst_repo_url: <git-info>`,
`created_by: <the current Signed-off-by actor>` to
`.catalyst-proj/DEPLOYMENT.md`, **ask which branch this actor will push
to** — the actor's own `<branch-safe-name>.catalyst-proj` is the
suggested default, but `thingamabob` itself is a valid choice too (see
`/thingamabob push` below for what that changes) — and write the answer
as `thingamabob_branch` in both `.catalyst-proj/DEPLOYMENT.md` and
`<app-name>.catalyst`. Then push the current local `.catalyst-proj/`
state as the first commit on a `thingamabob` branch there. Nothing is
vetted on this first push. If `.catalyst-proj/DEPLOYMENT.md` **already**
shows `repoed: true`: don't refuse — if `<git-info>` matches the
registered `catalyst_repo_url`, create a new branch off `thingamabob`'s
current state named `<name>` in its branch-safe form (§13) and stop
there (no repo mutation, no `.catalyst-proj/DEPLOYMENT.md` change); if `<git-info>`
names a different repo, confirm explicitly with the user before doing
anything, since that's an unusual second-repo scenario rather than
ordinary branching. On the first-call path only, also run the identity
migration below, then report the result.

When the user enters `/thingamabob get <repo> <username>: ...`, validate
`<username>` against the branch-safe-name rule (§13) — refuse with a
suggested alternative if it doesn't survive sanitization uniquely against
already-registered users. Download `<repo>`'s `thingamabob` branch content
and check out `<username>.catalyst-proj` (branch-safe form) from it as
this user's local `.catalyst-proj/`, creating a `IAM/users/users.json`
entry for them first if one doesn't already exist. **Ask which branch
this actor will push to**, same as `create` above (the just-created
`<username>.catalyst-proj` is the default), and record
`thingamabob_branch`. Then run the identity migration below for this
user, and report the result.

**Identity migration** (part of both `/thingamabob create`'s first call
and `/thingamabob get`): set `git_username` on the current user's
`IAM/users/users.json` entry to their resolved git identity (`git
config user.name`, branch-safe form, for `create`; the given `<username>`
for `get`). Rewrite every existing artifact's `Signed-off-by` field that
currently names this user's old `name` to their new `git_username` —
from this point on, every `Signed-off-by`/journal `actor` written for
them uses `git_username`, never `name`. **Never rewrite the journal
itself** (`Rules-of-Rules.md` §12, INV-17 — entries are immutable, no
exception for this either); instead append one new entry (`action:
"update"`, `intent` describing the migration) covering every artifact
file actually rewritten.

When the user enters `/thingamabob push [--force]`, refuse with a clear
message if `.catalyst-proj/DEPLOYMENT.md` doesn't show `repoed: true` (point to
`/thingamabob create`). If no `thingamabob_branch` is recorded yet (a
deployment from before this field existed), ask now — same question as
`/thingamabob create`'s — and record the answer before continuing.

**If `thingamabob_branch` names a real contributor branch**
(`<git_username>.catalyst-proj` if the actor has one, otherwise the
branch-safe form of `name`): push local `.catalyst-proj/` there in the
repoed repository (creating that branch on their first push), **scoped
to artifact files whose `Signed-off-by` names the current actor** —
check the actor's `roles` array in `IAM/users/users.json` against
`IAM/roles/roles.json`; if it includes the `Admin` role, skip scoping
and push everything. Otherwise leave out any artifact file signed by
someone else, and report which files (if any) were excluded and why.
Shared registries/indexes (`rules.md`, `requirements.md`,
`roadmaps.md`, `BACKLOG.md`, `IAM/users/users.json`,
`IAM/roles/roles.json`) and the journal aren't signed by one person and
are never filtered by this rule. This scopes what gets pushed; it never
refuses the command outright. If `--force` is given: refuse unless the
current actor matches
`.catalyst-proj/DEPLOYMENT.md`'s `created_by`; otherwise confirm with the user, then
overwrite `thingamabob` directly from local state and skip everything
below. Otherwise: (1) vet the incoming branch against `thingamabob` —
`/check-rules` plus an independent four-eyes sub-agent pass checking
whether the incoming state still matches what its own rules claim;
disagreement between the two sub-agents, or a flagged violation, stops
here rather than proceeding silently; (2) merge —
attempt a normal merge first, and only where that leaves conflicts
(git-level or vetting-flagged), have a sub-agent propose a resolution
guided by `Rules-of-Rules.md` §1's conflict-check principle, stopping to
ask the user if a conflict is genuinely irreconcilable rather than
guessing; (3) update both `thingamabob` (the merge commit) and the
contributor's own branch (fast-forwarded to match); (4) pull the updated
`thingamabob` down and overwrite the local `.catalyst-proj/` directory
and this session's in-memory record of it.

**If `thingamabob_branch` *is* `thingamabob` itself** (single-maintainer
mode): push local `.catalyst-proj/` state directly onto `thingamabob`,
overwriting it — every time, no vetting, no merge, not gated behind
`--force`. Still refuse unless the current actor matches
`.catalyst-proj/DEPLOYMENT.md`'s `created_by`. This is the expected mode
for catalyst's own self-dogfooding, offered as the natural follow-up
after a `/dogfood` run ends clean or ends with fixes applied and
reverified — `/dogfood`'s own four-eyes audit is what already vetted the
state, so repeating that check on push would be redundant.

Report the result either way.

When the user enters `/project create <project name>: ...`, refuse if a
`<app-name>.catalyst` pointer or an in-project `.catalyst-proj/` already
exists at this project's root — point to `/project import ... force`
instead. Otherwise run the instantiation procedure
(`INSTANTIATION-GUIDE.md`): resolve `agent-source` (`BOOTSTRAP.md` §1),
build the working copy there, then write `<app-name>.catalyst` from
`templates/catalyst-pointer.template.json` with `<project name>` and the
resolved `agent-source`. Report the result; per hard rule 4, nothing is
committed automatically.

When the user enters `/project remove <project name> [force]: ...`,
without `force`: delete this project's `<app-name>.catalyst` (and, on
the in-project fallback, stop treating that `.catalyst-proj/` as active)
— nothing else. The working copy at `agent-source`, this agent's memory
note, and any `thingamabob` repo are left exactly as they are (never
delete, retire in place — `Rules-of-Rules.md` §14). With `force`: this is
externally-visible within this agent's own state and hard to reverse, so
confirm explicitly with the user first, distinct from the general assent
already implied by invoking this command; then additionally delete the
working copy at `agent-source` and this agent's memory note for the
project. Never delete a `thingamabob` repo — that is a separate,
possibly multi-contributor, externally-hosted artifact outside a local
removal's scope, regardless of `force`.

When the user enters `/project export <project name> [export filename]:
...`, resolve `agent-source` for `<project name>` and read every file
under its working copy into one JSON bundle keyed by path relative to
`.catalyst-proj/`, plus the pointer fields from `<app-name>.catalyst`
(all but `agent-source`, which is meaningless outside this machine).
Write it to `<export filename>` if given, else
`<project name>-catalyst-export-<UTC timestamp>.json` in the current
directory. Report the result.

When the user enters `/project import <export filename> [force]: ...`,
without `force`: refuse if a `<app-name>.catalyst` pointer or an
in-project `.catalyst-proj/` already exists at the current project's
root — point to the `force` form instead. Otherwise (or with `force`,
after confirming explicitly with the user what will be overwritten):
parse the bundle, resolve a **fresh** `agent-source` (never the
exporting machine's original), materialize every bundled file there,
then write `<app-name>.catalyst` carrying the bundle's pointer fields
over as-is (`repoed`, `catalyst_repo`, `catalyst_repo_url`,
`created_by`) with `agent-source` set to the new location. Append one
journal entry for the import (`action: "import"`), then report the
result.

When the user enters `/status <artefact-id> <status> [force]`, update the
artifact's `Status` field. If the supplied status is one of the valid statuses
for that artifact type, change it normally. If the status is invalid and the
command includes the word `force`, change it to that invalid value anyway. If
the status is invalid and `force` is not supplied, respond that the status
change is impossible and do not modify the artifact. If the artifact ID does
not resolve to an existing artifact, state that the artifact cannot be found.

Each plugin must be defined by the following minimum metadata fields: `name`,
`description`, `uuid`, `version`, `active`, and `type`. The plugin definition
template must be updated to include these fields and to record the plugin's
current state in the framework. The framework must read the plugin's
`active` flag at startup and activate only the plugins marked active; this is
mandatory and must not be bypassed. All plugin-specific functionality,
operational guidance, and implementation details must live inside the plugin
package itself; the framework only defines the interface and lifecycle contract.

When the user enters `/audit <file-name>`, inspect the repository and the
current framework state to determine the impact of changes against the named
file. The command must identify whether the file is a rule, template,
artifact, plugin contract, or other framework asset; inspect related indexes,
references, and dependent artifacts; and return a concise summary of likely
impact, affected areas, and any blocking concerns. If the file cannot be
resolved, report that it was not found and do not invent a result.

When the user enters `/run-analysis`, open and execute the analysis playbook
from `ANALYSIS-PLAYBOOK.md` in the project root, following its steps and
returning the resulting analysis summary. If the playbook is missing, report
that it is unavailable and do not invent missing content.

When the user enters `/sync-framework [latest|<version>] [--force <scope>]`,
inspect the requested framework version, compare it with the deployed
framework, and synchronize any missing or outdated files and version
information. If the first argument is `latest`, resolve the newest available
framework version from the framework source. If no version argument is
provided, synchronize against the currently installed local version. Before
synchronizing an item, check the root-level `.frozen` file. If the item's
path is listed there, skip it unless the command includes one of the valid
overrides: `--force <type>`, `--force <item-id>`, or `--force all`. When an
item is refreshed during the synchronization process, it must not remain in
`.frozen`; remove it from the list so the refreshed version no longer carries
the frozen protection. Synchronization must never deactivate an
already-active plugin as a side effect of a framework version change: a
plugin stays active across the sync unless its entry in the relevant
`plugins/<type>/catalog.md` explicitly excludes the target framework
version via the `Compatibility` field — a bare `*`, or an absent field, is
never grounds for deactivation. Only when that field names a version or
range that excludes the target version may the synchronization process
deactivate the plugin, and it must then report which plugin was deactivated
and why. Synchronization must also never treat a deployed project's
`plugins/<type>/catalog.md` or any installed plugin directory under
`plugins/<type>/<name>/` as framework template content to overwrite
wholesale: once a project has registered or activated any plugin, that
catalog and those directories are project-owned state, so synchronization
may only merge into `catalog.md` — adding rows for newly available plugins
not yet present, and refreshing the pinned `Release`/`Tag`/`Compatibility`
columns of a row that already exists — and must never delete an existing
row, blank the file, or delete or replace an installed plugin's directory
contents. A missing row or directory is something the user resolves
afterward via `/catalyzer activate` or `/catalyzer download`, never
something `/sync-framework` performs or silently corrects on its own. After
the refresh completes, perform a four-eyes
verification pass: one sub-agent verifies the newly deployed framework against
`INSTANTIATION-GUIDE.md` and the framework rules, and a second independent
sub-agent repeats the verification from a separate pass. The sync is not
complete until both sub-agents approve the deployment; any disagreement or
failed validation becomes a blocking issue.

When the user enters `/check-rules`, inspect the deployed framework for
missing rule targets, conflicting domains, missing indexes, and broken links,
then report the result.

When the user enters `/commands list [--filter ...]`, list every slash
command available in this deployment — name, one-line purpose — sourced
from this document's §4 (the canonical list; never re-enumerate a
subset). Apply `--filter` the same way `/list` does. If this session is
working on catalyst's own repository (`development-framework/` present
at the root) rather than a deployed project, also list
catalyst-development-only commands that exist there but aren't part of
this deployed set — `/dogfood` (see that repo's own `.claude/commands/`)
is the current example.

When the user enters `/show-backlog`, inspect the current artifact indexes
(open bugs by severity, in-progress/proposed requirements, work items with no
linked `REQ-`/`BUG-` doc, rules with no open work targeting them, feature
ideas with no requirement yet, and every `development/roadmaps/<name>.md`
not marked `Retired`, rows grouped by roadmap name then Status),
**overwrite `development/BACKLOG.md` in full** with the result (from
`templates/backlog.template.md`'s structure, with a refreshed timestamp),
**also refresh every active `development/roadmaps/<name>.md`** in place —
for each `RM-NNNNNN` row, resolve whichever `FEAT-`/`REQ-` its `Linked` field
names (if any) and set `Status` to `Not triaged` / `Triaged` /
`In progress` / `Done` accordingly, leaving `Title`/`Notes`/`Source`
untouched — and also report the same summary to the user in this turn. No
file write is optional — a stale `BACKLOG.md`, or any roadmap file that
doesn't match the last `/show-backlog` run, is itself a bug in the
deployment.

When the user enters `/journal [--since <date>] [--artifact <id>]
[--actor <name>] [--rule <id>]`, read `development/journal.jsonl` (one
JSON object per line) and apply whichever filters were given — `--since`
on `timestamp`, `--artifact` on `artifact`, `--actor` on `actor`,
`--rule` on membership in `targets`. Report the matching entries in
timestamp order: what changed, who, which command, which rule(s), and
each entry's `intent`. If the journal doesn't exist or is empty, say so
rather than inventing history. This command never appends to the journal
itself.

When the user enters `/journal-restore <timestamp>`, read
`development/journal.jsonl` and, for every file path that appears in any
entry with `timestamp <= <timestamp>`, take that path's `after` hash from
its latest such entry (skip the path entirely if that latest `after` is
`null` — the file didn't exist at that point). Materialize each into a
new side directory (e.g. `.catalyst-proj/.journal-restore/<timestamp>/`)
via `git cat-file -p <hash>` — **never write into the live working
tree**. Report the side directory's path and which files it contains. If
a referenced hash isn't retrievable from the git object store (was never
written with `-w`, or the repository was pruned), report that file as
unrecoverable rather than silently omitting it.

When the user enters `/help` without any additional entry, run `/commands
list` for the command listing rather than re-describing it, then list
every artifact type and its purpose in a compact reference format. When
the user enters `/help <command>`,
return the detailed help documentation for that command only, including its
syntax, behavior, and prerequisites. If the command is unknown, respond that
it is unsupported and suggest the available commands.

## 5. Domain field

Every item's `Domain` field is the `DOMAIN` code of the rule(s) it targets,
from `{{RULES_DIR}}/domains/` — not free text. (Feature entries under
`features/` are not development artifacts under this document and carry no
`Domain` field — see `Rules-of-Rules.md` §9.)

## 6. Development-artifact IDs

Per `Rules-of-Rules.md` §5: `(BUG|REQ|HK)-(NNNNNN)`, global per type,
sequential, zero-padded 6 digits, never reused. Meta-tags use a file-name
pattern of `tag-<key>-<artefact-id>` rather than a sequential numeric ID.
This is a hard requirement for all new artifacts and work items: every item
name must be more than the bare ID and must follow the format
**`<artifact-id>-<short-summary>`**. The corresponding markdown filename must
also follow the same descriptive pattern as
**`<artifact-id>-<short-summary>.md`**, not simply `<artifact-id>.md`.
Example: `BUG-000001-login-form-validation` or
`BUG-000001-login-form-validation.md`, and `REQ-000002-password-reset-flow` or
`REQ-000002-password-reset-flow.md`. The same rule must be applied
retroactively during framework deployment or synchronization to existing
deployed items whose names or filenames are still only the ID.

## 7. Closing an item

Before closing a bug or requirement, ensure the corresponding entry exists in
its individual file and is reflected in the relevant index file.

- **Bug**: not closeable as "fixed" without its test-plan item landing.
- **Requirement**: not closeable as "done" until the acceptance criteria and
  rule targets are reflected in the implementation and tests.
- **House-keeping**: closeable once its stated verification passes.

## 8. Retired rules and development work

Retiring a *rule* is `Rules-of-Rules.md` §4's process — status marker to
🗑, reason plus date appended, ID never reused. Closing a *dev-artifact*
(`BUG-`/`REQ-`/`HK-`) as `wontfix`/`rejected`/`abandoned` is independent
of that: closing an artifact never retires the rule(s) it targeted, and
retiring a rule never auto-closes the artifacts that cite it. Each is
closed on its own, citing the other's ID and the reason, so the history
stays traceable in both directions rather than one silently orphaning the
other.

## 9. Journaling

`development/journal.jsonl` is an append-only, transaction-log-grade
record — see `Rules-of-Rules.md` §12 for the full entry schema (exact
before/after `git hash-object -w` content pointers per file, one or more
`intent` statements, the `targets` rule IDs) and the point-in-time
restore mechanism (`/journal-restore`, materializes a reconstructed tree
into a side directory — never overwrites the live tree).

**Every command in §4 that creates, modifies, closes, or retires a
rule-linked artifact, rule, domain, or work item, or changes a `Status`
field, appends exactly one journal entry as its last step** — after
everything that command's own section above already specifies, not
instead of any of it. Concretely: resolve each touched file's `before`
hash before editing it, make the edit(s), compute and write each file's
`after` hash, then append one entry covering every file the command
touched. Entries are immutable — never edited, deleted, or reordered
afterward, the same "never delete, retire in place" principle as a
retired rule (`Rules-of-Rules.md` §4) applies here in its strictest
form: nothing about a written entry ever changes, period.

Two read-only commands operate on the journal without writing to it
themselves: `/journal [--since <date>] [--artifact <id>] [--actor <name>]
[--rule <id>]` reconstructs/filters the history for review, and
`/journal-restore <timestamp>` materializes the tree as it stood at that
point into a side directory for inspection.

This is core framework infrastructure, distinct from the `catalyst-git`
plugin's continuous rule-compliance auditing of a *deployed* project
(`INVARIANTS.md` INV-13) — the journal applies to catalyst's own
self-deployment too, and answers "what changed, why, and can I get back
to how it was," not "did anything just break a rule."
