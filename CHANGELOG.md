# Changelog

catalyst is pre-1.0: minor versions may change the deployed layout. Every
such change ships a migration (`framework/kernel/migrations/migrations.md`)
that `/sync-framework` applies to an existing deployment. Versions before
0.37.0 are described by that migrations index and by the tagged commit
messages.

## 0.92.0 — 2026-10-19

A workspace member inherits the workspace's roles. No layout change, no migration.

- Fixed: a member of a VS Code workspace did not inherit the workspace criterion's roles. The roles list, the gates'
  role check and the reconciliation level read only the member's own; they now read the member's roles, then the
  workspace's whose names the member does not use (BUG-000021, R3.1b audit).
- Fixed: proposing a change to a rule inherited from the workspace crashed; it is refused, read-only in the member.

## 0.91.0 — 2026-10-19

Status changes in one step, intents that say why, and declared transitions enforced. No layout change, no migration.

- `catalyst status set <ID> <state> --through` reaches a state the type's declared transitions reach only through
  other states: the shortest path, each state's gates and guards checked, nothing written on a refusal, one journal
  entry naming the path. It does not go with `--force` (R4.8).
- `journal append` and every writing verb warn when an `--intent` has fewer than three words once IDs are left out
  ("work starts", "R4.8"); the change is still made (R4.8).
- Fixed: a type's `workflow.transitions` were never read, so `status set` allowed any move and `graph` showed none
  (BUG-000019). A module that declares transitions now gets the checks it asks for.
- Fixed: `catalyst new` and `catalyst link` refused a reference to an entity stored as a table row, such as a
  roadmap's `RM-` item cited by a feature (BUG-000020).

## 0.90.0 — 2026-10-18

The share status served. No layout change, no migration.

- `catalyst serve --local` answers `GET /v1/share` (`?fetch=1` asks the shared copy first): what
  `catalyst share status --json` prints, its location without credentials (`spec/share-status.schema.json`). A
  shared server refuses it.

## 0.89.0 — 2026-10-18

The three first-class agents run commands (decision B2), and changes name their tier. No layout change, no migration.

- `catalyst agent run` runs GitHub Copilot (`copilot -p`) and Gemini CLI (`gemini -p`) beside Claude Code: what they
  print is passed on as text, the run `ok` when the agent exits 0. They report no tool calls, usage or cost; their
  `end` event says `measured: false` (`spec/run-event.schema.json`).
- The writing verbs (`new`, `status set`, `link`, `rename`, `restore`) record, when given no `--tier`, the tier
  their artifact's type opens, when exactly one tier names that type (R4.8: 27% of entries had no tier).

## 0.88.0 — 2026-10-18

Journal hygiene (R4.8) and the definitions served. No layout change, no migration.

- `catalyst journal append` warns when `--command` is none of the deployment's commands (`CODE-OF-CONDUCT.md` §4
  and its aliases), a `catalyst <verb>` or a tier's name; the entry is still written.
- `catalyst definition list [--json]` and `GET /v1/definitions`: each deployed definition's slug, version and
  description (`spec/definitions.schema.json`), for a client to show what a type is without reading the criterion.

## 0.87.0 — 2026-10-18

The audit pack and a README badge. No layout change, no migration.

- `catalyst audit [--json] [--html <file>]`: what the deployment runs, the record's integrity (journal, `check`,
  gated rules lacking approvals), who signed, and each rule with everything that rests on it, transitively; as data
  (`spec/audit.schema.json`), in brief, or as a self-contained page printable to a PDF.
- `catalyst serve --local`: `GET /v1/audit`.
- `catalyst badge [--metric check|chain] [--out <file>]`: a README badge, an SVG of `check`'s result or of the rules
  something rests on, for CI to publish.
- Fixed: `catalyst serve` could hang at startup while DNS did not answer: it no longer looks its own address up.
- Rule storage (decision B7): a rule is a heading in a rule document or its own file, both checked alike; a file named
  as a rule that also holds a rule heading is `check`'s `rule-file-heading` error.
- `check` warns when a `user` or `user-list` field names someone who is not a registered user (`unknown-user`).
- `catalyst new` fills an optional `user` or `date` field only when it is given (a required one still defaults to the
  signer and today): an item is not assigned to whoever creates it.
- `catalyst serve --allow-origin <origin>` and `catalyst.toml`'s `embed_origins` (decision B8): pages of those origins
  read through `serve`, each with its reader's token; they write nothing, and no origin is allowed unless named.

## 0.86.0 — 2026-10-18

Modules as data, for a Studio to administer them. No layout change, no migration.

- `catalyst module available <id> [--json]`: the version tags at the module's recorded repository, newest first,
  each marked installed or newer (`spec/module-releases.schema.json`; the network).
- `catalyst serve --local`: `GET /v1/modules` (`module list --json`), `GET /v1/modules/<id>/available`, and
  `GET /v1/modules/<id>/plan?to=<tag>`, the plan of upgrading to one of those releases (`module upgrade --plan
  --json`; never another source). A shared server has none of them.
- `GET /v1/head` (local mode) also gives the project's name, `project`.

## 0.85.0 — 2026-10-18

An analysis as data, for a workspace to read and triage, and two fixes. No layout change, no migration.

- `catalyst analysis status <id> --json`: the full report of one analysis — its summary (phase, mode, passes, scope,
  code state, findings decided, accepted and rejected), what each pass recorded, the diff's counts, each reconciled
  finding with its decision, and what keeps it from its phase (`spec/analysis.schema.json`).
- `catalyst analysis list [--json]`: every analysis in brief, newest first (`spec/analyses.schema.json`).
- `catalyst serve`: `GET /v1/analyses` and `GET /v1/analyses/<id>`, as the verbs print them.
- Fixed: `catalyst check` rejected a rule kept in its own file (`FORMAT.md` §5.2), asking it for a rule document's
  `## Contents` and `## Linked Artifacts` headings.
- Fixed: `catalyst journal adopt` recorded the git author's name as the actor instead of the registered user's
  `git_username`, and did not ask an adopted fix or feature to name its artifact. Past entries stay as written.

## 0.84.0 — 2026-10-18

Configurable four-eyes analysis (decision B5). Migration: `framework/kernel/migrations/0.84.0/single-pass-analysis.md`.

- `catalyst analysis start --passes 1|2` chooses the number of independent passes of one analysis, and
  `catalyst.toml`'s optional `analysis_passes` the deployment's default; without either, two, as before.
- A single-pass analysis is recorded as such (`Passes`, `inventory.json`'s `passes`), refuses pass B, and every
  finding it keeps says how it was verified against the code; the user still decides each one.
- An analysis started before 0.84.0 is read as two-pass. `/run-analysis` takes `--passes 1|2`; the analysis template
  gains `Passes`.

## 0.83.0 — 2026-10-18

Rule strength (decision S): a rule says how hard it binds. Migration: `framework/kernel/migrations/0.83.0/rule-strength.md`.

- A rule states `must`, `should` or `may` on a `**Strength**` line of its text (`FORMAT.md` §5.2); one that states
  none is `must`, so no existing rule changes.
- `catalyst check` reports any other value as `rule-strength` (an error).
- `catalyst view`, `list rule` and `graph` give each rule its `strength` (`spec/view.schema.json`,
  `spec/list.schema.json`, `spec/graph.schema.json`).
- A breach is reported by the rule's strength: a violation for `must`, a warning for `should`, a note for `may`
  (`Rules-of-Rules.md` §5, `/check-rules`, `ANALYSIS-PLAYBOOK.md` step 5).
- The rule template gains the `**Strength**` line.
- `catalyst sync apply` scaffolds the folder of a type a module adds — its templates, their catalog and its index,
  as `init` does — so `catalyst new` works on it at once; until now a new type arrived with its definition only.

## 0.82.0 — 2026-10-17

Impact simulation (decision T, design 27): try a change before making it. No layout change, no migration.

- `catalyst try [--json] [--keep] <verb> <its arguments…>` makes one of catalyst's writing verbs (`status`, `new`,
  `link`, `rename`, `restore`, `approve`, `reconcile`, `propose`) on a scratch copy of the criterion — a
  `git clone --shared` under `$CATALYST_HOME/scratch/` with the criterion's current files over it — and reports
  what it would do: the files it writes, the `check` findings it adds and clears, the `impact` of the entity it
  touches and the approvals it would leave waiting. A refused change is the answer, said as the verb says it.
  Nothing in the criterion or the project changes; the copy is removed (kept with `--keep`).
