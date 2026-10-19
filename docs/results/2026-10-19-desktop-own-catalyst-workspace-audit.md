# Results — 2026-10-19: the desktop app carries its own catalyst; the workspace audit

The owner's three decisions are applied. The desktop app now runs without catalyst installed. The workspace
criterion's inheritance is audited, and two gaps were fixed. Kernel 0.92.0 was in CI when this was written.

| Release | What's in it |
|---|---|
| The UI 0.54.1 (its own repository) | The default sources name the public distribution repository (BUG-000003); the maker is CanticaTech |
| The UI 0.55.0 | The desktop app carries kernel 0.90.0's `catalyst.pyz` and runs it when no catalyst is installed (R6.20) |
| Kernel 0.92.0 | A workspace member inherits the workspace's roles (BUG-000021) |

## 1. The owner's decisions, applied

- **The distribution repository is `cantica-tech/cantica-tech`, and it is public.** Before the change, its files and
  history were checked for secrets; none were found. Downloads work without credentials. UI 0.54.1 points the
  extension's defaults at it.
- **The maker is CanticaTech:** the desktop app's copyright and its Linux package maintainer.
- **GitHub:**
  - The organisation is named CanticaTech and describes Catalyst.
  - The kernel's, the UI's, the process module's and the distribution repository's descriptions say what each holds.

## 2. The desktop app carries its own catalyst (R6.20, UI 0.55.0)

- The `Desktop` workflow downloads the `catalyst.pyz` of the kernel named in `catalyst-version.txt` (0.90.0) from the
  public distribution repository, and ships it inside the app.
- The app uses an installed catalyst when there is one. Otherwise it runs its own copy with the first Python 3.11 or
  later on the `PATH`.
- Without such a Python, the app says what to install. macOS's own `python3` is 3.9, which is too old for catalyst.
- **Verified:**
  - A packaged macOS app contains the file.
  - With no catalyst installed and Python 3.12 present, it served the catalyst project (HTTP 200).
  - With only Python 3.9, it fell back as designed.
  - The release's builds passed on all three platforms, each shipping catalyst 0.90.0, with 11 installers attached.

## 3. The workspace audit (R3.1b, kernel 0.92.0)

Rules, domains and users were inherited as documented. Roles were not:

- The roles list, the gates' role check and the reconciliation level each read only the member's own roles.
- So a workspace user whose role only the workspace defines had no rights in the member.
- Proposing a change to an inherited rule crashed with a traceback.

Both are fixed (BUG-000021). One reader gives the member's roles plus the workspace's, with the member's own winning
on a clash. An inherited rule is refused as read-only, with a message saying where to propose it. R3.1b is marked
audited.

## Problems along the way

- The kernel's GitHub releases carry no files, so the desktop build downloads from the distribution repository.
  That repository has kernel 0.90.0, not 0.91.0 or later, which have not been published there.
- CI caught a lint error that my local run had printed, but I had read only its last line. Lint's exit code is now
  checked.
- A test passed on macOS only: a file named `py.exe` matched `py.EXE` on the case-insensitive disk. Fixed.
- The UI's trace check ran once before its criterion pull request was merged; criterion pull requests are now merged
  before the code is pushed.

All tests pass: 709 in the kernel, every UI package.

## What's left

**Publishing (needs your yes):**

- Kernel 0.91.0 and 0.92.0 to the distribution repository. Then the desktop app's pinned catalyst can be raised from
  0.90.0.
- The UI 0.54.1 and 0.55.0 `.vsix` copies.
- The Marketplace upload, which needs a new token.

**The brand roadmap:**

- Trademark counsel unblocks item 2.
- Item 7 needs your tagline.
- Item 8 is done except the organisation's avatar, which waits for the mark (item 6).
- Items 4, 5 and 9 have not started.

**The UI's roadmap, not done:** R6.20's signing and auto-update, both waiting on you. R6.29 is disabled.

**The kernel's roadmap, not done:**

- R4.4 generated docs (partly done): the kernel's prose is still written by hand, which needs a content decision.
- R4.6 unverifiable hard rules (partly done): the role check is advisory by design (rr-META-011), unless you want it
  enforced.
- R4.9 N4: module signatures wait for R7's release feed.
- R3.4: `catalyst migrate` was not built (it is optional).
- RM-026, RM-028 and RM-029 of the beta path wait on a trial by a real person.

**Waiting on the owner:** the Marketplace token, the signing credentials, the update feed's choice, trademark counsel,
the tagline, and a public address for the Linux package's maintainer.

**Not tried by a person:** the Team and Share views in a real host, the desktop installers (including running on
their own catalyst), and the Copilot and Gemini CLI adapters with the real CLIs.
