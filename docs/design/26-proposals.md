# 26 — Proposals: a change offered for review before it lands (design for the owner, 2026-10-17)

> **Status: decided (owner, 2026-10-17), all six choices as recommended (§7); proposals are built first, then
> [`27`](27-impact-simulation.md).** Asked for by the Studio's roadmap (R6.44 in the UI repository's
> `24`): "propose a rule or a change; reviewers see it in the inbox with its diff". Builds on reconciliation (INV-21)
> and the approval gates of [`25`](25-approval-gates.md).

## 1. Today

A change lands when someone makes it: an edit journaled by its author, or a verb (`status set`, `restore`, …) that
writes and journals at once. Review happens after the fact (the journal, `history`, a pull request on the shared
criterion) or, with a gate (`25`), as approvals of the version that is already there: the gated rule's text is in its
document, and `check` errors until it is approved.

There is no way to say "here is the text I would like this rule to have" and let someone else decide before the file
changes. Reconciliation comes closest: a `RECON-` case records two versions that disagree and a person's decision,
and its `propose` verb adds a revision in words. But a case is opened for a dispute (a conflict that stopped a push, a
rights mismatch, or by hand), its proposal is prose, not content, and accepting a case records the decision only —
applying the accepted version stays someone's ordinary work (`edit.reconcile`). The UI's own `PROP-` entity was dropped
(the UI's decision S5) because it lived outside the kernel.

## 2. The proposal: a reconciliation opened by its author, carrying the content

A proposal is a `RECON-` case whose second version is the proposed content, kept in the criterion beside the case,
and whose acceptance applies it. No new entity type: a proposal *is* two versions of one entity and a person's
decision between them, which is what a reconciliation records (INV-21). What changes is that the proposed version is
content, not prose, and that accepting it writes it.

```
catalyst propose <ID> --from <file> [--as <user>] [--intent …]      # a change to an existing entity or rule document
catalyst propose new <type> --from <file> [--as <user>] [--intent …]  # an entity that does not exist yet
```

- The case is opened (`Status: Open`, `Entity: <ID>`, a new field `Kind: proposal`), signed by the proposer.
- The proposed file is stored at `reconciliations/<RECON-id>/proposed/<path>` (its path in the criterion), with the
  **base**: the blob of the entity's file when the proposal was made.
- One journal entry (action `propose`): the case's file and the proposed file, created; the entity's own file is
  untouched.
- A rule lives in its rule document: the proposal is of the document (its whole file). Unlike `restore`, which refuses
  a document other rules share, a proposal may change one: its base pins the whole file, and the case names the rules
  whose text differs from it.
- `Kind` is a new field of the reconciliation template: a format change, shipped with its migration (owner decision
  B6); a case without it is a dispute, as today.

`catalyst view <RECON-id>` and `GET view/<id>` give the case with its base and proposed blobs, so a client shows the
diff with the history's own content (`GET history/<id>` already serves blobs). `catalyst inbox` lists an open
proposal under a new kind, `proposal`, with its entity, its proposer, the base and the proposed blob, and the verbs
that settle it.

## 3. Deciding it

The reconciliation verbs, with the same role gate (`reconciliation: full|propose|none`, §16):

| Verb | On a proposal |
|---|---|
| `accept` | Writes the proposed content to the entity's file (derived fields recomputed, as `restore` does), journaled by the person who accepts, citing the case; the case becomes `Resolved-Accepted` |
| `accept-with-edits` | The same, with the content the acceptor gives (`--from <file>`); recorded as a revision of the case |
| `reject` | Nothing is written; `Resolved-Rejected`; the proposed file stays as the record |
| `propose` | A new revision of the proposal (`--from <file>`, or `--text` for words); the earlier one is kept in the case's `Revisions` |
| `close` | Withdrawn by its author, or closed by a `full` role |

Three checks on `accept`:

1. **The base still holds.** If the entity's file has changed since the proposal (its blob is not the base), `accept`
   is refused: the proposer, or anyone, revises the proposal against the current text, or the acceptor uses
   `accept-with-edits`. No silent three-way merge (law L4: a merge is a person's).
2. **Four eyes.** The proposer never accepts their own proposal (law L4), even with a `full` role.
3. **Gates.** A gate covering the entity counts approvals of a version, its blob (`25` §3), and the proposed content
   is a version with a blob before it lands: `catalyst approve <RECON-id> --gate <gate>` approves the proposed
   version, and once accepted those approvals count for the entity, whose current blob is now that one. The author of
   that version is the proposer, not the acceptor: the `accept` entry names the proposer (`proposed_by`), and the gates'
   author lookup reads it. A gated rule then lands already approved, and `check` never errors on it.

## 4. A proposal is shared like the rest

The case and its proposed file are criterion files: they reach the team through `catalyst share push`, one pull
request for the batch, like any change. A reviewer elsewhere pulls, sees the proposal in their inbox, and decides it;
the decision is shared back the same way. Nothing new travels outside the criterion, and a served criterion
(`catalyst serve`) gives proposals through the same `view` and `inbox` routes.

## 5. In the Studio

The inbox's `proposal` items open a page with the side-by-side diff (base against proposed, the Studio's diff
component from R6.37), the case's revisions, and — through the host (W1) — `accept`, `accept-with-edits`, `reject`
and `propose`, each shown as the exact command and run on the person's yes. Making a proposal from the Studio (an
editor for the proposed text) is a later step: the first release reads and decides proposals made from the CLI or an
agent.