- `catalyst try --proposal <case> --as <user>` tries accepting a proposal (0.81.0).
- The report is described by `spec/try.schema.json`.

## 0.81.0 — 2026-10-17

Proposals (decision P, design 26): a change offered for review before it lands. Migration
`0.81.0/proposals.md`: the reconciliation template gains the `proposal` trigger (a new template version, a judgment
step); nothing is converted.

- `catalyst propose <ID> --from <file>` opens a reconciliation case with `Trigger: proposal`: its entity, the
  entity's file as it is (`Baseline`, the base) and the proposed content, kept beside the case as
  `reconciliations/<RECON-id>.proposed`. The entity is untouched. A rule is proposed as its rule document.
- `catalyst reconcile <case> accept` on a proposal writes the proposed content to the entity, journaled by the
  acceptor with `proposal` and `proposed_by`. It is refused when the entity has changed since (revise it with
  `reconcile <case> propose --from <file>`, which re-bases it), for the proposed version's own author, and for a
  move into a gated state until the proposed version has the gate's approvals. `accept-with-edits --from <file>`
  writes the acceptor's content; the author may `close` an open proposal.
- `catalyst approve <case> --gate <gate>` approves the proposed version; once it lands those approvals count, with
  the proposer as the version's author, so a gated rule can land already approved.
- `catalyst inbox` has a sixth kind, `proposal`, listed apart from the disputes; `catalyst view <case>` gives the
  proposal with both contents; `catalyst check` reports an open proposal whose proposed file is missing or changed
  outside catalyst. `Rules-of-Rules.md` §16 says what a proposal is.

## 0.80.0 — 2026-10-17

Approval gates enforced (decision G, design 25, steps A3 and A4). A deployment without `IAM/gates.json` sees no change. No layout change, no migration.

- `catalyst status set` refuses to move an entity into a gated state until
  the gate's approvals for its current version are recorded, naming how
  many are missing and from which role. `--force` passes the module's
  guards, never a gate: a gate that must be passed is removed in
  `IAM/gates.json`, a journaled change. `catalyst new` refuses an initial
  status a gate covers, and `catalyst restore` a version that enters a
  gated state without its approvals. A malformed `IAM/gates.json` refuses
  every move until it is fixed.
- `catalyst check` reports one error (`gates unapproved`) per rule of a
  gated domain whose current text lacks its approvals.
- `catalyst inbox` has a fifth kind, `approval`: each gated rule whose text
  lacks its approvals, and each open entity one move away from a gated
  state that lacks them, settled by `catalyst approve`
  (`spec/inbox.schema.json`). `catalyst serve` answers
  `GET approvals/<id>` like `catalyst approvals <id> --json`.
- `Rules-of-Rules.md` §11 (`rr-META-011`): roles are advisory except
  reconciliation and approval gates; `ACCESS-CONTROL.md`, `INVARIANTS.md`
  INV-16 and `FORMAT.md` say the same.

## 0.79.0 — released with 0.80.0

Approval gates, opt-in (decision G, design 25, steps A1 and A2): declared and checked, approvals recorded and counted. Nothing is enforced yet; that comes with A3. No layout change, no migration.

- `IAM/gates.json` declares a deployment's approval gates; without it there
  is no gate. A gate covers the rules of one domain or an entity type
  entering one state, and asks for a number of approvals from one role.
  `catalyst check` reports a malformed gate, or one naming an unknown role,
  domain, type or state, as an error
  (`framework/kernel/schemas/gates.schema.json`).
- `catalyst approve <ID> --gate <gate> [--as] [--intent]` journals one
  approval (action `approve`, no file changed) of the entity's current
  version: its file's blob. It is refused for a gate that does not cover the
  entity, a signer who is not active or lacks the role, the author of that
  version, or a second approval of the same version by the same person.
- `catalyst approvals <ID> [--json]` lists each gate covering the entity,
  the approvals that count for its current version and how many are missing
  (`spec/approvals.schema.json`). Once the text changes, earlier approvals
  no longer count.
- Fix: `catalyst module install` no longer fails when git's background gc
  moves objects while the install takes its snapshot; the snapshot never
  enters `.git` or `.venv`.

## 0.78.0 — 2026-10-17

What a UI's read side needs from the engine: check findings with their entity, rule coverage, and this user's run log. No layout change, no migration.

- `check --json` (and `GET /v1/check`) gains `findings`: each error and
  warning with its level, its text and the entity it is about, so a client
  can show drift where it shows that entity. `errors` and `warnings` keep
  their shape.
- `backlog --json` gains `coverage`: the project's active rules (the
  handbook's meta-rules left out) and how many an artifact cites.
- `catalyst agent run` keeps a run log for this user, in catalyst's home and
  never in the criterion; `catalyst agent runs [--limit] [--json]` lists it
  with the total cost, and `serve --local` gives it at `GET /v1/runs`
  (`spec/runs.schema.json`).

## 0.77.0 — 2026-10-17

An entity's earlier version written back as a new journaled change (`catalyst restore`); the design notes, the roadmap and the decisions log move into `docs/`. No layout change, no migration.

- `catalyst restore <ID> --to <timestamp|#N>` writes an entity's earlier
  version back as a new journaled change, never a rewrite: the version after
  the last entry at or before a time, or after its `N`th change. Its derived
  fields are recomputed from their sources. A rule that shares its document,
  a version redacted or no longer held, and a file already at that version
  are refused with the reason.

## 0.76.0 — 2026-10-16

A command dispatched to the project's agent with its output streamed and its cost (R5.5), and a rule's view with the rule itself (R6.14). No layout change, no migration.

- `catalyst agent run <command> [<arguments>…]` dispatches a command to the
  project's agent, non-interactively, from the project's root, and streams
  what it does as events — text, tool calls and results — closed by `ok`,
  turns, token usage, cost and the tools the user's own agent settings
  denied (`--json`: `spec/run-event.schema.json`). catalyst widens no
  permission. Claude Code has the first adapter; no `serve` route starts a
  run (roadmap R5.5). The MCP prompts and the run share one procedure text.
- `catalyst view <rule> --json` and `GET /v1/view/<rule>` give the rule's
  `title`, `status`, `domain` and `text` — its own section, read as `graph`
  reads rules — so a rule's page can show the rule itself (roadmap R6.14;
  `spec/view.schema.json`).

## 0.75.2 — 2026-10-16

The laws brief every session loads, tightened under its target, wording only. No layout change, no migration.

- The laws brief that every session loads is tightened, wording only, from
  785 tokens to 634 (the target is 700): every law keeps its
  obligation; lists the law's own sentence already implies, and the
  intro's pointer to the format documents, are gone. The token baseline is
  rewritten to hold it.

## 0.75.1 — 2026-10-16

The install documents cut to the judgment `catalyst init` leaves to the agent. No layout change, no migration.

- The install documents keep only the judgment `catalyst init` leaves to the
  agent: `INSTANTIATION-GUIDE.md` from 21.6 KB to 5.3 KB, its checklist from
  6.1 KB to 2.0 KB, `BOOTSTRAP.md` from 7.9 KB to 3.7 KB. The install path
  measures about 3.5k tokens, from about 9.7k (target 3k). What `init`
  writes is listed in `CLI.md` (`catalyst init`); the tree stays in
  `ARTIFACT-LAYOUT.md`. BOOTSTRAP no longer sends the agent through
  `INVARIANTS.md` in full and the kernel `README.md`: the laws are loaded at
  session start and `catalyst why` explains the rest. The token baseline is
  rewritten to hold the cut.

