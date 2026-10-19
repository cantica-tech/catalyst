# Results — 2026-10-19: every payload described, no image of unknown licence, a status line

Kernel 0.95.0 and 0.96.0 and UI 0.56.0 are released.
The workspace was also set up for every repository this work touches.

| Release | What's in it |
|---|---|
| Kernel [0.95.0](https://github.com/cantica-tech/catalyst/releases/tag/0.95.0) | Schemas for `validate`, `journal verify` and `report` (REQ-000074); `check` reads format 1.0 (REQ-000075) |
| The UI 0.56.0 (its own repository) | The inspector's icons are VS Code's own; a placeholder mark of our own (brand item 4) |
| Kernel [0.96.0](https://github.com/cantica-tech/catalyst/releases/tag/0.96.0) | A status line after each command (REQ-000076, brand item 9) |

## 1. The workspace

- **VS Code:** the workspace file, which git ignores, now lists every repository this work touches: the kernel, the
  UI, both modules and the distribution repository. It also lists catalyst's and the UI's criteria. Those are
  excluded from the extension's install offer, being records rather than projects.
- **Claude Code:** its project settings name the same directories.

## 2. Every machine-readable output has a schema (R5.1, kernel 0.95.0)

- `spec/validate.schema.json`, `spec/journal-verify.schema.json` and `spec/report.schema.json` are written from the
  code that builds each payload.
- They hold for the test fixture and for catalyst's and the UI's real output, including catalyst's 90 journal issues.
  A wrong payload is refused.
- R5.1 is marked done.

## 3. Format 1.0 is readable (kernel 0.95.0)

`check` accepts a deployment that declares format `1.0`. Such a deployment gets the release's strictness: unrecorded
changes are errors, and legacy deployments are read-only. `init` still writes `1.0-rc`; declaring 1.0 stays the
owner's, at the release.

## 4. No image of unknown licence (brand item 4, UI 0.56.0)

- **The audit:** 37 images, all in the UI. Seven carried the signature of Flaticon/Freepik downloads, whose free
  licence asks for credit; the rest had no recorded source; one was unused.
- **The inspector's icons:** its section and type icons are now VS Code's own Codicons. They ship with VS Code and
  follow its themes, and they cover the decision, risk-management and other types the old set lacked. The 35 stock
  SVGs are gone.
- **The flask:** replaced by a neutral placeholder mark of our own drawing, three linked nodes for rule, work and
  commit. The Marketplace and desktop icons show it in white on neutral slate, with no brand colour: colour is item 5,
  the real mark item 6.
- **The sources:** the UI repository's `brand/`, with how to regenerate the PNGs.

## 5. A status line after each command (brand item 9, kernel 0.96.0)

- On an interactive terminal, a command ends with one line on stderr:
  `catalyst · <project> · checked 14:08 · 0 error(s), 3 warning(s)`.
- It shows the last check's result, which `check` now records in the criterion's git directory. It never runs a
  check.
- It never reaches a pipe or an agent, and never appears with `--json`. `CATALYST_FOOTER=0` turns it off.

## 6. R4.3's 15 KB target retired (decision D6)

The target was for the process module's `module.yaml` (26.3 KB), not for the kernel's documents, as earlier results
said. Reaching 15 KB would have meant rewriting the generated templates and definitions, with a new template version
and a definition migration for each of its 8 types in every deployment. The owner retired the target instead: agents
never read `module.yaml` whole; the kernel does. That is the reason the 30 KB prose target was retired on
2026-10-16. Its comments stay, since they explain the file to module authors.

## Problems along the way

- Earlier results called R4.3 "the kernel's documents: 23.6 KB against 15 KB". It was the module's `module.yaml`;
  the kernel's documents are R4.4.

- My first status-line code left a quoted type annotation and an unused `noqa`; ruff and pyright caught both.
- Two shell loops split their arguments wrongly in zsh: a schema check, and a file lookup by full ID. Both were rerun
  correctly.
- The first render of the mark showed the connecting lines biting into a ring; the segments were shortened.

All tests pass: 725 in the kernel, every UI package.

## What's left

**Your decisions:**

- **R4.4:** generate the kernel's reference prose from the code, or keep it written by hand.
- **The brand:** the colour and type system (item 5), the mark (item 6: a designer, or Claude's drafts), the tagline
  (item 7), and "criterion" or "the Record" (item 12; the recommendation is no).
- **R3.4:** drop the optional `catalyst migrate`, or build it.
- **Publishing:** kernel 0.93.0 to 0.96.0, module 3.4.1 and the UI 0.55.1 to 0.56.0 to the distribution
  repository, each time or as a standing yes. With 0.96.0 published, the desktop app's own catalyst can be raised
  from 0.92.0.
- **Declaring format 1.0:** at the 1.0 release.

**Your time:**

- The beta trial (RM-026, RM-028, RM-029).
- Trying the Team and Share views, the desktop installers, the new icons, the status line, and Copilot and Gemini
  CLI through `catalyst agent run`.

**Waiting on you:** the Marketplace token, the signing credentials, the update feed, trademark counsel, and a public
address for the Linux package.

**Work Claude can do without you:** nothing left on the roadmaps. R4.3 is retired (D6). The remaining brand items (2,
3, 5, 6, 7, 10, 11 and 12) and R4.4 wait on decisions.

**Blocked on something outside this repository:** module signatures (R4.9 N4) and signed releases (R7) wait on the
signing credentials and the release feed.
