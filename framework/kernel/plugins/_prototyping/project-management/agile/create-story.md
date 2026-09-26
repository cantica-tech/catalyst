---
description: Create a new story work item, linked to a development artifact of the active module, and register it in stories/stories.md
argument-hint: <story> --artifact <PREFIX-NNNNNN> [--epic <EPIC-NNNNNN>]
---

> **Prototype — not implemented.** Part of the agile schema at
> `plugins/_prototyping/project-management/agile/`, not a deployed
> command. No concrete project-management plugin exists yet to activate
> this; kept here as the spec a future one implements against.

Create a new story work item. Full spec: this plugin's schema, `rules-of-work-items.template.md`
(this directory), template:
`templates/TEMPLATE-STORY-v1.md` (this directory).
Input: $ARGUMENTS

1. Resolve the next `STORY-NNNNNN` ID from `stories/stories.md` + a
   directory listing of `stories/`.
2. Must link to exactly one grounded development artifact of the active
   module (`<PREFIX>-NNNNNN`) — never a substitute for one
   (`rules-of-work-items.md` §1). If none exists yet, create it first with
   the active module's own creation command.
3. Resolve who is signing this per CODE-OF-CONDUCT.md §2 and fill
   `Signed-off-by`.
4. Copy the current `TEMPLATE-STORY-vN.md`, fill every field, save as
   `stories/STORY-NNNNNN-<short-summary>.md`.
5. Register it in `stories/stories.md`.
6. Report the result. Do not commit or push — leave changes unstaged
   unless the user asks otherwise.
