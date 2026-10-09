# Migration 0.50.0: the journal in shards

> Apply this migration when synchronizing a deployment whose `version.txt`
> is being advanced past `0.49.x` to `0.50.0` or later. See `SYNCHRONIZE.md`
> for the full synchronization procedure. Never re-run on a later sync once
> applied.

Until `0.49.x` the journal was one file, `development/journal.jsonl`, that
every session appended to: two sessions could compute a file's `before` from
the same stale state, two contributors' appends conflicted when a shared
criterion merged, and whether a commit was recorded was decided by comparing
its committer time with entry timestamps — wrong under clock skew, rebases,
or a commit made before its journal entry. From `0.50.0` (roadmap R3.3):

## What changed

1. **Shards.** New entries go to
   `development/journal/<actor>@<machine>/<YYYY-MM>.jsonl`: one file per
   actor, per machine (a random id created once in
   `$CATALYST_HOME/machine`) and per month. An existing
   `development/journal.jsonl` stays where it is and is read as one more
   source; it is never written again, never rewritten, and its lines are
   never moved (INV-17). A new deployment has no `journal.jsonl`.
2. **Lock.** `catalyst journal append` and `journal adopt` hold the
   criterion's journal lock, kept in the working copy's git directory, from
   reading the last states to writing the entry.
3. **Causal order.** The journal reads as every source merged so that each
   file's chain is followed (`before` = the previous `after`); timestamps
   only break ties. `journal verify` and `check` name an entry
   `<source>:<line>` (`journal/ada@k3j9q2/2026-10.jsonl:3`) instead of
   `line <n>`; `catalyst journal show --json` has `at` in place of `line`.
4. **Unrecorded changes by content.** A commit's change is recorded when its
   result is a state the file's journal chain reaches after the commit's
   parent state. Committing before journaling, rebases and skewed clocks no
   longer produce false reports; a hand revert to an older state is still
   one. `journal adopt` decides "journaled again since the commit" the same
   way.
5. **Shared criteria:** the `.gitattributes` union block also covers
   `development/journal/**/*.jsonl`.
6. **`catalyst share`** (roadmap R3.2, R3.6): `info|status|pull|push|create|join`
   works whatever the sharing driver (`local` or `git`; `share = "<driver>"`
   in `catalyst.toml`, else the criterion's remote decides).
7. **Assent is enforced (INV-4):** `share push|create`, `criterion push`,
   `criterion create <url>` and a first `--url` on `criterion sync` print what
   they would publish and exit `3` unless given `--yes` (a terminal asks).
   An agent shows the preview to the user and re-runs with `--yes` once they
   agree.
8. **`catalyst check` checks merges:** when the criterion's HEAD is a merge,
   nothing either side recorded may be missing (`criterion integrity`).

## Steps for every deployment

1. **Synchronize** with `catalyst sync plan|apply --kernel <0.50.0 release>`.
   Nothing in the criterion is converted: the next append creates the first
   shard.
2. **Shared criteria:** every contributor upgrades before appending again —
   an older CLI appends to `development/journal.jsonl` and does not read the
   shards, so its `verify` reports the shards' files as unjournaled. Run
   `catalyst criterion push` once after the sync so the `.gitattributes`
   block gains the shard line.
3. **Scripts that push the criterion** (`catalyst criterion push` in CI or a
   wrapper) add `--yes`: the person who runs them has agreed.
4. **Tools that read the journal file directly** read every `*.jsonl` under
   `development/journal/` as well as `development/journal.jsonl`, or call
   `catalyst journal show --json`.
