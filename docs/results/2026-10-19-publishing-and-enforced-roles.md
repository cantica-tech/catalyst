# Results — 2026-10-19: kernel 0.91.0–0.92.0 published; roles enforced

The owner said yes to publishing and to enforcing roles. Kernel 0.93.0, module 3.4.1 and UI 0.55.1 are released.

| What | Where | Result |
|---|---|---|
| Kernel 0.91.0 and 0.92.0 | the public distribution repository, `catalyst/kernel/` | published |
| Process module 3.4.0 (unchanged) and risk-management 0.1.0 | the same | republished |
| The VS Code extension 0.54.1 and 0.55.0 (`.vsix`) | the same, `catalyst/vsix/` | published |
| Kernel 0.92.0 | GitHub release | released |
| Kernel [0.93.0](https://github.com/cantica-tech/catalyst/releases/tag/0.93.0) | GitHub release | roles grant commands |
| Process module 3.4.1 | its repository, tagged on main | INV-16's module part reworded |
| The UI 0.55.1 | its repository, released | the desktop app ships kernel 0.92.0 |

## 1. Roles are enforced (decision D5, kernel 0.93.0, REQ-000072)

- **The check:** a writing verb refuses a signer none of whose roles grants the command its change is for. The
  refusal names the command that would grant it (`catalyst role modify <role> --action /<command>`).
- **What counts as a grant:**
  - A role grants each `actions` entry that starts with `/`: `/status on tasks` grants `status`, `/user-add` grants
    that alias, and `/user` grants all its aliases.
  - `*` grants everything, and so does the `Admin` role. This means upgrading never locks the administrator out:
    the first `sync apply` to 0.93.0 runs as `Admin`.
  - Descriptive actions grant nothing.
- **Not checked:** a tier named as the command (`chore`, `fix`, `feature`), and a command the deployment does not
  have. Reconciliation and approval gates keep their own, stricter checks.
- **Deactivated users:** `--as` refuses one.
- **Opt-out:** a deployment may set `role_check = "warn"` in `catalyst.toml`, which warns instead.
- **Where it was written down:**
  - The meta-rule `rr-META-011` is now "Users sign; their roles grant the commands they may run". INV-16,
    `ACCESS-CONTROL.md`, `FORMAT.md` and the README follow it.
  - The kernel's roles template gives each role the commands its description means.
  - A migration, 0.93.0, asks a deployment to grant its non-Admin roles their commands. In catalyst's own deployment
    it had nothing to do: the only active user is an Admin.
- **What it means for the process module:** wording only (INV-16's module part, version 3.4.1).

## 2. Publishing

Kernel 0.91.0 was packaged from its release tag, and 0.92.0 from the checkout. The two `.vsix` files were each built
from their tag. Every file downloads without credentials. With 0.92.0 published, the desktop app's own catalyst is
raised from 0.90.0 to 0.92.0 (UI 0.55.1).

## Problems along the way

- A first design had a migration give `*` to `Admin`. But the new CLI would have refused the very `sync apply` that
  installs it, because `Admin`'s actions did not name `/sync-framework`. The `Admin` role now grants everything by
  name instead.
- A first run of the suite collected no tests, because of the shell's working directory. It ran again from the
  repository: 713 passed.

## What's left

Besides the six items the owner listed (the Marketplace token, the signing credentials, the update feed, trademark
counsel, the tagline, the Linux package's public address):

**Your decisions:**

- **R4.4:** generate the kernel's reference prose from the code, or keep it written by hand.
- **Brand item 12:** whether "criterion" becomes "the Record". The recommendation is no.
- **Brand item 5:** approve a colour and type system (`09` §5.3 proposes indigo with an amber accent). Item 6, the
  mark, needs a designer, or a draft by Claude for you to choose from.
- **R3.4:** drop the optional `catalyst migrate`, or build it.
- **Publishing 0.93.0, module 3.4.1 and UI 0.55.1** to the distribution repository: a yes each time, or a standing
  yes.

**Your time:**

- The beta trial (RM-026, RM-028, RM-029): you are its first tester (D3).
- Trying what no person has tried yet:
  - the Team and Share views in VS Code or the desktop app;
  - the desktop installers, including on a machine without catalyst;
  - Copilot and Gemini CLI through `catalyst agent run`.
- Granting commands to your deployments' non-Admin roles, if any have users.

**Work Claude can do without you:**

- Brand item 4: trace every image's source and replace the stock flask with a neutral mark of our own.
- Brand item 9: the one-line status footer in the CLI.
- R5.1: schemas for `validate`, `journal verify` and `report`.
- R7:
  - the risk-management module as a CI fixture for the kernel;
  - the deprecation window for 0.x pointers;
  - manual-change detection's switch from warning to error, prepared for 1.0.
- R4.3's documents: still 23.6 KB against a 15 KB target.

**Blocked on something outside this repository:** R4.9's module signatures and R7's signed releases wait on the
signing credentials and the release feed.
