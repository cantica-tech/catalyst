# R1.2: Installation UX Simplification

**Objective:** Reduce installation judgment questions from ~6 to ≤3.

**Current state (BOOTSTRAP §2 step 2 − Resolve inputs):**
Judgment questions asked during install:
1. Project name (asks if no `dev-instructions.yaml`)
2. Active module (asks; no default)
3. Rule document(s) and prefix per seam (asks)
4. First user name (asks)
5. First user git username (asks)
6. Working-copy directory (asks unless agent has computed location)
7. Command directory (for agents supporting command files)

**Target:** ≤3 judgment questions.

---

## Consolidations and Eliminations

### Q1: Project name — **KEEP**

**Recommendation:** Keep. Single fallback (repository name) reduces confusion.
**Effort:** None; already has good default.

---

### Q2–Q3: Module choice → **DEFER TO R3/R5**

**Current:** Ask user to pick from `framework/modules/catalog.md` (free choice).

**Proposed:** For R1 and R2, the **Software Engineering (SE)** module is the
only production module. Hardcode `--module se` as the default for now.

**Why:** Reduces one question; unblocks install for common case; R5 adds UI
module selection, R3 adds multi-module deployments. SE is stable for the
refactor window (2–3 months).

**Risk:** Future modules arriving later than R3/R5 will need the choice back,
but that's acceptable — this is a tactical R1 simplification, not permanent.

**Effort:** 
- Update BOOTSTRAP §2 to make `--module se` default during R0–R2.
- Document in migration that this changes at R3/R5 when multi-module is ready.

---

### Q4–Q5: Rule documents → **CONSOLIDATE**

**Current:** Ask for one `--rule-doc <file>:<prefix>` per project seam.
Most projects answer: "business-rules:br" (single document).

**Proposed:** 
- Default to one rule document: `<project-name>-rules.md` with prefix `br`.
- Offer an *advanced* option: "Custom rule documents?" (yes/no).
- If yes, ask for list; if no, use default.

**Why:** ~90% of projects use one rule document. Two-tier UX (simple + advanced)
cuts a question for the common case.

**Effort:**
- Add `--no-advanced` flag to `catalyst init` (use default rule doc; skip prompt).
- Modify BOOTSTRAP judgment step to offer "Simple (one document) / Advanced (custom)".
- Update INSTANTIATION-GUIDE §1 to reflect this choice.

---

### Q6: First user name and git username → **CONSOLIDATE**

**Current:** Ask for both `--user <name>` and `--git-username <name>` separately.

**Proposed:**
- Infer git username from `git config user.name` (via `catalyst init` detection).
- Fall back to `git config user.email` (extract local part before `@`).
- If no git config found, ask once: "Git user identity?" (accepts `name <email>`).
- Use `name` as both `--user` and `--git-username` by default; allow override.

**Why:** Reduces two questions to zero (auto-detect) or one (if git config missing).
Git config is already present on most developer machines.

**Effort:**
- Add git-config probe to `catalyst init` entry point (Python).
- Update BOOTSTRAP §2 to say "Catalyst will detect your git user; or type…".
- Document fallback path for machines without git config.

---

### Q7: Working-copy directory → **AUTO (Agent-owned)**

**Current:** Ask where to put `.criterion/` for agent-owned storage.

