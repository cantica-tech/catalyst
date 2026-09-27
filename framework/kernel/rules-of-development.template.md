# Rules of Development — template

> Copy to `CODE-OF-CONDUCT.md` in the project root and resolve every
> `{{PLACEHOLDER}}`. See [`INSTANTIATION-GUIDE.md`](INSTANTIATION-GUIDE.md).

Standards for how development work — the active module's development
artifacts and meta-tags — gets proposed, tracked, and closed. Subordinate to
[`{{RULES_DIR}}/Rules-of-Rules.md`]({{RULES_DIR}}/Rules-of-Rules.md):
that file governs the rules themselves; this file governs the work items
that reference those rules.

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

## 2. Users, roles, and signing

`IAM/users/users.json` is a JSON array of registered users
(`{name, roles, registered, active, notes, userid}`, plus `git_username`
once a repoed deployment resolves it — `Rules-of-Rules.md` §13), managed
only by
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
2. Look up that name in `IAM/users/users.json`. If unregistered, proceed
   anyway, noting that the signer isn't registered — `/user-add` can
   register them properly as a follow-up, but doesn't gate this write.
3. Look up their role(s) in `IAM/roles/roles.json` and check whether the
   action being performed is one that role covers. If it isn't, proceed
   anyway — never refuse outright — noting the mismatch.
4. Fill the artifact's `Signed-off-by` field with the user's name
   (carrying forward any unregistered-signer or role-mismatch note from
   steps 2-3) and proceed.
5. Allocate the entity's ID with `catalyst id next <PREFIX> --as <signer>`
   (`CLI.md`), which carries that signer's `userid` as its suffix
   (`Rules-of-Rules.md` §20, INV-26) — the same moment, never a separate
   step done later. Always pass the signer confirmed in step 1 as `--as`;
   the CLI's own fallback to the git identity is not a confirmation. If
   the signer has no `userid` yet (unregistered, or registered before
   INV-26 existed), register them first (`/user-add`); the CLI refuses to
   allocate a suffixed ID ahead of its signer.

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
Every command that creates or changes an artifact, rule, domain or
`Status` ends the same way, after its own steps below:

1. `catalyst index regen` — rebuild every entity index from the files.
2. `catalyst journal append --command /<name> --action <action>
   --artifact <id> [--target <rule-id> ...] --intent "<goal>"
   --file <path> ...` — one entry covering every touched file (§9).
3. `catalyst check` — unless the agent's end-of-turn hook already runs
   `catalyst hook stop`; resolve every error before reporting.

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
- `/role-add <role> <actions>` — add a new role entry to
  `IAM/roles/roles.json`. Refuses if `<role>` already exists — use
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
- `/criterion create <name> <git-info>` — bootstrap a repoed deployment
  (`Rules-of-Rules.md` §13, `INVARIANTS.md` INV-18): register or create
  the dedicated repo (confirm explicitly first if `<git-info>` already
  has *unrelated* content — a different deployment's own state, not a
  rejoin of this one), then ask which branch this actor will push to and
  record it as `criterion_branch` in `<app-name>.catalyst`, then push
  local `.criterion/` as the first commit on its `criterion`
  branch. Also resolves the current actor's `git_username` and migrates
  their prior `Signed-off-by` occurrences to it (never the journal — see
  §9/§13). Called again against the same repo with a different `<name>`,
  branches instead of refusing: a new branch off `criterion`, named
  `<name>` in its branch-safe form.
- `/criterion get <repo> <username>` — join an already-repoed
  deployment: download `<repo>`'s `criterion` branch and check out
  `<username>.criterion` (branch-safe form) from it as this user's
  local `.criterion/` (in the running agent's owned location, linked by
  the gitignored `.criterion` symlink — INV-6). `<username>` is this user's `git_username`,
  same identity-migration treatment as `create`. Also asks which branch
  to push to and records `criterion_branch`, same as `create`.
