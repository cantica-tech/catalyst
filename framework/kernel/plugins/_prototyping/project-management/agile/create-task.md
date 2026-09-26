---
description: Create a new task work item under a parent story and register it in tasks/tasks.md
argument-hint: <task> --story <STORY-NNNNNN>
---

> **Prototype — not implemented.** Part of the agile schema at
> `plugins/_prototyping/project-management/agile/`, not a deployed
> command. No concrete project-management plugin exists yet to activate
> this; kept here as the spec a future one implements against.

Create a new task work item. Full spec: this plugin's schema, `rules-of-work-items.template.md`
(this directory), template:
`templates/TEMPLATE-TASK-v1.md` (this directory).
Input: $ARGUMENTS

1. Resolve the next `TASK-NNNNNN` ID from `tasks/tasks.md` + a
   directory listing of `tasks/`.
2. A task never gets its own rule target — it inherits its parent story's
   (`rules-of-work-items.md` §2). If it needs a rule the story doesn't
   cover, fix the story's development artifact first.
3. Resolve who is signing this per CODE-OF-CONDUCT.md §2 and fill
   `Signed-off-by`.
4. Copy the current `TEMPLATE-TASK-vN.md`, fill every field, save as
   `tasks/TASK-NNNNNN-<short-summary>.md`.
5. Register it in `tasks/tasks.md`.
6. Report the result. Do not commit or push — leave changes unstaged
   unless the user asks otherwise.
