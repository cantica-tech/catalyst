# `ANALYSIS-NNNNNN` — short title of what was analysed

| Field | Value |
|---|---|
| **ID** | `ANALYSIS-NNNNNN-<userid>` — the userid suffix is the resolved signer's (`Rules-of-Rules.md` §20); allocated by `catalyst analysis start`, never by hand |
| **Name** | short descriptive summary, e.g. `payments-service-bootstrap` |
| **Filename** | `ANALYSIS-NNNNNN-<userid>-<name>.md` |
| **Status** | exactly one of `Extracting` / `Reconciling` / `Deciding` / `Closed` / `Abandoned` — set by the `catalyst analysis` commands as each phase completes; `Closed` and `Abandoned` are its closed states |
| **Mode** | `bootstrap` (a project with no rules yet) or `incremental` (rules exist: find what they miss, and where the code breaks them) |
| **Scope** | the paths analysed, space-separated, relative to the project root |
| **Code state** | the product commit analysed (`HEAD` at `start`); every finding's evidence refers to it |
| **Opened** | YYYY-MM-DD |
| **Closed** | YYYY-MM-DD — blank until `Closed` or `Abandoned` |
| **Signed-off-by** | the registered user who started the analysis |

## Passes

Two independent, blind extraction passes over the same scope and code
state (`ANALYSIS-PLAYBOOK.md`), recorded with `catalyst analysis record
--pass A|B`: `reports/<ID>/A.json`, `reports/<ID>/B.json`.

## Reconciliation

`catalyst analysis diff` classifies the two passes' findings (agreed,
A-only, B-only, conflicting) into `reports/<ID>/diff.json`; the
reconciler's list, `reports/<ID>/reconciled.json`, accounts for every
finding of both passes.

## Decisions

One human decision per reconciled finding (`catalyst analysis decide`),
in `reports/<ID>/decisions.json`: accepted findings name the artifact
they became.

## Summary

Filled in at close: how many findings of each kind were accepted, and
the artifacts they became.
