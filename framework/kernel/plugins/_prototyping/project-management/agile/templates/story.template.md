# `STORY-NNNNNN` — short title

| Field | Value |
|---|---|
| **ID** | `STORY-NNNNNN` |
| **Status** | backlog / ready / in-progress / review / done |
| **Epic** | `EPIC-NNNNNN` (or "none") |
| **Targets** | rule ID(s) this story implements/extends — required per `CODE-OF-CONDUCT.md` §1; if none exist yet, see Development artifact below |
| **Development artifact** | `<PREFIX>-NNNNNN` — the corresponding grounded artifact of the active module, which owns rule-compliance bookkeeping. Create it first if it doesn't exist |
| **Points** | story-point estimate |
| **Domain** | `DOMAIN` code(s), from the linked development artifact/rule IDs |
| **Signed-off-by** | name of the registered user (`IAM/users/users.json`) who signed this story — see `CODE-OF-CONDUCT.md` §2 |

## Story

As a **\<role\>**, I want **\<capability\>**, so that **\<benefit\>**.

## Acceptance criteria

Given/When/Then, one block per criterion — should mirror the acceptance
criteria already in the linked development artifact, not diverge from them.

- **Given** … **When** … **Then** …

## Tasks

| Task | Title | Status |
|---|---|---|
| `TASK-NNNNNN` | … | … |

## Related

Other `STORY-`/`TASK-`/`SPIKE-` IDs, or rule IDs.
