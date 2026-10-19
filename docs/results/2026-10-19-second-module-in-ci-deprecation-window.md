# Results — 2026-10-19: a second module in CI, the deprecation window, manual-change detection

Three R7 items for 1.0, and one bug found along the way, in kernel 0.94.0, released.

| Release | What's in it |
|---|---|
| Kernel [0.94.0](https://github.com/cantica-tech/catalyst/releases/tag/0.94.0) | The deprecation window for 0.x deployments (REQ-000073); a second module in CI (HK-000005); BUG-000022 |

## 1. The risk-management module in the kernel's CI (HK-000005)

- **What the test does** (`tests/test_second_module.py`):
  - installs the published risk-management module into a scratch project;
  - adds a domain and a rule, then creates a risk, the control treating it and an incident;
  - checks the risk lists its control by itself;
  - confirms each closing state is refused until its section is written (Evidence, Lessons, Treatment);
  - reads the list, the graph and the audit, checks the module's own tiers are inferred, and ends with a clean
    `check`.
- **CI:** it checks the module out at its release tag (0.1.0) and runs the test on Linux, macOS and Windows, where it
  cannot be skipped. Locally it is skipped without the sibling checkout.
- **Result:** the first CI run passed on all six platform and Python combinations.

## 2. The deprecation window for 0.x deployments (REQ-000073, R3.4)

- `catalyst check` warns about a project still on a `<name>.catalyst` pointer, or with its criterion outside
  catalyst's home, and names `catalyst move --to-home`.
- Once a project declares format 1.0, every writing verb refuses on such a deployment: read-only, as decided for one
  minor version after 1.0. Until then nothing changes but the warning.
- catalyst's and the UI's own deployments get no warning.

## 3. Manual-change detection (R7)

Already built and tested since 0.42.0: it warns under format `1.0-rc` and errors under `1.0` (or with
`strict_journal`). It flips when a deployment declares 1.0, which `check` does not accept yet. Declaring 1.0 is the
owner's, at the 1.0 release.

## 4. BUG-000022

`catalyst new` left an optional field's template hint in place, which `check` then warned about. It showed on
HK-000005's `Priority`, and an earlier bug's `Area` had the same hint. The field is now written empty.

## Problems along the way

- **The private criterion repositories' checks were stuck for about 40 minutes.**
  - The cause was GitHub's own incident ("Degraded availability for GitHub Actions, GitHub Pages and Webhooks").
  - Not the cause: billing showed no Actions use by the private repositories this month, Actions are enabled, and
    the runner is the standard one.
- The purity check caught a module named in the CHANGELOG; reworded.
- A background job from before the incident merged the criterion pull request once its check passed. It had nothing
  left to commit, so nothing was duplicated.

All 716 kernel tests pass locally; CI ran 710, with 4 environment skips that were already there.

## What's left

**Your decisions:**

- **R4.4:** generate the kernel's reference prose from the code, or keep it written by hand.
- **The brand:** the colour and type system (item 5), the mark (item 6: a designer, or Claude's drafts), and
  "criterion" or "the Record" (item 12; the recommendation is no).
- **R3.4:** drop the optional `catalyst migrate`, or build it.
- **Publishing:** kernel 0.93.0 and 0.94.0, module 3.4.1 and the UI 0.55.1 to the distribution repository, each time
  or as a standing yes.
- **Declaring format 1.0:** when 1.0 ships. It turns unrecorded changes into errors and makes legacy deployments
  read-only.

**Your time:**

- The beta trial (RM-026, RM-028, RM-029).
- Trying the Team and Share views, the desktop installers, and Copilot and Gemini CLI through `catalyst agent run`.

**Waiting on you:** the Marketplace token, the signing credentials, the update feed, trademark counsel, the tagline,
and a public address for the Linux package.

**Work Claude can do without you:**

- Schemas for `validate`, `journal verify` and `report` (R5.1).
- Brand item 4: replace the stock flask with a mark of our own.
- Brand item 9: the CLI's status footer.
- The kernel's documents: 23.6 KB against a 15 KB target (R4.3).
- `check` accepting format 1.0, ready for the release.

**Blocked on something outside this repository:** module signatures (R4.9 N4) and signed releases (R7) wait on the
signing credentials and the release feed.
