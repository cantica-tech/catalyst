# `workflow` — entity definition (v1)

| Field | Value |
|---|---|
| **Entity type** | `workflow` |
| **Version** | 1 |

## Description

A `WORKFLOW-NNNNNN` is a process-definition document, not a unit of
work — it documents a repeatable multi-step procedure (e.g. how an
item moves from triage to resolution) rather than tracking a specific piece
of work. Other core entities may optionally reference one by ID to
guide their own process; reconciliation cases are the first to do so.
Lives in the `workflows/` root folder, registered in `workflows.md`.
