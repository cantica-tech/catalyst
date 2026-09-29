# Migration 0.42.0: changes made outside catalyst

> Apply this migration when synchronizing a deployment whose `version.txt`
> is being advanced past `0.41.0` to `0.42.0` or later. See `SYNCHRONIZE.md`
> for the full synchronization procedure. Never re-run on a later sync once
> applied.

Until `0.41.0`, catalyst saw a product change only if it went through
catalyst: a file edited by hand and committed with git left no journal
entry, and nothing noticed unless the file had been journaled before. From
`0.42.0` such a change is detected wherever it lands, and resolved with
`/adopt`.

## What changed

1. **Unrecorded changes.** Every journaled file state is a git blob hash.
   A product commit after the deployment's baseline — the pointer's new
   `journal_since` — that changes a file to a state no journal entry
   records is an *unrecorded change*: written outside catalyst.
   `catalyst unrecorded` lists them; `catalyst check`, `catalyst trace`
   (CI) and the commit-msg hook (staged files) report them; `catalyst
   report` counts them (`CODE-OF-CONDUCT.md` §9, "Changes made outside
   catalyst"). Merge commits and the working copy are not checked.
2. **Warn during the beta, fail after it.** An unrecorded change is a
   warning while the pointer's `format` is a release candidate (`1.0-rc`)
   and an error from format `1.0` — the same rollout as the format and
   trace checks. A deployment can opt in early with
   `"strict_journal": true` in the pointer.
3. **Adopt or reject.** `/adopt` lists them and resolves each with the
   user: `catalyst journal adopt <commit>` records it in the journal (the
   commit's parent and commit blobs, the git author as actor, `origin:
   manual`, `commit: <sha>` — `Rules-of-Rules.md` §12), or the commit is
   reverted with the user's assent. A contested one becomes a `RECON-`
   case with the new `Trigger: unrecorded-change` (§16). What an adopted
   fix or feature requires beyond the entry is the active module's.
4. **`catalyst init`** writes `journal_since` (the current `HEAD`, or `""`
   for a repository with no commit yet).

## Steps for every deployment

1. **Declare the baseline.** Add `"journal_since": "<sha>"` to
   `<app-name>.catalyst`, where `<sha>` is the product repository's
   current `HEAD` (`git rev-parse HEAD`): history up to it is not checked,
   and never rewritten. Set `updated` to today. This is a tracked file:
   commit it with the rest of the sync, with the user's assent (INV-4).
   Journal the pointer before committing it, so the baseline commit's own
   successor is recorded.
2. **Re-vendor the CLI.** Replace `.criterion/bin/catalyst.pyz` with the
   `0.42.0` release's; check that `python3 .criterion/bin/catalyst.pyz
   unrecorded --help` and `journal adopt --help` work.
3. **Refresh the kernel files.** Recompose `CODE-OF-CONDUCT.md`,
   `rules/Rules-of-Rules.md` and `Taskfile.common.yml` with `catalyst
   recompose --base-kernel <0.41.0 kernel> --base-module <the module
   version it was composed from> --kernel <0.42.0 kernel> --module-dir
   <module>` (leave anything listed in `.frozen` alone): §4 gains `/adopt`,
   §9 "Changes made outside catalyst", §12 the `origin`/`commit` fields,
   §16 the `unrecorded-change` trigger, the Taskfile an `adopt` task.
   Refresh the reconciliation template (`TEMPLATE-RECONCILIATION-vN`) if
   the deployment keeps a copy, as a new version. Refresh the module, and
   apply its own `0.42.0` migration if its `migrations/migrations.md` lists
   one.
4. **Add the command file** for `/adopt` (the kernel's, from the catalyst
   release's command files), or its fallback (`BOOTSTRAP.md` §1).
5. **Check.** Run `catalyst check` and `catalyst unrecorded`. Nothing is
   listed right after the baseline; a change listed later is resolved with
   `/adopt`, never by editing the journal.
6. **Version.** Set `.criterion/version.txt` and the pointer's
   `kernel_version` to `0.42.0`.
7. **Journal.** Append one entry with
   `catalyst journal append --command /sync-framework --action sync
   --artifact "kernel 0.42.0" --intent "<detect changes made outside
   catalyst>" --file <app-name>.catalyst --file <each other touched file>`.

A shared deployment lands the working-copy changes as one pull request
(`catalyst criterion push`); the pointer change is a product-repository
commit.

## Rollback

Remove `journal_since` (and `strict_journal`) from the pointer, restore the
`0.41.0` kernel files, command files, vendored CLI and `version.txt`.
Entries written by `catalyst journal adopt` stay valid: the `0.41.0` CLI
ignores `origin` and `commit`.
