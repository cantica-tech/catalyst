# Analysis Playbook

A recipe for bootstrapping this framework's rules, domains and first
active-module artifacts against an
**existing** codebase that has no prior rules documentation — the process
used to build this project's own [`.criterion/rules/`](../../.criterion/rules/)
directory. Reusable on any project once you've picked your rule
document(s) and prefixes per
[`INSTANTIATION-GUIDE.md`](INSTANTIATION-GUIDE.md).

## The four-eyes principle

Every extraction pass in this playbook is run **twice, independently**,
by two agents that cannot see each other's output, followed by a
**reconciliation pass** that diffs the two and produces the final
document. Two independent full passes catch what a single pass misses
(an agent that stops early, misreads a code path, or hallucinates a rule
that doesn't exist in the code) far more reliably than one pass plus a
self-review, because the second agent has no anchor bias from the first
agent's framing. This is not the same as the internal "N passes" some of
the individual prompts below already do (a single agent re-reading its
own work) — four-eyes is a second, wholly separate agent.

```
Agent A (independent) ──┐
                         ├──▶ Reconciliation pass ──▶ final document
Agent B (independent) ──┘
```

Use `Agent` tool calls with `run_in_background: true`, launched in the
**same message** so they run in parallel, `subagent_type:
general-purpose`, and (for this kind of long, careful reading task)
`model: opus`. Give A and B the *same* prompt verbatim — the independence
comes from them being separate agent instances with no shared context,
not from varying the instructions.

---

## Recipe 1 — Extract a small set of artifact-shaping rules

Run once per **rule document** you are bootstrapping, not per every
implementation category. For this framework, keep the scope intentionally
small: create only a limited number of high-level rules that help define
the active module's development artifacts, especially for:

- **Rules of Rules:** what counts as a valid rule, how it is named, how it
  is structured, and how conflicts are resolved.
- **Business Rules:** the domain constraints and workflow expectations that
  should inform development artifacts.
- **UI Rules:** the interaction, validation, presentation, and
  initialization definitions that shape the user-facing behavior.

These should be treated as definitions and scaffolding for development
artifacts, not as a full catalog of implementation behavior. Keep each rule
concise, high-level, and directly useful when drafting artifacts.

**Prompt template** (send identically to both agents of each pair):

```
Audit this codebase for the {{RULE_DOCUMENT}} document and extract only a
small set of artifact-shaping rules — high-level definitions that help
describe expected behavior, not detailed implementation policies.

Do THREE separate passes over the code, in this order, then reconcile
them into one list before reporting back:
  1. A keyword/pattern sweep (grep-style) across {{relevant source dirs}}
     for the kinds of rules or definitions that describe expected behavior.
  2. A manual walkthrough of the relevant modules, reading the actual
     logic rather than trusting names/comments.
  3. A cross-check against the project's automated checks ({{check
     paths}}) — does a check exist for each rule you found? Note ones that
     don't.

For every rule found, report:
  - A short bold name for the rule
  - A one-line description of the rule as an artifact-shaping definition
  - Status: ✅ working as intended / ⚠️ buggy or incomplete / ❌ documented
    intent but not actually implemented
  - Which functional area of the app it belongs to (e.g. "Gateway
    Management", "Recording") — group your final report by this

Only report concise, high-level rules that are useful when describing
expected behavior. Keep them tied to concrete application areas, user
flows, components, or domain behaviors rather than abstract definitions.
These rules should support verifiable work items and the defects that will
later be raised when behavior is wrong. Flag anything you're unsure about explicitly
rather than guessing.
```

Launch A and B for each category in one message (background, parallel).
When both return, run **Recipe 3 (reconciliation)** on the pair before
moving to the next category.

## Recipe 2 — Extract business-rule definitions

Use the same shape as Recipe 1, but focus only on the domain constraints
and workflow expectations that help define expected behavior. Keep the output
limited to a small set of high-level business-rule definitions, grouped by
functional area rather than by implementation detail (for example:
connectivity/security, data/persistence, orchestration/lifecycle). Everything
else — three passes, four-eyes pairing, and per-rule reporting fields —
is identical to Recipe 1.

## Recipe 3 — Reconciliation pass (four-eyes merge)

Run as a single foreground agent (or do it yourself) once both of a
pair's independent reports are in hand.

**Prompt template:**

```
Two independent audits of {{scope}} were run separately; their raw
reports are below. Reconcile them into one final list:

  - A rule both agents found: keep it, merge the best citation/wording
    from each.
  - A rule only one agent found: include it, but verify it yourself
    against the actual code before keeping it — don't take either
    agent's word alone. If you can't verify it, mark it explicitly as
    unverified rather than dropping it silently.
  - A rule where the two agents *disagree* on status (✅ vs ⚠️/❌) or
    on the actual behavior: this is the most important case to catch —
    resolve it by reading the code yourself, and note in the final
    entry that this was a disagreement worth double-checking again
    later.

Output the reconciled list in the target document's existing format
(see {{path to doc if one exists, else the format spec above}}).

--- AGENT A REPORT ---
{{paste}}

--- AGENT B REPORT ---
{{paste}}
```

Repeat Recipe 1/2 + Recipe 3 for each category/area, then merge all
reconciled category lists into the final document, grouped by
functional area (§ per area, not per rule category) — do this merge
yourself; it's editorial work (matching this project's format,
resolving cross-category overlaps), not another audit pass.

