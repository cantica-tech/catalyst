# The multi-user trial

catalyst's beta ends with one trial: a small team using a shared
deployment for real work, long enough to hit the cases a single user
never does — concurrent IDs, merges, reviews, forgotten steps. This
document is its protocol. It is the evidence behind three roadmap items:
**RM-000026** (two or more people on one project for four or more weeks,
with zero lost work), **RM-000028** (the on-disk format,
`framework/kernel/FORMAT.md`, can be declared `1.0`) and **RM-000029** (a
newcomer's first traced change in under 15 minutes, measured with
[`QUICKSTART.md`](QUICKSTART.md)).

## Goal

Show, on a real project, that a shared deployment:

1. **loses no work** — every journal line, artifact, rule and index row
   anyone recorded is still there at the end;
2. **traces every commit** — each product commit cites the artifact or rule
   it serves, or is a declared chore;
3. **needs no format change** — nothing the team did required changing
   how any file in `FORMAT.md` is written.

## Setup

- **People:** at least **two**, each with their own registered user
  (`/user-add`), working on the same product repository. At least one of
  them has not used catalyst before and starts with
  [`QUICKSTART.md`](QUICKSTART.md).
- **Duration:** at least **four weeks** of ordinary work, not a
  demonstration: real features, fixes and chores.
- **Project:** any repository the team really develops. A new one is fine,
  but not a toy.
- **Install** (one person, once):
  1. `catalyst init --name <project> --module <module-id> --user <name>
     --git-username <u> --rule-doc <file>:<prefix> ... --at <dir>`
     (`framework/kernel/CLI.md`) with `--at` naming a directory outside the
     project — `criterion create` starts from the symlinked working copy —
     then write the first rules.
  2. Create an empty criterion repository on the hosting service, then
     `catalyst criterion create <url>` and commit what it staged in the
     product repository.
  3. `catalyst criterion protect --yes` (GitHub), so pull requests and the
     `catalyst` check are required on the shared branch.
  4. Add the `catalyst trace` step to the product repository's CI
     (`framework/kernel/CLI.md`, `catalyst trace`), checking out the
     `.criterion` submodule so IDs resolve.
- **Each participant**, in their own clone: `catalyst criterion join`,
  `/user-add` themselves (through a pull request), and
  `catalyst hook install`.
- Record the start: the date, the commit it starts from (existing history
  is not checked), and each participant's userid.

## During the trial

- Work normally through the agent: pick the tier, open the artifacts the
  tier needs, journal, land working-copy changes with
  `catalyst criterion push`, and commit product changes with traced
  messages.
- **Never bypass the checks** (`--no-verify`, merging a red pull request,
  editing the journal by hand). If one gets in the way, that is a finding:
  log it, then do what the check asks.
- **Weekly**, one person runs, from the product repository with the
  submodule synced (`catalyst criterion sync`):

  ```sh
  catalyst report --since <trial start date>
  catalyst report --since <trial start date> --json > report-week-<N>.json
  catalyst check
  catalyst trace <trial start commit>..HEAD
  ```

  and adds a short entry to the trial log: the report's figures (journal
  entries per actor and tier, commits traced, commits with changes
  outside catalyst — unrecorded and adopted —, validate errors and
  warnings, reconciliation cases) and anything that went wrong.

## Logging issues

Every problem gets a line in the trial log the day it happens — even
when it was solved in a minute:

| Date | Who | What happened | Command | Lost work? | Format change needed? | Severity | Resolved how |
|---|---|---|---|---|---|---|---|

- **Severity:** *blocker* (work stopped or was lost), *major* (a
  workaround was needed), *minor* (friction, confusion, a bad message).
- **Lost work?** Anything recorded that disappeared or had to be
  recreated: a journal line, an artifact, a rule, an index row, a commit.
- **Format change needed?** Yes when the fix would change how a file in
  `FORMAT.md` is written — a field, a file name, a table shape, the
  journal schema. Say which section.
- A reproducible defect is also filed as an issue on the catalyst
  repository, citing the log line.

Newcomers fill in [`FEEDBACK.md`](FEEDBACK.md) after the quickstart;
every participant fills it in again at the end, for the whole trial.

## Pass criteria

The trial **passes** when, over at least four weeks with at least two
active participants (each with journal entries in at least three of the
weeks):

| Criterion | Evidence | Pass |
|---|---|---|
| Zero lost work (integrity) | `catalyst criterion integrity` green on every merged pull request of the shared branch; the log's "Lost work?" column | No `blocker` for lost work; no integrity failure left unexplained. |
| Every commit traced | `catalyst trace <start>..HEAD` on the product repository at the end; the weekly `commits traced` figures | 100% of non-merge commits since the start trace. |
| Chain intact | `catalyst check` at the end | No errors. |
| No format change needed | The log's "Format change needed?" column | Every entry *no*. |
| Newcomer path | `FEEDBACK.md` from each newcomer | The quickstart finished in about 15 minutes, with no step abandoned. |

A failed criterion does not end the trial: fix, log and continue. The
trial passes only on a run where every criterion holds.

## Exit

- **RM-000026 — multi-user operation:** closed by a passing trial: no lost
  work, every commit traced, the chain intact, with two or more people for
  four weeks or more.
- **RM-000028 — format 1.0:** the format is declared `1.0` (the pointer's
  `format`, `FORMAT.md`, `SUPPORTED_FORMATS`) only when the trial also
  needed no format change. If it did, the change ships with a migration,
  the format stays `1.0-rc`, and the "no format change" criterion is
  re-run.
- **RM-000029 — newcomer time:** met when someone outside the project
  reaches a traced commit with [`QUICKSTART.md`](QUICKSTART.md) in 15
  minutes or less, as their `FEEDBACK.md` records. A newcomer who needed
  longer is a finding: say which step, fix the kit or the tool, and
  measure again with someone new.
- The trial log, the weekly reports and the feedback forms are kept with
  the release that closes the two items.
