# Results — 2026-10-18: decisions B7–B9, the second module, G4 and G5

Everything for decisions B7 (rule storage), B8 (embeds), B9 (assignee and roadmap dates) and the risk-management
module's repository is built and released on GitHub. Nothing has been published to the Marketplace or the
distribution repository yet.

| Release | What's in it |
|---|---|
| Kernel [0.86.0](https://github.com/cantica-tech/catalyst/releases/tag/0.86.0) | The installed modules, their available releases and an upgrade's plan, readable by the Studio |
| Kernel [0.87.0](https://github.com/cantica-tech/catalyst/releases/tag/0.87.0) | The audit pack, the README badge, decisions 1–3 below, and the DNS fix |
| Process module [3.4.0](https://github.com/cantica-tech/catalyst-software-engineering/releases/tag/3.4.0) | Assignee on work, start and due dates on roadmap rows |
| Risk-management module [0.1.0](https://github.com/cantica-tech/catalyst-risk-management/releases/tag/0.1.0) | The second module, in a new public repository |
| The UI 0.52.0 (its own repository) | All of G4 and G5 |

## 1. Rule storage (R0.9, decision B7)

A rule can be either a heading in a rule document or a file of its own, and both are checked the same way. The new
decision ADR-000047 supersedes ADR-001 (ADR-000025 in the record). `check` now rejects a rule file that also
contains a rule heading, because that file used to be read as a document and its own rule was silently lost.

## 2. Embedding in other sites (decision B8)

`catalyst serve --allow-origin <origin>`, or `embed_origins` in `catalyst.toml`, lets pages from those sites read
the record. Each read still needs its reader's token, nothing can be written, and no site is allowed unless it is
named. In the UI, `embed.js` provides `<catalyst-entity>`, which shows one entity's title, status and what cites it
on another site's page.

## 3. Assignee and roadmap dates (decision B9)

- The process module's work types now have an optional `Assignee`, and roadmap rows have optional `Start` and `Due`
  dates.
- `check` warns when an assignee isn't a registered user.
- Fixed along the way: `catalyst new` used to fill every person field with whoever created the item, so new items
  were assigned to their creator. Optional ones now stay empty unless set.
- In the Studio, the Team view shows each person's open work, and the Roadmap view has a Gantt chart.

## 5. Risk-management module

Created at `cantica-tech/catalyst-risk-management`, public like the process module, with `main` as the default
branch, and added to catalyst's module catalog (`framework/modules/catalog.md`).

## Problems along the way, all fixed before release

- CI's type check caught one error in a new test, which was fixed.
- One UI check needed a re-run because it started before the UI criterion PR had merged.
- A second Claude session worked on the UI alongside this one. The repositories were split between the two
  sessions, and it made most of the UI commits before it ended.

All tests pass: 688 in the kernel, and every UI package. CI passed on every platform. Nobody has tried any of the
new views in the real app yet, or the embed on another site's page.

## Still open

- **Decision 4:** the desktop app's code signing and auto-update need certificates and an update server the owner
  would own.
- **Unaudited items:** the rest of the R4.8 journal-hygiene findings, and the UI's last few small file reads
  (R5.3).
- **Publishing:** UI 0.52.0 to the Marketplace and the distribution repository, and kernel 0.87.0 to the
  distribution repository, each waiting on the owner's yes.
