# Results — 2026-10-19: publishing kernel 0.88.0–0.90.0 and the UI 0.53.0–0.54.0

The owner said yes to publishing these releases. Everything is in the distribution repository
(`cantica-tech/cantica-tech`) except the Marketplace upload, which was refused because its token has expired.

| What | Where | Result |
|---|---|---|
| Kernel 0.88.0, 0.89.0, 0.90.0 | distribution repository, `catalyst/kernel/` | published (commit `2bfdf22`) |
| Process module 3.4.0 | its own repository's `main`, and the distribution repository | published |
| Risk-management module 0.1.0 | its own repository's `main`, and the distribution repository (new there) | published |
| The VS Code extension 0.53.0 and 0.54.0 (`.vsix` with manifest) | distribution repository, `catalyst/vsix/` | published (`4433d5b`, `7a6ee40`) |
| The VS Code extension 0.54.0 | VS Code Marketplace | **refused: the publisher's access token has expired** |
| Desktop app 0.54.0 | the UI's GitHub release | 11 installers attached by the `Desktop` workflow, unsigned |

## How it was done

- Kernel 0.88.0 and 0.89.0 were packaged from temporary worktrees at their release tags, without a commit. Then 0.90.0
  was packaged from the checkout, and one commit pushed all three versions together with the two modules.
- The two `.vsix` files were each built from their release tag (`release:vsix:publish --tag`).
- For the Marketplace, `publish:vscode-extension:release` ran from the 0.54.0 tag; the Marketplace only serves the
  latest version, which includes everything in 0.53.0. It built the package, and the upload was refused.

## Problems along the way

- The Marketplace access token (PAT) stored for the CanticaTech publisher has expired.

## What's left

**To finish this round:** a new Azure DevOps access token for the CanticaTech publisher, scoped to
*Marketplace: Manage*. Then `npx vsce login CanticaTech` (or `VSCE_PAT=…`) and the publish from the 0.54.0 tag; the
`.vsix` copy is already in place.

**The kernel's roadmap, not done:**

- R4.8 journal hygiene (partly done): short placeholder intents and repeated `/status` entries.
- R4.4 generated docs (partly done): the kernel's prose is still written by hand, which needs a content decision.
- R4.6 unverifiable hard rules (partly done): the role check is still advisory (INV-16).
- R4.9 N4: module signatures wait for R7's release feed.
- R3.4 legacy deployments: `catalyst migrate` was not built (it is optional).
- RM-026, RM-028 and RM-029 of the beta path wait on a trial by a real person.

**The UI's roadmap, not done:**

- R6.20, the desktop app: signing, auto-update, bundling `catalyst` with the app, and signing the app inside the
  Windows installer.
- R6.21, the brand: needs a decision (a trademark search first).
- R6.29, the sandboxed module UI: needs a decision.

**Waiting on the owner:**

- The Marketplace token (above).
- The Windows (Azure) and macOS (Apple) signing credentials, a public address for the Linux package's maintainer,
  and the choice of update feed.
- Decisions on R6.21 and R6.29.

**Not tried by a person:** the Team and Share views in a real host, the desktop installers, and the Copilot and
Gemini CLI adapters with the real CLIs.
