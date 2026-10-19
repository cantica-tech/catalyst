# Results — 2026-10-19: R4.8 done, two kernel bugs fixed, the brand name sweep begun

Kernel 0.91.0 closes R4.8 (journal hygiene) and fixes two bugs found along the way. The brand roadmap's name
consistency item has started. Kernel 0.91.0 and UI 0.54.1 are released.

| Release | What's in it |
|---|---|
| Kernel [0.91.0](https://github.com/cantica-tech/catalyst/releases/tag/0.91.0) | `status set --through`; a warning on a thin intent; declared transitions enforced (BUG-000019); references to roadmap rows accepted (BUG-000020) |
| The UI 0.54.1 (its own repository) | The default sources name the public distribution repository (BUG-000003); the maker is CanticaTech |

## 1. R4.8's last findings (REQ-000071)

The audit counted:

- 71 of catalyst's 277 status changes followed another on the same artifact within ten minutes, 57 of them with the
  same intent.
- 5% of catalyst's intents and 9% of the UI's were under 15 characters, mostly "work starts" and "acceptance met".

What changed:

- **`catalyst status set <ID> <state> --through`** reaches a state that the type's declared transitions reach only
  through other states. It takes the shortest path and checks each state's gates and guards. If any state refuses,
  nothing is written. A successful walk is journaled as one entry that names the path.
- **A thin intent is warned about:** fewer than three words once IDs are left out. The warning comes from
  `journal append` and from every writing verb. The change is still made.
- **The cause:** the process module declares no transitions, so a requirement can go from `Draft` to `Active` in one
  change. Walking through every state was habit, not a requirement.

R4.8 is marked done in the kernel's roadmap.

## 2. Two bugs

- **BUG-000019:** a type's `workflow.transitions` were never read. The ETD schema, FORMAT.md, the module spec and
  CLI.md all say `status set` checks them; `status set` allowed any move, and `graph` showed no transitions. No
  production module declares any yet, so nothing that worked changes.
- **BUG-000020:** `catalyst new` and `catalyst link` refused a reference to an entity stored as a table row. So no
  feature could cite its roadmap row (`RM-`) through the CLI. Found when opening the brand roadmap's first feature.

## 3. Brand item 8: name consistency (FEAT-000010, in the UI's criterion)

- **Done:** the UI's README now names "Catalyst Studio" (it said "Catalyst framework") and links the kernel's
  repository in the organisation. The extension's `repository` URL points to the organisation.
- **Found:** the distribution repository was **`oliben67/cantica-tech`, private**, on the owner's account. It never
  moved to the organisation. The extension's default module and kernel sources point there, so they only worked for
  accounts with access to it. The publishing results document said `cantica-tech/cantica-tech`; it is corrected.

## 4. The owner's three decisions, applied (C7 in the UI's decisions)

- **The distribution repository is now `cantica-tech/cantica-tech`, and it is public.** Before the change, its files
  and full history were checked for secrets; none were found. Its commits carry `osteck@gmail.com`, as the kernel's
  public repository already does. Raw downloads answer without credentials. It is fixed as the UI's BUG-000003: the
  extension's default sources, the API and raw URLs, the Marketplace README and the tests name it. Released as UI
  0.54.1.
- **The maker is CanticaTech:** the desktop app's copyright and the `.deb` maintainer, and `docs/desktop.md`.
- **GitHub:**
  - The organisation is named "CanticaTech" and described as "CanticaTech makes Catalyst: rules, journal and
    traceability for AI-assisted development."
  - The kernel's, the UI's, the process module's and the distribution repository's descriptions name what each
    holds; the UI's no longer says "Catalyst UI".
  - The process module's README links the kernel in the organisation.

## Problems along the way

- My first test fixture for `--through` passed when it should have failed, and the reason was BUG-000019.
- The guard test needed the type's template text, as the guard compares a section with its template.
- Catalyst's own deployment was synced to 0.91.0 before BUG-000020 was fixed; it was synced again.

All 708 kernel tests pass.

## What's left

**The brand roadmap:**

- Choose trademark counsel: that unblocks item 2.
- Item 8 is done except the organisation's avatar, which is still GitHub's default, and waits for the mark (item 6).
- Items 4, 5 and 9 can start. Item 7 needs your tagline.

**The UI's roadmap, not done:** R6.20 (signing, auto-update, bundling `catalyst`, signing the app inside the Windows
installer). R6.29 is disabled.

**The kernel's roadmap, not done:**

- R4.4 generated docs (partly done): the kernel's prose is still written by hand, which needs a content decision.
- R4.6 unverifiable hard rules (partly done): the role check is still advisory.
- R4.9 N4: module signatures wait for R7's release feed.
- R3.4: `catalyst migrate` was not built (it is optional).
- RM-026, RM-028 and RM-029 of the beta path wait on a trial by a real person.

**Waiting on the owner:**

- The Marketplace token.
- The signing credentials, the Linux maintainer address and the choice of update feed.
- Trademark counsel and the tagline.

**Not tried by a person:** the Team and Share views in a real host, the desktop installers, and the Copilot and
Gemini CLI adapters with the real CLIs.
