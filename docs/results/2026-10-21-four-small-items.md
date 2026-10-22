# Results — 2026-10-21: the four small items

The owner asked for the four small items the last round left, as one release. Two were the kernel's, two the UI's,
so they shipped as one release of each, the UI's built on the kernel's:

| Release | What's in it |
|---|---|
| Kernel [0.102.1](https://github.com/cantica-tech/catalyst/releases/tag/0.102.1) | Legacy-deployment messages point to `catalyst migrate --apply`; `try`'s `impact` typed (BUG-000027) |
| The UI 0.58.0 (its own repository) | The audit pack's meta-rules; `try`'s `impact` typed from `spec/`; `spec/` and the desktop app's kernel held equal; the desktop app ships kernel 0.102.1 |

Both are published in the distribution repository.

## The four items

1. **Legacy messages.** `open`, `unrecorded`, `runtime`, `move --name` and sharing through a server told a legacy
   deployment to run `catalyst move --to-home`. They now say `catalyst migrate --apply`, which moves it and catches
   it up in one step. `move --to-home` still works.
2. **`try`'s `impact`.** It is `catalyst impact --json`, but its schema typed it only as an object, because a schema
   refers only within itself. `spec/try.schema.json` now carries the impact schema in its `$defs`, and a test holds
   the copy equal to `spec/impact.schema.json`. The UI's generated type for it is now exact.
3. **The UI's copy of `spec/` and the desktop app's kernel.** A test in the UI fails when the kernel the copy was taken
   from differs from the one the desktop app ships, so syncing one means syncing the other.
4. **The audit pack's meta-rules.** This one was a bug, not only a missing mark: the UI counted every meta-rule as a
   rule nothing rests on, and flagged it so, though no work rests on a meta-rule by design and catalyst's own audit
   leaves them out. The UI now marks a meta-rule as such and never counts it as a gap (BUG-000004 in the UI's
   record).

## Checks

The kernel's 754 tests pass, with ruff, pyright, purity, the frozen surface and the generated documents. The UI's
checks were run from a clean build this time (no build output, no incremental build information), as CI runs them:
lint, format, typecheck, the browser bundle and every package's tests pass. Every pull request merged only after
every check passed.

## Problems along the way

- **A network hang:** a `git fetch` hung while syncing the UI's `spec/`; the tag was already local, so the sync ran
  from it.

## What's left

**Your decisions:**

- **This deployment's module templates:** adopt the module's seven generated templates as new versions (`catalyst
  migrate --apply --template all`), some of them, or none.
- **The brand:** the colour and type system (item 5), the mark (item 6: a designer, or Claude's drafts), the tagline
  (item 7), and "criterion" or "the Record" (item 12; the recommendation is no).
- **Declaring format 1.0:** at the 1.0 release.

**Your time:**

- The beta trial (RM-026, RM-028, RM-029).
- Trying the icons, the status line, the Team and Share views, the desktop installers, and Copilot and Gemini CLI
  through `catalyst agent run`.

**Waiting on you:** the Marketplace token, the signing credentials, the update feed, trademark counsel, and a public
address for the Linux package.

**Work Claude can do without you:** none open from these rounds.

**Blocked on something outside this repository:** module signatures (R4.9 N4) and signed releases (R7) wait on the
signing credentials and the release feed.
