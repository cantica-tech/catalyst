# Results — 2026-10-25: designs 30 and 31, and a change forewarned before it is permanent (kernel 0.112.0)

| What                                                                                         | Where                                                     |
| -------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Kernel [0.112.0](https://github.com/cantica-tech/catalyst/releases/tag/0.112.0) (REQ-000093) | `cantica-tech/catalyst` (PRs 331, 332); distribution repo |
| Design 30, visibility (proposed)                                                             | `docs/design/30-visibility.md`                            |
| Design 31, who creates, edits and deletes what (decided)                                     | `docs/design/31-who-changes-what.md`                      |

- **Design 30** (the owner's answers): a person sees their own work and its direct links, queries the rest, never above
  their clearance unless elevated; hidden results are absent; Admin above all, a Criterion Admin in their project;
  user groups (assignment-scoped, the lowest clearance of their members, members of the project); **no one outside
  the catalyst realm has any access**; the server as the read boundary, its self-issued tokens to go.
- **Design 31** (decided): admins change directly, forewarned; others create the module's types their grants allow,
  edit or retire what is unlinked, and route a linked entity's change through its workflow (tag, type, then
  criterion); deleting is retiring; no one edits an ID.
- **Kernel 0.112.0**, design 31's first phase: every writing verb takes `--preview` (its `catalyst try`) and
  `--forewarned` (tried first, made anyway, the `check` findings it adds recorded in its journal entry by catalyst
  itself), `fw-STRUCTURE-000019`. The full suite passed (821); every job of both pull requests passed before merging.

## What's left

- **Design 30's eight open questions** (§8), first among them what makes a person a member of a project.
- **Design 31's next phases**: contributors' types and grants, edits and retirements through workflows, tags and tag
  workflows.
- **The server's self-issued tokens** (`serve token issue`), which let in someone outside the realm, until design 30's
  phase 2.
