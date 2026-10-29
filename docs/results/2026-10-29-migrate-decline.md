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
- **Hooks:** `catalyst hook install` rewrote the pre-0.117.1 commit-msg hooks of catalyst, catalyst-ui and
  catalyst-users (catalyst-mcp's was current). Each refuses an untraced message and accepts a `chore:` one.

## catalyst-docs and the container

- **Design 01 is done.** Phase 6's live check, with the catalyst-api secret read from the owner's keychain:
  - a realm token got `/me` and `/search` (8 passages, an Internal rule among them);
  - no token, a non-token, a token claiming another realm's issuer, a tampered realm token and an expired one were
    each refused (401).
  - No genuine token from another realm was tried (it needs the master admin's password); the owner accepted the
    check. The catalyst-docs lead completed REQ-000010-7TE7wuaB.
- **catalyst-kb-engine 0.14.1** (the catalyst-docs lead, BUG-000044-7TE7wuaB): an `ollama:` model defaults to the
  local server when `OLLAMA_BASE_URL` is unset; found by the live check (`serve`'s search failed with a 500).
- **catalyst-kb-container at engine 0.14.1**: the version set everywhere, `uv lock`, the wheels fetched, both images
  rebuilt (each runs 0.14.1) and the bundle packaged; pushed to `development`. It embeds through Copilot, so the bug
  never affected it. The old local images (0.11.0 to 0.14.0) are removed.

## Retired-rule citations and an adopted commit (kernel 0.118.1)

- **Records cite the replacing rules:** ADR-000048, ADR-000049, REQ-000086 and TEST-000001 cite
  `fw-IDENTITY-000007` and `000008` in place of the retired `000001` and `000004` (ADR-000049). `catalyst link` cannot
  remove a reference, so the four fields were rewritten, journaled, and `catalyst repair derived` confirmed the
  back-references; the eight retired-target warnings are gone.
- **BUG-000045 (kernel 0.118.1):** adopting `19baa1c` (the creation of `kernel-purity-fix.md`, whose deletion was
  adopted on 2026-10-10) joined the file's chain, and every later entry of that journal file was reported out of time
  order (1,336 warnings). The two entries, never pushed, were removed with the owner's assent. `journal adopt` now
  records such a commit as history only (`superseded`) when HEAD no longer holds its result; the catalyst-docs lead
  then adopted `19baa1c` with the fix.
- catalyst's own deployment is at 0.118.1; `catalyst check` passes with only the 88 pre-CLI journal warnings.

## What's left

- `catalyst link` has no way to remove a reference: an `unlink` would have made the citation change a command.
