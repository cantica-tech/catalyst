# Changelog

catalyst is pre-1.0: minor versions may change the deployed layout. Every
such change ships a migration (`framework/kernel/migrations/migrations.md`)
that `/sync-framework` applies to an existing deployment. Versions before
0.37.0 are described by that migrations index and by the tagged commit
messages.

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
