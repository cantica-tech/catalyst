---
description: Create a new board container and register it in boards/boards.md
argument-hint: <board-name>
---

Create a new board container. Full spec:
`.catalyst-proj/CODE-OF-CONDUCT.md` §4,
`.catalyst-proj/work-items/rules-of-work-items.md`, template:
`.catalyst-proj/work-items/boards/templates/TEMPLATE-BOARD-v1.md`.
Input: $ARGUMENTS

**Kanban/Scrumban flavor only** — the structural counterpart to
`/create-sprint`. Refuse (pointing at the project's chosen agile flavor,
`rules-of-work-items.md` §2) if this deployment uses Scrum instead.

1. Resolve the next `BOARD-NNNNNN` ID (6 digits) from
   `boards/boards.md` + a directory listing of `boards/`.
2. `Status: Active`. Stories/tasks reference this board in place of
   sprint membership — never both at once for the same item.
3. Resolve who is signing this per CODE-OF-CONDUCT.md §2 and fill
   `Signed-off-by`.
4. Copy the current `TEMPLATE-BOARD-vN.md`, fill every field, save as
   `boards/BOARD-NNNNNN-<short-summary>.md`.
5. Register it in `boards/boards.md`.
6. Report the result. Do not commit or push — leave changes unstaged
   unless the user asks otherwise.
