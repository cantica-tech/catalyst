# `TASK-NNNNNN` — short title

| Field | Value |
|---|---|
| **ID** | `TASK-NNNNNN` |
| **Status** | todo / in-progress / review / done |
| **Parent** | `STORY-NNNNNN` (technical/maintenance work with no story goes under a development artifact of the active module directly instead) |
| **Assignee** | who's doing it |
| **Estimate** | hours or points, per team convention |
| **Signed-off-by** | name of the registered user (`IAM/users/users.json`) who signed this task — see `CODE-OF-CONDUCT.md` §2 |

## Description

Small enough to finish within a day or two. Inherits its rule target from
the parent story's development artifact — if it needs a rule the story
doesn't cover, fix the story's development artifact first rather than implementing
the gap silently at task level.

## Definition of done

Rolls up into the parent story's acceptance criteria, not new ones.

## Related

Sibling `TASK-` IDs under the same story, or blocking dependencies.
