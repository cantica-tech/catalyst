# `workflow` — entity definition (v2)

| Field | Value |
|---|---|
| **Entity type** | `workflow` |
| **Version** | 2 |

## Description

A `WORKFLOW-NNNNNN` is a process-definition document, not a unit of
work: it documents a repeatable multi-step procedure (e.g. how an item
moves from triage to resolution) rather than tracking a specific piece of
work. Other core entities may reference one by ID to guide their own
process; reconciliation cases are the first to do so.

A workflow may also **govern** an entity type (`Governs`): while it is
`Active`, its `## Transitions` table is the moves that type may make, each
with the role its signer must hold and a condition on the entity's fields,
and `catalyst status set` refuses any other move (`--force` does not pass
it). One type has at most one active governing workflow. `Escalates to`
names the role an overdue entity of that type is escalated to in the
inbox. Lives in the `workflows/` root folder, registered in `workflows.md`.
