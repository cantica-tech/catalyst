# Rules of Development — template

> Copy to `CODE-OF-CONDUCT.md` in the project root and resolve every
> `{{PLACEHOLDER}}`. See [`INSTANTIATION-GUIDE.md`](INSTANTIATION-GUIDE.md).

Standards for how development work — the active module's development
artifacts and meta-tags — gets proposed, tracked, and closed. Subordinate to
[`{{RULES_DIR}}/Rules-of-Rules.md`]({{RULES_DIR}}/Rules-of-Rules.md):
that file governs the rules themselves; this file governs the work items
that reference those rules.

Documents cited by name that are not in this working copy — `CLI.md`,
`MODULE-SPECIFICATION.md`, `SYNCHRONIZE.md`, `INSTANTIATION-GUIDE.md`,
`FORMAT.md` and the like — are the catalyst kernel's, under
`framework/kernel/` in the `catalyst` repository.

---

## 1. No development without a targeted rule

**No rule-linked development artifact of the active module, and no
meta-tag, may start without citing one or more existing rule IDs in its
`Targets` field when the tag is
used to annotate a rule-linked artifact.** If no rule currently covers the
behavior in question:

1. Define the rule(s) first, as a normal edit to the relevant rule
document.
2. That definition must satisfy `Rules-of-Rules.md` §1 (conflict check)
and follow the ID scheme in §3.
3. Only then open the `<PREFIX>-NNNNNN` item, citing the new ID(s).

The active module may declare an entity type for which "no rule applies"
is a legitimate answer (pure repo hygiene with no bearing on any documented
behavior or process) — but it must be stated explicitly, not left blank.
Likewise, a change that alters no rule's behaviour at all may be a
**chore** (§9): no artifact, one journal entry whose empty `targets`
states explicitly that it serves no rule — when the active module defines
ceremony tiers (its §3 contribution).

## 2. Users, roles, and signing

