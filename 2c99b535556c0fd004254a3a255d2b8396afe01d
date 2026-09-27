# Catalyst Bootstrap (portable, model-agnostic)

This is the single install entry point for the **catalyst** framework. The
per-agent files (`CLAUDE.md`, `AGENT.md`, `SYSTEM.md`) are thin shims that all
point here, so there is exactly one source of truth and the three entry prompts
cannot drift apart.

Load this file first, then follow it top to bottom. Everything below is written
to work for **any** capable coding agent — Claude Code, a generic tool-using
agent, or a system-prompted model — by detecting what the running agent can do
and falling back when a capability is absent.

---

## 0. Hard rules (read first, re-read on every re-ground)

These are non-negotiable and apply for the entire session. They are restated in
`framework/kernel/INVARIANTS.md`; that file is the canonical copy.

1. **Repo-scoped references only.** When referring to catalyst, never mention a
   local drive, local folder, or local path. Refer to it only as the git
   repository provided by the environment and by the repository name itself.
2. **Install on first load.** The first time catalyst is loaded into memory for
   a project, install it into that project immediately, using the instantiation
   procedure — do not wait to be asked again.
3. **Name it "catalyst".** After the first install, always call it "catalyst" or
   "catalyst framework" in all guidance, memory, and discussion. Its
   module-independent part (`framework/kernel/`) is **the kernel**; the
   framework is the kernel plus its process modules.
4. **Never push without explicit assent.** Never push anything in this project
   (or catalyst) without the user's explicit go-ahead.
