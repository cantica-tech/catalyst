# 0.81.0 — Proposals

From `0.80.x` to `0.81.0` (design 26, owner decision P).

## What changes

- `catalyst propose <ID> --from <file>` opens a reconciliation case with `Trigger: proposal`: its `Entity`, the
  entity's file as it is (`Baseline`, its blob) and the proposed content, kept beside the case as
  `reconciliations/<RECON-id>.proposed` (`Proposed`, its blob). The entity's file is untouched.
- `catalyst reconcile <case> accept` on a proposal writes the proposed content to the entity, refused when the
  entity's file is no longer the base and for the proposed version's author; `accept-with-edits --from <file>`
  writes the acceptor's content; `propose --from <file>` revises it; its author may `close` it while it is open.
- The reconciliation template gains the `proposal` trigger and says what a proposal's `Baseline`, `Proposed` and
  `accept` mean.

## Steps

1. `catalyst sync apply --kernel <0.81.0>`: the CLI, the runtime and the recomposed documents
   (`Rules-of-Rules.md` §16 says what a proposal is).
2. **Judgment:** if the deployment keeps `reconciliations/templates/`, add the kernel's
   `templates/reconciliation.template.md` as its next version (`TEMPLATE-RECONCILIATION-v<N+1>.md`) with a row in
   `templates-reconciliation.md`, journaled; never edit an earlier version (L6). A deployment without it needs
   nothing: `catalyst propose` writes the fields itself.
3. `catalyst check`. Existing cases are disputes, as before: nothing is converted.
