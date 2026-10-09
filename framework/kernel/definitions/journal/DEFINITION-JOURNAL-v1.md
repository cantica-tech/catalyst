# `journal` — entity definition (v1)

| Field | Value |
|---|---|
| **Entity type** | `journal` |
| **Version** | 1 |

## Description

The journal (`development/journal/`, one shard per actor, machine and month)
is an append-only log of events
across a deployment's lifetime — one JSON line per entry, never rewritten or
reordered. It's read-only from every command's perspective except the one that
appends to it; `/journal` filters and reports over it without ever mutating it.
