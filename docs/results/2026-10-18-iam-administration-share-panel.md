# Results — 2026-10-18: IAM administration and the share panel (R6.25)

Kernel 0.89.0 is released, and R6.25 is released in the kernel (0.90.0) and the UI (0.54.0).

| Release | What's in it |
|---|---|
| Kernel [0.89.0](https://github.com/cantica-tech/catalyst/releases/tag/0.89.0) | `catalyst agent run` runs GitHub Copilot and Gemini CLI; changes record their tier |
| Kernel [0.90.0](https://github.com/cantica-tech/catalyst/releases/tag/0.90.0) | `GET /v1/share`: the share status, served locally |
| The UI 0.54.0 (its own repository) | Users and roles administered in the Studio; a Share view |

## 1. The share status served (kernel 0.90.0)

- `catalyst serve --local` answers `GET /v1/share`, the same thing `catalyst share status --json` prints: the
  driver, where the shared copy is, the files not published yet, and how far ahead or behind each side is.
  `?fetch=1` checks the shared copy first. A shared server refuses the request.
- The location is served without the credentials a remote URL can carry.
- The response is described by `spec/share-status.schema.json`.

## 2. Users and roles in the Studio (UI 0.54.0)

- Inside a host that can run commands (VS Code, the desktop app), the Team view can register a user (name, role,
  git username), give a user another role, and deactivate one. Someone who appears in the journal but isn't
  registered can be registered from their own card.
- Without a host, the view offers none of this.

## 3. The Share view (UI 0.54.0)

- It shows where the criterion is shared, what isn't published, and how far each side is. "Compare with the shared
  copy" asks the network.
- **Pull** and **Publish** go through the host. The publish message is the reason the person types.
- A conflict is never resolved in the Studio: it becomes a `RECON-` case in the Inbox.

## How the actions stay safe

- The five new actions (`user add`, `user remove`, `user assign-role`, `share pull`, `share push`) were added to
  the Studio's list of allowed actions, and every field is checked. A name can't start with `-`, so it can't pass
  as an option, and it can't contain control characters.
- The host shows the exact command and runs it only after the person says yes. `share push` is given `--yes`
  because that dialog is the person's assent (law L3).
- "Try it" is not offered for these actions, because `catalyst try` can't run them.

## Problems along the way

- I edited the CLI command table by hand, but it is generated (law L6). I reverted the edit.
- One lint rule rejected the spread used for the control-character check; it was rewritten.
- The UI's trace check first ran before its criterion's pull request was merged, so it could not find the new
  requirement; run again afterwards, it passed.

All tests pass: 694 in the kernel, and every UI package (the new tests include an accessibility check). Not tried by
a person: the two new views in a real host.

## What's left

**From this round:** the desktop builds for UI 0.54.0 are made by its `Desktop` workflow, started by the release.

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
- R6.29, the sandboxed module UI: needs a decision (`09` D3 says no module code runs in the UI).

**Waiting on the owner:**

- The Windows (Azure) and macOS (Apple) signing credentials, a public address for the Linux package's maintainer,
  and the choice of update feed.
- Decisions on R6.21 and R6.29.
- Your yes to publish UI 0.53.0 and 0.54.0, and kernel 0.88.0 to 0.90.0, to the Marketplace or other distribution.

**Not tried by a person:** the Team and Share views in a real host, the desktop installers, and the Copilot and
Gemini CLI adapters with the real CLIs.
