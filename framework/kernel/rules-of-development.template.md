# Code of Conduct — the command catalogue

> The kernel's command catalogue, composed into the criterion as
> `CODE-OF-CONDUCT.md` with the active module's types and commands inserted.

The commands of this deployment (§4), read one at a time: `catalyst spec
<command>` prints one command's entry and procedure, and the `catalyst mcp`
server serves each as a prompt. The rules behind them are the ten laws
(`INVARIANTS.md`, `catalyst why`) and the handbook (`rules/Rules-of-Rules.md`);
the sections around §4 point there and are kept so that their numbers stay
citable.

## 1. No development without a targeted rule

Work traces to an artifact and the artifact to a rule (law L2); a chore,
which changes no rule's behaviour, needs no artifact. The tier, and what
each tier needs: `Rules-of-Rules.md` §6 and the active module's part.

## 2. Users, roles, and signing

The signer is a registered user, declared with `--as` and confirmed when more
than one could sign — never guessed (`Rules-of-Rules.md` §11). Roles are
advisory, except for reconciliation (§16 there). The registry files:
`FORMAT.md` §6.

## 3. Standard document types

The kernel's own types are rules and domains (`rules/`), reconciliation
cases (`RECON-`), workflows (`WORKFLOW-`), analyses (`ANALYSIS-`), meta-tags
(`tag-<key>-<artefact-id>`, `development/meta-tags/`) and the user and role
registries (`IAM/`). Formats are in `FORMAT.md`, meanings in
`definitions/`. The active module's types follow.

## 4. Slash-command entry points

The framework exposes the following kernel slash commands. The active
module's commands are appended at the end of this section
(`MODULE-SPECIFICATION.md` §6.2); kernel and module entries together are
this deployment's canonical command list.

Mechanical steps are calls to the catalyst CLI (`CLI.md`), never
re-derived by hand. **`catalyst <args>`** is the launcher
(`$CATALYST_HOME/bin/catalyst <args>`; `CLI.md`, Invocation).
`catalyst spec <name>` prints one command's own bullet and procedure from
this section; the `catalyst mcp` prompts return that instead of the whole document.
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
  this would leave zero active users.
- `/user-modify <name> <field> <value>` — edit `<name>`'s `notes` or other
  descriptive fields. Refuses `roles` (use `/user-assign-role`), the
  identity fields `name`, `registered` and `userid`, and `active` set to
  false (use `/user-remove`).