## Recipe 4 — Derive domains from a reconciled rule list

Once a document's rules are reconciled and grouped by functional area,
turn each group into a formal domain per
[`rules-of-rules.template.md` §6](rules-of-rules.template.md):

```
For each functional-area group in this reconciled rule list, propose:
  - A `##` domain heading (the area name)
  - A short DOMAIN code (3-7 uppercase chars, unique in this document)
  - A one-two sentence Scope statement
  - Whether it plausibly overlaps/conflicts with any other proposed
    domain in this same list — if so, say which and why, so a human
    can decide whether to merge them before finalizing.
```

Then mechanically assign IDs (`<prefix>-<CODE>-<NNN>`, in document
order) and create each domain's `rules/domains/<prefix>-<CODE>-<short-description>.md`
file per §6 — this step is deterministic, not another agent pass; a short
script or careful manual edit is more reliable than delegating it.

## Recipe 5 — Cross-reference known defects to rule IDs

Once rules have IDs, existing known-issue material (or defects discovered
during Recipe 1/2's audits — an ⚠️/❌ rule *is* a defect) gets linked back:

```
For each defect in this list, find the rule bullet in {{rules doc}} that it
violates (its description should match the ⚠️/❌ rule's behavior almost
exactly, since that's where it came from). Report the defect number and the
matching rule ID. If no matching rule bullet exists, say so explicitly —
that means the rule was never written down and needs to be added first.
```

Then open the active module's defect-type artifacts for them, per the
composed `CODE-OF-CONDUCT.md`
([`rules-of-development.template.md`](rules-of-development.template.md)
plus the module's §3/§4), citing the matched rule ID in `Targets`.

## Recipe 6 — Meta-rule / process changes

Changes to the process itself (new ID scheme, retirement policy, domain
standard — the kind of thing that becomes an `rr-META-NNN`) are
**not** run through four-eyes agent audits — they're a direct design
conversation with whoever owns the process, then written once. Four-eyes
is for *extracting what already exists in code*, where independent
verification catches misreadings; it isn't useful for *deciding what the
process should be*, which has no ground truth to independently verify
against.

---

## Why this shape (lessons from actually running it)

- **Background + parallel, not sequential**: launching a full category's
  A/B pair sequentially wastes the wall-clock four-eyes is supposed to
  buy you for free — always launch both in the same message.
- **Research agents only, never edit agents**: every agent in Recipes
  1/2/4/5 only reads code and returns a report; none of them write files
  directly. Direct file edits (creating the actual `.md` docs, inserting
  IDs, writing domain files) are done by the orchestrating
  session/agent after reconciliation, because letting research agents
  also own the merge step is how disagreements get silently
  auto-resolved in whichever agent happened to run last, defeating the
  point of four-eyes.
- **Three-digit `NNN` sequencing must happen after full reconciliation**,
  never per-agent — two independent agents numbering rules `001, 002, …`
  in parallel will collide the moment you merge.
- **Delegation drift**: watch for an agent re-delegating to further
  sub-agents instead of doing the audit itself — this wastes significant
  time with no findings landing. If it happens, tell it directly to stop
  delegating and do the reading itself.
