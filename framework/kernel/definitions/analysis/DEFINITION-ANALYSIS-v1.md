# `analysis` — entity definition (v1)

| Field | Value |
|---|---|
| **Entity type** | `analysis` |
| **Version** | 1 |

## Description

An `ANALYSIS-NNNNNN` record follows one four-eyes analysis of existing
code (`ANALYSIS-PLAYBOOK.md`, `/run-analysis`): its scope and mode, the
product commit analysed, two independent blind extraction passes, their
matched findings, the reconciled list that accounts for every finding of
both passes, and one human decision per reconciled finding — domains,
rules and rule-grounded defects. Its phases (`Extracting`, `Reconciling`,
`Deciding`, then `Closed` or `Abandoned`) are set by the `catalyst
analysis` commands, never by hand; `catalyst check` rejects a record whose
reports do not support its phase. Lives in `analyses/`, its reports in
`analyses/reports/<ID>/`.
