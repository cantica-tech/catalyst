# Results — 2026-10-20: the UI's types generated from `spec/`

The owner said yes to the follow-up the last round left: the UI's types for what catalyst prints are now generated
from catalyst's `spec/`, not written by hand. The UI calls it R6.50 (decision S7 in its own repository).

Generating them did more than replace types: comparing each generated type with the hand-written one found mistakes
on both sides. Two schemas were looser than what catalyst prints, and those were fixed here, in catalyst, not
worked around in the UI.

| Release | What's in it |
|---|---|
| Kernel [0.101.1](https://github.com/cantica-tech/catalyst/releases/tag/0.101.1) | `approvals`: a gate's `covers` gives its two exact shapes; `analysis`: a dropped finding's `source` and `reason` (BUG-000025) |
| Kernel [0.101.2](https://github.com/cantica-tech/catalyst/releases/tag/0.101.2) | `analysis`: each field of a reconciled finding, which the schema had named only in prose (BUG-000026) |
| The UI 0.57.0 (its own repository) | Its types generated from `spec/` at 0.101.2; the desktop app ships kernel 0.101.2 |

All three are published in the distribution repository.

## How it works

- **The source:** the UI keeps a copy of `spec/` at one kernel release, with that release's tag beside it. One
  command replaces the copy from a catalyst checkout at a tag.
- **The generator:** a small script of the UI's own, with no dependency, writes the types from the copy. A keyword it
  does not handle is refused, so a new one can't be dropped silently. A test fails when the generated file differs
  from what the copy generates.
- **Older kernels:** the UI supports kernels from 0.54.0. Where an older kernel lacks a field the UI reads, the field
  is marked optional, with the version that added it. Where a newer kernel may add something, as a new kind in the
  inbox, the UI accepts it. Both allowances are written once, beside the types.

## What the comparison found

**In catalyst's schemas** (fixed in 0.101.1 and 0.101.2):

- An approval gate's `covers` was any object, although `IAM/gates.json`'s own schema gives its two shapes. A malformed
  one passed.
- An analysis's findings named their fields (title, statement, evidence, …) only in a sentence, so a client's types
  knew nothing of them.

**In the UI** (fixed in 0.57.0):

- A rule with no status line would have thrown in the rule browser and the search: the UI assumed every rule has a
  status.
- The type map counted a closed table row as open: a row's status is under `fields`, and the map read it at the top.
- Four copies of a row's field lookup became one, shared by the VS Code tree and the browser views.
- Test fixtures described shapes catalyst never prints: a row's columns flat, no `mentions`, a plan's migrations as
  paths. Fixtures are now built as catalyst prints them.
- Seven of the 21 compared types matched both ways. The others differed in the ways above, or where the UI had not
  caught up (an inbox item's author can be null; an audit pack's rules carry `meta`), or where a field is optional
  for older kernels, or where the schema is more exact (closed lists of states and kinds).

## Checks

The kernel's 746 tests pass, with ruff, pyright, purity and the generated documents. In the UI, every package's tests
pass (core 183, the browser views 142, and the rest), with `tsc`, eslint and prettier. Every pull request merged only
after every check passed, Windows included.

## Problems along the way

The UI's first pull request for 0.57.0 failed CI twice; the gate stopped both times, so nothing merged until it passed.

- **A stale build:** local checks passed on incremental build information, which hid a type error in the VS Code
  host's tests. CI builds from nothing and caught it. Fixed, and the checks were rerun from a clean build.
- **A bundle that reached node modules:** the browser views imported the shared row helpers from the core package's
  root, which also loads the parts that run commands. Bundling for a browser failed. The helpers now have their own
  browser-safe entry.

## What's left

**Your decisions:**

- **The brand:** the colour and type system (item 5), the mark (item 6: a designer, or Claude's drafts), the tagline
  (item 7), and "criterion" or "the Record" (item 12; the recommendation is no).
- **R3.4:** drop the optional `catalyst migrate`, or build it.
- **Declaring format 1.0:** at the 1.0 release.

**Your time:**

- The beta trial (RM-026, RM-028, RM-029).
- Trying the icons, the status line, the Team and Share views, the desktop installers, and Copilot and Gemini CLI
  through `catalyst agent run`.

**Waiting on you:** the Marketplace token, the signing credentials, the update feed, trademark counsel, and a public
address for the Linux package.

**Work Claude can do without you:**

- `try`'s `impact` field points to another schema file, which the test checker can't follow, so the UI's type for it is
  `unknown`. The UI doesn't read it yet; if it ever does, inlining the impact schema would type it.
- An audit pack marks each rule `meta`, which the UI now knows of but doesn't show.
- Each kernel release can change `spec/`; the UI's copy moves only when someone syncs it. A check in the UI's CI that
  the copy matches the kernel it pins for the desktop app would keep the two together.

**Blocked on something outside this repository:** module signatures (R4.9 N4) and signed releases (R7) wait on the
signing credentials and the release feed.
