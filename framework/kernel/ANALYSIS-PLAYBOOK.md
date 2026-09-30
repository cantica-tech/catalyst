# Analysis Playbook

How `/run-analysis` infers **domains, rules and defects** from existing
code, with a four-eyes process that `catalyst analysis` enforces and a
human decision on every finding (`Rules-of-Rules.md`, the kernel's
analysis rule; the `ANALYSIS-` entity). This file ships in every working
copy as `.criterion/ANALYSIS-PLAYBOOK.md`; `/sync-framework` refreshes it.

Two modes:

- **bootstrap** — the project has no rules yet: find its domains and a
  small set of rules, and the defects where the code breaks them.
- **incremental** (the default) — rules exist: find what they miss, and
  where the code breaks them (existing or new).

## The four-eyes principle

Every analysis runs **two independent extraction passes** over the same
scope and code state, by two agents that cannot see each other's work,
then a **reconciliation** that diffs them and verifies against the code
whatever only one pass found or the two disagree on. Two blind passes
catch what one pass misses — an agent that stops early, misreads a code
path, or reports a rule the code does not have — far better than one pass
plus a self-review, because the second agent carries none of the first
one's framing.

```text
pass A (independent) ──┐
                        ├──▶ diff ──▶ reconciliation ──▶ the user decides each finding
pass B (independent) ──┘
```

- A and B get the **same prompt, verbatim**; their independence comes
  from being separate agent instances with no shared context. If the agent
  can run sub-agents, launch both at once, in parallel, with a model
  suited to long, careful reading. If it cannot, run each pass in a fresh
  session that has not seen the other's output — never both in one
  context.
- **Research agents only read code and return findings.** No pass and no
  reconciler writes an artifact: the orchestrating session writes them,
  after the user's decision. Letting a research agent also merge is how a
  disagreement gets silently resolved by whichever agent ran last.
- **IDs are allocated after the decision**, by the CLI (`catalyst id next`,
  `catalyst id next-rule`) — never by a pass, whose numbering would
  collide.
- **Delegation drift:** an agent that hands its reading to further
  sub-agents instead of doing it wastes the pass. Tell it to read the code
  itself.

## The process

Each phase is a `catalyst analysis` command; it refuses to skip a phase,
and `catalyst check` rejects a record whose reports do not support its
phase. The record is `analyses/ANALYSIS-NNNNNN-<userid>-<name>.md`, its
reports `analyses/reports/<ID>/`.

1. **Start.** `catalyst analysis start <paths...> [--mode bootstrap|incremental]
   [--name <name>] --as <signer>` records the scope, the product commit
   analysed, and `inventory.json`: every tracked file in scope with its
   blob hash and, for `incremental`, the rules, domains and rule-grounded
   artifacts that already exist.