`IAM/users/users.json` holds the registered users as a `users` array
(`{"users": [...]}` of `{name, roles, registered, active, notes, userid}`, plus an optional
`git_username`, the name `catalyst criterion push` commits under —
`Rules-of-Rules.md` §13), managed only by
`/user-add`/`/user-remove`/`/user-modify`/`/user-assign-role`/`/user-list`
— see §4. A `Signed-off-by` value resolves a user by `name`,
`git_username` or `userid`; one already written is never rewritten.
Each user has one or
more roles drawn from
`IAM/roles/roles.json`, a `roles` array (`{"roles": [...]}`) of
`{name, actions, reconciliation}` objects mapping each role to the
actions/commands it's expected to perform (`reconciliation`:
`Rules-of-Rules.md` §16). `roles.json` is seeded with a default
agile-role mapping (`IAM/roles/templates/TEMPLATE-ROLES-vN.json`) and
then extended via `/role-add` (new role) or `/role-modify` (change an
existing role's actions). Every command that writes either file journals
it (§4).

**This is JSON, not hand-edited markdown, precisely because it's managed
exclusively by commands** — the same reasoning that keeps
regenerated summary documents machine-only, just with structured data
instead of a regenerated document.

**Hard requirement: `IAM/users/users.json` must always have at least
one entry with `"active": true`.** A project with nobody registered has
nobody to sign work. `/user-remove` must refuse rather than silently
drop the last active user to zero — this specific case isn't advisory,
since it would break this hard requirement (INV-25's
fundamental-invariant exception to acting without asking).

**Beyond that one hard requirement, this role model is advisory, not an
access-control system, and per INV-25 it never pauses for authorization
either.** Catalyst has no way to verify who is actually typing, so a
role mismatch is noted, never a block or a confirmation prompt:

1. Before an artifact-creating or work-item-status-changing command
   completes, resolve who is signing it: the user established earlier
   this session, or ask if not yet established (don't guess from git
   config — confirm with the user).
2. Look up that name in `IAM/users/users.json`. If unregistered, register
   them first (`/user-add`): the CLI refuses an unregistered signer
   (`CLI.md`, "Signer").
3. Look up their role(s) in `IAM/roles/roles.json` and check whether the
   action being performed is one that role covers. If it isn't, proceed
   anyway — never refuse outright — noting the mismatch.
4. Fill the artifact's `Signed-off-by` field with the user's name
   (carrying forward any role-mismatch note from step 3) and proceed.
5. Allocate the entity's ID with `catalyst id next <PREFIX> --as <signer>`
   (`CLI.md`), which carries that signer's `userid` as its suffix
   (`Rules-of-Rules.md` §20, INV-26) — the same moment, never a separate
   step done later. Always pass the signer confirmed in step 1 as `--as`;
   the CLI's own fallback to the sole active user is not a confirmation.
   If the signer has no `userid` yet (registered before INV-26 existed),
   the CLI refuses to allocate a suffixed ID ahead of its signer.

Every development artifact of the active module and every work item
carries a `Signed-off-by` field for this reason (see each type's
template). It records who actually signed the artifact, which may differ
from who typed the command on their behalf.

## 3. Standard document types

The kernel defines one document type of its own; the active module's
document types are appended at the end of this section
(`MODULE-SPECIFICATION.md` §6.2).

| Type | Folder | Template | ID prefix |
|---|---|---|---|
| Meta-tag | `meta-tags/` | `templates/meta-tag.template.md` | `TAG-<KEY>-<ARTEFACT-ID>` |

The active module states, for each of its entity types, whether it is
rule-linked (bound by this document's rules — `Targets`, `Domain`, closed
against a rule) or exempt from them, and how its entity types relate to
one another.

### Hard rule: individual files and indexes

- **This is a hard requirement.** Every rule-linked development artifact
  of the active module, and every meta-tag, must be stored as its own
  individual markdown file in the corresponding folder, not only as
  free-form notes or grouped content.
- **This is also a hard requirement.** Every item must be listed in the
  corresponding type index file so the repository has an authoritative catalog
  of the concrete documents that exist.
- Each item directory must also contain an index file named after the item
  type — `<folder>/<folder>.md` for each of the active module's entity
  types, and `meta-tags/meta-tags.md` for the meta-tag index.
- These index files are the canonical indexes for their directory. Each
  entity type's index is regenerated from the artifact files with
  `catalyst index regen`, never edited by hand or merged; `meta-tags/meta-tags.md`,
  which is not an entity type's index, is kept by `/meta-tag`.
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

- **Meta-tag**: a lightweight annotation attached to an existing artifact.
  It stores one key/value pair whose key is one of `comment`, `version`, or
  `link-to`, and it is saved under the name `tag-<key>-<artefact-id>`.

## 4. Slash-command entry points

The framework exposes the following kernel slash commands. The active
module's commands are appended at the end of this section
(`MODULE-SPECIFICATION.md` §6.2); kernel and module entries together are
this deployment's canonical command list.

Mechanical steps are calls to the catalyst CLI (`CLI.md`), never
re-derived by hand. **`catalyst <args>`** is shorthand for
`python3 .criterion/bin/catalyst.pyz <args>` (or `task catalyst -- <args>`).
`catalyst spec <name>` prints one command's own bullet and procedure from
this section; command files read that instead of the whole document.
Every command that creates or changes an artifact, rule, domain or
`Status` ends the same way, after its own steps below:

1. `catalyst index regen` — rebuild every entity index from the files.
2. `catalyst journal append --command /<name> --action <action>
   --artifact <id> [--target <rule-id> ...] [--tier <tier>]
   --intent "<goal>" --file <path> ...` — one entry covering every touched
   file (§9).
3. `catalyst check` — unless the agent's end-of-turn hook already runs
   `catalyst hook stop`; resolve every error before reporting.

A product commit made for the change cites the artifact or rule it serves
(or its subject starts `chore:`) — §9, "Traced commits".

- `/user-add <name> <role>` — register a new user in
  `IAM/users/users.json` with an initial role from
  `IAM/roles/roles.json`. Refuses if `<name>` is already registered —
  use `/user-modify`/`/user-assign-role` instead.
- `/user-remove <name>` — set `<name>`'s `active` field to `false` in
  `IAM/users/users.json`. Never deletes the entry (see §2). Refuses if
  this would leave zero active users (hard rule, §2).
- `/user-modify <name> <field> <value>` — edit `<name>`'s `notes` or
  `active` field. Refuses for `roles` (use `/user-assign-role`) and for
  identity/audit fields (`name`, `registered`).
- `/user-assign-role <name> <role>` — add `<role>` to `<name>`'s `roles`
  array (additive; doesn't remove their other roles).
- `/user-list [--role <role>] [--active-only]` — list registered users,
  optionally filtered.
- `/role-add <role> <actions> [full|propose|none]` — add a new role
  entry, with its `reconciliation` level, to `IAM/roles/roles.json`. Refuses if `<role>` already exists — use
  `/role-modify` instead.
- `/role-modify <role> <actions>` — replace an existing role's `actions`.
  Refuses if `<role>` doesn't exist — use `/role-add` instead.
**`/create-epic`, `/create-story`, `/create-task`, `/create-spike`,
`/create-sprint`, `/create-board`, `/create-workflow` are not core
commands.** `work-items/` and its seven artifact types are
plugin-territory (`Rules-of-Rules.md` §8, INV-22) — these commands only
exist in a deployment once a project-management-type plugin extending
`plugins/_prototyping/project-management/agile/`'s schema is activated;
that plugin's own `working-contract.md` `## Contributes` section is
their spec, not this document. No concrete plugin exists yet, so none of
the seven currently exist anywhere.
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
- `/migrate-definition <entity-type> <version>` — the only way to move a
  deployed `definitions/<entity-type>.md` forward once it exists
  (`INVARIANTS.md` INV-23: ordinary `/sync-framework` never touches one
  that already exists). Refuses if `<entity-type>` isn't a real entity
  type, or if `<version>` doesn't exist for it in this framework's own
  `definitions/<entity-type>/` folder.
- `/catalyzer <subcommand>` — manage plugin installation and activation through
  the framework interface. Every subcommand resolves plugins against the
  registry file `framework/kernel/plugins/<type>/catalog.md` in catalyst's
  own repository (currently only `framework/kernel/plugins/repository/catalog.md`,
  since the repository type is the only
  plugin type defined at this time), which is the sole source of truth for
  which plugins are registered, their git repository URL, the release/tag
  that ships with the current catalyst release, and their kernel-version
  compatibility. Each catalog entry has a `Compatibility` field: a bare `*`
  means the plugin is compatible with every kernel version — the default
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
- `/criterion create [<url>] | get | push <message> | sync | status` —
  share this deployment's working copy through a criterion repository
  (`Rules-of-Rules.md` §13, `INVARIANTS.md` INV-18). Each subcommand is
  the matching `catalyst criterion` command (`CLI.md`); the agent adds
  only the judgment around it.
  - `create [<url>]` — turn a local-only deployment into a shared one: the
    working copy is pushed to `<url>` and `.criterion` becomes a
    submodule of the product repository. Without a URL, the working copy
    is versioned strictly locally (a git repository on the shared
    branch), and the first `push`, `sync` or `get` asks for the URL, then
    publishes before carrying on.
  - `get` — in a fresh clone of the product repository, check out the
    shared working copy (`catalyst criterion join`); a product with no
    `.criterion` submodule yet asks for the criterion repository's URL.
  - `push <message>` — land the working copy's changes as a pull request
    against the shared branch. A conflict stops it with nothing pushed.
  - `sync` — fast-forward to the shared branch; refuses while local work
    is uncommitted or unpushed.
  - `status` — where the working copy stands against the shared branch.
  After a `/dogfood` run that ends clean or ends with fixes applied and
  reverified, offer this command (`create` if not yet shared, `push`
  otherwise) as the natural next step — never run it automatically.
- `/reconcile <RECON-id> accept|accept-with-edits|reject|propose <text>|close`
  — resolve, or move toward resolving, an open reconciliation case
  (`Rules-of-Rules.md` §16, `INVARIANTS.md` INV-21): `accept` merges its
  `Proposed` content into the `Entity` it names as-is, `accept-with-edits`
  appends a new `Revisions` row first and merges that instead, `reject`
  leaves the shared branch's version unchanged and the proposer drops or
  reworks their change — each sets `Status` to the matching `Resolved-*` value,
  fills `Resolved`/`Resolver`, and regenerates
  `reconciliations/reconciliations.md` (`catalyst index regen`). `propose <text>` instead appends
  `<text>` as a new `Revisions` row and moves `Status` to `Under Review`
  without resolving anything. `close` moves a `Resolved-*` case to
  `Closed` once any accepted change has landed in the `Entity`; a
  `Closed` case is final (a dispute that returns opens a new case).
  **Genuinely role-gated, not advisory**: the
  actor's `reconciliation` field in `IAM/roles/roles.json` must be `full`
  for the three resolving verbs and `close` — `propose`-level actors may only use
  `propose`, and `none`-level actors are refused on any verb. If the case
  names a `Workflow` (`WORKFLOW-NNNNNN`, `Rules-of-Rules.md` §19), read
  its `## Steps`/`## Gates / exit criteria` before choosing a verb.
- `/project create <project name>` — install a fresh catalyst deployment
  here, on this explicit request (`Rules-of-Rules.md` §14, INV-2): resolve
  the inputs, run `catalyst init` (working copy in agent-owned space,
  `<app-name>.catalyst` with no path in it, `.criterion` symlink,
  `/.criterion` gitignored). Refuses if a deployment already exists here.
- `/project remove <project name> [force]` — un-link the local
  `<app-name>.catalyst` pointer and `.criterion` symlink; the working
  copy, memory note, and any `criterion` repo are left untouched (retire
  in place). `force` additionally deletes the working copy and this
  agent's memory note for the project — confirm explicitly first; never
  touches a `criterion` repo.
- `/project export <project name> [export filename]` — bundle every file
  under the working copy, plus its pointer fields (never a path), into
  one JSON export. Default filename:
  `<project name>-catalyst-export-<UTC timestamp>.json`.
- `/project import <export filename> [force]` — install a bundle into
  the current project, in this agent's owned location, linked by a
  fresh `.criterion` symlink. Refuses if a deployment already exists here,
  unless `force` is given, in which case it overwrites the existing one
  — confirm explicitly first.
- `/switch-agent [agent-id]` — force the agent-switch procedure (INV-6,
  `Rules-of-Rules.md` §14's Agent switching procedure) to run now, regardless of whether the running agent's
  identity already appears to match `<app-name>.catalyst`'s `agent`
  field. The manual escape hatch for when the automatic per-session
  check is skipped or only partially completes (e.g. the working copy
  already mirrored but the pointer's `agent` field never updated to
  match). Resolves the owned location of `<agent-id>` (defaulting to the
  running agent's own identifier if omitted) per `Rules-of-Rules.md` §14,
  mirrors `.criterion/` into it if it existed elsewhere (exact copy,
  overwriting the destination — never a partial merge), repoints the
  `.criterion` symlink, updates `<app-name>.catalyst` (`agent`,
  `updated`) unconditionally, and refreshes persistent framework memory.
  No `Taskfile.yml` edit: it reaches the working copy through the
  symlink.
- `/status` — update an artifact or work item's `Status` field, then
  regenerate indexes and journal the change. Refuses a `RECON-` case:
  its `Status` changes only through `/reconcile` (role-gated).
- `/audit <file-name>` — analyze the change-impact of the specified file by
  checking the current repository state, the file's role in the framework,
  and the rules or artifacts that depend on it, then return a concise impact
  summary.
- `/run-analysis [<path>...] [--bootstrap|--incremental]` — analyse
  existing code to infer domains, rules and the defects where the code
  breaks a rule, with a four-eyes process: two independent blind passes,
  a reconciliation that accounts for every finding of both, and the
  user's decision on each finding (`ANALYSIS-PLAYBOOK.md`, an `ANALYSIS-`
  record, `catalyst analysis`). `--bootstrap` for a project with no rules
  yet; `--incremental` (the default) finds what existing rules miss.
- `/sync-framework [latest|<version>]` — synchronize the deployed framework
  with the requested kernel version. If the argument is `latest`, use the
  newest kernel version available from the framework source. If no argument
  is provided, synchronize against the currently installed local version.
- `/check-rules` — verify that rules, domains, and artifact links remain
  consistent and do not conflict: `catalyst check` for the mechanical
  checks, then the judgment ones.
- `/commands list [--filter ...]` — list every slash command available in
  this deployment (name, one-line purpose), sourced from this document's
  §4 — kernel and active-module entries alike. `/help` with no argument delegates here for its command listing
  rather than re-describing it.
- `/journal [--since <date>] [--artifact <id>] [--actor <name>] [--rule
  <id>]` — read-only: filter and report `development/journal.jsonl`
  entries. Never writes to the journal (see §9).
- `/journal-restore <timestamp>` — read-only: reconstruct the tree as it
  stood at `<timestamp>` into a side directory with
  `catalyst journal restore` (`Rules-of-Rules.md` §12). Never overwrites
  the live working tree.
- `/adopt [<commit>|<range>]` — list the product changes committed
  outside catalyst (`catalyst unrecorded`) and resolve each with the user:
  accept it into the journal (`catalyst journal adopt`) or reject it by
  reverting the commit (§9, "Changes made outside catalyst").
- `/help` — return help documentation for the framework or for a specific
  command when provided.

When the user enters `/user-add <name> <role>: ...`, refuse with a clear
message if `<name>` already has an entry in `IAM/users/users.json`
(point to `/user-modify`/`/user-assign-role`). If `IAM/users/users.json`
or `IAM/roles/roles.json` doesn't exist yet, create them from the
deployment's own current `IAM/users/templates/TEMPLATE-USERS-vN.json`
and `IAM/roles/templates/TEMPLATE-ROLES-vN.json` (the highest `N`
present). If `<role>` isn't one of the roles listed in
`IAM/roles/roles.json`, ask whether to use an existing role or run
`/role-add` for `<role>` first. Otherwise draw the new user's `userid`
with `catalyst userid gen` (never by hand — `Rules-of-Rules.md` §11,
INV-26), append a new entry (`registered`: today, `active: true`,
`roles: [<role>]`, `userid`), journal it (`catalyst journal append --command /user-add --action create --artifact "user <name>" ... --file IAM/users/users.json`) — plus `--file IAM/roles/roles.json` if it
was just created — and report it. If this is the
project's first registered user, note that the hard "at least one active
user" requirement (§2) is now satisfied.

When the user enters `/user-remove <name>`, refuse with a clear message if
`<name>` has no entry in `IAM/users/users.json`. If `<name>` is the only
`active: true` entry, refuse — this would leave the project with zero
active users (hard rule, §2, INV-25's fundamental-invariant exception to
acting without asking) — and point at `/user-add` for a replacement
first. Otherwise set that entry's `active`
field to `false` — never delete it, since existing `Signed-off-by`
references on already-signed artifacts must stay resolvable. Then
journal it (`catalyst journal append --command /user-remove --action update --artifact "user <name>" ... --file IAM/users/users.json`) and report the
result.

When the user enters `/user-modify <name> <field> <value>: ...`, refuse
with a clear message if `<name>` has no entry in `IAM/users/users.json`
(point to `/user-add`). Refuse if `<field>` is `roles` (point to
`/user-assign-role`) or `name`/`registered` (identity/audit fields, never
edited in place). Refuse if `<field>` is `active` set to `false` (point to
`/user-remove`, which also checks the "at least one active user" rule).
Otherwise update `<field>` to `<value>`, journal it (`catalyst journal append --command /user-modify --action update --artifact "user <name>" ... --file IAM/users/users.json`) and report the result.

When the user enters `/user-assign-role <name> <role>: ...`, refuse with a
clear message if `<name>` has no entry in `IAM/users/users.json` (point
to `/user-add`). If `<role>` isn't one of the roles listed in
`IAM/roles/roles.json`, ask whether to use an existing role or run
`/role-add` for `<role>` first. If `<name>`'s `roles` array already
contains `<role>`, say so and make no change. Otherwise append `<role>` to
that array, journal it (`catalyst journal append --command /user-assign-role --action update --artifact "user <name>" ... --file IAM/users/users.json`) and report the result.

When the user enters `/user-list [--role <role>] [--active-only]`, run
`catalyst list user` (`--filter roles=<role>`, `--filter active=true`) and
report what it prints; never add users it does not list.

When the user enters `/role-add <role> <actions>: ...`, refuse with a
clear message if `<role>` already has an entry in
`IAM/roles/roles.json` (point to `/role-modify`). If
`IAM/roles/roles.json` doesn't exist yet, create it from the
deployment's own current `IAM/roles/templates/TEMPLATE-ROLES-vN.json`
first. Otherwise append a new entry (`name: <role>`, `actions: <actions>`,
`reconciliation: <reconciliation>` — `full`/`propose`/`none`,
`Rules-of-Rules.md` §16; `propose` when not given, never silently
`full`), journal it (`catalyst journal append --command /role-add --action create --artifact "role <role>" ... --file IAM/roles/roles.json`) and report it.

When the user enters `/role-modify <role> <actions>: ...`, refuse with a
clear message if `<role>` has no entry in `IAM/roles/roles.json` (point
to `/role-add`). Otherwise replace that entry's `actions`,
journal it (`catalyst journal append --command /role-modify --action update --artifact "role <role>" ... --file IAM/roles/roles.json`) and report the
result. This never retroactively changes a `Signed-off-by` value already
recorded on an existing artifact.

The seven work-item creation commands (§4) have no procedure here —
they're plugin-contributed, not core; see whichever
project-management-type plugin's own `working-contract.md` is active.

When the user enters `/meta-tag <artefact-id>`, create a new meta-tag artifact
immediately, save it as `tag-<key>-<artefact-id>`, register it in
`meta-tags/meta-tags.md`, and link it to the specified artifact. If the key
is not supplied explicitly, prompt for it. A meta-tag is named by its key
and target, not numbered, so no ID is allocated; `meta-tags/meta-tags.md`
is not an entity index, so its row is added here rather than by
`catalyst index regen`. Then journal the change with
`catalyst journal append --command /meta-tag --action create ...`.

When the user enters `/list <type> [--filter ...]`, run `catalyst list
<type> [--filter ...]` (`--type <family>` for templates) and report what it
prints; an empty result stays empty.

When the user enters `/freeze <item-id|item-path|type|template-name>`, resolve
the item to its backing file path, append that path to the root-level
`.frozen` file if it is not already present, and report success. The item is
then protected from automatic framework synchronization until it is
explicitly removed from `.frozen` or re-synchronized with an override.

When the user enters `/migrate-definition <entity-type> <version>`, first
confirm `<entity-type>` names a real entity type (this framework's source
has a `definitions/<entity-type>/` folder for it — see `definitions/
README.md`'s "Entity types covered" list); if not, refuse and name the
valid types. Obtain this framework's current source content the same way
`/sync-framework` does (`SYNCHRONIZE.md`'s "Version rule" — the `release`
branch of the catalyst repository), and check whether `definitions/
<entity-type>/DEFINITION-<ENTITY-TYPE>-v<version>.md` exists there. If it
does not, refuse and report the highest version number that does exist for
that type instead of guessing or rounding to the nearest one. If it does,
overwrite the deployed `.criterion/definitions/<entity-type>.md` with that
exact version's content — this is the one and only way that file ever
changes once deployed, per `SYNCHRONIZE.md`'s definitions carve-out — and
report the old version number moving to the new one.

Every `/catalyzer` subcommand resolves plugin identity, repository URL, and
version information exclusively from the `catalog.md` registry of the
relevant plugin type in catalyst's own repository (e.g.
`framework/kernel/plugins/repository/catalog.md`); a plugin
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

When the user enters `/criterion create` without a URL: run `catalyst
criterion create` (`--branch <name>` only if the user wants a shared
branch other than `criterion`). Nothing leaves the machine: report what
it printed, offer to commit the staged pointer (INV-4), and say
that the first `/criterion push`, `sync` or `get` will ask for the
criterion repository's URL.

Whenever `catalyst criterion push`, `sync` or `join` fails because the
deployment has no criterion repository yet (its message names `--url`),
ask the user for the repository's URL — with the same confirmations as
`/criterion create <url>` below — and re-run the same command with
`--url <url>`: it publishes the working copy first (as `create <url>`
does), then carries on. Never invent or guess a URL.

When the user enters `/criterion create <url>`: confirm the user wants
this deployment shared, and that the criterion repository at `<url>`
exists (empty, or holding this working copy's own history) — creating it
on a hosting service is externally visible, so ask before doing it. Run
`catalyst criterion create <url>` (`--branch <name>` only if the user
wants a shared branch other than `criterion`). If it refuses because the
remote branch holds history the working copy lacks, report it: that is
someone else's work or another deployment, never something to overwrite.
Report the steps it printed, then offer to commit the product
repository's staged changes (`.gitmodules`, the `.criterion` gitlink,
the pointer, `.gitignore`) — never commit without assent (INV-4) — and
offer `catalyst criterion protect` (show its output, then `--yes` on
assent).

When the user enters `/criterion get`: in a clone of the product
repository, run `catalyst criterion join`. When the product has no
`.criterion` submodule yet it needs the criterion repository's URL (see
above): with `--url` it adds that repository as the submodule and stages
the product changes — offer to commit them (INV-4) — or, where this
machine holds the local working copy, publishes it there. If the joining person is not yet in
`IAM/users/users.json`, they register with `/user-add` (which draws their
`userid`) before signing anything, and land that registration with
`/criterion push` like any other change.

When the user enters `/criterion push <message>`: resolve the signer
(§2) and run `catalyst criterion push -m "<message>" --as <signer>`.
Report the pull request (or the branch to open one from). If the push
stops on a conflict, report the conflicting files and stop: nothing was
pushed. Never resolve the conflict by applying an edit of your own. You
may propose a resolution: open a `RECON-` case (`catalyst id next RECON
--as <signer>`, `Trigger: merge-conflict`, `Baseline` the shared
branch's version, `Proposed` your resolution — `Rules-of-Rules.md` §16),
then `catalyst index regen` and `catalyst journal append`, and leave it
for a human to decide with `/reconcile`. If `catalyst check` or the
integrity check fails, report the errors and fix them as ordinary work
before pushing again.

When the user enters `/criterion sync`: run `catalyst criterion sync`.
If it refuses, report why (uncommitted or unpushed work) and offer
`/criterion push`. Afterwards, offer to commit the moved `.criterion`
gitlink in the product repository, which pins the synced rules.

When the user enters `/criterion status`: run
`catalyst criterion status --fetch` and report it.

When the user enters `/adopt [<commit>|<range>]`: run `catalyst
unrecorded [<range>]` (every commit after the baseline by default) and
list each commit with its author and files. For each one, ask the user
whether to accept or reject it; never decide for them. To accept: read
the commit (`git show`), state its tier (chore, fix or feature, §1), do
what the active module requires for that tier (the artifact a fix or a
feature needs), then run `catalyst journal adopt <commit> --intent "<why
the change was made>" --tier <tier> [--target <ID>]` — oldest commit
first when adopting several, so each file's chain stays unbroken — and
`catalyst check`. To reject: propose `git revert <commit>` and run it only
with the user's assent (INV-4); the revert is itself a change to journal.
When the change is contested, or the actor may not decide it (their
`reconciliation` rights in `IAM/roles/roles.json`), open a `RECON-` case
instead (`Trigger: unrecorded-change`, `Entity` the commit and its files,
`Baseline` the parent's version, `Proposed` the commit's —
`Rules-of-Rules.md` §16) for a human to decide with `/reconcile`.

When the user enters `/project create <project name>: ...`, refuse if a
`<app-name>.catalyst` pointer or an in-project `.criterion/` already
exists at this project's root — point to `/project import ... force`
instead. Otherwise run the instantiation procedure
(`INSTANTIATION-GUIDE.md` §1): resolve the module, rule documents, first
user and agent-owned location (`Rules-of-Rules.md` §14), then run
`catalyst init --name <project name> ...`, which builds the working copy,
writes `<app-name>.catalyst` (no path in it), links `.criterion` (or keeps
the in-project fallback directory) and gitignores `/.criterion`; then the
guide's judgment steps. Report the result; per INV-4, nothing is
committed automatically.

When the user enters `/project remove <project name> [force]: ...`,
without `force`: delete this project's `<app-name>.catalyst` and its
`.criterion` symlink (on the in-project fallback, stop treating that
`.criterion/` as active) — nothing else. The working copy, this agent's
memory note, and any `criterion` repo are left exactly as they are (never
delete, retire in place — `Rules-of-Rules.md` §14). With `force`: this is
externally-visible within this agent's own state and hard to reverse, so
confirm explicitly with the user first, distinct from the general assent
already implied by invoking this command; then additionally delete the
working copy (agent-owned, or the in-project fallback) and this agent's
memory note for the project. Never delete a `criterion` repo — that is a separate,
possibly multi-contributor, externally-hosted artifact outside a local
removal's scope, regardless of `force`.

When the user enters `/project export <project name> [export filename]:
...`, resolve the working copy for `<project name>` (`Rules-of-Rules.md`
§14's resolution order) and read every file under it into one JSON
bundle keyed by path relative to `.criterion/`, plus the pointer fields
from `<app-name>.catalyst` (never a path — a legacy `agent-source`,
meaningless outside this machine, is dropped).
Write it to `<export filename>` if given, else
`<project name>-catalyst-export-<UTC timestamp>.json` in the current
directory. Report the result.

When the user enters `/project import <export filename> [force]: ...`,
without `force`: refuse if a `<app-name>.catalyst` pointer or an
in-project `.criterion/` already exists at the current project's
root — point to the `force` form instead. Otherwise (or with `force`,
after confirming explicitly with the user what will be overwritten):
parse the bundle, resolve this agent's own owned location on this
machine (never the exporting machine's), materialize every bundled file
there, create the `.criterion` symlink at the project root pointing at
it and gitignore `/.criterion`, then write `<app-name>.catalyst`
carrying the bundle's pointer fields over as-is (`repoed`,
`catalyst_repo`, `catalyst_repo_url`, `created_by`, `criterion_branch`), with no path. Journal
the import with `catalyst journal append --command /project --action sync`
covering the pointer and `.gitignore`, then report the result.

When the user enters `/status <artefact-id> <status> [force]`, update the
artifact's `Status` field. If the supplied status is one of the valid statuses
for that artifact type, change it normally. If the status is invalid and the
command includes the word `force`, change it to that invalid value anyway. If
the status is invalid and `force` is not supplied, respond that the status
change is impossible and do not modify the artifact. If the artifact ID does
not resolve to an existing artifact, state that the artifact cannot be found.
If it is a `RECON-` case, refuse even with `force` and point to `/reconcile`:
its role gate (`Rules-of-Rules.md` §16) is the only way a reconciliation's
`Status` changes. The valid statuses are the `Status` values the type's entity type
definition allows (a forced value outside them is reported by
`catalyst validate` as an `enum-value` warning). After the edit, run
`catalyst index regen` and
`catalyst journal append --command /status --action status-change ...`
(§4's common ending).

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
references, and dependent artifacts (`catalyst validate --json` resolves
every reference mechanically); and return a concise summary of likely
impact, affected areas, and any blocking concerns. If the file cannot be
resolved, report that it was not found and do not invent a result.

When the user enters `/run-analysis [<path>...] [--bootstrap|--incremental]`,
follow `.criterion/ANALYSIS-PLAYBOOK.md` (the deployed playbook) phase by
phase: `catalyst analysis start <path>... --mode <mode> --as <signer>`
(the whole project when no path is given), two independent passes with the
playbook's pass prompt recorded with `catalyst analysis record --pass A|B`,
`catalyst analysis diff`, a reconciliation recorded with `catalyst analysis
reconcile`, then each reconciled finding presented to the user — accept,
edit then accept, or reject; never decided for them. Only after acceptance,
write the domain, the rule (`catalyst id next-rule`) or the artifact a fix
requires (§3) targeting its rule, and record the decision with `catalyst
analysis decide --artifact <ID>`; research agents never write artifacts.
Close with `catalyst analysis close` and `catalyst check`, and report the
summary. Never skip a phase or hand-edit a report to get past the CLI: a
refused pass goes back to its agent. If the playbook is missing, report that
it is unavailable (`/sync-framework` restores it) and do not invent missing
content.

When the user enters `/sync-framework [latest|<version>] [--force <scope>]`,
inspect the requested kernel version, compare it with the deployed
framework, and synchronize any missing or outdated files and version
information. If the first argument is `latest`, resolve the newest available
kernel version from the framework source. If no version argument is
provided, synchronize against the currently installed local version. Before
synchronizing an item, check the root-level `.frozen` file. If the item's
path is listed there, skip it unless the command includes one of the valid
overrides: `--force <type>`, `--force <item-id>`, or `--force all`. When an
item is refreshed during the synchronization process, it must not remain in
`.frozen`; remove it from the list so the refreshed version no longer carries
the frozen protection. Synchronization must never deactivate an
already-active plugin as a side effect of a kernel version change: a
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
something `/sync-framework` performs or silently corrects on its own. The
refresh always replaces `.criterion/bin/catalyst.pyz` with the release's
`bin/catalyst.pyz`, then journals the sync with
`catalyst journal append --command /sync-framework --action sync` and
runs `catalyst check`. After
the refresh completes, perform a four-eyes
verification pass: one sub-agent verifies the newly deployed framework against
`INSTANTIATION-GUIDE.md` and the framework rules, and a second independent
sub-agent repeats the verification from a separate pass. The sync is not
complete until both sub-agents approve the deployment; any disagreement or
failed validation becomes a blocking issue.

When the user enters `/check-rules`, start with `catalyst check`: it
reports the mechanical findings — deployment structure, missing rule
targets and broken links (the chain), journal integrity, and stale or
missing index rows (`CLI.md` lists every code). Then do what only
judgment can: look for rules that conflict with one another
(`Rules-of-Rules.md` §1), domains that overlap or are misassigned, and
artifacts whose content no longer matches the rule they cite. Report
both parts; never hand-edit an index to clear a finding —
`catalyst index regen` does that.

When the user enters `/commands list [--filter ...]`, list every slash
command available in this deployment — name, one-line purpose — sourced
from this document's §4 (the canonical list; never re-enumerate a
subset). Apply `--filter` the same way `/list` does. If this session is
working on catalyst's own repository (`framework/` present
at the root) rather than a deployed project, also list
catalyst-development-only commands that exist there but aren't part of
this deployed set — `/dogfood` (see that repo's own `.claude/commands/`)
is the current example.

When the user enters `/journal [--since <date>] [--artifact <id>]
[--actor <name>] [--rule <id>]`, run `catalyst journal show` with the same
filters and report what it prints, in its order; for integrity too, run
`catalyst journal verify`. Never append to the journal.

When the user enters `/journal-restore <timestamp>`, run
`catalyst journal restore <timestamp> <side-dir>` with a new, empty side
directory (e.g. `.criterion/.journal-restore/<timestamp>/`) — it
materialises every journaled file as of that time and **never writes
into the live working tree**. Report the side directory's path and which
files it contains. Report every path the CLI lists as a missing blob as
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
from `{{RULES_DIR}}/domains/` — not free text. (An entity type the active
module declares exempt from this document's rules is not a development
artifact under this document and carries no `Domain` field.)

## 6. Development-artifact IDs

Per `Rules-of-Rules.md` §6: `<PREFIX>-(NNNNNN)-(userid)`, where `<PREFIX>`
is one of the active module's rule-linked entity-type ID prefixes —
sequential per type, zero-padded 6 digits, never reused, never renumbered,
plus the signer's `userid` as a trailing suffix from the moment they're
signed (`Rules-of-Rules.md` §20, INV-26). The number is unique per type and
signer: in a shared deployment two contributors may hold the same number
under different userids (`Rules-of-Rules.md` §6, §13). The next ID comes from
`catalyst id next <PREFIX> --as <signer>`, never from reading the index by
hand. Meta-tags use a file-name pattern of
`tag-<key>-<artefact-id>` rather than a sequential numeric ID. This is a
hard requirement for all new artifacts and work items: every item name
must be more than the bare ID and must follow the format
**`<artifact-id>-<short-summary>`**. The corresponding markdown filename must
also follow the same descriptive pattern as
**`<artifact-id>-<short-summary>.md`**, not simply `<artifact-id>.md`.
Example, for the `example-process` module's `ITEM` entity type
(`MODULE-SPECIFICATION.md`): `ITEM-000001-Ab3xR9pQ-login-form-validation`
or `ITEM-000001-Ab3xR9pQ-login-form-validation.md`. The same rule must be
applied retroactively during framework deployment or synchronization to existing
deployed items whose names or filenames are still only the bare ID.

## 7. Closing an item

Before closing a development artifact, ensure the corresponding entry
exists in its individual file and is reflected in the relevant index file
(`catalyst index regen`).
What each of the active module's entity types requires before it may be
closed — and with which terminal `Status` values — is defined by the
module, in its own §3 entries and entity definitions.

## 8. Retired rules and development work

Retiring a *rule* is `Rules-of-Rules.md` §4's process — status marker to
🗑, reason plus date appended, ID never reused. Closing a *dev-artifact*
(any rule-linked development artifact of the active module) as a terminal
negative status such as `wontfix`/`rejected`/`abandoned` is independent
of that: closing an artifact never retires the rule(s) it targeted, and
retiring a rule never auto-closes the artifacts that cite it. Each is
closed on its own, citing the other's ID and the reason, so the history
stays traceable in both directions rather than one silently orphaning the
other.

## 9. Journaling

`development/journal.jsonl` is an append-only, transaction-log-grade
record — see `Rules-of-Rules.md` §12 for the full entry schema (exact
before/after git blob pointers per file, project-root-relative paths, one
or more `intent` statements, the `targets` rule IDs, the `writer`) and the
point-in-time restore mechanism (`/journal-restore`, materializes a
reconstructed tree into a side directory — never overwrites the live
tree).

**Every command in §4 that creates, modifies, closes, or retires a
rule-linked artifact, rule, domain, or work item, or changes a `Status`
field, appends exactly one journal entry as its last step** — after
everything that command's own section above already specifies, not
instead of any of it. Concretely: make the edit(s), then run
`catalyst journal append` once, with a `--file` for every file the
command touched; it records each file's real `before`/`after` hashes and
pins the blobs. Entries are written only this way, never by hand, and the
agent's judgment goes into `--intent`, `--target` and `--tier`.

**Ceremony tiers.** `--tier chore|fix|feature` records how much ceremony a
change carries: a **chore** changes no rule's behaviour, a **fix** restores
a documented rule's behaviour, a **feature** adds or changes behaviour. The
agent picks the tier, states it to the user before starting, and escalates
(chore → fix → feature) if the change turns out bigger; when unsure, the
higher tier. A chore needs no artifact: its one entry has no `--target`
(`targets: []`), which says explicitly that it serves no rule. What a fix
and a feature require — which artifacts, which steps, which tests — is the
active module's, in its §3 contribution. A tiered change is journaled even
when no §4 command is involved: `--command` is then the tier itself
(e.g. `--command chore --action update --tier chore`). Entries are immutable — never edited, deleted, or reordered
afterward, the same "never delete, retire in place" principle as a
retired rule (`Rules-of-Rules.md` §4) applies here in its strictest
form: nothing about a written entry ever changes, period.

**Traced commits.** The chain reaches the product repository's history
too (INV-5): every product commit's message cites an artifact or rule ID
that resolves in this deployment — full (`<PREFIX>-NNNNNN-<userid>`,
`<doc-prefix>-<DOMAIN>-NNNNNN-<userid>`) or short (the same without the
userid) — or its subject starts `chore:` or `chore(<scope>):` when the
change is a chore. A fix or a feature cites its artifact; a commit that
only edits a rule cites the rule. Merge commits are not checked.
`catalyst hook commit-msg`, installed with `catalyst hook install` (with
the user's assent — it writes into `.git/hooks`), refuses an untraced
commit; `catalyst trace <range>` re-checks new commits in CI
(`--pattern-only` where CI has no working copy). The agent writes traced
messages itself and never bypasses the hook (`--no-verify`) without the
user's say-so. History from before the check was introduced is not
checked.

**Changes made outside catalyst.** A product change can also be written
by hand, straight into git, with no journal entry. Every journaled file
state is a git blob hash, so a product commit after the pointer's
`journal_since` baseline that changes a file to a state the journal did
not record as its latest state at that commit — a revert by hand to an
older journaled state included — is an **unrecorded change**. `catalyst
unrecorded` lists them; `catalyst check`, `catalyst trace` (CI) and the commit-msg hook (for
staged files) report them. They are warnings while the deployment's
format is a release candidate (the beta) and errors from format `1.0`, or
earlier when the pointer sets `"strict_journal": true`. Merge commits and
the working copy are not checked. An unrecorded change is resolved with
`/adopt`: accepted into the journal (`catalyst journal adopt`, which
records the commit with its git author as actor and `origin: manual`), or
rejected by reverting it. The agent never adopts or reverts a change on
its own: it lists them and asks. What an adopted fix or feature requires
beyond the journal entry is the active module's, as for any change of its
tier.

Two read-only commands operate on the journal without writing to it
themselves: `/journal [--since <date>] [--artifact <id>] [--actor <name>]
[--rule <id>]` reconstructs/filters the history for review, and
`/journal-restore <timestamp>` materializes the tree as it stood at that
point into a side directory for inspection (`catalyst journal restore`).
`catalyst journal verify` checks the hash chains, blobs and pins, and
flags any journaled file edited without an entry.

This is kernel infrastructure, distinct from the `catalyst-git`
plugin's continuous rule-compliance auditing of a *deployed* project
(`INVARIANTS.md` INV-13) — the journal applies to catalyst's own
self-deployment too, and answers "what changed, why, and can I get back
to how it was," not "did anything just break a rule."