## 6. What it is not

Not a branch per change: one file's proposed content, decided as a whole. Not a merge tool: a proposal whose base has
moved is revised, never merged. Not mandatory: making a change directly stays allowed unless a gate covers it; a team
that wants review before every change of some kind declares a gate (`25`), and proposals are how a change reaches that
gate already approved.

## 7. Choices to confirm

1. **A proposal is a reconciliation case** (`Kind: proposal`, recommended: one entity, one role gate, one inbox kind
   per purpose), or its own kernel type (`PROPOSAL-`, more surface for the same record).
2. **The proposed content lives in the criterion** beside its case (recommended: shared like everything else), or in
   the journal's blobs only (smaller, but a pull request would not show it as a file).
3. **`accept` writes the change** (recommended: the decision and the change are one act, journaled once), or records
   the decision only, as `accept` on a dispute does today.
4. **A moved base refuses `accept`** (recommended), or `accept` tries a three-way merge.
5. **Approvals of a proposal count once it lands** (recommended: the blob is the version), or gates count only
   approvals made after it lands.
6. **What a proposal covers at 1.0**: one entity's file or one rule document (recommended), or several files at once.

## 7a. As built (kernel 0.81.0, REQ-000053)

Three departures from §2, each simpler than the text above:

- **No `Kind` field.** The reconciliation template already had `Proposer`, `Baseline` and `Proposed`; a proposal is a
  case with `Trigger: proposal`, a new value of an existing field. The template gains the value as a new version (a
  judgment step of migration 0.81.0); nothing else in the format changes.
- **The proposed content is `reconciliations/<RECON-id>.proposed`**, one file beside the case, not
  `reconciliations/<RECON-id>/proposed/<path>`: the structure check reads every `.md` under a type's folder, and a
  proposed artifact kept as `.md` there would be read as a second file with the same ID.
- **`propose new <type>` is not built.** A new rule is proposed as a change to its rule document; a new artifact is
  created directly, since there is no earlier version for review to protect. The journal entry of a proposal is a
  `create` (of the case) by `catalyst propose`, not a new `propose` action.

A revision (`reconcile <case> propose --from <file>`) re-bases the proposal on the entity as it is then, so a moved base
is settled by revising, as §3 says.

## 8. Steps once confirmed

| Step | Content |
|---|---|
| P1 | `catalyst propose <ID>\|new <type> --from <file>`: the case with `Kind: proposal`, its base, the proposed file; the `propose` journal action; `check` on a proposal's files (a missing proposed file, a base that is no blob) |
| P2 | `reconcile … accept` and `accept-with-edits` apply a proposal: the base check, the proposer never accepting; `reject`, revisions with `--from` |
| P3 | Gates: `approve <RECON-id>` approves the proposed version; `proposed_by` read as the version's author |
| P4 | `inbox` kind `proposal`; `view` gives base and proposed blobs; `serve` and the schemas; `CLI.md`, `Rules-of-Rules.md` §16 |
| P5 | The Studio (UI repository, R6.44): the proposal page with its diff and the decisions through the host |

About 4–5 kernel sessions (two releases), then 1–2 for the Studio.
