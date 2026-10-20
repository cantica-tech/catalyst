# Results — 2026-10-20: `catalyst migrate` (R3.4)

The owner decided R3.4: build `catalyst migrate`, and, when asked which of its two meanings, both in one command.
Kernel [0.102.0](https://github.com/cantica-tech/catalyst/releases/tag/0.102.0) ships it, published in the
distribution repository.

## What it does

`catalyst migrate` lists what a deployment is behind on and changes nothing. `--apply` does the mechanical part,
journaled. Three kinds of step:

| Step | What it is | `--apply` |
|---|---|---|
| `layout` | A legacy deployment: a `*.catalyst` pointer, or a `.criterion` in the project, as a symlink or a submodule | Moves it to the home store, as `move --to-home` does |
| `template` | A templates folder that doesn't hold the template the kernel or its module ships today | The kernel's: added as the next version, with a catalog row. A module's: only with `--template <type>` or `all` |
| `judgment` | A step a migration since the previous sync leaves to a person (`--since <version>` lists from further back) | Never taken; listed with its qualifier ("optional", "only if the owner asks") and its migration |

Two choices shaped it:

- **"Held" is decided by content.** A template the deployment already holds, as any version, is never added again,
  even if it was copied raw from the kernel by hand. A team's own later version therefore stays the latest. Running
  it twice adds nothing.
- **A module's templates are opt-in.** The kernel's migrations require their template step wherever templates are
  kept; the module's own migration (0.87.0) calls adopting its generated templates optional. So `--apply` takes only
  the kernel's, and nothing is decided for the owner.

The new template is written exactly as `init` writes one: `init`'s seeding was factored out so both share it.

## On catalyst's own deployment

- **The kernel's templates:** all held. Two of them had been copied raw by hand during earlier migrations; they count.
- **The module's templates:** seven generated templates (BUG, FEAT, HK, REQ, RM, STEP, TEST) are offered as optional
  new versions; the deployment still writes these types from its older hand-made templates. They were not taken: that
  is the owner's call (see What's left).

## Checks

753 tests pass (746 before; seven new). ruff, pyright (0 errors), purity, frozen surface, token budgets, command
parity and the generated documents pass. `--json` is described by `spec/migrate.schema.json`, so every `--json`
command stays described. The release's pull requests merged only after every check passed.

## Problems along the way

- **A first comparison that was too strict:** the first version of `migrate` proposed 11 templates for catalyst's
  own deployment, because hand-added copies kept the kernel's notice and placeholders. Both sides are now compared
  after the same seeding, so a raw copy counts as held.
- **The journal's actions are a closed set:** "migrate" was refused; a template version added is an `update`.

## What's left

**Your decisions:**

- **This deployment's module templates:** adopt the module's seven generated templates as new versions (`catalyst
  migrate --apply --template all`), some of them, or none. New BUGs, REQs and the rest would then be written with the
  current fields (`Assignee`, `Opened`, the module's status names).
- **The brand:** the colour and type system (item 5), the mark (item 6: a designer, or Claude's drafts), the tagline
  (item 7), and "criterion" or "the Record" (item 12; the recommendation is no).
- **Declaring format 1.0:** at the 1.0 release.

**Your time:**

- The beta trial (RM-026, RM-028, RM-029).
- Trying the icons, the status line, the Team and Share views, the desktop installers, and Copilot and Gemini CLI
  through `catalyst agent run`.

**Waiting on you:** the Marketplace token, the signing credentials, the update feed, trademark counsel, and a public
address for the Linux package.

**Work Claude can do without you:**

- The messages that point a legacy deployment to `catalyst move --to-home` (`open`, `unrecorded`, the share
  commands) could point to `catalyst migrate --apply`, which moves it and catches up in one step.
- From the last round: typing `try`'s `impact` field; showing the audit pack's `meta` mark; a UI check that its copy
  of `spec/` matches the kernel the desktop app ships.

**Blocked on something outside this repository:** module signatures (R4.9 N4) and signed releases (R7) wait on the
signing credentials and the release feed.