- `/user-assign-role <name> <role>` — add `<role>` to `<name>`'s `roles`
  array (additive; doesn't remove their other roles).
- `/user-list [--role <role>] [--active-only]` — list registered users,
  optionally filtered.
- `/role-add <role> <actions> [full|propose|none]` — add a new role
  entry, with its `reconciliation` level, to `IAM/roles/roles.json`. Refuses if `<role>` already exists — use
  `/role-modify` instead.
- `/role-modify <role> <actions>` — replace an existing role's `actions`.
  Refuses if `<role>` doesn't exist — use `/role-add` instead.
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
  item from `/sync-framework` by recording its file path in the criterion's
  `.frozen` file. The command accepts one of four argument forms: an item
  ID, an item path, a type, or a template name.
- `/migrate-definition <entity-type> <version>` — the only way to move a
  deployed `definitions/<entity-type>.md` forward once it exists
  (`INVARIANTS.md` INV-23: ordinary `/sync-framework` never touches one
  that already exists). Refuses if `<entity-type>` isn't a real entity
  type, or if `<version>` doesn't exist for it in this framework's own
  `definitions/<entity-type>/` folder.
- `/share info | status | pull | push <message> | create <url> [--protect] | join [<url>]`
  — share this criterion through its sharing driver (`Rules-of-Rules.md`
  §13, `INVARIANTS.md` INV-18). Each subcommand is the matching
  `catalyst share` command (`CLI.md`); the agent adds only the judgment
  around it. `push` and `create` publish: they show what would leave and
  run only on the user's yes (law L3).
- `/reconcile <RECON-id> accept|accept-with-edits|reject|propose <text>|close`
  — decide, or move toward deciding, a reconciliation case
  (`Rules-of-Rules.md` §16, `INVARIANTS.md` INV-21) with `catalyst
  reconcile`, which enforces the signer's `reconciliation` level: `full`
  may use every verb, `propose` only `propose`, `none` none.
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
  <id>]` — read-only: filter and report the journal's
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

When the user enters `/user-add <name> <role>: ...`, run `catalyst user add
"<name>" "<role>" [--git-username <u>] --intent "<why>"`. It refuses a name
already registered and a role `IAM/roles/roles.json` lacks (then ask
whether to pick an existing role or `/role-add` it first), creates the IAM
files from their templates when missing, draws the userid (INV-26) and
journals. If this is the project's first registered user, note that the
"at least one active user" requirement (§2) is now satisfied.

When the user enters `/user-remove <name>`, run `catalyst user remove
"<name>" --intent "<why>"`: it deactivates, never deletes (signatures stay
resolvable), and refuses to deactivate the only active user (§2) — then
point at `/user-add` for a replacement first.

When the user enters `/user-modify <name> <field> <value>: ...`, run
`catalyst user modify "<name>" <field> "<value>" --intent "<why>"`. It refuses
`roles` (use `/user-assign-role`), the identity fields `name`/`registered`/
`userid`, and `active` set to false (use `/user-remove`).

When the user enters `/user-assign-role <name> <role>: ...`, run `catalyst user
assign-role "<name>" "<role>" --intent "<why>"`; on an unknown role, ask
whether to pick an existing one or `/role-add` it first.

When the user enters `/user-list [--role <role>] [--active-only]`, run
`catalyst list user` (`--filter roles=<role>`, `--filter active=true`) and
report what it prints; never add users it does not list.

When the user enters `/role-add <role> <actions>: ...`, run `catalyst role add
"<role>" --action <a> ... [--reconciliation full|propose|none] --intent
"<why>"` (`propose` when not given, never silently `full`;
`Rules-of-Rules.md` §16). It refuses a role that exists (use `/role-modify`).

When the user enters `/role-modify <role> <actions>: ...`, run `catalyst role
modify "<role>" --action <a> ... --intent "<why>"`: it replaces the role's
actions and never changes a `Signed-off-by` already recorded.

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

When the user enters `/freeze <item-id|item-path|type|template-name>`, run
`catalyst freeze <item> --intent "<why>"`: it resolves the item to its path,
lists it in the working copy's `.frozen` and journals it; `/sync-framework`
then skips it until `catalyst unfreeze <item>` or a forced sync.

When the user enters `/migrate-definition <entity-type> <version>`, run
`catalyst definition migrate <entity-type> <version> --kernel <framework/kernel
of the release> --intent "<why>"` (the release as `/sync-framework` obtains
it, `SYNCHRONIZE.md` "Version rule"). It refuses a type with no definitions
and a version that does not exist (naming the highest that does), and is
the only way a deployed `definitions/<type>.md` changes (INV-23).

When the user enters `/adopt [<commit>|<range>]`: run `catalyst
unrecorded [<range>]` (every commit after the baseline by default) and
list each commit with its author and files. For each one, ask the user
whether to accept or reject it; never decide for them. To accept: read
the commit (`git show`), state its tier (chore, fix or feature, `Rules-of-Rules.md` §6), do
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

When the user enters `/share push <message>`: resolve the signer (§2) and
run `catalyst share push -m "<message>" --as <signer>`. It prints what it
would publish — uncommitted changes, local commits, and whether they join
the open pull request or start one — and exits `3`: show that to the user
and re-run it with `--yes` only once they agree (law L3). Report the pull
request (or the branch to open one from). If the push stops on a conflict,
report the conflicting files and stop: nothing was pushed. Never resolve
the conflict by an edit of your own; you may propose a resolution as a
`RECON-` case (`catalyst new RECON --as <signer>`, `Trigger:
merge-conflict`, `Baseline` the shared branch's version, `Proposed` yours)
for a human to decide with `/reconcile`. If `catalyst check` fails, fix the
errors as ordinary work before pushing again.

When the user enters `/share create <url> [--protect]`: confirm the user
wants this criterion shared and that the repository at `<url>` exists,
empty or holding this criterion's own history — creating one on a hosting
service is externally visible, so ask before doing it. Run `catalyst share
create <url> [--protect]`; it exits `3` with what it would publish: show it,
and re-run with `--yes` on the user's yes. It records the remote in
`catalyst.toml`: offer to commit that, never without assent. If it refuses
because the remote holds history this criterion lacks, report it — that is
someone else's work, never something to overwrite.

When the user enters `/share join [<url>]`: in a clone of the product
repository, run `catalyst open` — it clones the criterion `catalyst.toml`
names into this machine's catalyst home — or `catalyst share join <url>`
when `catalyst.toml` names none. A person not yet in `IAM/users/users.json`
registers with `/user-add` before signing anything, and lands that with
`/share push`.

When the user enters `/share pull`: run `catalyst share pull`. If it
refuses because local work is unpublished, report why and offer `/share
push`. When the user enters `/share info` or `/share status`: run
`catalyst share info`, or `catalyst share status --fetch`, and report it.

When the user enters `/reconcile <RECON-id> <verb> [<text>]`: if the case
names a `Workflow` (`WORKFLOW-NNNNNN`, `Rules-of-Rules.md` §19), read it
first. Run `catalyst reconcile <RECON-id> <verb> [--text "<text>"] --as
<signer>`; it refuses a verb the signer's role does not allow — then say
who may act, never retry as someone else. After `accept` or
`accept-with-edits`, applying the accepted version to the case's `Entity`
is ordinary work, journaled like any other change; `close` only once it has
landed.

When the user enters `/status <artefact-id> <status> [force]`, run
`catalyst status set <artefact-id> <status> [--force] --intent "<why>"` and
report what it prints. It checks the type's statuses and transitions,
refuses a `RECON-` case even with `--force` (only `/reconcile` changes one,
`Rules-of-Rules.md` §16), regenerates the indexes and journals the change;
on a refusal, change nothing by hand.

When the user enters `/audit <file-name>`, inspect the repository and the
current framework state to determine the impact of changes against the named
file. The command must identify whether the file is a rule, template,
artifact, or other framework asset; inspect related indexes,
references, and dependent artifacts (`catalyst validate --json` resolves
every reference mechanically); and return a concise summary of likely
impact, affected areas, and any blocking concerns. If the file cannot be
resolved, report that it was not found and do not invent a result.

When the user enters `/run-analysis [<path>...] [--bootstrap|--incremental]`,
follow the criterion's `ANALYSIS-PLAYBOOK.md` (the deployed playbook) phase by
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
obtain the target kernel release (`latest`: the newest on the release
branch; none given: the installed version; a version that is not a tag is
refused, `SYNCHRONIZE.md` "Version rule") and the active module's matching
release, then run `catalyst sync plan --kernel <kernel> [--module <module>]`
and show the plan; on the user's one confirmation, `catalyst sync apply`
with the same sources. It re-vendors the CLI, copies the invariants,
refreshes the module tree, recomposes the governing documents (items in
`.frozen` are skipped; `--force <scope>` means `catalyst recompose --force`
for them, by hand), retires the command files and hooks older versions
wrote into the project (one edited locally is reported, never deleted), creates definitions for new
types only (INV-23), sets the versions and journals the sync. Then carry out, in the
order the plan lists them, each migration's judgment steps, add a
`DEPLOYMENT.md` history line, run `catalyst check`, and do the four-eyes
verification: one sub-agent verifies the deployment against
`INSTANTIATION-GUIDE.md` and the framework rules, a second independently;
the sync is complete only when both approve.

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
directory outside the project (e.g. `$TMPDIR/journal-restore-<timestamp>/`) — it
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

A rule-linked artifact's `Domain` is a registered domain code
(`FORMAT.md` §3; `catalyst validate` checks it).

## 6. Development-artifact IDs

IDs come from `catalyst new` or `catalyst id next`, never by hand
(`Rules-of-Rules.md` §6, §20).

## 7. Closing an item

A type's statuses and closed states are its definition's; what closing
needs beyond them is the active module's (`Rules-of-Rules.md`, its part).

## 8. Retired rules and development work

Closing an artifact never retires a rule, and retiring a rule never closes
an artifact (`Rules-of-Rules.md` §4).

## 9. Journaling

Every change is journaled as it happens, with the tier, the targets and the
intent; a change made outside catalyst is listed to the user and adopted or
reverted on their word; commits are traced (`Rules-of-Rules.md` §12, §23;
the entry format: `FORMAT.md` §7).