- `/criterion push [--force]` — refuses if not yet repoed (point to
  `/criterion create`), or asks for and records `criterion_branch`
  first if this deployment predates that field. If `criterion_branch`
  is a real contributor branch (the default —
  `<git_username>.criterion`, or the branch-safe form of `name`):
  vet the pushed state against `criterion` (`/check-rules` + a
  four-eyes sub-agent pass), AI-merge where a plain merge can't resolve
  it, update both branches, and refresh the local `.criterion/` to
  match; `--force` skips vetting for this one push and overwrites
  `criterion` directly anyway — refused for anyone but the repo's
  `created_by` user. If `criterion_branch` **is** `criterion`
  itself (single-maintainer mode, e.g. catalyst's own self-dogfooding):
  every push overwrites `criterion` directly, no vetting, no merge —
  the normal behavior in this mode, not a `--force`-only shortcut —
  still refused for anyone but `created_by`. After a `/dogfood` run that
  ends clean or ends with fixes applied and reverified, offer this
  command (`create` if not yet repoed, `push` otherwise) as the natural
  next step — never run it automatically.
- `/reconcile <RECON-id> accept|accept-with-edits|reject|propose <text>`
  — resolve, or move toward resolving, an open reconciliation case
  (`Rules-of-Rules.md` §16, `INVARIANTS.md` INV-21): `accept` merges its
  `Proposed` content into the `Entity` it names as-is, `accept-with-edits`
  appends a new `Revisions` row first and merges that instead, `reject`
  leaves `criterion` unchanged and flags the proposer's local copy for
  reverting — each sets `Status` to the matching `Resolved-*` value,
  fills `Resolved`/`Resolver`, and regenerates
  `reconciliations/reconciliations.md` (`catalyst index regen`). `propose <text>` instead appends
  `<text>` as a new `Revisions` row and moves `Status` to `Under Review`
  without resolving anything. **Genuinely role-gated, not advisory**: the
  actor's `reconciliation` field in `IAM/roles/roles.json` must be `full`
  for the three resolving verbs — `propose`-level actors may only use
  `propose`, and `none`-level actors are refused on any verb. If the case
  names a `Workflow` (`WORKFLOW-NNNNNN`, `Rules-of-Rules.md` §19), read
  its `## Steps`/`## Gates / exit criteria` before choosing a verb.
- `/project create <project name>` — install a fresh catalyst deployment
  here (`Rules-of-Rules.md` §14): resolve the agent-owned location,
  build the working copy there, write `<app-name>.catalyst` at this
  project's root (no path in it), create the `.criterion` symlink, and
  gitignore `/.criterion`. Refuses if a deployment already exists here.
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
- `/switch-agent [agent-id]` — force the agent-switch procedure (hard
  rule 6, `BOOTSTRAP.md` §1.1, `Rules-of-Rules.md` §14's Agent switching
  procedure) to run now, regardless of whether the running agent's
  identity already appears to match `<app-name>.catalyst`'s `agent`
  field. The manual escape hatch for when the automatic per-session
  check is skipped or only partially completes (e.g. the working copy
  already mirrored but the pointer's `agent` field never updated to
  match). Resolves the owned location of `<agent-id>` (defaulting to the
  running agent's own identifier if omitted) per `BOOTSTRAP.md` §1,
  mirrors `.criterion/` into it if it existed elsewhere (exact copy,
  overwriting the destination — never a partial merge), repoints the
  `.criterion` symlink, updates `<app-name>.catalyst` (`agent`,
  `updated`) unconditionally, and refreshes persistent framework memory.
  No `Taskfile.yml` edit: it reaches the working copy through the
  symlink.
- `/status` — update an artifact or work item's `Status` field, then
  regenerate indexes and journal the change.
- `/audit <file-name>` — analyze the change-impact of the specified file by
  checking the current repository state, the file's role in the framework,
  and the rules or artifacts that depend on it, then return a concise impact
  summary.
- `/run-analysis` — open and execute the analysis playbook from
  `ANALYSIS-PLAYBOOK.md` in the project root, following its steps and
  returning the resulting analysis summary.
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
`roles: [<role>]`, `userid`) and report it. If this is the
project's first registered user, note that the hard "at least one active
user" requirement (§2) is now satisfied.

When the user enters `/user-remove <name>`, refuse with a clear message if
`<name>` has no entry in `IAM/users/users.json`. If `<name>` is the only
`active: true` entry, refuse — this would leave the project with zero
active users (hard rule, §2, INV-25's fundamental-invariant exception to
acting without asking) — and point at `/user-add` for a replacement
first. Otherwise set that entry's `active`
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
`IAM/roles/roles.json` doesn't exist yet, create it from the
deployment's own current `IAM/roles/templates/TEMPLATE-ROLES-vN.json`
first. Otherwise append a new entry
(`name: <role>`, `actions: <actions>`) and report it.

When the user enters `/role-modify <role> <actions>: ...`, refuse with a
clear message if `<role>` has no entry in `IAM/roles/roles.json` (point
to `/role-add`). Otherwise replace that entry's `actions` and report the
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

When the user enters `/criterion create <name> <git-info>: ...`: if
`.criterion/DEPLOYMENT.md` doesn't yet show `repoed: true`, this is the first-call
bootstrap — check whether `<git-info>` already exists: if it does,
inspect its content before registering it as-is — if it's genuinely this
same deployment's own prior state (a real rejoin), proceed; if it holds
*unrelated* content (a different project's own `.criterion/`
deployment), that's not a rejoin, stop and confirm explicitly with the
user before doing anything, the same tier of confirmation as creating a
new repo; if `<git-info>` doesn't exist yet, create it there under
`<name>` — this is an externally-visible, hard-to-reverse action, so
confirm with the user before creating it, distinct from the general
push-assent already implied by invoking this command. Write `repoed:
true`, `catalyst_repo: <name>`, `catalyst_repo_url: <git-info>`,
`created_by: <the current Signed-off-by actor>` to
`.criterion/DEPLOYMENT.md`, **ask which branch this actor will push
to** — the actor's own `<branch-safe-name>.criterion` is the
suggested default, but `criterion` itself is a valid choice too (see
`/criterion push` below for what that changes) — and write the answer
as `criterion_branch` in both `.criterion/DEPLOYMENT.md` and
`<app-name>.catalyst`. Then push the current local `.criterion/`
state as the first commit on a `criterion` branch there. Nothing is
vetted on this first push. If `.criterion/DEPLOYMENT.md` **already**
shows `repoed: true`: don't refuse — if `<git-info>` matches the
registered `catalyst_repo_url`, create a new branch off `criterion`'s
current state named `<name>` in its branch-safe form (§13) and stop
there (no repo mutation, no `.criterion/DEPLOYMENT.md` change); if `<git-info>`
names a different repo, confirm explicitly with the user before doing
anything, since that's an unusual second-repo scenario rather than
ordinary branching. On the first-call path only, also run the identity
migration below, then report the result.

When the user enters `/criterion get <repo> <username>: ...`, validate
`<username>` against the branch-safe-name rule (§13) — refuse with a
suggested alternative if it doesn't survive sanitization uniquely against
already-registered users. Download `<repo>`'s `criterion` branch content
and check out `<username>.criterion` (branch-safe form) from it as
this user's local `.criterion/` — in the running agent's owned location
(`BOOTSTRAP.md` §1), then create or repair the `.criterion` symlink at
the project root and make sure `/.criterion` is gitignored (INV-6) —
creating a `IAM/users/users.json`
entry for them first if one doesn't already exist. **Ask which branch
this actor will push to**, same as `create` above (the just-created
`<username>.criterion` is the default), and record
`criterion_branch`. Then run the identity migration below for this
user, and report the result.

**Identity migration** (part of both `/criterion create`'s first call
and `/criterion get`): set `git_username` on the current user's
`IAM/users/users.json` entry to their resolved git identity (`git
config user.name`, branch-safe form, for `create`; the given `<username>`
for `get`). Rewrite every existing artifact's `Signed-off-by` field that
currently names this user's old `name` to their new `git_username` —
from this point on, every `Signed-off-by`/journal `actor` written for
them uses `git_username`, never `name`. **Never rewrite the journal
itself** (`Rules-of-Rules.md` §12, INV-17 — entries are immutable, no
exception for this either); instead append one new entry with
`catalyst journal append --action update` (`intent` describing the
migration) covering every artifact file actually rewritten.

When the user enters `/criterion push [--force]`, refuse with a clear
message if `.criterion/DEPLOYMENT.md` doesn't show `repoed: true` (point to
`/criterion create`). If no `criterion_branch` is recorded yet (a
deployment from before this field existed), ask now — same question as
`/criterion create`'s — and record the answer before continuing.