## 0.75.0 — 2026-10-16

The commands and their specs as data, for a command palette (R6.8). No layout change, no migration.

- `catalyst spec --json`, `GET /v1/commands` and `GET /v1/spec/<command>[/<part>]`
  give the deployment's commands as data: each command's `usage`, one-line
  `summary`, `aliases` and `parts` (`spec/commands.schema.json`), and one
  command's or part's spec as `{command, part, text}`
  (`spec/command-spec.schema.json`) — so a command palette reads what
  `catalyst spec` reads, never a list of its own (roadmap R6.8). The MCP
  server's prompt descriptions come from the same code.
- A criterion without a `CODE-OF-CONDUCT.md` is said as such by
  `catalyst spec` (and lists no command on the server), not a crash.

## 0.74.0 — 2026-10-16

The local head says what the deployment runs (R6.5). No layout change, no migration.

- `GET /v1/head` of `catalyst serve --local` adds what the deployment runs:
  `kernel`, `modules` (each `id` and `version`) and `catalyst`, the version
  serving it — so a client sees a deployment behind the catalyst it is read
  with (roadmap R6.5).

## 0.73.0 — 2026-10-16

What an entity page shows: an artifact's sections and next states, a type's transitions, guards and sections (R6.7). No layout change, no migration.

- What an entity page shows (roadmap R6.7): `catalyst view <id> --json` and
  `GET /v1/view/<id>` give an artifact's `sections` (each heading and its
  text) and `next`, the states it may move to from its own, each with what
  its guards say blocks it now; `catalyst graph --json` gives each type's
  `transitions`, `guards` and `sections`. `spec/view.schema.json` and
  `spec/graph.schema.json` describe them.

## 0.72.0 — 2026-10-16

The plugin system is removed from the kernel (R4.7, ADR-022). No layout change, no migration.

- The plugin system is removed from the kernel (roadmap R4.7, ADR-022):
  `framework/kernel/plugins/` (the catalog, the activation checklist, the
  working-contract template, the work-item prototypes), the `catalyst-git`
  submodule, the plugin check scripts and their CI workflow. The plugin
  invariants (INV-10 to INV-13, INV-22) and meta-rules (§8, §17) are
  retired in place, their numbers never reused. New capability comes as a
  module; work items are a module's types. `catalyst-git` remains an
  optional extension in its own repository. No CLI verb read any of it: no
  layout change, no migration. A deployment that copied a plugin catalog
  keeps it as a file nothing reads.

## 0.71.0 — 2026-10-16

