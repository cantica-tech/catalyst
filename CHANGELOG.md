# Changelog

catalyst is pre-1.0: minor versions may change the deployed layout. Every
such change ships a migration (`framework/kernel/migrations/migrations.md`)
that `/sync-framework` applies to an existing deployment. Versions before
0.37.0 are described by that migrations index and by the tagged commit
messages.

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
