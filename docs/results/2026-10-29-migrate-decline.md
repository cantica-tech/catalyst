# Results: `migrate --decline` and criteria cleanup (kernel 0.118.0), 2026-10-29

The 0.117.3 sync's verifiers noted that `catalyst migrate` in catalyst-users kept offering the optional KSOURCE v2
template the owner declined on 2026-10-26: nothing recorded a decline. The owner asked for it, and for the cleanup the
verifiers noted (a finished install ledger, merged pull-request branches on the criteria's remotes).

## What shipped

- **`catalyst migrate --decline TYPE`** (REQ-000102, kernel 0.118.0):
  - takes a type prefix, a template name or `all`, repeatable;
  - writes each matching optional module template to the criterion's `modules/declined.json`: template, type, file,
    source, the sha256 of its seeded text, date and signer;
  - journaled; a decline matching nothing offered is refused.
- **What `migrate` does with it:**
  - `plan` leaves the declined template out;
  - `--apply --template all` skips it;
  - naming its type or name in `--apply --template` adds it and clears the decline, journaled;
  - a module release whose template text differs is offered again;
  - a kernel template is required, so it is never declinable.
- **`FORMAT.md`** documents `modules/declined.json`; `CLI.md` regenerated.

## Cleanup

- **catalyst-users' criterion:** `.ledger/install.todo.md` (the install of 2026-10-22, finished; its last open item,
  the commit hook, is installed) removed, journaled, pull request #35 merged.
- **Merged pull-request branches:** 309 deleted across the six criteria repositories (`criterion` 170,
  `catalyst-ui-criterion` 105, `catalyst-users-criterion` 18, `catalyst-kb-engine-criterion` 9,
  `catalyst-knowledge-base-criterion` 4, `catalyst-docs-criterion` 3). A branch was deleted only when its tip was the
  head its merged pull request merged and no open pull request used it.

## Tested

- Three new tests in `tests/test_catalyst_migrate.py`. The whole suite: 896 passed.
- ruff 0.16.10, pyright 1.1.414 and the standards lint pass on a clean copy; kernel purity passes.

## Then, as the owner asked

- **Synced to 0.118.0:** catalyst-users, catalyst-ui, catalyst-kb-engine and catalyst-knowledge-base, from the release
  zip; no migration in that range; `catalyst check` passes in each (catalyst-ui keeps its 10 older warnings).
- **catalyst-users:** `catalyst migrate --decline KSOURCE` recorded the KSOURCE v2 template declined on 2026-10-26;
  `migrate` now has nothing to offer there.
- **Branches:** `delete_branch_on_merge` is on in the six criteria repositories; after the syncs' merges, each holds
  only its shared branch.

## What's left

- **Old hooks:** a hook installed before 0.117.1 (catalyst-users' among them) keeps the old script until
  `catalyst hook install` rewrites it.
