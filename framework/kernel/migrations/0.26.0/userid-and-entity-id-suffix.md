# Migration: userid field + entity-ID signer suffix

> Target version: `0.26.0` — this is the migration that produces the
> shape `0.26.0` introduces. Triggered by `SYNCHRONIZE.md`'s
> "Version-specific one-time migrations" (`From 0.25.1`). Applies once,
> the first time a deployment's `version.txt` advances past `0.25.1` to
> `0.26.0` or later. Never re-run on a later sync once applied.

## What changed

- Every entry in `IAM/users/users.json` gains a `userid`: 8 characters,
  case-sensitive alphanumeric, containing at least one uppercase
  letter, generated once and never changed (`Rules-of-Rules.md` §11,
  INV-26).
- Every rule, active-module `<PREFIX>-NNNNNN`, `WORKFLOW-`, and `RECON-`
  ID now carries its creator/signer's `userid` as a trailing
  `-XXXXXXXX` segment, assigned once at creation, immutable after
  (`Rules-of-Rules.md` §20).
- A rule ID's sequence number widens from 3-digit `NNN` to 6-digit
  `NNNNNN` (`Rules-of-Rules.md` §3, revised) — padded before the
  `userid` suffix is appended, never after.
- Rules and domains have no authorship field of any kind — until one
  exists, a rule's suffix uses the sole/most-recently-active registered
  user (`Rules-of-Rules.md` §20's documented limitation). Domains have
  no numeric ID and are out of scope for the suffix entirely.

## Preconditions

- Clean git working tree (or an explicit journal checkpoint) — this
  migration renames every existing rule ID it finds, never deletes
  anything, specifically so a clean starting point makes it trivially
  revertible.
- Resolve the deployment root the normal way.

## Steps

1. **Users first, always — no exceptions.** For every entry in
   `IAM/users/users.json` lacking a `userid`, generate one per
   `Rules-of-Rules.md` §11's procedure: draw 8 characters from
   `[A-Za-z0-9]` via a cryptographically-secure source, redraw if it
   contains no uppercase letter, check against every existing `userid`
   (including ones assigned earlier in this same pass), redraw on
   collision. Do this as one complete pass over every user before
   touching any entity.
2. **Verify** every user now has a valid, unique 8-char alphanumeric
   userid (containing an uppercase letter) before proceeding — treat
   any failure as a blocker, not something to skip past.
3. **Compute the full rename map before renaming anything.** For every
   existing rule ID across every rule document: resolve its signer's
   `userid` per §20's rule/domain limitation, and compute
   `old-id -> new-id` (zero-pad `NNN` to `NNNNNN`, then append
   `-userid`) for the entire set first. A half-repadded tree breaks
   lexicographic sort — `"000010"` sorts before `"003"` as strings even
   though 10 > 3 — so this must never be left partially done.
4. **Apply renames, one atomic pass per ID.** For each id: rename its
   own heading, its entry in the type's index (skip if the prefix is
   self-governing/exempt from that index — check
   `rules-of-rules.template.md` §1 for which ones are), then search the
   **entire deployment tree** for the bare old-id string and update
   every real citation found — structured fields (`Targets`, `Entity`,
   `Workflow`, and every link field the active module's templates
   define) and
   free-text `## Related`/`## Notes`/prose citations alike, since there
   is no dedicated cross-reference-checking script to catch a missed
   one. Carve-outs, never touched:
   - `development/journal.jsonl` — **never edit** (INV-17). Historical
     entries correctly keep citing the pre-rename form forever.
   - any generated file the active module declares never hand-edited —
     regenerate it with the command the module names after every
     rename lands instead.
   A completed `.ledger/*.todo.md` checklist line narrating a past
   action is historical record, same posture as the journal — leave it.
   A domain's own filename/code that merely shares a rule's
   `DOC_PREFIX`/`CODE` substring is not a rule-id citation — domains
   have no numeric ID; don't touch it.

   Re-search for that same old form immediately after each rename —
   zero remaining hits outside the carve-outs before moving to the
   next id. An unresolved hit is a blocker, not something to skip.
5. **Re-sync governing docs**: refresh this deployment's own
   `rules/Rules-of-Rules.md` (§3/§11/§20) and `CODE-OF-CONDUCT.md`
   (§2/§6) against their now-updated source templates, the same way any
   other `/sync-framework` pass would.
6. **Module**: regenerate any active-module generated file a renamed id
   appeared in, and apply the active module's migration for this
   version, if any (`MODULE-SPECIFICATION.md` §6.6).
7. **Journal**: two entries — one for the user migration (step 1-2),
   one for the rule-id migration (steps 3-4) — each with real
   `git hash-object` before/after hashes for every file it touched.
8. **Version**: update the deployment's own `version.txt` to `0.26.0`.
9. **Verify**: run `scripts/check_deployment.py` (or `task
   check:all` if this is the framework's own self-deployment) against
   the migrated tree and resolve every reported issue, including the
   new `check_users_have_userid`/`check_rule_id_shape` checks this same
   version introduces, before considering the migration done.

Note: active-module artifacts, `WORKFLOW-` and `RECON-` commonly have
zero existing instances in a fresh or lightly-used deployment —
there is nothing to rename there in that case, but `Rules-of-Rules.md`
§20 governs every future instance of every one of these types from now
on regardless.

## Rollback

Step 1-2 (userid assignment) is additive only — no rename, trivially
revertible on its own. Steps 3-4 (rule-id migration) are renames, never
deletes — the clean pre-migration git/journal-checkpoint state fully
reverts them. Never leave a partially-completed pass in place (see step
3's sort-order hazard) — either finish it in the same session or roll
the whole thing back to the pre-migration state.
