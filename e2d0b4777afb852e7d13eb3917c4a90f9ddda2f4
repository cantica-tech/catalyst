---
description: Vet catalyst's own repository against its own rules (check-rules + a four-eyes drift check); reports, never fixes. Catalyst-development-only. `recreate` additionally runs a blind recreation drift check.
argument-hint: "[recreate]"
---

Dogfood catalyst's own repository. Full spec:
`framework/kernel/rules-of-rules.template.md` §13 ("`/dogfood` is
catalyst-development-only") and, for the `recreate` mode, §18
("Recreation drift check").
Input: $ARGUMENTS

**This command is not part of the catalyst framework's deployed command
set** — it's never listed in `CODE-OF-CONDUCT.md` §4, and
`INSTANTIATION-GUIDE.md`/`SYNCHRONIZE.md` never materialize it into a
deployed project. It exists only here, in catalyst's own repository, for
verifying catalyst's own rules against catalyst's own actual state.

1. Parse `$ARGUMENTS`. Empty runs the default checks below (steps 2–4).
   The literal token `recreate` additionally runs step 3's recreation
   drift check. Anything else — ask for clarification rather than
   guessing a mode.
2. Run `scripts/check_deployment.py`/`scripts/check_plugins.py`/
   `scripts/check_plugin_contracts.py`/`scripts/check_command_parity.py`
   and the pytest suite against `.criterion/` — the structural half of
   `/check-rules`. Always runs, regardless of `$ARGUMENTS`.
3. **Only when `recreate` was given** — the recreation drift check
   (`rules-of-rules.template.md` §18): spawn the isolated agent, get its
   report, then compare it yourself against `.criterion/rules/framework/
   fw-framework-rules.md`'s existing `INV-N` coverage. Full mechanics live
   in §18, not here. When active, launch this spawn alongside step 4's
   four-eyes pair in the same message — independent spawns, no reason to
   run them sequentially.
4. Spawn two independent four-eyes sub-agents (no shared context) that
   each separately evaluate whether catalyst's actual state (code, tests,
   docs) still matches what `.criterion/rules/framework/fw-framework-rules.md`
   claims: for a ✅ rule, does the cited `file:line` still hold with real
   test coverage; for a ⚠️/❌ rule, is that status still accurate rather
   than stale.
5. Reconcile step 4's pair. Where they disagree, surface the disagreement
   rather than silently picking one. If `recreate` was given, reconcile
   step 3's findings separately — evidence staleness (step 4/5) and
   coverage existence (step 3) are different failure classes, not one
   merged pass.
6. Report every drift found — step 2's structural findings, step 3's
   coverage gaps (`recreate` mode only), and step 4/5's evidence-staleness
   findings alike. Never fix anything automatically — that's the user's
   or a follow-up command's call.
7. If this run ends clean, or ends with fixes applied and reverified,
   **offer** to sync — `/criterion push` if this deployment is already
   repoed, `/criterion create` otherwise. Never run either
   automatically; offer it and proceed only once the user says to.

This is the same procedure `/criterion push` runs inline against an
incoming branch before merging, in any repoed deployment
(`framework/kernel/rules-of-rules.template.md` §13) — described
there directly rather than depending on this command, since this command
doesn't exist outside catalyst's own repo. Running `/dogfood` here
standalone never touches `criterion` or any branch on its own — step 7
above only ever *offers* that as a next step, never triggers it.
