# `role` — entity definition (v1)

| Field | Value |
|---|---|
| **Entity type** | `role` |
| **Version** | 1 |

## Description

A role is a named entry in `IAM/roles/roles.json` mapping to a list of actions
it's permitted to take — which slash commands or responsibilities (e.g.
"approve rule changes", "cutting releases") belong to it. Users are assigned
one or more roles via `/user assign-role`; roles themselves are managed via
`/role add|modify`.