**If `criterion_branch` names a real contributor branch**
(`<git_username>.criterion` if the actor has one, otherwise the
branch-safe form of `name`): push local `.criterion/` there in the
repoed repository (creating that branch on their first push), **scoped
to artifact files whose `Signed-off-by` names the current actor** —
check the actor's `roles` array in `IAM/users/users.json` against
`IAM/roles/roles.json`; if it includes the `Admin` role, skip scoping
and push everything. Otherwise leave out any artifact file signed by
someone else, and report which files (if any) were excluded and why.
Shared registries/indexes (`rules.md`, every entity type's own index
file, any regenerated summary document the active module defines,
`IAM/users/users.json`,
`IAM/roles/roles.json`) and the journal aren't signed by one person and
are never filtered by this rule. This scopes what gets pushed; it never
refuses the command outright. If `--force` is given: refuse unless the
current actor matches
`.criterion/DEPLOYMENT.md`'s `created_by`; otherwise confirm with the user, then
overwrite `criterion` directly from local state and skip everything
below. Otherwise: (1) vet the incoming branch against `criterion` —
`/check-rules` plus an independent four-eyes sub-agent pass checking
whether the incoming state still matches what its own rules claim;
disagreement between the two sub-agents, or a flagged violation, stops
here rather than proceeding silently; (2) merge —
attempt a normal merge first, and only where that leaves a conflict
(git-level, vetting-flagged, or a rights-mismatch against the actor's
role in `IAM/roles/roles.json`), have a sub-agent propose a resolution
guided by `Rules-of-Rules.md` §1's conflict-check principle. Where
that's itself contested, or genuinely irreconcilable, open a
`RECON-NNNNNN` (ID from `catalyst id next RECON`) instead of guessing
which side wins (`Rules-of-Rules.md` §16, resolved later via
`/reconcile`) — that one entity stays unmerged,
everything else in the push proceeds; (3) update both `criterion` (the
merge commit) and the
contributor's own branch (fast-forwarded to match); (4) pull the updated
`criterion` down and overwrite the local `.criterion/` directory
and this session's in-memory record of it.

