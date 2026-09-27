# Migration: uniform artifact-type layout (INV-20)

> Target version: `0.12.0` — this is the migration that produces the
> shape `0.12.0` introduces. Triggered by `SYNCHRONIZE.md`'s
> "Version-specific one-time migrations" (`From 0.11.0`). Applies once,
> the first time a deployment's `version.txt` advances past `0.11.0` to
> `0.12.0` or later, to any project still on the pre-INV-20 flat layout.
> Never re-run on a later sync once applied.

## What changed

- Every artifact-type directory now carries a versioned, catalogued
  `templates/` subdirectory (`README.md`, `templates-<type>.md` —
  Version | File | Timestamp | Notes — and `TEMPLATE-<TYPE>-vN.md`,
  files only, never edited in place) and its own `README.md`
  (`Rules-of-Rules.md` §15, `INVARIANTS.md` INV-20).
- `domains/` nests under `rules/domains/` — it never was a top-level
  sibling in principle (`rules-of-rules.template.md` §7 always said
  `{{RULES_DIR}}/domains/`), but several other spec files and most real
  deployments had it at the root. This migration is also where that
  inconsistency gets resolved for an existing project.
- `development/users.json`/`development/roles.json` move to
  `IAM/users/users.json`/`IAM/roles/roles.json`.
- `development/bugs/`, `development/house-keeping/`,
  `development/meta-tags/` are promoted from loose files directly under
  `development/` to full artifact-type folders.
- `work-items/` gains two optional types — `boards/` (`BOARD-NNNNNN`,
  Kanban/Scrumban's counterpart to `sprints/`) and `workflows/`
  (`WORKFLOW-NNNNNN`, a process-definition document, never itself
  worked) — plus a `tickets/` slot reserved for plugin population
  (`Rules-of-Rules.md` §8). None of these three are retroactively
  required just because the framework now supports them.
- Every dev-artifact/feature/roadmap/work-item ID widens from 4-digit
  `NNNN` to 6-digit `NNNNNN` (`BUG-0001` → `BUG-000001`, etc.). Rule IDs
  (`(prefix)-(DOMAIN)-(NNN)`, 3-digit) and `SPRINT-NNN` (3-digit) are
  **unaffected** — this widening only applies to the 4-digit scheme.

## Preconditions

- Clean git working tree (or an explicit journal checkpoint) before
  starting — this touches many files across the whole deployment, and
  every step here is a move/rename, never a delete, specifically so a
  clean starting point makes the whole migration trivially revertible.
- Resolve the deployment root the normal way (`<app-name>.catalyst`'s
  `agent-source`, or the in-project fallback) before any file operation.

## Steps

1. **Domains**: move `domains/` → `rules/domains/` (filenames unchanged,
   only the directory relocates). Add `rules/domains/templates/`
   (`TEMPLATE-DOMAIN-v1.md` from `templates/domain.template.md`,
   `templates-domain.md` seeded with a `v1` row, `README.md`) and
   `rules/domains/README.md`. Update every reference to the old
   top-level `domains/` path across deployed docs.
2. **Rules**: create `rules/templates/`, move `rules/TEMPLATE-RULE.md` →
   `rules/templates/TEMPLATE-RULE-v1.md`, seed
   `rules/templates/templates-rule.md` (`v1`, today's date, "carried
   over from the pre-INV-20 layout"), write `rules/templates/README.md`.
3. **Requirements, Features**: same treatment per type — create
   `<type>/templates/`, move the existing bare `TEMPLATE-<TYPE>.md` in
   as `TEMPLATE-<TYPE>-v1.md`, seed its catalog and `README.md`.
4. **IAM**: create `IAM/users/` and `IAM/roles/`. Move
   `development/users.json` → `IAM/users/users.json` and
   `development/roles.json` → `IAM/roles/roles.json` (content
   unchanged). Each gets its own `README.md` — but **no `templates/`**:
   each is one JSON array, not a one-file-per-instance document type, so
   there's nothing to version.
5. **development/bugs, house-keeping, meta-tags**: create each as a
   full artifact-type folder; move the existing `TEMPLATE-<TYPE>.md`,
   `<type>.md` index, and every instance file into it, each gaining the
   nested `templates/` treatment.
6. **work-items**: for epics/stories/tasks/spikes/sprints, same nested
   `templates/` treatment as above. Add `boards/` and/or `workflows/`
   only if the project actually wants to start using them — this
   migration does not require adopting either. Add the `tickets/` slot
   (`README.md` + empty `tickets.md`, no `templates/` — no core
   template exists for it).
7. **Widen IDs to 6 digits**: for every `BUG-`/`REQ-`/`HK-`/`FEAT-`/
   `RM-`/`EPIC-`/`STORY-`/`TASK-`/`SPIKE-` (and `BOARD-`/`WORKFLOW-` if
   adopted in step 6) instance: rename its file, and update every index
   row, cross-reference, `Targets`/`Requirement(s)`/`Roadmap`/`Feature`
   field, and journal `artifact`/`targets` mention consistently. This is
   the highest-risk step — do it as one atomic pass per ID, verify
   against the relevant `<type>.md` index immediately after each
   rename, and treat any reference this pass can't find and fix as a
   blocker to resolve before continuing, not something to skip past.
8. **Deployed commands**: update every `.claude/commands/<name>.md`
   file's template-path reference (or equivalent, per
   `BOOTSTRAP.md` §1's fallback) to the new nested/versioned locations.
9. **Re-sync governing docs**: refresh the deployed
   `CODE-OF-CONDUCT.md`, `rules/Rules-of-Rules.md`, and
   `work-items/rules-of-work-items.md` against their (now-updated)
   source templates, the same way any other `/sync-framework` pass
   would.
10. **Verify**: run `scripts/check_deployment.py` against the migrated
    tree and resolve every reported issue before considering the
    migration done.
11. **Journal**: append exactly one entry for this migration
    (`action: "migrate"`, `intent` describing the restructuring,
    `files` covering every touched path by content hash) — per
    `Rules-of-Rules.md` §12, this is precisely what the journal exists
    to record.
12. **Version**: update the deployment's own `version.txt` to `0.12.0`
    (or later, if synchronizing further than this one migration in the
    same run).

## Rollback

Every step above is a move or a rename, never a delete — the clean
pre-migration git state (or the journal checkpoint from step 11's `before`
hashes) is enough to fully revert if something goes wrong partway
through. Never treat a partially-completed migration as acceptable to
leave in place; either finish it or roll it back to the pre-migration
state.