Four steps an agent did by hand move into the CLI (R2's exit): `catalyst rename`, `id next --count`, a default `journal restore` directory, and a tier that needs an artifact names one. No layout change, no migration.

Four steps an agent did by hand move into the CLI (roadmap R2's exit:
at least 80% of command steps in code).

- `catalyst rename <ID> --title "<title>"`: a new title; the heading,
  `Name`, `Filename` and the file name follow, the ID never changes, the
  indexes are regenerated and the move journaled.
- `catalyst id next <PREFIX> --count N`: N consecutive IDs, each reserved,
  for a batch of rows.
- `catalyst journal restore <timestamp>` without a directory restores into
  `journal-restore-<timestamp>` in the system's temporary directory,
  outside the project.
- `catalyst journal append` refuses a change whose tier needs an artifact
  (`fix`, `feature`) when it names none: an `--artifact` ID or a
  `--target`, as `trace` already asks of a commit.

## 0.70.0 — 2026-10-16

Section 4 is the one command registry: the Taskfile is generated from it (R2). No layout change, no migration: `catalyst sync apply` rewrites the Taskfile.

- The deployed `CODE-OF-CONDUCT.md` §4 is the one command registry (roadmap
  R2): the criterion's `Taskfile.common.yml` is generated from it, one task
  per command, kernel and modules alike, its description the bullet's first
  phrase. A module ships no task, and a `Taskfile.module.yml` is no longer
  read. `sync apply` and `recompose` write the Taskfile as composed, unless
  it is frozen.
- A module's commands, for the collision check, are every name in its
  bullets' heads, aliases included; a part of `/create` brings its alias,
  not `/create`, so two modules with create parts no longer collide.

## 0.69.0 — 2026-10-15

One `/create <type>`, a command with parts; meta-tags dropped (R2, ADR-021). Migration `0.69.0/one-create-command.md`.

- One `/create <type> <title>` (roadmap R2, ADR-021): each type a module
  declares is a part of it (`/create item <title>`, alias `/create-item`).
  `catalyst spec create <type>`, `catalyst spec create-<type>` and the MCP
  prompt `/create <type> …` read the shared text and that part alone;
  `catalyst spec create` lists the parts; `spec --budget` checks each part.
  One `create` task replaces the per-type tasks, generated ones included.
- Meta-tags are dropped (decision B4): no `/meta-tag`, no meta-tag type,
  definition or template. `catalyst sync apply` removes a deployment's
  `development/meta-tags/` and `definitions/meta-tag.md` when the folder
  holds no tag, and keeps them when it holds some. On a shared criterion it
  waits until the gate runs 0.69.0: the older checker requires the type.
- `catalyst sync apply` and `recompose` merge what catalyst itself
  generates (a module type's catalogue entry, its old task) from the form
  the deployment holds, so a change to the generator reaches the deployment;
  before, the three-way merge saw no change and kept the old form.
- Migration `0.69.0/one-create-command.md`.

## 0.68.1 — 2026-10-15

The kernel purity check stops flagging a module command's plain-word name in prose (BUG-000014). No layout change, no migration.

- The kernel purity check denies a module command whose name is one plain
  word only in its slash form: a module's `/board` in kernel text is
  flagged, the word "board" in prose is not. A hyphenated name is still
  denied as a word.

## 0.68.0 — 2026-10-15

Fewer slash commands: `/user`, `/role`, and `/check-rules`, `/help` and `/journal` absorbing `/audit`, `/commands` and `/journal-restore`, the old names kept as aliases (R2, ADR-020). No layout change, no migration.

- Fewer slash commands, with the old names kept as aliases (roadmap R2,
  ADR-020). `/user add|remove|modify|assign-role|list` replaces the five
  `/user-*` commands, `/role add|modify` the two `/role-*`, `/check-rules
  <file>` absorbs `/audit`, `/help` absorbs `/commands`, and `/journal
  restore` absorbs `/journal-restore`. The kernel goes from 23 commands to
  15, and its command specs from 8,494 tokens to 6,958. `catalyst spec
  <old name>` still resolves. The common tasks follow: `catalyst task user
  -- add <name> <role>` replaces `catalyst task user-add`, and the task
  names of the absorbed commands are gone. The parity check counts the
  command a §4 bullet defines; its aliases need no task.
- `catalyst new` no longer names a file `check` rejects: a name never ends
  in `-<digits>`, which INV-7 reads as a bare ID. `catalyst journal append`
  refuses an empty `--file` and a directory.

## 0.67.0 — 2026-10-15

`catalyst journal redact`: content journaled by mistake redacted as an auditable tombstone (R3.7, decision A5). No layout change, no migration.

- `catalyst journal redact <blob>... --intent <why>`: content journaled by
  mistake (a secret) is redacted as an auditable tombstone (roadmap R3.7,
  decision A5). One `redact` entry names the blobs; they leave the pins of
  the criterion and the product repository, whose pin ref is rewritten
  without history. No entry, hash or commit changes. `journal verify`,
  `check`, pinning, the pin merge, the history and `journal restore` treat
  the content as redacted from then on. A commit holding the file still
  holds the blob: rotate the secret; purging history is the owner's call.
- The history payload (`spec/history.schema.json`) gains `redacted`.

## 0.66.1 — 2026-10-15

Generated sections in the reference documents (R4.4, first step). No layout change, no migration.

- `CLI.md` opens its command reference with an index of every command and
  its options, and `FORMAT.md` §10 with the kernel's entity types, both
  generated from the code by `scripts/gen_docs.py` between markers; a test
  fails when either is stale (run `python3 scripts/gen_docs.py` after
  changing a command, an option or a kernel type).
- `catalyst hook start`'s help says it also records the session's baseline.

## 0.66.0 — 2026-10-15

A session's Stop hook blocks on what that session broke, not on what it found (ADR-002, R0.5). No layout change, no migration: run `catalyst agent install claude-code` again to get the new session-start hook.

- A session's Stop hook blocks on what that session broke, not on what it
  found (ADR-002, roadmap R0.5). `catalyst hook start` records what
  `catalyst check` fails on as the session starts, keyed by the agent's
  session id, in the criterion's git directory; `catalyst hook stop`
  reports those failures without blocking and blocks on the new ones.
  Without a session id or a baseline, every failure blocks, as before.
- `catalyst hook start --quiet` records the baseline and prints nothing.
  `catalyst agent install claude-code` (and the Claude Code plugin)
  registers it as the session-start hook: run `agent install` again to
  get it.

## 0.65.2 — 2026-10-15

Python consolidation (R3.8): one git runner, catalyst's own YAML reader on every machine, the legacy Stop hook script gone. No layout change, no migration.

- A module file is read by catalyst's own YAML reader on every machine. It
  used PyYAML when installed, which keeps the final newline of a block
  text where catalyst's reader drops it; neither CI nor a deployment's
  runtime has PyYAML, so this is what they already read.
- `scripts/stop_hook.py`, the Stop hook before `catalyst hook stop`, is
  gone with its tests; nothing ran it. The 1,000-word budget per command
  it checked is a test on fresh installs.
- One way to run git (`proc.git`): the text-mode git calls decode UTF-8 and
  line endings the same on every platform, and `catalyst check` hands
  `cat-file --batch-check` its paths as bytes (a text pipe on Windows sends
  `\r\n`).

## 0.65.1 — 2026-10-14

`catalyst view` takes an ID as `impact` and the history do. No layout change, no migration.

- `catalyst view` takes a short ID (`REQ-000030`) and a meta-rule as the
  handbook writes it (`rr-META-015`), as `impact` and the history already
  did (BUG-000012). The three verbs resolve an ID with the same code, and a
  short form two artifacts share is refused with both IDs.

## 0.65.0 — 2026-10-14

Schemas for every read payload. No layout change, no migration, no change
of behaviour.

- `spec/` describes every read payload: `list`, `view`, `backlog`, `graph`,
  `journal show` and `check` join `impact`, the history and `inbox`. A
  test checks each verb's output against its schema; the schemas allow a
  module's own fields without naming them.
- The three earlier schemas state that they allow no property beyond those
  they describe, as their tests already required.

## 0.64.0 — 2026-10-14

`catalyst serve --local --static`: a page served beside the local API. No
layout change, no migration.

- `catalyst serve --local --static <dir>`: the local server also serves a
  directory's files outside `/v1` (`/` is its `index.html`), so a browser
  page reads the criterion from the same origin. The kernel ships no page.
  The files need no token; the start line gives the page's URL with the
  token in its fragment; in this mode an API request from another origin
  is refused.

## 0.63.0 — 2026-10-14

`catalyst inbox`: what waits for a person. No layout change, no migration.

- `catalyst inbox`: what waits for a person, each item with its evidence
  and the commands that settle it. Commits made outside catalyst, changed
  files not journaled yet, reconciliation cases that are not closed, and
  analyses to decide. It lists and settles nothing.
- `catalyst serve` answers `GET /v1/inbox`; a server has no project
  history, so its inbox holds the cases and the analyses only.
- `spec/inbox.schema.json` describes the payload.

## 0.62.0 — 2026-10-13

The history of one entity, with its content before and after each change.
No layout change, no migration.

- `catalyst journal show --artifact <id> --content`: the history of one
  entity. Every journal entry that changed its file, whatever it is
  labelled with, each with the file's content before and after; as text,
  a unified diff per change. Read-only.
- `catalyst serve` answers `GET /v1/history/<id>` with the same payload;
  a served criterion takes the content from the blobs the server holds.
- `spec/history.schema.json` describes that payload.

## 0.61.0 — 2026-10-13

`catalyst impact`: what an entity rests on and what rests on it. No layout
change, no migration.

- `catalyst impact <id>`: what an entity rests on and what rests on it,
  transitively, each entry with its depth and the link that reached it
  (`--up`, `--down`, `--depth`, `--json`). IDs cited in prose only are
  listed apart and not followed. Read-only.
- `catalyst serve` answers `GET /v1/impact/<id>` with the same payload.
- `spec/impact.schema.json` describes that payload: the first of the
  schemas a client can generate its types from.

## 0.60.0 — 2026-10-13

Module install, step N3: several modules in one deployment. No migration:
a deployment with one module is unchanged, and its composed documents are
the same.

- A deployment holds several modules. `catalyst module install` adds one
  beside those already there; each module's types, tiers, aliases,
  namespace, commands, meta-rules and laws are loaded and composed, in
  install order, under its own `From module <id>` heading.
- What two modules must not share is refused before anything is written:
  an id, an entity type or folder, a definition, a namespace, a meta-rule
  ID, a command, a tier with another meaning, or a different grounding
  type.
- `catalyst sync --module` and `catalyst module upgrade` move the one
  module the source names and leave the others; a kernel-only sync
  recomposes with every module. A source naming a module that is not
  installed is refused (it replaced the installed one's tree).
- `catalyst check` reports its scope as `modules <id>, <id>` when there are
  several, and checks each module's kernel range.

## 0.59.0 — 2026-10-13

Module install, step N2: a module installed into a deployment that has
none, and upgraded, by its own verbs. No migration.

- `catalyst module install <source>[@<ref>]` installs a module into a
  deployment that has none: from a directory, a release zip or a git
  repository (a branch, a tag or a commit). It seeds the module as `init`
  does, merges its part into the governing documents and journals one
  entry; every refusal comes before anything is written.
- `catalyst init --no-module` installs the kernel's types only. `init`
  without `--module` or `--no-module` still refuses and lists the modules
  it finds.
- `catalyst module upgrade <id> [<source>]` moves the installed module to
  another release through `sync` (`--plan` only plans); without a source
  it fetches the repository the record names.
- `catalyst sync --module` takes a git repository with an optional `@<ref>`.
- A module reaches a criterion with the line endings its repository
  stores: a clone ignores the machine's conversion on checkout, and `sync`
  takes a file whose line endings alone differ as unchanged, as the
  journal does.

## 0.58.0 — 2026-10-13

Module install, step N1: one way to seed a module, and a record of what a
criterion holds. No migration: a sync writes the record for a deployment
that has none.

- `catalyst init` and `catalyst sync apply` seed a module the same way: what
  its release ships, with the manifest a release carries. `init` copied the
  checkout minus a few folders and wrote no manifest.
- A criterion records the modules it holds in `modules/modules.json`: id,
  version, source (never a path), commit and the sha256 of the deployed
  tree. `init` writes it; `sync apply` updates it, and writes it for a
  deployment that has none.
- `catalyst module list` prints that record; `catalyst module verify`
  recomputes each tree's hash and exits `1` on a difference, which
  `catalyst check` reports as an error.
- `catalyst sync` with a module checkout no longer needs catalyst's
  packaging script, which the shipped CLI does not carry.

## 0.57.1 — 2026-10-13

Three fixes found while releasing 0.57.0. No layout change, no migration.

- `catalyst sync plan|apply` refuse a module that needs a kernel newer than
  the one the shared criterion's gate runs, and say what to do: sync the
  kernel alone, publish and merge it, pull, then sync the module. The gate
  checks a pull request with the CLI of its base branch.
- `catalyst sync apply` brings the criterion's own runtime to the vendored
  CLI. The launcher and the Stop hook kept running the old version, which
  could misread what the sync had deployed.
- `catalyst share push` says when the branch is pushed but no pull request
  was opened, and why. It printed nothing, so the publish looked finished.

## 0.57.0 — 2026-10-12

Module v3, steps M3 to M5: module format 3, a module's own namespace, and a
second module run in CI. No layout change, no migration: a sync recomposes
the handbook and the catalogue, and deployed templates and definitions stay
as they are. The release notes name the module release it pairs with.

Upgrade order for a criterion shared on git: sync this kernel alone,
publish and merge, then sync a format 3 module and publish again. The
criterion's gate runs the CLI of its base branch, and an older one cannot
read a format 3 module. After the sync, `catalyst runtime install` brings
the criterion's runtime to this version.

- Module format 3: `module.yaml` with `format: 3` declares its types under
  `entities:`; catalyst generates each type's template, definition and
  `/create-<type>` command (catalogue and Taskfile). A shipped file still
  wins; format 2 stays readable until 1.0. The YAML reader takes flow lists
  and maps and folded or literal blocks.
- A module's own namespace (ADR-019): `namespace:` gives its meta-rules
  `rr-<NS>-NNN` and its invariants `INV-<NS>-n`; `aliases:` maps old IDs to
  new ones for `catalyst why`. The kernel handbook drops the four numbers it
  lent the module (9, 10, 21, 22), never to reuse them.
- `catalyst why rr-META-n` finds the meta-rule on a deployment, whose
  handbook carries widened, signed IDs.
- An old meta-rule ID a module lists under `aliases:` keeps resolving where
  artifacts cite it, short or widened and signed: `validate` and `view` take
  it as the rule it now is, and `why` explains it (IDs are permanent, L7).
- Format 3 fields take a `hint:` (and a type a `status_hint:`) for what the
  generated template's cell tells the author; section hints may be literal
  blocks. A generated template always carries `Signed-off-by`; a shipped
  `<folder>.template.md` is a generated type's index template; a catalogue
  entry with arguments (`/create-x <id>`) counts as the type's own command,
  and a type kept as rows gets none.
- The in-repo `sample-process` module is in format 3 with its own
  namespace; CI installs it and runs its work cycle.
- `catalyst share push` and `catalyst criterion integrity` take a rule a
  module renamed into its own namespace as kept when the module's
  `aliases:` name the ID it now has; they reported it as lost, which
  refused the publish after such a sync.

## 0.56.0 — 2026-10-11

Module v3, step M2: derived fields kept by catalyst, and guards on entering
a state. No layout change, no migration. The release notes name the module
release it pairs with.

- Derived fields are catalyst's: a field another type names as its
  `backref` is derived from its sources; `catalyst check` reports one that
  disagrees as the `derived` error (it was the `backref` warning), and
  `catalyst repair derived` rewrites it, journaled.
- Guards on entering a state: a type's `workflow.guards` maps a state to
  `children_closed`, `nonempty` or `section_written` conditions;
  `catalyst status set` refuses to enter it while one fails (`--force`
  overrides, journaled), and `catalyst check` warns about an artifact
  already past one.

## 0.55.0 — 2026-10-11

Module v3, step M1: a module declares its tiers, and the kernel range it
states is enforced. No layout change, no migration. The release notes name
the module release it pairs with.

- A module declares its ceremony tiers (`module.yaml` `tiers:`, each with
  the artifact it opens, or `none`, and a commit prefix for a tier with no
  artifact); without them, `chore`, `fix` and `feature` as before. Every
  `--tier`, journal entry and adoption is checked against the active
  module's tiers, and `catalyst trace` accepts as ID-less only commits with
  a no-artifact tier's prefix.
- A module's `kernel_version` is enforced: `catalyst init` and
  `catalyst sync` refuse a kernel outside it, `catalyst check` reports a
  deployment outside it.

## 0.54.0 — 2026-10-10

The server's read side, `catalyst graph` and a local read-only server, so a
client reads every criterion through one API; no layout change (no
migration).

- `catalyst serve` answers the read commands (roadmap R3.9, S3): `GET
  /v1/list`, `/v1/view/<id>`, `/v1/backlog` and `/v1/journal` return what
  `catalyst list|view|backlog|journal show --json` return, computed by the
  CLI's own code over the server's current files, with the batch they are
  for in `X-Catalyst-Batch`; `GET /v1/events` streams each new batch
  (server-sent events). A client no longer needs a parser of its own.
- `catalyst graph [--json]`: every rule, domain and artifact with its links,
  and each entity type's definition, in one answer; `GET /v1/graph` serves
  it. Items kept as table rows (`row: true`, with their cells) are
  included; rules carry their title and status line, domains their document
  and title; every rule and artifact carries `mentions`, the IDs its text
  cites apart from its field links.
- `catalyst serve --local`: a project's own criterion, read-only, on
  127.0.0.1 with a token made for the run (printed as one JSON line), with
  the read endpoints, `events` (a change counter) and `GET /v1/check`
  (`catalyst check --json`). A client reads every criterion the same way,
  served or not.

## 0.53.0 — 2026-10-10

`catalyst serve`, a server several people share a criterion through, and a fix;
no layout change (no migration). A sync brings the handbook's and
`ACCESS-CONTROL.md`'s served-criterion wording to a deployment.

- `catalyst serve`: a server several people share a criterion through,
  with a `serve` share driver (`catalyst.toml`: `share = "serve"`,
  `share_url`). Each person's criterion stays in catalyst's home and works
  offline. A push applies all or nothing and is refused when a file moved on
  the server since, when a change is not journaled, when an entry is signed
  by anyone but the token's user, when an artifact ID is taken, or when a
  reconciliation decision exceeds the signer's role. New: `catalyst share
  login`, `share create --driver serve`, `serve token issue|list|revoke`;
  `catalyst open` joins a served criterion. Standard library only.

- `catalyst journal append --file <path>` refuses a path that does not
  exist and was never journaled or committed, and names it so. It used to
  call it "unchanged". When the criterion has that file, the error suggests
  the `.criterion/<path>` spelling.

## 0.52.1 — 2026-10-10

A fix; no layout change, no migration.

- Both rule shapes real deployments use are recognised: a heading in a rule
  document, or one file per rule, `<ID>-<slug>.md`, that a rule document
  lists. A citation of `<ID>-<slug>` resolves to its rule.
- Domain codes may carry one sub-domain level (`CORE.INGEST`), in rule IDs
  too (`cor-CORE.INGEST-000001-…`): headings, the `rules.md` index, criterion
  integrity and `trace` all read them.
- The structure check no longer errors on a pre-CLI journal entry's malformed
  hashes: such an entry is immutable, and `journal verify` warns about it.
- The handbook (§3, §7), INV-8 and `FORMAT.md` §5 document both rule shapes
  and sub-domains (the 0.52.0 handbook wrongly said sub-domains were
  unsupported).
- The token budgets measure every command spec again (composed from the
  kernel's catalogue, not a deployment), and catalyst and its module are
  referenced under `cantica-tech`.

## 0.52.0 — 2026-10-10

The ten laws and the handbook (migration `0.52.0/the-handbook.md`; ADR-018). Pairs with
the module releases that require kernel `>=0.52.0` (see the release notes).

- The ten laws (roadmap R4.1): `INVARIANTS.md` opens with ten laws an agent
  must judge — what a session loads (about 0.8k tokens instead of 4.8k) —
  then every invariant, its law and what enforces it. INV-19 (project
  lifecycle) is retired, INV-10 to INV-13 and INV-22 (plugins) parked; every
  number stays resolvable. A module adds at most three laws (software
  engineering: SE-L1, the tier decides the artifact).
- `catalyst why <L1…L10|INV-n|rr-META-n|ID>` explains a law, an invariant, a
  meta-rule or an ID. `hook start` and the MCP server's instructions carry the
  laws only; `BOOTSTRAP.md` points to them instead of restating nine hard
  rules.
- The handbook (roadmap R4.2, ADR-018; migration `0.52.0/the-handbook.md`):
  `Rules-of-Rules.md` holds every judgment rule, deduplicated (66 KB → 10 KB,
  with the module's part 13 KB); `CODE-OF-CONDUCT.md` is the command catalogue
  (51 KB → 22 KB). Obsolete text (the pointer, symlink and submodule model,
  `/project`), plugin text (parked) and catalyst-development-only text
  (`/dogfood`, now `docs/dogfood.md`) left the deployed documents; ten
  contradictions fixed (rules are headings in rule documents, `domains.md` is
  the domain registry, files may be renamed but IDs never, no "sync before
  work", sub-domains marked unsupported, …).
- Commands: `/share` replaces `/criterion`; `/project …` and `/switch-agent`
  removed; `/catalyzer` parked.
- `catalyst reconcile <RECON-id> accept|accept-with-edits|reject|propose|close`
  enforces the reconciliation role gate (INV-21).
- `FORMAT.md`, `CLI.md` and the invariants describe the home store, not the
  pointer and `.criterion`; the unused pointer template is removed.

## 0.51.0 — 2026-10-10

`catalyst open`, a faster end-of-turn check; no layout change (no migration).

- `catalyst open` (roadmap R3.5): the one step after `git clone` and the start
  of every session — clones a criterion missing on this machine from the
  repository `catalyst.toml` names (with the product's journal pins), fills
  the criterion's runtime from its vendored CLI, installs the launcher, and
  reports versions, the shared copy and what is left to do. `catalyst hook
  start` leads with the same report, changing nothing.
- The agent is each user's choice: `catalyst open --agent <id>` records it in
  catalyst's home, never in `catalyst.toml`; `catalyst task` dispatches to it.
  The agent switching procedure and `/switch-agent` reduce to that command;
  `catalyst where` replaces the memory note.
- A faster end-of-turn check (part of roadmap R3.8): the journal is read and
  its blobs looked up once per run, legacy paths are normalised once, and
  files committed as journaled are compared with HEAD in one batch — `catalyst
  check` takes about 1 s instead of 2 s (catalyst-ui) and 10 s (a deployment
  with a long legacy journal).
- Fixed: in a project below its repository's top level (a monorepo), the
  journal read every product file as deleted (`git hash-object --stdin-paths`
  resolves paths from the top level).
- Migration 0.50.0 now says the upgrade's own pull request fails the
  criterion's base-branch gate once: review it and merge it by hand.

## 0.50.0 — 2026-10-09

The journal in shards (migration `0.50.0/journal-shards.md`; roadmap R3.3).

- Journal shards: each actor on each machine appends to its own
  `development/journal/<actor>@<machine>/<YYYY-MM>.jsonl`, so a shared
  criterion merges without conflicts; `development/journal.jsonl` is read,
  never written. `init` and `workspace init` no longer create it.
- Appends and adoptions run under the criterion's journal lock (the ID lock's
  mechanism, now `catalyst.lock`).
- The shards read in causal order: each file's chain decides, timestamps only
  break ties. Issues and `journal show --json` name an entry `<source>:<line>`
  (`at`).
- Unrecorded changes are decided by content hashes, never by clocks:
  committing before journaling, rebases and skewed machines no longer produce
  false reports.
- The criterion's store (roadmap R3.2): its working form (read, list, append,
  lock; driver `home`) and its sharing (`catalyst share info|status|pull|push`;
  drivers `local` and `git`, chosen by `share` in `catalyst.toml` or by the
  criterion's remote). The journal reads, appends and locks through it.
- Teams on git (roadmap R3.6): `catalyst share create <url> [--protect]` and
  `share join` (a second machine); publishing needs the user's assent —
  `share push|create`, `criterion push`, `criterion create <url>` print what
  they would publish (the batch: added to the open pull request, or a new
  one) and exit `3` unless given `--yes` (INV-4); `catalyst check` runs the
  integrity check whenever the criterion's HEAD is a merge.

## 0.49.0 — 2026-10-09

Agents at user level, nothing in a project but `catalyst.toml` (migration
`0.49.0/agents-at-user-level.md`). Process modules drop their command files with it (see the release notes).

- VS Code workspaces (roadmap R3.1b): `catalyst workspace init|status
  <name>.code-workspace` creates the meta criterion
  `$CATALYST_HOME/workspaces/<name>/criterion` (shared rules, domains, users
  and roles) and registers the member projects (`workspace = "<name>"` in
  their `catalyst.toml`); a member sees the workspace's rules and users,
  read-only. `catalyst where` names the workspace.
- catalyst touches no project file but `catalyst.toml` (owner requirement,
  2026-10-09; INV-6): no root `Taskfile.yml` include any more. The criterion's
  `Taskfile.common.yml` runs on its own with `catalyst task <command> -- <args>`;
  each task runs from the caller's directory.
- Any agent, at user level (roadmap R3.1c): `catalyst mcp` serves the
  project's commands as MCP prompts (and a `command` tool), the CLI as a tool
  and the invariants as instructions; `catalyst agent install|uninstall|status
  <agent>` registers it, with the end-of-turn check, for Claude Code, Copilot
  (CLI and VS Code), Cursor, Codex and Gemini CLI. `hook stop|start --format`
  speak each agent's hook format.

## 0.48.0 — 2026-10-09

The criterion in catalyst's home store (migration `0.48.0/criterion-in-catalyst-home.md`).

- `catalyst sync plan|apply` (roadmap R2 W4): the mechanical half of
  `/sync-framework` from a checkout or a release zip — CLI, invariants,
  module tree, recompose, changed command files (local edits reported, never
  overwritten), definitions of new types, versions, one journal entry — and
  the migrations to run, in order. `/sync-framework` runs it.
- Kernel release archives carry the command files and `agents/`, so an
  install or sync from a release has them.
- The criterion's place (roadmap R3.1, ADR-010): `catalyst.toml` at the
  project root (a legacy `<name>.catalyst` is still read) and
  `$CATALYST_HOME/projects/<name>/criterion` (default `$HOME/.catalyst`),
  else a legacy `.criterion`; `catalyst where` reports which.
- A runtime per criterion: `catalyst runtime install|status` builds a runtime
  per catalyst version once, copies it into the criterion's `.venv`, and
  installs the `catalyst` launcher, which runs the project's own runtime.
- **Python 3.11 or later** (was 3.9): the criterion's runtime brings it.
- `init` installs into the home store: the criterion at
  `$CATALYST_HOME/projects/<name>/criterion` with its runtime, `catalyst.toml`
  the only file added to the project (no symlink, no `.gitignore` entry); a
  name already used on the machine is refused. `--at` (agent-owned space and
  a `.criterion` symlink) remains for one minor; the in-project fallback is
  gone. Hooks call the launcher (`agents/claude-code/settings.template.json`).
  INV-6 and the install docs say so.
- `catalyst move --to-home` moves a legacy deployment (symlink, in-project
  directory or shared submodule) into the home store, keeping its history,
  branches and remote; `catalyst move --name <new>` renames a project
  (roadmap R2 W5).
- Sharing in the home store (R3.1 stage F): `catalyst criterion create <url>`
  pushes the criterion and records its remote in `catalyst.toml` (no
  submodule); `catalyst criterion join` clones it into the collaborator's own
  home store and fills its runtime; product CI clones it into its own
  `$CATALYST_HOME`. The commit-msg hook runs each project's own runtime
  through the launcher. The submodule model stays for one minor.
- Windows: `catalyst move` removes the product's old submodule git data even
  though git writes its object files read-only.

## 0.47.0 — 2026-10-08

Verbs replace procedures (migration `0.47.0/verbs-replace-procedures.md`).

- Read-only views (roadmap R2 W1): `catalyst list <type|all>` (artifacts of
  any entity type, rules, users, roles, templates; `--filter KEY=VALUE`),
  `catalyst view <ID>` (fields, links both ways, journal history),
  `catalyst backlog` (open work by type and status, missing links, rules no
  open work targets) and `catalyst journal show` (filtered entries), each
  with `--json`. `/list`, `/user-list` and `/journal` now run them instead
  of having the agent read the files.
- Writing verbs (roadmap R2 W2): `catalyst new <type> --title … --field …`
  (next ID, latest template filled and signed, references checked,
  back-references kept), `catalyst status set <ID> <status> [--force]`
  (statuses and transitions from the ETD; a `RECON-` case is refused) and
  `catalyst link <ID> <field> <ID>…`; each regenerates the indexes and
  journals. `/status` runs `catalyst status set`.
- Administration verbs (roadmap R2 W3): `catalyst user add|remove|modify|assign-role`,
  `catalyst role add|modify`, `catalyst freeze|unfreeze`, `catalyst definition
  migrate`, each with the refusals of its slash command and one journal entry.
  `/user-*`, `/role-*`, `/freeze` and `/migrate-definition` run them.

## 0.46.1 — 2026-10-08

- `init` asks less: `--user` defaults to the project's `git config user.name`,
  `--commands-dir` to the agent's (`.claude/commands` for `claude-code`), and
  without `--module` it installs nothing and lists the modules it finds (there
  is still no default module). No layout change, no migration.
- Migration 0.46.0, step 6 corrected: the criterion pull request that
  rewrites the CI workflow is not checked; check it locally before merging.
- Windows: parallel `id next` callers wait while the ID lock is being
  released (a "delete pending" file reads as permission denied) instead of
  failing.

## 0.46.0 — 2026-10-08

Grounded sessions and safe gates (migration
`0.46.0/grounded-sessions-and-safe-gates.md`).

- Deployed sessions start grounded: `init` copies `INVARIANTS.md` (and the
  module's `INVARIANTS.module.md`) into the working copy, and
  `catalyst hook start` prints them from the agent's session-start hook.
- Gates hold: `catalyst hook stop` fails closed (exit `2`) on any error;
  the criterion repository's CI runs the base branch's checker, verified
  by `bin/catalyst.pyz.sha256`, on the pull request as data; this
  repository's CI checks fail when there is nothing to check (`--require`)
  and run against freshly installed deployments; Python 3.9–3.13 on Linux,
  macOS and Windows, all enforced.
- Install: `--at` takes the `.criterion` directory or its parent; a
  `.criterion` holding only `.ledger/` is adopted; a failed `init` restores
  a pre-existing target.
- IDs: `id next` and `id next-rule` reserve under a cross-platform lock;
  `next-rule` never reuses a number cited in prose or the journal.
- Commands: `/user-*` and `/role-*` journal their writes; roles carry
  `reconciliation` (`/role-add` defaults to `propose`); `/status` refuses
  `RECON-` cases; `/reconcile <id> close` is the only way to `Closed`.
- `catalyst spec` keeps module procedures written `/name: ...`.
- `check` honours `.catalystignore` and nested deployments for uncommitted
  files and never reports `.DS_Store`, `Thumbs.db`, `desktop.ini`.
- Security: revisions, URLs and branches that look like git options are
  refused; `criterion sync`/`push` fetch the product's journal pins;
  `init` and `journal append` announce the `refs/catalyst/journal` they
  write into the product repository.
- `catalyst --version` carries the build (`X.Y.Z+g<sha>[.dirty]`).
- Windows: git's standard input is fed as bytes (no `\r\n` in `mktree`,
  `hash-object`, `cat-file`); every file and subprocess is read and written
  as UTF-8; the CLI writes UTF-8 whatever the console code page; reported
  paths use `/`.
- Documentation: one `--at` meaning everywhere, `SYNCHRONIZE.md` lists the
  0.42.0–0.46.0 migrations, stale references and contradictions fixed.

## 0.45.0 — 2026-10-01

What a deployment governs (migration `0.45.0/workspace-scope.md`).

- A deployment governs the files under it, minus nested directories with
  their own pointer — separate, isolated deployments; the inner one wins —
  and minus what a `.catalystignore` opts out: empty, its whole directory;
  with lines, those paths. Changes outside catalyst, `journal adopt`,
  `trace` and `analysis start` read only those files; `catalyst init`
  refuses an opted-out directory, `catalyst check` reports a pointer in one.
- The commit-msg hook routes: every deployment owning a staged file checks
  the message and its staged files with its own CLI, so projects sharing a
  repository stay apart. Reinstall it (`catalyst hook install`) after
  re-vendoring the CLI.
- `criterion create`, `join` and the submodule detection work for a
  project in a repository subfolder.

## 0.44.1 — 2026-09-30

- A process module declares the kernel versions it works with
  (`module.yaml` `kernel_version`, `MODULE-SPECIFICATION.md` §3.1). Its
  release manifest's `kernelVersion` is that declaration, no longer the
  version of the kernel packaging it — so publishing an unchanged module
  with a newer kernel no longer re-commits its archive or overstates what
  it needs. Without a declaration the packaging kernel is assumed, with a
  warning.
- `/criterion`'s command file numbers its items 1–5 again.
- No layout change, no migration.

## 0.44.0 — 2026-09-30

Four-eyes analysis of existing code (migration `0.44.0/four-eyes-analysis.md`).

- `/run-analysis [<path>...] [--bootstrap|--incremental]` infers domains,
  rules and the defects where the code breaks a rule. Two independent,
  blind passes over the same scope and commit; a reconciliation that
  accounts for every finding of both, verifying against the code whatever
  only one pass found or the two disagree on; then the user's decision on
  each finding before any artifact is written.
- The `ANALYSIS-` kernel entity (`analyses/`) records each run and its
  reports; `catalyst analysis start|record|diff|reconcile|decide|close|
  abandon|status` moves it phase by phase and refuses to skip one, and
  `catalyst check` rejects a record whose reports do not support its phase.
- `ANALYSIS-PLAYBOOK.md` is rewritten as the deployed playbook (phases,
  pass and reconciliation prompts, findings format) and deployed at
  `.criterion/ANALYSIS-PLAYBOOK.md` by `catalyst init` and `/sync-framework`;
  before, no deployment had it, so `/run-analysis` could not run.

## 0.43.0 — 2026-09-30

- `catalyst criterion create` takes the criterion repository's URL as
  optional. Without it the working copy is versioned strictly locally (a
  git repository on the shared branch, with its merge attributes and CI
  workflow) and stays behind the `.criterion` symlink; nothing leaves the
  machine. The first `push`, `sync` or `join` (`/criterion get`) that
  needs the repository takes `--url <url>`, or asks for it on a terminal,
  publishes as `create <url>` does, then carries on; `join` in a product
  with no submodule yet adds the given repository as the submodule.
- No layout change, no migration: `/sync-framework` recomposes the
  `/criterion` text and re-vendors the CLI.

## 0.42.2 — 2026-09-30

- Release archives are reproducible: the module zip, the kernel zip and
  `catalyst.pyz` use fixed entry timestamps, sorted entries and normalised
  permissions, so rebuilding an unchanged release yields the same bytes and
  `task release:publish` no longer re-commits an unchanged module archive.
- No layout change, no migration.

## 0.42.1 — 2026-09-29

- `task release:publish` commits a module's release archive onto the
  module repository's `origin/main` through a temporary worktree, whatever
  branch its checkout is on; it no longer commits on the checked-out
  branch and pushes a stale local `main`.
- No layout change, no migration.

## 0.42.0 — 2026-09-29

Changes made outside catalyst (roadmap manual-changes, items 30–33;
migration `0.42.0/changes-outside-catalyst.md`).

- A product commit after the pointer's new `journal_since` baseline that
  changes a file to a blob no journal entry records is an *unrecorded
  change*: `catalyst unrecorded [range] [--json]` lists them, and `check`,
  `trace` and the commit-msg hook report them. Warnings during the beta
  (format 1.0-rc), errors from format 1.0 or with `"strict_journal":
  true`. Merges and the working copy are skipped.
- `catalyst journal adopt <commit...|A..B>` records each commit as one
  entry (`origin: manual`, `commit: <sha>`, the git author as actor),
  oldest first; `/adopt` drives accept, reject (revert, with assent) or a
  `RECON-` case (Trigger `unrecorded-change`).
- `catalyst init` writes `journal_since`; `catalyst report` counts
  commits with changes outside catalyst, unrecorded and adopted.
- The reference module (2.3.0) says what an adopted fix or feature
  requires; the catalyst-git plugin (0.4.0) triggers the kernel's
  detection on each new commit.

## 0.41.0 — released with 0.42.0

Beta-readiness Phase 4: the beta gate's tooling (migration
`0.41.0/traced-commits-and-format.md`).

- Every commit traces to the chain: `catalyst hook commit-msg` (installed
  with `catalyst hook install`) and `catalyst trace <range>` in CI require
  a commit to cite an artifact or rule ID that resolves (an ambiguous short
  ID must be written in full) or to be a `chore:`; merges are exempt.
- `framework/kernel/FORMAT.md`: the on-disk format, 1.0-rc; pointers declare
  `format`, and `catalyst check` reads only formats it supports. 1.0 is
  declared after the multi-user trial.
- `catalyst report`: actors, tiers, traced commits, artifacts, validate
  totals — the trial's measurements.
- `beta/`: the multi-user trial protocol, a timed newcomer quickstart and a
  feedback template.
- From a two-contributor dry run: `criterion push` fetches the others'
  journal pins before checking; `criterion create` journals the product
  files it changes; `join` fetches the product's pins; `journal pin
  --share` shares both repositories' pins; `sync` removes merged topic
  branches; merged concurrent edits are notes, not warnings.
- From a newcomer dry run: `journal restore` rebuilds a file first
  journaled after the timestamp from that entry's `before` (the content it
  had until then); the quickstart commits the working copy and clones the
  beta branch.

## 0.40.0 — released with 0.42.0

Beta-readiness Phase 3: product shape (migration
`0.40.0/explicit-install-and-tiers.md`).

- `catalyst init` installs catalyst deterministically — every entity
  folder with its index, templates and README, the composed
  CODE-OF-CONDUCT and Rules-of-Rules, definitions, the first user, the
  journal, the vendored CLI, the pointer — and a fresh install passes
  `catalyst check`. Installing is only ever an explicit request (INV-2).
- Three ceremony tiers (reference module 2.2.0): a chore is one journal
  entry (`--tier chore`), a fix is a bug report, a feature a requirement
  with steps —
  enforced by the new ETD field flag `required_when_closed`
  (`closed-incomplete`).
- `catalyst spec <command>` prints only what one command needs from
  CODE-OF-CONDUCT §4 (at most ~1,300 tokens, against ~32k for the full
  documents); catalyst holds every command to a 1,000-word budget.
- `framework/kernel/GLOSSARY.md`; name collisions explained.
- ETDs can declare `location` (a folder's parent, e.g. `development`).
- The portability claim is narrowed: Claude Code is supported and tested;
  other agents are untested.
- README leads with what catalyst is for.

## 0.39.0 — released with 0.42.0

Beta-readiness Phase 2: shared deployments on git (`catalyst criterion`,
INV-6/INV-18 revised, migration `0.39.0/criterion-on-git.md`).

- A shared deployment's working copy is a git submodule of the product
  repository at `.criterion`, so every product commit pins the rules in
  force; a local-only deployment keeps the agent-owned working copy.
- Contributors land changes through pull requests: `catalyst criterion
  push` commits, rebases on the shared branch (the journal and regenerated
  indexes merge by union, the merged state is journaled), runs `catalyst
  check` and an integrity check, pushes a topic branch with a lease and
  opens a pull request. The criterion repository's CI runs the same checks
  (`catalyst --working-copy .`); `catalyst criterion protect` makes them
  required on GitHub.
- A real conflict stops the push with nothing pushed; the agent never
  applies a merge — it may propose a resolution as a RECON case.
- `catalyst criterion integrity` fails any merge that loses an ID, an index
  row or a journal line; `catalyst criterion sync` refuses while local work
  is uncommitted or unpushed.
- ID numbers are unique per entity type and signer: two contributors may
  hold the same number under different userids; nothing is renumbered.
- `journal verify` treats merge forks as concurrent edits (warnings).
- The feature freeze recorded in `CONTRIBUTING.md` is lifted.

## 0.38.0 — released with 0.42.0

Beta-readiness Phase 1: the `catalyst` CLI (`framework/kernel/CLI.md`).
Python, stdlib only, shipped as the single-file zipapp `catalyst.pyz`
(kernel release `bin/catalyst.pyz`), vendored into `.criterion/bin/`.

- `catalyst validate`: the traceability chain checked against the entity
  type definitions — structural breaks are errors, shape mismatches
  warnings (`--strict` promotes).
- `catalyst id next` / `id next-rule` / `userid gen`: ID and userid
  allocation, never reused, never guessed.
- `catalyst journal append|verify|restore|pin`: real hashes and time,
  hash-chain and unjournaled-edit detection, point-in-time restore, and
  blobs pinned under `refs/catalyst/journal` so `git gc` keeps them.
  Journal paths are now relative to the project root (`.criterion/...` for
  the working copy); older entries are read as written.
- `catalyst index regen [--check]`: indexes rebuilt from the artifacts;
  rows whose file is gone and hand-written cells are kept, so no ID is
  ever freed for reuse.
- `catalyst check` / `catalyst hook stop`: every check in one pass, and
  the same pass as an end-of-turn hook (Claude Code template in
  `agents/claude-code/`). catalyst's own Stop hook now runs it, so an
  unjournaled edit blocks the end of a turn.
- Command procedures (the kernel's, and the reference process module's
  from its 2.1.0) call the CLI instead of describing its mechanics; the signer is never
  guessed from git config.
- Migration `0.38.0/catalyst-cli.md`.

## 0.37.0 — released with 0.42.0

Beta-readiness Phase 0.

- Licensed under Apache-2.0; added `CONTRIBUTING.md`, `SECURITY.md` and this
  changelog.
- `scripts/package_release.py` no longer commits or pushes anything unless
  given `--push`; the distribution target is a `--publish-dir` argument
  instead of a hardcoded sibling checkout, and the kernel zip now carries
  `LICENSE`. `task release` packages only; `task release:publish
  PUBLISH_DIR=<checkout>` packages, publishes, commits and pushes.
- Removed stale files: `SUBMODULE-NOTE.txt`, `PROPOSAL-generic-framework.md`
  (shipped as the kernel/module split) and the 2026-08-04 audit report.
- **Working copy location is computed, never committed** (migration
  `0.37.0/computed-working-copy-location.md`, INV-6 revised). The
  `<app-name>.catalyst` pointer no longer stores `agent-source`; each
  machine computes its agent-owned location, and a gitignored `.criterion`
  symlink at the project root is the single access path. The root
  `Taskfile.yml` includes `.criterion/Taskfile.common.yml` as optional, so
  fresh clones and CI work. Tools resolve `.criterion` first and honor a
  legacy `agent-source` until migrated.
- The Claude Code Stop hook now actually enforces: `scripts/stop_hook.py`
  runs every checker and, on failure, writes the output to stderr and exits
  2, so the agent sees the failures and keeps working (a second consecutive
  block lets the stop through, to avoid loops).
- `check_deployment.py` reports version drift between the working copy's
  `version.txt`, the pointer's `kernel_version` (or legacy
  `framework_version`) and, in catalyst's own repository, the kernel's
  `version.txt`.
- Feature freeze recorded in `CONTRIBUTING.md`: no new invariants,
  meta-rules or entity types until criterion is rebuilt on git.
