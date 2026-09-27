# `RECON-NNNNNN` — short title

> A reconciliation case: two diverging versions of an existing entity
> that need resolving, never a unit of work with its own acceptance
> criteria (`Rules-of-Rules.md` §16). Opened by `/criterion push`'s
> vet+merge step when it can't cleanly reconcile two versions of the
> same entity — a git-level conflict, a vetting-flagged semantic clash,
> or a rights-mismatch (`Rules-of-Rules.md` §11) — or manually.

| Field | Value |
|---|---|
| **ID** | `RECON-NNNNNN-<userid>` — the userid suffix is the resolved signer's/proposer's (`Rules-of-Rules.md` §20) |
| **Name** | short descriptive summary summarizing the reconciliation's purpose — follows Rules of Rules naming conventions |
| **Entity** | type + ID/path of the artifact actually being reconciled |
| **Workflow** | `WORKFLOW-NNNNNN` guiding this case's resolution, if any — optional, leave blank unless a documented procedure for this recurring kind of conflict exists (`Rules-of-Rules.md` §19) |
| **Trigger** | `rights-mismatch` / `merge-conflict` / `manual` |
| **Status** | `Open` / `Under Review` / `Resolved-Accepted` / `Resolved-Accepted-with-Edits` / `Resolved-Rejected` / `Closed` |
| **Proposer** | name (role) — see `IAM/users/users.json` |
| **Baseline** | content hash + short description of `criterion`'s version at open time |
| **Proposed** | content hash + short description of the proposer's version |
| **Opened** | YYYY-MM-DD |
| **Resolved** | YYYY-MM-DD (blank until `Status` leaves `Open`/`Under Review`) |
| **Resolver** | name (role) — blank until resolved |
| **Signed-off-by** | name of the registered user who opened this case — see `CODE-OF-CONDUCT.md` §2 |

## Description

Why the two versions diverge, in plain language — what each side changed
and why, not just that they differ.

## Revisions

Append-only within this section, never a new file per round (unlike
`templates/`'s own versioning) — this case's own edit history, journaled
via the normal before/after content-hash mechanism (INV-17) like any
other edit to this file:

| Round | Author | Timestamp | Content hash | Note |
|---|---|---|---|---|
| 1 | {{proposer}} | {{timestamp}} | {{hash}} | Initial proposal |

## Resolution

Final decision and rationale, filled in once `Status` moves to a
`Resolved-*` state. `Resolved-Accepted` merges `Proposed` into
`criterion` as-is; `Resolved-Accepted-with-Edits` merges the last
revision's content instead; `Resolved-Rejected` leaves `criterion`
unchanged and flags the proposer's local divergence for reverting.

## Related

Other `RECON-`/rule/entity IDs this touches.