2. **Two passes.** Send the [pass prompt](#the-pass-prompt) to agent A and
   agent B, filled in identically. Save each answer as a findings file
   ([format](#findings-format)) and record it:
   `catalyst analysis record <ID> --pass A <file>`, then `--pass B`. A
   file that fails validation is returned to its agent to fix — never
   edited to pass.
3. **Diff.** `catalyst analysis diff <ID>` pairs the findings and writes
   `diff.json`: *agreed*, *conflicting* (paired, but a different rule
   status or a different broken rule), *A-only*, *B-only*.
4. **Reconcile.** Send the [reconciliation prompt](#the-reconciliation-prompt)
   with both passes and the diff to a third agent (or do it yourself).
   Record its answer: `catalyst analysis reconcile <ID> <file>`. It is
   accepted only if every finding of both passes is kept (a final
   finding's `sources`) or dropped with a reason, exactly once, and every
   final finding that is not a plain agreement says how it was verified.
5. **Decide.** Present the reconciled findings to the user — domains
   first, then rules, then defects, each with its statement, evidence and
   verification. For each one, the user accepts, edits then accepts, or
   rejects; never decide for them. On acceptance, write the artifact:
   - a **domain**: `rules/domains/<prefix>-<CODE>-<short-description>.md`
     per `Rules-of-Rules.md` §6, registered in `domains.md`;
   - a **rule**: its ID from `catalyst id next-rule <prefix> <DOMAIN>`,
     written into the rule document and `rules/rules.md` per
     `Rules-of-Rules.md` (status ✅ / ⚠️ / ❌ from the finding: `holds` /
     `partial` / `missing`);
   - a **defect**: the artifact a fix requires (`CODE-OF-CONDUCT.md` §3,
     fix tier), targeting the rule it breaks — the existing rule, or the
     rule accepted from the finding it names.
   Then `catalyst index regen`, `catalyst journal append`, and record the
   decision: `catalyst analysis decide <ID> <finding> accept --artifact
   <the domain code, rule ID or artifact ID>` (or `reject --reason
   "<why>"`). A defect whose rule was rejected is rejected too, or waits
   for a rule the user writes. A finding the user and the reconciler
   still disagree on can become a `RECON-` case (`Rules-of-Rules.md` §16).
6. **Close.** `catalyst analysis close <ID>` once every finding is decided;
   it refuses while an accepted finding's artifact does not exist. Then
   `catalyst check`, and report the summary. `catalyst analysis abandon <ID>
   --reason "<why>"` stops an analysis that should not go on.

## The pass prompt

Send identically to A and B, filling the `{{…}}` placeholders from the
record and `inventory.json`:

```text
You are one of two independent auditors of this codebase; you will not see
the other's work, and yours will be compared with it. Read the code
yourself — do not delegate the reading.

Scope: {{paths}}, at commit {{code state}}.
Mode: {{bootstrap | incremental}}.
{{incremental: the rules and domains already recorded, with their text —
  do not report them again; do report where the code breaks them}}

Do three passes over the code, then merge them into one list:
  1. A sweep (search) of the scope for the behaviour the code enforces:
     validations, invariants, workflows, permissions, error handling,
     configuration limits.
  2. A walkthrough of the main modules, reading the logic rather than
     trusting names and comments.
  3. A cross-check against the project's automated tests or checks: is
     each rule exercised? Say so in the finding's notes.

Report three kinds of finding:
  - domain: a functional area of the product, with a 3–7 letter code and a
    one-sentence scope. Bootstrap mode mostly; in incremental mode only for
    an area no existing domain covers.
  - rule: a concise, high-level statement of behaviour the product must
    have — useful for writing work items and the defects raised against
    them, not an implementation detail. Status: holds (implemented as
    stated), partial (implemented but buggy or incomplete), missing (clearly
    intended — documented, half-built, referenced — but not implemented).
  - defect: code that breaks a rule — an existing rule (its ID) or a rule
    finding of yours (its id). A problem that breaks no rule you can state is
    not reported as a defect: report the rule instead.

Every rule and defect cites evidence: a file in the scope and a line.
Flag anything you are unsure of with confidence low; never guess.
Answer with the findings JSON only, in the format below.
```

Append the [findings format](#findings-format) to the prompt.

## Findings format

A pass answers with one JSON object:

```json
{"findings": [
  {"id": "A1", "kind": "domain", "title": "Session management", "code": "SESSION",
   "statement": "Login sessions: creation, expiry, revocation.", "area": "SESSION",
   "confidence": "high", "evidence": []},
  {"id": "A2", "kind": "rule", "title": "Sessions expire", "area": "SESSION",
   "statement": "An idle session expires after the configured timeout.",
   "status": "partial", "confidence": "medium",
   "evidence": [{"path": "src/session.py", "line": 12}],
   "notes": "no test covers expiry"},
  {"id": "A3", "kind": "defect", "title": "Timeout of zero never expires", "area": "SESSION",
   "statement": "TIMEOUT defaults to 0, which the expiry check treats as never.",
   "breaks": "A2", "confidence": "high",
   "evidence": [{"path": "src/session.py", "line": 3}]}
]}
```

- `id` unique in the file; `kind` is `domain`, `rule` or `defect`;
  `title` and `statement` are required; `confidence` is `high`, `medium`
  or `low`.
- A `rule` has a `status` (`holds`, `partial`, `missing`). A `domain`
  may have a `code` (3–7 capital letters).
- A `rule` or `defect` has at least one `evidence` entry: a `path` from the
  inventory and, where it applies, a positive `line`.
- A `defect` names what it `breaks`: an existing rule ID or a rule finding's
  `id` in the same file.

## The reconciliation prompt

```text
Two independent audits of {{paths}} at {{code state}} were run separately.
Their findings and the mechanical pairing of them are below. Produce the
final list:

  - agreed pair: keep one finding, merging the best wording and evidence of
    both; sources ["A:<id>", "B:<id>"]; verification "both passes".
  - conflicting pair (different status, or a different broken rule): read
    the code yourself and decide; say what you read in `verification`.
    These are the most important to get right.
  - A-only or B-only: verify it against the code yourself. Keep it (with
    what you checked in `verification`) or drop it with a reason — never
    drop one silently. If you cannot verify it, keep it with confidence low
    and say so.
  - a pairing the diff got wrong: split or merge it, and say so.

Every finding of both passes appears exactly once: in a final finding's
`sources`, or in `dropped`. A defect's `breaks` names an existing rule ID or
a final rule finding's id. Answer with JSON only:
{"findings": [ ...findings format, plus "sources" and "verification" ... ],
 "dropped": [{"source": "A:<id>", "reason": "..."}]}

--- PASS A ---
{{A.json}}
--- PASS B ---
{{B.json}}
--- DIFF ---
{{diff.json}}
```

## What is not a four-eyes analysis

Changes to the process itself — the ID scheme, retirement policy, the
domain standard, anything that becomes a meta-rule — are a design
conversation with whoever owns the process, written once. Four-eyes is
for *extracting what already exists in code*, where an independent second
reading catches misreadings; it has nothing to verify against when the
question is *what the process should be*.
