# R0 owner decisions: Session-scoped stop hook and rule storage model

**Date:** 2026-10-07  
**Related:** `11-r0-status.md`, roadmap R0 phase completion

---

## R0.5: Session-scoped Stop hook

**Decided:** Yes — Stop hook fails only on changes made in this session, not on other sessions' in-flight edits.

### Problem

The Stop hook runs `catalyst check` and other validators on every session end. If ANY unjournaled changes exist (from any session, concurrent or historical), the hook fails and blocks the stop. In multi-session scenarios, this means one contributor's uncommitted work blocks every other contributor's ability to stop their own session.

**Example:** Session A has an unjournaled change in `.criterion/rules/`. The stop hook detects it and blocks. Sessions B, C, and D cannot stop even though they made no changes to `.criterion/`.

### Solution

The stop hook should distinguish between:
- Changes that existed when **this session started** (do not block)
- New changes made **during this session** (block on these)

**Implementation approach:**

1. At session start, capture baseline state (via hook input or env tracking)
2. At session end, compare current failures against baseline
3. Only exit 2 (block) if new failures emerged
4. If failures were present at session start, report them but exit 0 (allow stop)

**Interim solution** (if baseline tracking is not ready for R0):
- Use the existing `stop_hook_active` flag to allow the stop after one block attempt
- This prevents infinite loops and lets concurrent sessions eventually proceed
- Full session-scoped checking can ship in R2 with proper metadata

### Migration impact

- No change to `.criterion/` structure
- No change to journal format
- Stop hook behavior becomes more permissive (existing baseline failures do not block)
- Sessions may need to run stop twice in rare cases until full implementation lands

---

## R0.9: Rule storage model — One file per rule document

**Decided:** Yes — Rules are organized by domain/purpose in documents; each rule document is one file.

### Problem

Two conflicting interpretations existed:
1. One file per individual rule ID (e.g., `rr-META-001.md`, `rr-META-002.md`, …) — creates ~100+ files, splits related rules
2. One file per rule document (e.g., `Rules-of-Rules.md` contains RR-META-001…006) — keeps related rules grouped

### Decision

**One file per rule document.** Rule documents represent a coherent domain:
- `Rules-of-Rules.md` — meta-rules (how rules are created, versioned, cited)
- Domain documents — structure rules, behavior rules, plugins rules, etc.
- Each document contains 1–20 related rules with clear ID numbering

### Rationale

- **Grouping:** Related rules stay together, providing context (e.g., "all structure rules" in one place)
- **Discoverability:** A new contributor finds all rules in their domain in one file
- **Manageability:** ~10 rule documents vs. ~100 rule files
- **Semantic clarity:** Each document title reflects its domain (not the case for "individual rule files")
- **Existing practice:** This formalizes how rules are already organized; no migration needed

### Validation

`catalyst validate` should enforce:
- Each rule document has a clear domain title
- Each rule within the document has a unique ID (`PREFIX-SERIAL-USERID`)
- Rule IDs are grouped by domain and never reused
- Cross-document references use full IDs and are bidirectional (§3.3 of rules-of-rules)

### Migration impact

- No structural change; formalizes existing layout
- Validators can now check compliance programmatically
- Future rule-creation commands can enforce the pattern
- No need to split or re-organize existing rule documents

---

## Decisions deferred to R1/R2

The following decisions remain open and will be addressed in later phases:

1. **R0.5 implementation detail:** Should baseline tracking use git state, journal pins, or a simpler `stop_hook_attempts` counter?
2. **RECON close rule:** Confirm `/reconcile close` as the only path; confirm `Resolved-Accepted-with-Edits` in ETD
3. **SE 2.4.0 ↔ kernel 0.46.0 coupling:** Module migrations keyed by kernel version; release order
4. **PROP- / RUN- entities:** Issue/task/run tracking (not in scope for R0)
5. **Commit/release order:** Should kernel 0.46.0 land before SE 2.4.0?

---

## No changes to code or deployment

This decision document records owner intent for implementation. R0 itself (fixes R0.1–R0.4, R0.6–R0.8, R0.10–R0.21) is complete and tested. R0.5 and R0.9 now have clear decisions; implementation begins in R1 if needed.
