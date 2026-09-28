# Migration 0.41.0: traced commits, the on-disk format version

> Apply this migration when synchronizing a deployment whose `version.txt`
> is being advanced past `0.40.0` to `0.41.0` or later. See `SYNCHRONIZE.md`
> for the full synchronization procedure. Never re-run on a later sync once
> applied.

Until `0.40.0`, the chain (INV-5) stopped at the journal: nothing tied a
product commit to the artifact or rule it served, and nothing said which
version of the on-disk format a deployment was written in. From `0.41.0`
every product commit traces, and the pointer declares its format.

## What changed

1. **Traced commits (INV-5 at commit granularity).** Every product commit
   cites an artifact or rule ID that resolves in the deployment — full or
   short (`<PREFIX>-NNNNNN`, `<doc-prefix>-<DOMAIN>-NNNNNN`) — or its
   subject starts `chore:` or `chore(<scope>):`. Merge commits are not
   checked. `catalyst hook commit-msg` enforces it at commit time, installed
   with `catalyst hook install`; `catalyst trace <range>` checks a range in
   CI (`--pattern-only` where CI has no working copy). `CLI.md`,
   `CODE-OF-CONDUCT.md` §9.
2. **The on-disk format, specified.** `FORMAT.md` specifies every file a
   deployment consists of, at format version `1.0-rc`. The pointer gains a
   `format` field; `catalyst check` warns when it is absent and fails when
   it names a format the CLI does not read.
3. **`catalyst report`**: usage figures from the journal, the artifacts and
   git — actors, tiers, traced commits, open work (`CLI.md`).

Nothing else in a deployment's shape changes. The composed documents gain
the traced-commits text (`CODE-OF-CONDUCT.md` §4, §9); `INVARIANTS.md`'s
INV-5 gains one sentence.

## Steps for every deployment

1. **Declare the format.** Add `"format": "1.0-rc"` to
   `<app-name>.catalyst`, after `project_name`, and set its `updated` to
   today. This is a tracked file of the product repository: commit it with
   the rest of the sync, with the user's assent (INV-4).
2. **Re-vendor the CLI.** Replace `.criterion/bin/catalyst.pyz` with the
   `0.41.0` release's; check that `python3 .criterion/bin/catalyst.pyz
   trace --help`, `hook install --help` and `report --help` work.
3. **Refresh the kernel files.** Recompose `CODE-OF-CONDUCT.md` and
   `rules/Rules-of-Rules.md` with `catalyst recompose --base-kernel <0.40.0
   kernel> --base-module <the module version it was composed from>
   --kernel <0.41.0 kernel> --module-dir <module>` (leave anything listed
   in `.frozen` alone), and refresh `INVARIANTS.md` wherever the deployment
   carries a copy. Refresh the module too if its release matching kernel
   `0.41.0` changed, and apply its own `0.41.0` migration if its
   `migrations/migrations.md` lists one.
4. **Install the commit-msg hook — with the user's assent.** Offer
   `catalyst hook install`. It writes `.git/hooks/commit-msg` in the
   product repository, so run it only when the user agrees. If it refuses
   because a `commit-msg` hook already exists, show the user both and let
   them merge (the catalyst hook is one line:
   `exec python3 "$(git rev-parse --show-toplevel)/.criterion/bin/catalyst.pyz" hook commit-msg "$1"`).
   Every contributor installs it in their own clone.
5. **Check new commits in CI.** If the product repository has CI, offer a
   step that runs `catalyst trace` on the commits each push or pull request
   adds. On GitHub Actions, with the checkout at `fetch-depth: 0`:

   ```yaml
   - name: Every new commit cites an artifact or rule ID, or is a chore
     run: |
       if [ "${{ github.event_name }}" = "pull_request" ]; then
         range="${{ github.event.pull_request.base.sha }}..${{ github.event.pull_request.head.sha }}"
       elif [ "${{ github.event.before }}" != "0000000000000000000000000000000000000000" ]; then
         range="${{ github.event.before }}..${{ github.sha }}"
       else
         range="${{ github.sha }}~1..${{ github.sha }}"
       fi
       python3 catalyst.pyz trace --pattern-only "$range"
   ```

   A pull request checks its own commits, a push the commits since the
   previous head, and a new branch's first push its head commit. A
   local-only deployment's CI has no working copy (`.criterion` is
   gitignored), so it runs `--pattern-only` with a `catalyst.pyz` taken
   from the kernel release (`bin/catalyst.pyz`); a shared deployment whose
   CI checks out the `.criterion` submodule runs
   `python3 .criterion/bin/catalyst.pyz trace "$range"`, so every ID must
   resolve.
6. **Existing history is not checked.** Commits made before this migration
   are left as they are: never rewrite history to add IDs. Start every
   range from a commit made after the hook and the CI step exist.
7. **Check.** Run `catalyst check`: the `format` warning is gone.
8. **Version.** Set `.criterion/version.txt` and the pointer's
   `kernel_version` to `0.41.0`.
9. **Journal.** Append one entry with
   `catalyst journal append --command /sync-framework --action sync
   --artifact "kernel 0.41.0" --intent "<adopt traced commits and the
   on-disk format version>" --file <app-name>.catalyst --file <each other
   touched file>`. The hook in `.git/hooks` is not a tracked file and is
   not journaled.

A shared deployment lands the working-copy changes as one pull request
(`catalyst criterion push`); the pointer change is a product-repository
commit — the first one the new hook checks, which it passes as a `chore:`
or by citing a rule.

## Rollback

Remove the `format` field, restore the `0.40.0` kernel files and vendored
CLI and `version.txt`, delete `.git/hooks/commit-msg` if catalyst wrote it,
and drop the CI step. No journal line changes; commits made in between
keep their IDs, which do no harm.
