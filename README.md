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

**Documentation:** <https://cantica-tech.github.io/catalyst-docs/> — the
guide (what catalyst is, getting started, working day to day and together)
and a reference of catalyst's public repositories.

### What it looks like

A fictional project: one rule, one piece of work fixing it, one journal line.

```text
rules/business-rules.md
  br-AUTH-000003-Ab3xR9pQ  ✅ A password-reset link expires after 30 minutes.

ITEM-000012-Ab3xR9pQ-reset-link-never-expires.md
  Targets: br-AUTH-000003-Ab3xR9pQ   Status: Done   Signed-off-by: Ada Lovelace

development/journal/ada@k3j9q2/2026-10.jsonl
  {"command": "/status", "action": "status-change", "tier": "fix", "via": "agent",
   "artifact": "ITEM-000012-Ab3xR9pQ", "targets": ["br-AUTH-000003-Ab3xR9pQ"],
   "intent": ["Reset links honour the 30-minute expiry again"],
   "files": [{"path": "src/auth/reset.py", "before": "9f2c…", "after": "41ab…"}, …]}

$ catalyst check
catalyst check passed: 0 error(s), 0 warning(s)
```

Months later, `/journal --rule br-AUTH-000003-Ab3xR9pQ` lists every change
made for that rule, and `/journal restore <timestamp>` rebuilds the tree as
it stood. The terms used here are defined in the
[glossary](framework/kernel/GLOSSARY.md); the
[guide](https://cantica-tech.github.io/catalyst-docs/) explains catalyst
from the start.

## Kernel and modules

The framework is the **kernel** plus one or more **process modules** per
deployment. The kernel is process-agnostic: it owns rules and domains,
reconciliation cases (`RECON-`), workflows (`WORKFLOW-`), signing and
grants, the journal, sharing and landing, and entity definitions as a
mechanism. A module adds its development-artifact types — their templates,
definitions, commands, meta-rules, invariants and migrations — and is named
in the project's `catalyst.toml` (`module`). Modules compose (INV-30): each
works as a deployment's only module and beside any other, in either install
order, and never names another (`catalyst module install` adds one). Each
production module lives in its own repository, listed in
`framework/modules/catalog.md`; see that repository for what its artifact
types are and how they relate. The contract between kernel and module is
`framework/kernel/MODULE-SPECIFICATION.md`.

## The core chain

At its center is a three-layer chain, each layer subordinate to the one below it:

```
Dev artifacts    <PREFIX>-NNNNNN-(userid) (a module's)   (rule-linked work)
                        ▼
Rules            (prefix)-(DOMAIN)-(NNNNNN)-(userid)     (documented behavior)
                        ▼
Rules of rules   the meta-rules governing all of the above
```

A module that needs a planning layer above its dev artifacts declares it as
its own types; they ground through their children, or a parent's.

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

## Development artifacts: the modules

Everything above a rule belongs to the modules: which
dev-artifact types exist, how they decompose into smaller units of work, how
they are verified, which ideas sit above the chain before they are ready to
be measured against a rule, and which day-to-day views summarize them. The
kernel only fixes the shape every such type shares — a permanent
`<PREFIX>-NNNNNN` ID, its own folder and index in the working copy, a
versioned definition, a `Signed-off-by`, and a grounding link down to a
rule, direct or through a parent artifact — and the commands that work on
any of them (`/create`, `/status`, `/list`, and `catalyst edit` for an
entity's fields and sections). A type's `WORKFLOW-`, once active, decides
which status moves it may make, by whom and under which conditions. Each
module's own commands (listed in its `code-of-conduct.module.md` §4) are
added to the deployment alongside the kernel's.

## Accountability: users, roles, signing

People are not kept in a criterion: they are catalyst-users', a facade to
any identity provider (Keycloak built in). Each signature is the verified,
logged-in identity, recorded once in the criterion's signers ledger
(`IAM/signers.jsonl`, append-only), so every artifact's `Signed-off-by` names
someone the provider vouched for. What a person may do comes from the
provider too: their grants decide which commands they run and which types
they create, their roles set their reconciliation level, and a criterion's
admins hold every grant in that criterion only. Anyone else creates only
the types a module leaves open to contributors, and edits only their own
entities — an entity already linked to others as a proposal an admin
decides. When no one is logged in, a machine's system account (set up by
catalyst-users) signs, and says so. A criterion shared through
`catalyst serve` can also record who belongs to it, in a signed,
encrypted ledger kept by the server, and admit only them
(`catalyst members`).

## History: the journal

The journal (`development/journal/`, one shard per actor, machine and month) is an append-only, transaction-log-grade record
of every rule-linked change — not a changelog. Each entry carries the exact
git content hash before and after, per touched file, plus the rule(s) it
served, the actual intent behind it (the goal, not a label), and how it
was made (`via`: an agent, a person, or a server). Because the
pointers are exact, `/journal restore <timestamp>` can materialize the tree
as it stood at any point into a side directory for inspection — a real
point-in-time reconstruction, never a guess, and never applied to the live
tree automatically. `/journal` is the read-only query side.

## The catalyst CLI

The mechanical steps — allocating IDs, drawing userids, hashing files into
the journal, regenerating indexes, validating the traceability chain — are
code, not prose: the `catalyst` command line, installed as
`~/.catalyst/bin/catalyst` and kept in every criterion as `bin/catalyst.pyz`
at the version it was deployed with. Procedures call it and keep only the
judgment parts in prose; agents with an end-of-turn hook run
`catalyst hook stop` so every turn ends on a passing `catalyst check`.
Commits trace too: a git `commit-msg` hook (`catalyst hook install`) and
`catalyst trace` in CI require every product commit to cite an artifact or
rule ID, or to be marked `chore:`. Changes made by hand, straight into
git, are caught too: `catalyst unrecorded`, `check` and `trace` report
every commit whose changes the journal does not record, and `/adopt`
either records it in the journal or reverts it. Every writing verb takes
`--preview`, to see what a change would do before making it, and
`catalyst migrate` lists (and, with `--apply`, makes) what a deployment
needs to catch up with its kernel. See
[`framework/kernel/CLI.md`](framework/kernel/CLI.md); every file the CLI
reads and writes is specified in
[`framework/kernel/FORMAT.md`](framework/kernel/FORMAT.md) (format
`1.0-rc`).

## Multi-user sync: sharing a criterion

A deployment stays local by default, but can opt into being **shared**.
`/share create <url>` (`catalyst share create <url>`) publishes the
criterion to a dedicated criterion repository and records it in
`catalyst.toml`; a teammate runs `catalyst open` in their clone of the
product and gets the same criterion in their own catalyst home. Changes
land through pull requests against the shared branch with `/share push`:
it rebases (the journal's per-person shards and the generated indexes
merge cleanly), runs `catalyst check` — which also checks a merge lost
nothing — and opens the pull request, after showing what it would publish
and getting your yes. The criterion repository's CI runs the same checks,
and `share create --protect` makes them required. The AI never applies a
merge: a real conflict stops the push, and a proposed resolution waits as
a reconciliation case for a human (`catalyst reconcile`). IDs stay unique
across contributors through their userid suffix, so nobody renumbers.
Signers are verified by the identity provider (above); branch protection
and review remain the controls on what merges.

A criterion can also be shared through a server, `catalyst serve`: its
members push their changes to it, and it lands them in the criterion
repository. How changes land is the criterion's own policy,
`IAM/landing.json` (`catalyst landing init|show`; without one, the
`standard` policy): the server groups accepted changes per change, per
session or per time window, commits each group on a topic branch with a
`Signed-off-by` per signer, opens a pull request, and merges it itself
only when the policy says no review is needed and the check passes. A file
changed on the shared branch since stops its landing for a human. See
[`framework/kernel/CLI.md`](framework/kernel/CLI.md).

## Dogfooding

A vetting procedure — `/check-rules` plus an independent four-eyes
sub-agent pass checking whether the actual state still matches what the
rules claim — runs as a standalone command, `/dogfood`, on demand against
catalyst's own repository. `/dogfood` is deliberately **not** part of what gets
deployed into other projects: it only ever exists in catalyst's own repo,
for verifying catalyst's own rules against catalyst's own actual state,
never as something an ordinary deployment carries around.

## Extensible through modules

New capability comes as a module: its types, templates, commands and
rules as data, several modules per deployment (`catalyst module install`),
each knowing none of the others.
The plugin system that came before is retired (ADR-022). `catalyst-git`,
which watches a deployed project and surfaces rule breaks as they happen,
remains an optional extension in its own repository; catalyst does not
load it.

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

The [guide](https://cantica-tech.github.io/catalyst-docs/) walks through
getting started, day-to-day work, people and signing, working together and
keeping up to date. To try catalyst by hand in about fifteen minutes, follow
[`beta/QUICKSTART.md`](beta/QUICKSTART.md). The beta's multi-user trial —
its protocol and the feedback form — is in [`beta/`](beta/)
([`TRIAL.md`](beta/TRIAL.md), [`FEEDBACK.md`](beta/FEEDBACK.md)).

## Agents

catalyst's documents are written to be agent-agnostic: they detect what the
running agent can do and fall back when a capability is absent. Only
**Claude Code** is supported and tested today. Other agents can follow
`AGENT.md` or `SYSTEM.md`, and the `catalyst` CLI works from any shell, but
those paths are untested. An agent is wired once per machine, at user
level — `catalyst agent install <agent>` registers the `catalyst mcp`
server (the commands as prompts) and the end-of-turn hook — and catalyst
writes no file into a project but `catalyst.toml`. catalyst installs only when you ask
(`catalyst init`, INV-2), and stays grounded across long runs through
explicit anti-drift mechanisms (an invariants file, deployment ledgers, a
re-ground cadence and an end-of-turn `catalyst check`) rather than trusting
the agent to simply remember.

The criterion is the project's governance context — not part of the
developed code, so it never sits in the project's tree: it lives in
catalyst's home, `$HOME/.catalyst/projects/<name>/criterion`, the same for
every agent. The project tracks exactly one small file, `catalyst.toml`,
which names it and holds no path, so it is identical on every clone;
`catalyst where` finds the criterion and `catalyst open` makes it ready on a
machine. Sharing it with a team is opt-in (`/share`, above).

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
