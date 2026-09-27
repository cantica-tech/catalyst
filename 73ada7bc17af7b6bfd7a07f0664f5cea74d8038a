---
description: Create a new story work item, linked to a REQ-/BUG- doc, and register it in stories/stories.md
argument-hint: <story> --req <REQ-NNNNNN|BUG-NNNNNN> [--epic <EPIC-NNNNNN>]
---

Create a new story work item. Full spec:
`.catalyst-proj/CODE-OF-CONDUCT.md` §4,
`.catalyst-proj/work-items/rules-of-work-items.md`, template:
`.catalyst-proj/work-items/stories/templates/TEMPLATE-STORY-v1.md`.
Input: $ARGUMENTS

1. Resolve the next `STORY-NNNNNN` ID from `stories/stories.md` + a
   directory listing of `stories/`.
2. Must link to exactly one `REQ-NNNNNN` or `BUG-NNNNNN` — never a substitute
   for one (`rules-of-work-items.md` §1). If none exists yet, create it
   first via `/create-req`/`/create-bug`.
3. Resolve who is signing this per CODE-OF-CONDUCT.md §2 and fill
   `Signed-off-by`.
4. Copy the current `TEMPLATE-STORY-vN.md`, fill every field, save as
   `stories/STORY-NNNNNN-<short-summary>.md`.
5. Register it in `stories/stories.md`.
6. Report the result. Do not commit or push — leave changes unstaged
   unless the user asks otherwise.
