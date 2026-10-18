# Decisions

The owner's decisions that shape the [roadmap](roadmap.md), one row per question, the decision and its date. The UI
records its own decisions in its repository. A number in backticks names a design note ([`design/`](design/README.md)).
Smaller decisions are recorded as ADRs ([`adr/`](adr/)).

## A. Storage and the criterion

| # | Question | Decision |
|---|---|---|
| A1 | Governance data inside the product repository, as the default? | First yes (2026-10-07), **superseded 2026-10-08** by the home-store requirement ([`13`](design/13-criterion-home-requirement.md)): the criterion lives in `$HOME/.catalyst/projects/<name>/criterion` (a workspace's in `$HOME/.catalyst/workspaces/<name>/criterion`), nothing in the project but `catalyst.toml`; a runtime per criterion; the name "criterion" stays |
| A2 | A multi-user server or database within about six months? | **Yes** (2026-10-07): the server driver scheduled as R3.9 and R5 ([`19`](design/19-server-design.md)), not "later" |
| A3 | Migrate the three existing deployments, or keep them as legacy? | **Legacy if it cuts work** (2026-10-07): `catalyst migrate` optional; read-only legacy support for one minor (R3.4) |
| A4 | Windows a 1.0 target? | **Yes** (2026-10-07): Windows in CI from R0.21; no symlinks, colons or absolute paths |
| A5 | Redact a secret journaled by mistake, although that weakens "immutable"? | **Yes, as an auditable tombstone** (2026-10-14): a redaction is itself a journal entry; the content gives way to a tombstone and its blob leaves the pins; the entry and its hash stay (R3.7, `catalyst journal redact`) |

## B. Scope and product

| # | Question | Decision |
|---|---|---|
| B1 | Software engineering first, or a second module (legal, research, …) at 1.0? | **Software engineering first, with a foray into risk management** (2026-10-17): a risk-management module as the second module, a pilot and the proof that nothing in the kernel or any UI names a module type; not a 1.0 product promise (R7); the risk-management module published 2026-10-18 (`cantica-tech/catalyst-risk-management` 0.1.0) |
| B2 | Which agents are first-class at 1.0? | **Claude Code, GitHub Copilot and Gemini CLI** (2026-10-17): `catalyst agent install` wires all three; `catalyst agent run` needs Copilot and Gemini CLI adapters beside Claude Code's (R5.5 follow-up) |
| B3 | Keep the plugin (catalyzer) concept? | **Parked** (2026-10-08), then **removed** in kernel 0.72.0 (2026-10-16, ADR-022); `catalyst-git` an optional extension |
| B4 | Keep meta-tags (no uses)? | **Dropped** for a `tags:` field (2026-10-08); removed in kernel 0.69.0 |
| B5 | Is four-eyes analysis (`/run-analysis`) a headline feature to keep? | **Keep it, and make its use configurable** (2026-10-16): two independent, blind passes then a person's decision stay the default; a deployment sets its default number of passes and one analysis can choose it when started (`catalyst analysis start … --passes 1\|2`); a single-pass analysis still ends with a person deciding each finding (law L4) and is recorded as single-pass. Built in kernel 0.84.0 (R4.10, REQ-000058): `catalyst.toml` `analysis_passes` and `--passes` |
| B6 | Break the 0.x format once, or in many small steps? | **Many small ones** (2026-10-17): each format change ships in its own release with its own migration (`framework/kernel/migrations/`) |
| B7 | One model for rule storage (R0.9): enforce ADR-001's one shape, or allow both? | **Allow both** (2026-10-18): a rule is a heading in a rule document or its own file listed by one, both checked alike; ADR-001 superseded in catalyst's record |
| B8 | May other sites embed views of the record (R6.28's web component)? | **Yes** (2026-10-18): `catalyst serve` answers reads from the origins a deployment allows, each with its reader's token, never writes; nothing is allowed by default |
| B9 | An assignee on work, dates on roadmap rows (the Studio's R6.48 and Gantt view)? | **Yes** (2026-10-18): the process module's work types gain an assignee and its roadmap rows a start and a due date; both optional |
| G | Should changes to some rules or entities need approval gates (e.g. two approvals from a role) before they take effect? | **For 1.0, opt-in** (2026-10-16): no gate unless a deployment declares one; a gate names what it covers (a rule domain, an entity type and state) and how many approvals from which role; `status set` and rule edits refuse until they are recorded, `check` reports a gated change that landed without them, each approval is a journaled act by a named person. Roles stay advisory outside gates. Design [`25`](design/25-approval-gates.md) decided 2026-10-17, all as recommended: `IAM/gates.json`; an approval is of a version; the author does not count; `--force` does not pass a gate; a gate covers a rule domain or an entity type entering a state |
| P | How is a change offered for review before it lands (the Studio's R6.44)? | **As a proposal** (2026-10-17), design [`26`](design/26-proposals.md), all as recommended: a reconciliation case of kind `proposal` carrying the proposed file beside it, with its base; `accept` writes it, refused when the base has moved and for its own proposer; approvals of the proposed version count once it lands; one file per proposal at 1.0 |
| T | How is a change tried before it is made (the Studio's R6.47)? | **`catalyst try <verb …>`** (2026-10-17), design [`27`](design/27-impact-simulation.md), all as recommended: the real verb on a scratch copy (a worktree of the criterion with its current files over it), the `check` findings it adds and clears reported, nothing kept, no `--apply`; the Studio's Try it needs no confirmation |
| S | Should rules be typed must / should / may (the Studio's R6.46)? | **Yes, with a strength that changes how a breach is reported** (2026-10-18): a rule states `must`, `should` or `may`; one that states none is `must`, so no existing rule loosens; `check` reports an unknown value; a `must` breach is a violation, a `should` breach a warning, a `may` one a note |
| E | Are decisions recorded as entities (the Studio's R6.45)? | **Yes** (2026-10-18): a decision is recorded, so it is an entity, an `ADR-` type of the process module (the kernel names no type); an ADR names the rules it shapes; catalyst's own ADRs move into its record |

## D. Process

| # | Question | Decision |
|---|---|---|
| D1 | Journal catalyst's own refactor (dogfooding) during R0–R2? | **Suspended 2026-10-07, restored 2026-10-10**: every catalyst change is journaled |
| D2 | Where do the analysis and design notes live? | **In `docs/`** (2026-10-17): moved from the owner's working notes as each is checked, reworded where it named a product or project built on catalyst; the roadmap and these decisions split by repository |
| D3 | Who is the first human beta tester? | **The owner** (2026-10-17): the beta trial (RM-026, RM-028, RM-029) can start |
| D4 | R0–R2 only (most of the token savings, no architecture change), or the full path? | **The full path**, answered in practice: R0 to R6 are done or under way |