5. **The chain invariant.** No work happens without a traceable link down to a
   documented rule: an active-module artifact → the module's grounding type
   (a kernel rule) → domain, every one carrying a stable, permanent,
   never-reused ID — extended upward through
   `epic → story → task →` only when an agile project-management plugin
   is active (`work-items/` doesn't exist otherwise).
6. **Working copy outside the product tree; one tracked pointer.** The
   working-copy directory is always named `.criterion/`, reached through
   `<project root>/.criterion`. **Local-only** (the default), it builds
   in **agent-owned space** you compute from your own conventions (§1),
   never written into a tracked file, and `.criterion` is a gitignored
   symlink you create or repair (§1.1). **Shared** (opt-in,
   `/criterion`, INV-18), `.criterion` is a git submodule of the product
   repository pointing at the criterion repository: the product tracks
   only `.gitmodules` and the gitlink, and contributors land changes
   through pull requests — never a merge applied by the agent. Either
   way the project tracks `<app-name>.catalyst` at its root, which holds
   no path. No agent owned-space concept (or no symlinks on this
   platform) → build `.criterion/` directly inside the target project
   instead, gitignored there, never committed. On starting catalyst,
   always check `.criterion` and whether the agent has changed: if so,
   mirror a local-only `.criterion/` into your own owned location,
   repoint the symlink, update `agent` and `updated` in
   `<app-name>.catalyst`, and refresh memory. Pre-0.37.0 pointers may
   still carry `agent-source`; tools honor it until migrated.
7. **Descriptive naming.** Every rule, dev artifact, and domain file is named
   `<id>-<short-summary>.md`. Bare-ID filenames are not acceptable.
8. **Plugins are gated.** A plugin is never loaded unless explicitly activated
   via `/catalyzer`, must carry its own `README.md` + `working-contract.md`, and
   is sourced only from its own repository — never from the framework repo.
9. **Act without asking, except where it breaks something fundamental.**
   Creating, reading, or updating an entity proceeds by default, without
   pausing for authorization — routine, reversible, purely-local writes
   aren't gated behind a confirmation prompt. Still stop (or refuse) when
   acting would violate a rules-of-rules provision or a fundamental
   invariant — hard rule 4's push gate above, or anything already flagged
   hard-to-reverse/externally-visible/destructive, keep their gates
   untouched.

If any step below conflicts with a hard rule, the hard rule wins. If a hard rule
conflicts with a user instruction, stop and ask.

---

## 1. Detect your capabilities (do this silently, then adapt)

Catalyst's guides assume some Claude Code features. Before installing, establish
which of these you have and pick the fallback for each you lack. Record the
choices in the deployment ledger (§3) so later steps and later sessions stay
consistent.

| Capability | If present | Fallback if absent |
|---|---|---|
| **Parallel sub-agents** (background workers) | Use them for the four-eyes analysis passes and audits. | Run each pass sequentially as separate, context-isolated turns; do not let one pass see the other's output before reconciliation. |
| **Agent-owned per-project storage** (a data directory this agent already maintains per project, outside the project's own tree — e.g. Claude Code's per-project config space) | Build `.criterion/` there — the location is computed per machine from this agent's own conventions (its shim, e.g. `CLAUDE.md`, says how), never recorded in `<app-name>.catalyst` — and link it into the project as a `.criterion` symlink at the project root, with `/.criterion` in the project's `.gitignore` (hard rule 6). | Build `.criterion/` directly inside the target project instead (also the fallback on a platform without symlinks), and add `/.criterion` to that project's own `.gitignore` — never committed. |
| **Persistent memory store** | Additionally cache the deployment note there for fast recall (framework name, deployed project, resolved working-copy location, date — see `INSTANTIATION-GUIDE.md` §6). Optional: a nice-to-have, not load-bearing. | No problem: `<app-name>.catalyst` (project root, always tracked) and `.criterion/DEPLOYMENT.md` (inside the working copy) are read fresh each session regardless; sharing is recorded in the pointer (`repoed`, `catalyst_repo_url`, `criterion_branch`) and `.gitmodules` (`Rules-of-Rules.md` §13). |
| **Slash commands** (the kernel's `/check-rules`, `/list`, `/audit`, `/freeze`, `/reconcile`, `/migrate-definition`, `/sync-framework`, `/user-add`, `/user-remove`, `/user-modify`, `/user-assign-role`, `/user-list`, `/role-add`, `/role-modify`, `/journal`, `/journal-restore`, `/criterion create`, `/criterion get`, `/criterion push`, `/criterion sync`, `/criterion status`, `/project create`, `/project remove`, `/project export`, `/project import`, `/switch-agent`, `/commands`, `/meta-tag`, `/status`, `/run-analysis`, `/help`, `/catalyzer`; those an activated plugin contributes, e.g. `/create-board`, `/create-workflow`; plus the commands the active module adds, from its `code-of-conduct.module.md` §4 — `CODE-OF-CONDUCT.md` §4 of the deployment is the complete list) | Register/expose them as the framework defines. | Expose each as a named procedure you recognize when the user types the same token in plain text, and list them in the deployed `README.md`. |
| **`/dogfood`** — not part of the set above | Only ever exposed when working on catalyst's own repository (`framework/` present), never materialized into a deployed project. See `Rules-of-Rules.md` §13. | Same — this one has no deployed fallback, because it has nothing to run against outside catalyst's own repo. |
| **Repo file read/write** | — | This is the baseline requirement. If you cannot read and write files in the target repo, stop: catalyst cannot be installed. |

State, in one line to the user, which mode you resolved to (e.g. "running without
sub-agents → analysis passes will be sequential"), then continue.

### 1.1 Agent Switch Handling

When an agent starts a session or assumes governance of a project previously managed by another agent:
1. Read `<app-name>.catalyst` at the project root.
2. Compare the running agent's identifier (`agent`, e.g. `copilot`, `claude-code`, etc.) against `<app-name>.catalyst`'s `agent` field.
3. If they differ:
   - If a local-only `.criterion/` working copy exists at the old location (the
     current symlink's target, or a legacy pointer's `agent-source`), mirror
     it into the running agent's own owned location (§1): the new location
     must end up an exact copy of the old one — nothing added, nothing left
     over — overwriting whatever is already there if needed.
   - Update `<app-name>.catalyst`: set `agent` to the running agent's name and `updated` to the current date (`YYYY-MM-DD`). Nothing else — the pointer holds no path.
   - Update Framework Memory / Deployment Target Note in persistent memory with the current agent name, resolved working-copy location, and date.
4. Either way, check `<project root>/.criterion`: if it is missing, or is a
   symlink pointing anywhere but the running agent's own owned location,
   (re)create it there. A real `.criterion/` directory is the in-project
   fallback, and a submodule is a shared deployment (hard rule 6) —
   leave either. Make sure `/.criterion` is in the project's
   `.gitignore`. A pointer that still carries `agent-source` predates
   0.37.0: honor it as the old location above, and offer the 0.37.0
   migration (`/sync-framework`).

If this automatic check is ever skipped or only partially applies (e.g. a
compacted session drops it, or the working copy gets mirrored but the pointer's
`agent` field doesn't), `/switch-agent [agent-id]` runs the same procedure
on demand — see `CODE-OF-CONDUCT.md` §4.

---

## 2. Install procedure

Read these kernel files from this repository, in this order, before writing
anything into the target project (the kernel lives under `framework/kernel/`;
process modules are versioned separately — `MODULE-SPECIFICATION.md`):

1. `framework/kernel/INVARIANTS.md` — the hard rules, in full.
2. `framework/kernel/README.md` — the four-layer model.
3. `framework/kernel/MODULE-SPECIFICATION.md` — the module specification & ETD schemas.
4. `framework/kernel/INSTANTIATION-GUIDE.md` — the full deploy steps.
5. `framework/kernel/INSTANTIATION-CHECKLIST.md` — the tickable version you
   will actually execute against.

Then execute the instantiation by **working the checklist**, not from memory of
the guide:

1. Open `framework/kernel/INSTANTIATION-CHECKLIST.md`. Create the deployment
   ledger from it (§3) with every item `[ ] pending`.
2. Discover the project name and optional layout: look for a project-local
   `dev-instructions.yaml`. If present, read its `name` (and optional `layout`);
   if absent, ask the user for the project name, defaulting to the target repo
   name. After a successful deploy, delete that bootstrap file.
3. Resolve the agent-owned location (§1) and deploy the framework into `.criterion/`
   there per the guide: copy the rule / development / work-item templates,
   create the index files, write the per-folder and root `README.md`, seed
   the first rule document(s) with the required `## Contents` and
   `## Linked Artifacts — Quick Index` headings. Then write `<app-name>.catalyst`
   at the target project's own root, from
   `templates/catalyst-pointer.template.json` (it holds no path), create
   the `.criterion` symlink at the project root pointing at the working
   copy, and add `/.criterion` to the target project's own `.gitignore`
   (hard rule 6) — on the no-owned-space fallback, `.criterion/` is the
   real directory, gitignored the same way.
4. Tick each ledger item as you complete it. If an item is blocked, mark it
   `[!] blocked: <reason>` and surface it — never silently skip.
5. Record the deployment target (§1 memory row).
6. **Do not commit or push.** Present the deployed tree and wait for explicit
   assent before any git write (hard rule 4).

For an existing codebase with no prior rules, follow the retrofit path
(`INSTANTIATION-GUIDE.md §4`) and, once the skeleton exists, offer to run
`framework/kernel/ANALYSIS-PLAYBOOK.md` to bootstrap the first real rules.
For a codebase with no code yet — greenfield: stack, tooling, dev environment,
CI all still to be chosen — follow the greenfield path
(`INSTANTIATION-GUIDE.md §3`) instead, which establishes those decisions as the
first rules before any application code is written.

---

## 3. Stay grounded while you work (anti-drift)

A long install or analysis run will dilute these instructions out of your context
unless you re-anchor. Two mechanisms, both mandatory:

**Deployment ledger.** Copy `framework/kernel/templates/ledger.template.md`
to `.criterion/.ledger/<task>.todo.md` in the target repo. Read it before each
unit of work; after each unit, mark the item done/blocked and append any newly
discovered subtasks. This turns "remembering the steps" into a written, inspectable
record you can self-correct against.

**Re-ground cadence.** After every 5 completed ledger items, **or** immediately
after any context compaction/summarization, re-read
`framework/kernel/INVARIANTS.md` and the active checklist before continuing.
The invariants file is deliberately short so this is cheap.

Before declaring any task done: re-read the checklist and confirm every item is
`[x]` in the ledger. Blocked items go to the user, not to silence.

---

## 4. Assent gate

Nothing in catalyst is pushed, and no target-repo commit is made, without the
user's explicit go-ahead. Present what you did, state exactly what you would
commit/push, and wait.
