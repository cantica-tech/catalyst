# `WORKFLOW-NNNNNN` — short title

> A process-definition document, not a unit of work: never itself "done"
> (`Rules-of-Rules.md` §19). Documents how a category of work or a
> procedure (e.g. an item's triage-to-resolution path, or how to resolve a
> particular recurring kind of reconciliation) moves through its steps.
> Other core entities may optionally reference one by ID to guide their
> own process — `RECON-` reconciliation cases are the first to do so
> (`Rules-of-Rules.md` §16).

| Field | Value |
|---|---|
| **ID** | `WORKFLOW-NNNNNN-<userid>` — the userid suffix is the resolved signer's (`Rules-of-Rules.md` §20) |
| **Name** | short descriptive summary summarizing the workflow's purpose — follows Rules of Rules naming conventions |
| **Status** | `Active` / `Deprecated` |
| **Defined** | YYYY-MM-DD |
| **Signed-off-by** | name of the registered user (`IAM/users/users.json`) who signed this workflow — see `CODE-OF-CONDUCT.md` §2 |

## Purpose

What this process governs, and why it exists as a documented procedure
rather than tribal knowledge.

## Steps

1. …
2. …

## Gates / exit criteria

What must be true for work to move from one step to the next, or to be
considered complete.

## Related

Other `WORKFLOW-`/`RECON-` IDs, or (only if a project-management plugin
happens to be active) `EPIC-`/etc. work-item IDs, this depends on,
supersedes, or overlaps with. If this workflow replaces an older one,
name it and mark that one `Deprecated` here (never delete — retire in
place).