**Proposed:**
- For Claude Code and other agents with agent-owned per-project storage,
  compute and use it silently (per the agent's shim, e.g. `CLAUDE.md`).
- For agents without owned-space, use in-project `.criterion/` (already fallback).
- Remove the ask. Document in INSTANTIATION-GUIDE §1 that this is automatic.

**Why:** Agent location is a platform/environment detail, not a user decision.
Eliminates one question entirely.

**Effort:**
- Update BOOTSTRAP §2 to remove the judgment step for `--at`.
- Modify `catalyst init` to compute `--at` from the agent's config if
  `--at` not provided.
- Document per-agent location strategies in BOOTSTRAP §1.1 (agent-switch section).

---

### Q8: Command directory — **AUTO (Agent-owned)**

**Current:** Judgment on whether to write `.claude/commands/` or equivalent.

**Proposed:**
- For agents supporting command files, compute the path from agent config
  (e.g. `.claude/commands` for Claude Code).
- Pass `--commands-dir` silently; no ask.

**Why:** Command directory is part of agent setup, not user decision. Eliminates one question entirely.

**Effort:**
- Update BOOTSTRAP §2 to remove judgment for command directory.
- Modify `catalyst init` to accept `--commands-dir` from agent config.
- Document per-agent command-dir paths in BOOTSTRAP §1.1.

---

## Simplified Install Flow (R1.2 Target)

After R1.2, BOOTSTRAP §2 "Resolve inputs" reduces to **3 judgments**:

1. **Project name** ← repo name default
2. **Simple or advanced rule docs?** ← "Simple (one file)" default
   - If advanced: ask for list
3. **Git user?** ← auto-detect from git config; ask only if missing

**Mechanical:** `catalyst init --name <X> --module se --user <git-user> --rule-doc <default>`

---

## Implementation Steps

### Phase 1: BOOTSTRAP/INSTANTIATION docs update
- [ ] Modify BOOTSTRAP.md §2 "Resolve inputs" to reflect new flow
- [ ] Update INSTANTIATION-GUIDE.md §1 with new defaults
- [ ] Document fallback for "advanced rule docs"
- [ ] Add git-config auto-detect strategy

### Phase 2: CLI (`catalyst init`) changes
- [ ] Add `--module se` hardcoded default for R1–R2
- [ ] Add git-config probe (call `git config user.name/email`)
- [ ] Add logic: if no `--at` provided and agent known, compute it
- [ ] Add logic: if no `--commands-dir` provided and agent known, compute it
- [ ] Add `--no-advanced` flag (use default rule doc; skip prompt)

### Phase 3: Testing
- [ ] Test install with all defaults (repo name, SE module, auto git user)
- [ ] Test install with git-config missing (should prompt once)
- [ ] Test install on macOS, Linux, Windows + WSL
- [ ] Test with existing agents (Claude Code, others) to verify location inference

### Phase 4: Token measurement
- [ ] Run `measure_tokens.py` after changes to verify BOOTSTRAP/INSTANTIATION 
  docs did not expand (should shrink by ~10–15%);
- [ ] Update BUDGETS-BASELINE.json if threshold crossed

---

## Acceptance Criteria

✓ **Install flow prompted reduced to ≤3 judgment questions for typical project**  
✓ **Default paths (SE module, simple rules, git-user auto-detect) work for 90% of cases**  
✓ **Advanced path available without breaking existing deployments**  
✓ **All tests pass (fresh installs on 3 OSes, existing deployment unaffected)**  
✓ **BUDGETS-BASELINE.json token count unchanged or decreased**  

---

## Rollout

- **Commit to development:** R1.2 implementation + updated docs
- **Testing window:** 1–2 days (test on catalyst, UI repo, example deployment)
- **Merge to main:** after passing token budget and UX validation

---

## Open Decisions

1. **Git-config fallback:** If `git config user.name` is missing, should we
   - Prompt for full "name <email>"?
   - Extract from `$USER` or `whoami`?
   - Recommendation: Prompt once; Git should be configured on dev machines.

2. **Rule-doc auto-detect:** Should we scan the project for a heuristic
   (e.g., existing rules file) to suggest document name?
   - For now: No. Simple default `<name>-rules.md` works. R3 project analysis
     can improve this.

3. **Module hardcoding scope:** Should SE be hardcoded for R1 only, or through R2?
   - Recommendation: Through R2 (end of "code replaces prose"). R3/R5 coincide
     (one-truth, UI module). Lock it in now.
