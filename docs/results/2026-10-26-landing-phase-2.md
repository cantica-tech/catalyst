# Results: landing, phase 2 (design 33), 2026-10-26

The owner asked to continue with design 33's phase 2 and to protect the criterion's shared branch. Phase 2 is built
for kernel 0.117.0 (REQ-000101, STEP-000126); the branch protection could not be applied.

## What was built

- **The server lands what it accepted** (`fw-STRUCTURE-000024`). `catalyst serve` holds every batch it accepts. Once
  connected (`serve landing connect <repository> [--forge github|git] [--token-command CMD] --yes`), a tick, run every
  minute and on demand with `serve landing tick`, does four things:
  - **Takes in the shared branch:** what an admin pushed there becomes a server batch, leaving every file a pending
    landing holds.
  - **Matches and groups:** each held batch goes to the landing policy's first matching rule (`via`, `change`, `who`,
    `types`), grouped per change, per session (once its signer has been idle) or per time window.
  - **Lands a group:** one commit on a topic branch, built in a bare workspace (the server checks nothing out); the
    author is the server, with a `Signed-off-by` per signer. The branch is pushed with the server's credential and a
    pull request opened.
  - **Merges** only under `review: none` and `merge: auto`, once the check passes: GitHub's check runs (none registered
    yet is pending, never a pass), or `catalyst check` on the merge result with the `git` forge. Otherwise the landing
    waits for a review or an admin, and a merge on the host is followed.
- **Conflicts:** a file the shared branch changed since a batch stops its landing, with nothing pushed. A human settles
  it, then runs `serve landing retry <n>`; `serve landing list` shows every landing.
- **The token** is read from its command at each tick and never stored.
- **INV-18** gains one sentence. The frozen surface is unchanged, so no ADR was needed (design 33 §11).

## Checked

- `tests/test_catalyst_serve_landing.py`: 11 tests pass, against a bare repository with the `git` forge and a fake
  GitHub. The whole suite: 888 pass.
- ruff (0.16.10) check and format, markdownlint, the generated docs, kernel purity, command parity, the frozen surface
  and the token budgets pass; typecheck reports 0 errors.
- `catalyst check` on catalyst's own deployment, synced to 0.117.0: 0 errors.

## Branch protection

`catalyst criterion protect --yes` cannot be applied to `cantica-tech/criterion`. GitHub refuses branch protection,
and rulesets, on a private repository under the free plan ("Upgrade to GitHub Pro or make this repository public",
HTTP 403). Until the organization's plan changes, the required `catalyst` check stays a convention there. The server's
own landings still wait for the check before merging.

## What's left

- **Phase 3:** approving a landing in catalyst's inbox; the Stop hook ending an agent's session; a conflict opened as a
  `RECON-` case.
- **Phase 4:** review on the host's pull request, and a GitHub App's installation token minted by catalyst rather than
  by a token command.
- **A real run:** no criterion is served and connected yet. Landing has run against test repositories only.
- **The criterion repository's protection:** waits on the organization's GitHub plan.
