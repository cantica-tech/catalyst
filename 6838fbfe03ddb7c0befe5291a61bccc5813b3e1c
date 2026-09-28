# catalyst

**Persistent, verifiable project memory for codebases developed with AI
coding agents.** An agent forgets between sessions why the code is the way
it is, and nothing it leaves behind says which requirement a line serves.
catalyst is for developers and teams who build with an agent and still need
to answer "why does this code do X?" months later. The agent works inside a
small, structured record kept next to the project: documented rules, work
that traces to those rules, and an append-only journal of every change —
so every change traces to a documented rule, and every rule back to the
work that exercises it. A tested CLI keeps the IDs, the journal and the
indexes honest, so the record can be checked rather than trusted.

catalyst is in **beta**. Claude Code is the supported and tested agent;
others can follow `AGENT.md`/`SYSTEM.md` but are untested (see
[Agents](#agents)).

### What it looks like

A fictional project: one rule, one piece of work fixing it, one journal line.

```text
rules/business-rules.md
  br-AUTH-000003-Ab3xR9pQ  ✅ A password-reset link expires after 30 minutes.

ITEM-000012-Ab3xR9pQ-reset-link-never-expires.md
  Targets: br-AUTH-000003-Ab3xR9pQ   Status: Done   Signed-off-by: Ada Lovelace

development/journal.jsonl
  {"command": "/status", "action": "status-change", "tier": "fix",
   "artifact": "ITEM-000012-Ab3xR9pQ", "targets": ["br-AUTH-000003-Ab3xR9pQ"],
   "intent": ["Reset links honour the 30-minute expiry again"],
   "files": [{"path": "src/auth/reset.py", "before": "9f2c…", "after": "41ab…"}, …]}

$ python3 .criterion/bin/catalyst.pyz check
catalyst check passed: 0 error(s), 0 warning(s)
```

Months later, `/journal --rule br-AUTH-000003-Ab3xR9pQ` lists every change
made for that rule, and `/journal-restore <timestamp>` rebuilds the tree as
it stood. The terms used here are defined in the
[glossary](framework/kernel/GLOSSARY.md).

## Kernel and modules

The framework is the **kernel** plus one **process module** per deployment.
The kernel is process-agnostic: it owns rules and domains, reconciliation
cases (`RECON-`), workflows (`WORKFLOW-`), meta-tags, users and roles, the
journal, repoed sync, plugins, and entity definitions as a mechanism. The
active module adds its development-artifact types — their templates,
definitions, commands, meta-rules, invariants and migrations — and is named
by the `module` field of the project's `<app-name>.catalyst` pointer. Each
production module lives in its own repository, listed in
`framework/modules/catalog.md`; see that repository for what its artifact
types are and how they relate. The contract between the two is
`framework/kernel/MODULE-SPECIFICATION.md`.

## The core chain

At its center is a four-layer chain, each layer subordinate to the one below it:

```
Work items    EPIC ─▶ STORY ─▶ TASK / SPIKE / SPRINT   (agile process layer)
                        ▼
Dev artifacts   <PREFIX>-NNNNNN (the active module's)  (rule-linked work)
                        ▼
Rules          (prefix)-(DOMAIN)-(NNNNNN)-(userid)      (documented behavior)
                        ▼
Rules of rules   the meta-rules governing all of the above
```

The work-items layer is optional, plugin-provided content, not core — see
"Extensible via plugins" below. Without one active, the chain starts one
layer down: dev artifacts trace straight to a rule.

The chain's one invariant: **no work happens without a traceable link down to a
documented rule** — an active-module artifact grounds to the module's
grounding type (a kernel rule), and that rule to its domain — and every
document, domain, and rule carries a stable, permanent, never-reused ID. That
is what makes both "why does this code do X" and "what rule does this ticket
satisfy" answerable by following IDs in either direction, indefinitely. Rules
are never deleted, only retired in place — a retired rule keeps its ID, gets
marked 🗑 with a reason and date, and stays a valid target for the
dev-artifact that explains why — so any reference to it, in code, tests, or
tickets, stays resolvable forever.

## Development artifacts: the active module

Everything between a work item and a rule belongs to the active module: which
dev-artifact types exist, how they decompose into smaller units of work, how
they are verified, which ideas sit above the chain before they are ready to
be measured against a rule, and which day-to-day views summarize them. The
kernel only fixes the shape every such type shares — a permanent
`<PREFIX>-NNNNNN` ID, its own folder and index in the working copy, a
versioned definition, a `Signed-off-by`, and a grounding link down to a
rule, direct or through a parent artifact — and the commands that work on any of them (`/status`, `/list`,
`/meta-tag`, `/audit`). The module's own commands (listed in its
`code-of-conduct.module.md` §4) are added to the deployment alongside the
kernel's.

## Accountability: users, roles, signing

Every artifact carries a `Signed-off-by` field, resolved against a
registered-user list (`/user-add`/`-remove`/`-modify`/`-assign-role`) and a
role → typical-action mapping (`/role-add`/`-modify`, seeded with a default
agile-role set). A project must always have at least one active user — the
one hard requirement — but role checks themselves are advisory, not access
control: catalyst has no way to verify who's actually typing, so a mismatch
prompts for confirmation rather than blocking.

## History: the journal

`development/journal.jsonl` is an append-only, transaction-log-grade record
of every rule-linked change — not a changelog. Each entry carries the exact
git content hash before and after, per touched file, plus the rule(s) it
served and the actual intent behind it (the goal, not a label). Because the
pointers are exact, `/journal-restore <timestamp>` can materialize the tree
as it stood at any point into a side directory for inspection — a real
point-in-time reconstruction, never a guess, and never applied to the live
tree automatically. `/journal` is the read-only query side.

## The catalyst CLI

The mechanical steps — allocating IDs, drawing userids, hashing files into
the journal, regenerating indexes, validating the traceability chain — are
code, not prose: the `catalyst` command line, vendored into every deployment
as `.criterion/bin/catalyst.pyz`. Procedures call it and keep only the
judgment parts in prose; agents with an end-of-turn hook run
`catalyst hook stop` so every turn ends on a passing `catalyst check`.
Commits trace too: a git `commit-msg` hook (`catalyst hook install`) and
`catalyst trace` in CI require every product commit to cite an artifact or
rule ID, or to be marked `chore:`. Changes made by hand, straight into
git, are caught too: `catalyst unrecorded`, `check` and `trace` report
every commit whose changes the journal does not record, and `/adopt`
either records it in the journal or reverts it. See
[`framework/kernel/CLI.md`](framework/kernel/CLI.md); every file the CLI
reads and writes is specified in
[`framework/kernel/FORMAT.md`](framework/kernel/FORMAT.md) (format
`1.0-rc`).

## Multi-user sync: criterion

A deployment stays local by default, but can opt into being **shared**
on plain git. `/criterion create` (`catalyst criterion create <url>`)
publishes the working copy to a dedicated criterion repository and makes
`.criterion` a submodule of the product repository, so every product
commit pins the rules in force. Contributors check it out with
`/criterion get`, and land changes through pull requests against the
shared branch with `/criterion push`: it rebases (the journal and the
generated indexes merge by union), runs `catalyst check` and an integrity
check that nothing recorded was lost, and opens the pull request; the
criterion repository's CI runs the same checks, and
`catalyst criterion protect` makes them required. The AI never applies a
merge: a real conflict stops the push, and a proposed resolution waits as
a reconciliation case for a human. IDs stay unique across contributors
through their userid suffix, so nobody renumbers. Identity is still
self-declared; branch protection and review are the real controls. See
[`framework/kernel/CLI.md`](framework/kernel/CLI.md).

## Dogfooding

A vetting procedure — `/check-rules` plus an independent four-eyes
sub-agent pass checking whether the actual state still matches what the
rules claim — runs as a standalone command, `/dogfood`, on demand against
catalyst's own repository. `/dogfood` is deliberately **not** part of what gets
deployed into other projects: it only ever exists in catalyst's own repo,
for verifying catalyst's own rules against catalyst's own actual state,
never as something an ordinary deployment carries around.

## Extensible via plugins

Plugins add ongoing capability without touching the kernel — each
lives in its own repository (never this one, with one exception: schemas
and plugins still maturing live under `plugins/_prototyping/` until they
graduate out), is gated behind explicit activation (`/catalyzer`), and
operates on the *deployed* project, never on catalyst itself. Two shapes
exist: **background** plugins that continuously watch a deployed
project — `catalyst-git`, the first one, surfacing rule breaks as they
happen — and **content-contributing** plugins that add whole artifact
types to a deployment on activation. Work-item tracking (`EPIC`/`STORY`/
`TASK`/`SPIKE`/`SPRINT`) is the first of the latter kind: currently
schema-only, in `plugins/_prototyping/project-management/agile/`, with
no concrete, activatable plugin yet.

## Getting started

Ask your agent to install catalyst into the project; nothing is installed
until you do. Under Claude Code the mechanical part is one command,
`catalyst init` (see `CLAUDE.md`); the agent then works with you on the
judgment — the rule documents, the first rules. The install follows one of
two paths:

- **Greenfield** — no code yet: the stack, tooling, and dev-environment
  decisions get written and implemented as the project's first rules,
  before any application code exists.
- **Retrofit** — existing code, no rules yet: rules get gathered
  incrementally from what's already there, optionally bootstrapped with a
  four-eyes analysis pass (`/run-analysis`) rather than written up front.

Either way, the active module decides what the day-to-day view of open work
looks like; see its repository.

To try catalyst by hand in about fifteen minutes, follow
[`beta/QUICKSTART.md`](beta/QUICKSTART.md). The beta's multi-user trial —
its protocol and the feedback form — is in [`beta/`](beta/)
([`TRIAL.md`](beta/TRIAL.md), [`FEEDBACK.md`](beta/FEEDBACK.md)).

## Agents

catalyst's documents are written to be agent-agnostic: they detect what the
running agent can do and fall back when a capability is absent. Only
**Claude Code** is supported and tested today. Other agents can follow
`AGENT.md` or `SYSTEM.md`, and the `catalyst` CLI works from any shell, but
those paths are untested. catalyst installs only when you ask
(`catalyst init`, INV-2), and stays grounded across long runs through
explicit anti-drift mechanisms (an invariants file, deployment ledgers, a
re-ground cadence and an end-of-turn `catalyst check`) rather than trusting
the agent to simply remember.

`.criterion/` itself is the agent's own governance context for the
project — not part of the developed code structure, so it doesn't build
inside the project's own tree at all. It builds in **agent-owned space**
instead, at a location each agent computes per machine, and the project
reaches it through a gitignored `.criterion` symlink at its root. The
target project tracks exactly one small, committed file for it,
`<app-name>.catalyst`, which holds no path, so it is identical on every
clone; `/project create`/`remove`/`export`/`import` manage that
lifecycle. An agent with no owned-space concept (or a platform without
symlinks) falls back to building `.criterion/` directly in the project,
gitignored there instead. Either way, `/criterion` is the opt-in mechanism for a team
that wants the working copy shared across contributors: it moves to a
dedicated criterion repository, mounted as the product's `.criterion`
submodule, so the product commits only a gitlink — never the working
copy's content.

`BOOTSTRAP.md` is the single source of truth. Everything else here either points
at it or extends it.

## Which prompt to load

Choose the prompt file that matches the agent you are running, and load only
that file.

- `CLAUDE.md` — running Claude Code.
- `AGENT.md` — running a generic agent workflow.
- `SYSTEM.md` — running the system-level prompt.

All three load `BOOTSTRAP.md`, the single install core. Open the selected
file and follow its instructions from top to bottom. `CLAUDE.md` is the only
tested path.

## License

Apache License 2.0 — see `LICENSE`. Contributions: `CONTRIBUTING.md`;
security reports: `SECURITY.md`.
