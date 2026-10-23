# `user` — entity definition (v2)

| Field | Value |
|---|---|
| **Entity type** | `user` |
| **Version** | 2 |

## Description

A user is an identity catalyst-users verifies: a person logged in to the provider `IAM/identity.json` points at, or a
machine's system account when no one is logged in. The criterion keeps no registry of them. Each identity's first
signature appends one line to `IAM/signers.jsonl`: the userid every ID it creates ends with, its issuer and subject
(which identify it for good), and a snapshot of its username and name. People are added, disabled and granted in
catalyst-users, never deleted, so existing Signed-off-by references stay resolvable forever.
