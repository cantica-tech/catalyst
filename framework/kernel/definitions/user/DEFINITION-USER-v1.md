# `user` — entity definition (v1)

| Field | Value |
|---|---|
| **Entity type** | `user` |
| **Version** | 1 |

## Description

A registered user is one entry in `IAM/users/users.json` — a name (and optional
metadata) that can appear in any artifact's Signed-off-by field and be assigned
one or more roles from `IAM/roles/roles.json`. Users are added via `/user add`,
never deleted (only deactivated via `/user remove`), so existing Signed-off-by
references stay resolvable forever.