**If `criterion_branch` *is* `criterion` itself** (single-maintainer
mode): push local `.criterion/` state directly onto `criterion`,
overwriting it — every time, no vetting, no merge, not gated behind
`--force`. Still refuse unless the current actor matches
`.criterion/DEPLOYMENT.md`'s `created_by`. This is the expected mode
for catalyst's own self-dogfooding, offered as the natural follow-up
after a `/dogfood` run ends clean or ends with fixes applied and
reverified — `/dogfood`'s own four-eyes audit is what already vetted the
state, so repeating that check on push would be redundant.

Report the result either way.

When the user enters `/project create <project name>: ...`, refuse if a
`<app-name>.catalyst` pointer or an in-project `.criterion/` already
exists at this project's root — point to `/project import ... force`
instead. Otherwise run the instantiation procedure
(`INSTANTIATION-GUIDE.md`): resolve the agent-owned location
(`BOOTSTRAP.md` §1), build the working copy there, then write
`<app-name>.catalyst` from `templates/catalyst-pointer.template.json`
with `<project name>` (the pointer holds no path), create the
`.criterion` symlink at the project root pointing at the working copy
(or keep the in-project fallback directory), and add `/.criterion` to the
project's `.gitignore` if absent. Report the result; per hard rule 4,
nothing is committed automatically.

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
`catalyst_repo`, `catalyst_repo_url`, `created_by`), with no path. Journal
the import with `catalyst journal append --command /project --action sync`
covering the pointer and `.gitignore`, then report the result.

When the user enters `/status <artefact-id> <status> [force]`, update the
artifact's `Status` field. If the supplied status is one of the valid statuses
for that artifact type, change it normally. If the status is invalid and the
command includes the word `force`, change it to that invalid value anyway. If
the status is invalid and `force` is not supplied, respond that the status
change is impossible and do not modify the artifact. If the artifact ID does
not resolve to an existing artifact, state that the artifact cannot be found.
The valid statuses are the `Status` values the type's entity type
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

When the user enters `/run-analysis`, open and execute the analysis playbook
from `ANALYSIS-PLAYBOOK.md` in the project root, following its steps and
returning the resulting analysis summary. If the playbook is missing, report
that it is unavailable and do not invent missing content.

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
[--actor <name>] [--rule <id>]`, read `development/journal.jsonl` (one
JSON object per line) and apply whichever filters were given — `--since`
on `timestamp`, `--artifact` on `artifact`, `--actor` on `actor`,
`--rule` on membership in `targets`. Report the matching entries in
timestamp order: what changed, who, which command, which rule(s), and
each entry's `intent`. Paths in older entries may be bare
(working-copy relative), `<repo>:path` or absolute; read them as their
project-root-relative form (`Rules-of-Rules.md` §12). To report the
journal's integrity as well, run `catalyst journal verify`. If the journal
doesn't exist or is empty, say so rather than inventing history. This
command never appends to the journal itself.

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

Per `Rules-of-Rules.md` §5: `<PREFIX>-(NNNNNN)-(userid)`, where `<PREFIX>`
is one of the active module's rule-linked entity-type ID prefixes — global
per type, sequential, zero-padded 6 digits, never reused, plus the signer's
`userid` as a trailing suffix from the moment they're signed
(`Rules-of-Rules.md` §20, INV-26). The next ID comes from
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
agent's judgment goes into `--intent` and `--target`. Entries are immutable — never edited, deleted, or reordered
afterward, the same "never delete, retire in place" principle as a
retired rule (`Rules-of-Rules.md` §4) applies here in its strictest
form: nothing about a written entry ever changes, period.

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
