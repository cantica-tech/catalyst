# 18 — The handbook (R4.2 outline for the owner, 2026-10-10)

> **Status: approved (owner, 2026-10-10)** — every recommendation: the handbook at `rules/Rules-of-Rules.md` and
> `CODE-OF-CONDUCT.md` as the command catalogue; `/dogfood` and rr-META-018 out of deployments; `/project` and the
> old `/switch-agent` procedure dropped; `/criterion` replaced by `/share`; `/catalyzer` parked; the ten
> contradictions fixed as recommended; `catalyst reconcile` added now (#7). **Implemented on `development` (unreleased, kernel 0.52.0 / module 2.7.0):** handbook 9.7 KB kernel + 3.4 KB module (12.9 KB composed), command catalogue 22 KB (35 KB composed, read one command at a time); ADR-018. #2 needed no exemption: composition already widens and signs every meta-rule ID (`rr-META-000012-<userid>`); the handbook says so. Built on two
> read-only audits of the four rule documents (the kernel's two templates, the module's two contributions), checked
> against the ten laws (`17`), `FORMAT.md`, `CLI.md` and a real deployment.

## 1. What we start from

| Document | Deployed as | Size | Of which always relevant (audits) |
|---|---|---|---|
| `rules-of-rules.template.md` | `rules/Rules-of-Rules.md` | 66 KB | ≈ 8.5 KB |
| `rules-of-rules.module.md` (software engineering) | appended to it | 18 KB | ≈ 2 KB |
| `rules-of-development.template.md` | `CODE-OF-CONDUCT.md` | 51 KB, of which §4 commands 35 KB | ≈ 3 KB outside §4 |
| `code-of-conduct.module.md` | inserted into §3 and §4 | 25 KB, of which §4 12 KB | ≈ 2 KB outside §4 |

Of the 84 KB of rules-of-rules text: ≈ 22 KB is obsolete or parked (the symlink/submodule/pointer model, agent-owned
space, `/project`, plugins), ≈ 7 KB is catalyst-development-only (`/dogfood`, the recreation drift check), ≈ 30 KB
restates `FORMAT.md`, `ARTIFACT-LAYOUT.md`, `INVARIANTS.md` or the CLI. The code of conduct outside §4 is almost all
enforced by the CLI or restated elsewhere.

## 2. Target shape

Two deployed documents, each with one job:

* **`rules/Rules-of-Rules.md` becomes the handbook** — every judgment rule, deduplicated, kernel then module, about
  **10–11 KB**. It keeps its path, so ID allocation (`id next-rule` counts `rr-META-` IDs there), `validate`
  (rules are headings in `rules/`) and `catalyst why rr-META-n` keep working unchanged. Every section keeps its
  `rr-META-NNN` ID (law L7); a retired one keeps a one-line placeholder.
* **`CODE-OF-CONDUCT.md` becomes the command catalogue** — a one-paragraph preamble (signer, tier first, the common
  ending), then §4 exactly as `catalyst spec`, the MCP prompts and the parity check parse it. It is read one command
  at a time, never whole. Its other sections (§1–3, §5–9) fold into the handbook or go to their reference.

Formats go to `FORMAT.md` and `ARTIFACT-LAYOUT.md`, entity semantics to `definitions/`, command behaviour to `CLI.md`.
The handbook links to them; it never restates them.

## 3. The handbook's sections

| § | Section | Meta-rule IDs kept | From | ≈ KB |
|---|---|---|---|---|
| 1 | **Rules: adding one** — check every rule document for a conflict first; stop and ask on a contradiction; which document a rule belongs in; "done" means gathered, implemented, tested, documented | 001, 002 | RoR §1–2, "Which document", CoC §1 | 1.3 |
| 2 | **Rules: IDs, retiring, domains** — one line each for what `id next-rule` enforces; retire in place, never reuse; creating a domain (conflict check, scope, relationships); domains are registered in `domains/domains.md` | 003, 004, 005, 007 | RoR §3–5, §7 | 1.2 |
| 3 | **Work: no work without a rule** — artifact before work, the chore exemption, the tier stated first and escalated, closing an artifact never retires a rule | 006 | CoC §1, §8, §9 tiers | 1.0 |
| 4 | **Signing and roles** — the signer is declared and confirmed, never guessed; a role mismatch is noted, never blocking; IDs carry the signer's `userid` | 011, 020 | RoR §11, §20, CoC §2 | 0.8 |
| 5 | **The journal** — what must append, at the moment of the change (batching only if declared first); `--intent` is a goal, not a label; changes made outside catalyst: list them and ask, never adopt or revert alone; traced commits, never bypass the hook without the user's say-so | 012, 023 | RoR §12, §23, CoC §9 | 1.4 |
| 6 | **Sharing** — through `catalyst share` (any driver); publishing previews and needs the user's yes (L3); a conflict stops the push and the agent never applies a merge (L4); identity is declared, branch protection and review are the real controls | 013 | RoR §13 (rewritten) | 1.0 |
| 7 | **Session start** — `hook start` reports, `catalyst open` makes ready, `open --agent` records this user's agent; nothing of catalyst in the project | 014 | RoR §14 "agent switching" (already rewritten) | 0.3 |
| 8 | **Layout and frozen things** — never hand-edit a generated file or a superseded template; links to `ARTIFACT-LAYOUT.md` | 015 | RoR §15 | 0.3 |
| 9 | **Reconciliation and workflows** — a disputed version becomes a `RECON-` case a human settles; who may resolve it (`full` / `propose` / `none`); a workflow guides, it is never work | 016, 019 | RoR §16, §19 | 0.8 |
| 10 | **Module: software engineering** — the tier decides the artifact (SE-L1): what a chore, a fix and a feature need; a feature is an idea until work starts as a requirement; a roadmap decomposes into requirements and derives its status; a step has one parent, is opened as the work happens, never backfilled; a test is grounded like a bug or requirement; the two closing checks `validate` cannot do (verified before done, a test passes only on a real run) | module 009, 010, 021, 022 | module RoR and CoC | 2.2 |
| — | Deployment-specific stub ("which document", rule-doc prefixes), connective text | — | — | 0.7 |

Total ≈ 11 KB, against 84 KB today. With the laws (3.9 KB brief, `17`), everything an agent may need to judge fits in
≈ 15 KB, and a session loads only the laws.

## 4. What leaves the handbook

| Content | Goes to |
|---|---|
| Rule ID grammar, rule template location, domain file shape, sub-domains | `FORMAT.md` §5 (already there) |
| Journal entry schema, pinning, restore | `FORMAT.md` §7 (already there, richer) |
| IAM file shapes, `userid` algorithm | `FORMAT.md` §6 (already there) |
| Directory shape, where every type sits | `ARTIFACT-LAYOUT.md` (already there) |
| `RECON-` verbs and statuses, `WORKFLOW-`, feature/roadmap/step/test field semantics and status flows | `definitions/` and the ETDs |
| `/dogfood` (RoR §13 tail) and the recreation drift check (RoR §18, rr-META-018) | catalyst's own development docs — not deployed |
| Sharing lifecycle details, CI gate | `CLI.md` (`share`, `criterion`) |

## 5. What is dropped

* **Obsolete:** RoR §14 (agent-owned working copy, pointer, symlink, in-project fallback, pre-pointer migration,
  `/project create|remove|export|import`), RoR §13's submodule model, the "synchronize before any work" paragraphs
  (RoR 182–185, 293–296; they contradict L8), the rename procedure for IDs (contradicts L7), history notes ("joined at
  0.30.0", "promoted from…").
* **Parked with the plugins (R4.7):** rr-META-008 (agile work items), rr-META-017 (content plugins), the `catalyst-git`
  comparison, the plugin callouts in §15 and in the commands. Their IDs stay as one-line placeholders.
* **Commands (§4):** `/project create|remove|export|import` and `/switch-agent`'s old procedure (replaced by
  `catalyst init` on request and `catalyst open --agent`), `/criterion *` replaced by `/share info|status|pull|push|
  create|join`, `/catalyzer` parked. Merging thin wrappers (`/user-*` into `/user`, `/role-*`, `/commands` into
  `/help`) is the slash-surface work of R2 and **not** part of this step.

## 6. Contradictions to settle

| # | Contradiction | Recommendation |
|---|---|---|
| 1 | RoR says every rule is **its own file** (RoR 18–24, 166–178; INV-8 too); in every deployment rules are **headings inside rule documents** (`FORMAT.md` §5) | Fix the text to the real model: rules are headings in rule documents, each indexed in `rules.md` |
| 2 | Meta-rules are `rr-META-001` (three digits, unsigned), against their own rule that IDs are six digits plus the signer's `userid` | State the exemption: meta-rule IDs are the framework's, fixed and unsigned; signed IDs are for a deployment's own rules |
| 3 | Rename "retroactively" to a descriptive file name (RoR 87, CoC 735) against L7 "never renamed" | A **file** may be renamed to its descriptive name; an **ID** never changes |
| 4 | "Synchronize before further work" (twice) against L8 "sync only when asked" | Drop: `check` and `open` report a version drift; the user decides |
| 5 | Sub-domains documented as supported; the tools do not recognise them (`FORMAT.md` §5.2) | Say "not supported yet" until the tools do |
| 6 | Two domain registries: "the canonical table in this file" and `rules/domains/domains.md` | `domains.md` is the registry (the CLI checks it) |
| 7 | INV-21 says the reconciliation role gate is enforced; no CLI command enforces it | Add `catalyst reconcile <id> <verb>` with the role gate (small), or keep it agent-applied and say so |
| 8 | Journal paths start `.criterion/` although nothing of catalyst is in the project (L5) | Say it is a namespace inside the journal, not a directory |
| 9 | `INVARIANTS.md` INV-8, INV-18 (submodule) and INV-23 (`.criterion/definitions`), `FORMAT.md` §1 (pointer) and §11 (`/.criterion`), `CLI.md` invocation text still describe the old model | Fix them in the same change, so the handbook can cite them |
| 10 | Plugins would copy command files into `.claude/commands/` (rr-META-017) against L5 | Moot while parked; record it for R4.7 |

## 7. How it lands

1. The prerequisites of contradiction 9 (`INVARIANTS.md`, `FORMAT.md`, `CLI.md` home-store fixes).
2. The handbook (`rules-of-rules.template.md`, module `rules-of-rules.module.md`), the slim code of conduct (kernel and
   module, §4 shape kept), the moves of §4.
3. The prose freeze (`docs/FROZEN-SURFACE.json`, ADR-017) records meta-rules, commands and documents: the removed
   commands and the moved meta-rules are a reviewed change of that surface — a new ADR and the snapshot rewritten.
4. Release kernel 0.52.0 and module 2.7.0 with a migration (`sync apply` recomposes both documents; the dropped
   commands disappear from `catalyst spec` and the MCP prompts). A UI client reads §4 only, whose shape is kept.

## 8. Decisions for the owner

1. **The target shape** (§2): the handbook at `rules/Rules-of-Rules.md`, `CODE-OF-CONDUCT.md` reduced to the command
   catalogue.
2. **The sections** (§3) and what leaves (§4) — in particular moving `/dogfood` and rr-META-018 out of deployments.
3. **The ten contradictions** (§6) — accept the recommendations, or say otherwise per item; for #7, a
   `catalyst reconcile` command now or later.
4. **The command removals** (§5) in this step, with the thin-wrapper merges left to R2's slash surface.
