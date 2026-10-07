# Catalyst Bootstrap

This is the single install entry point for the **catalyst** framework. The
per-agent files (`CLAUDE.md`, `AGENT.md`, `SYSTEM.md`) are thin shims that all
point here, so there is exactly one source of truth and the three entry prompts
cannot drift apart.

Load this file first, then follow it top to bottom. It is written to be
agent-agnostic — it detects what the running agent can do and falls back when
a capability is absent — but only **Claude Code** is supported and tested
today. Other agents can follow `AGENT.md`/`SYSTEM.md`, and the `catalyst` CLI
works from any shell, but those paths are untested.

---

## 0. Hard rules (read first, re-read on every re-ground)

These are non-negotiable and apply for the entire session. They are restated in
`framework/kernel/INVARIANTS.md`; that file is the canonical copy.

1. **Repo-scoped references only.** When referring to catalyst, never mention a
   local drive, local folder, or local path. Refer to it only as the git
   repository provided by the environment and by the repository name itself.
2. **Install only when asked.** Loading or reading catalyst never installs
   it. Install into a project only when the user explicitly asks
   (`catalyst init`, `/project create`, or in plain words), using the
   install procedure (§2); otherwise, at most offer to.
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
| **Slash commands** (every command in the deployment's `CODE-OF-CONDUCT.md` §4 — kernel, active module and activated plugins; `catalyst spec` lists them. Never keep a copy of that list here or anywhere else) | Register/expose them as the framework defines. | Expose each as a named procedure you recognize when the user types the same token in plain text, and list them in the deployed `README.md`. |
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

Run this only on the user's explicit request (hard rule 2). The mechanical
part is one command, `catalyst init` (`framework/kernel/CLI.md`); the agent
keeps the judgment. Read first, from this repository: `framework/kernel/INVARIANTS.md`
(in full), `framework/kernel/README.md`, `framework/kernel/INSTANTIATION-GUIDE.md`
and `framework/kernel/INSTANTIATION-CHECKLIST.md` (the tickable version you
work against). Then:

1. **Ledger.** Create the deployment ledger from the checklist (§3), every
   item `[ ] pending`. `catalyst init` adopts a `.criterion` that holds
   only that `.ledger/`.
2. **Resolve the inputs** — judgment, asked of the user only when needed.
   R1.2+ simplifies this to **≤3 questions** for the common case:
   
   - **the project name** — from a project-local `dev-instructions.yaml`'s 
     `name` if present (deleted after install), else ask, defaulting to the 
     repository name. **[1 question; common default]**
   
   - **rule documents** — one judgment: "Simple (one default document) or 
     Advanced (customize)?" If simple, use `<name>-rules.md` with prefix `br`; 
     if advanced, ask for list and prefixes per natural seam 
     (`INSTANTIATION-GUIDE.md` §1). **[1 question]**
   
   - **git user** — auto-detect from `git config user.name` or `git config 
     user.email` (extract local part before `@`). If not found on the machine, 
     ask once: "Git user? (name and/or email)". Both `--user` and 
     `--git-username` resolve from this single answer. **[0–1 question]**
   
   The following are auto-detected or use defaults and **require no judgment**:
   
   - **the active module** — defaults to `software-engineering` (SE module). 
     Multi-module support and module choice return in R3/R5 when the locator 
     replaces the pointer. Pass `--module <id>` to override if needed.
   
   - **working-copy directory** — computed from the running agent's conventions 
     (agent-owned space per §1). Agent shim (e.g. `CLAUDE.md`) documents the 
     location. For agents without owned-space, `.criterion/` builds in-project 
     (also fallback on platforms without symlinks).
   
   - **commands directory** — computed from the running agent's config 
     (e.g. `.claude/commands` for Claude Code). For agents not supporting 
     command files, skipped.
3. **Run `catalyst init`** from the project root with the resolved inputs.
   The command line varies by judgment outcome:
   
   **Minimal case (all defaults):**
   ```
   catalyst init --name <project-name> --user <git-user> --agent <agent-id> \
                 --kernel <framework/kernel>
   ```
   (Uses `--module software-engineering`, `--rule-doc <name>-rules:br`, 
   auto-detected `--at` and `--commands-dir`.)
   
   **Advanced rules:**
   ```
   catalyst init --name <project-name> --user <git-user> --agent <agent-id> \
                 --rule-doc <file1>:<prefix1> --rule-doc <file2>:<prefix2> ... \
                 --kernel <framework/kernel>
   ```
   
   Catalyst init builds the whole skeleton: composed governing documents,
   the seeded module, every entity folder with its index and templates 
   catalog, frozen definitions, the first user with a userid, the journal, 
   the vendored CLI, the `<app-name>.catalyst` pointer and the gitignored 
   `.criterion` symlink. It also copies `INVARIANTS.md` into the working copy 
   and installs a session-start hook (where the agent supports one) that 
   re-injects it, so later sessions in the project are grounded without this 
   repository. It refuses if catalyst is already installed.
4. **Finish the judgment work** per `INSTANTIATION-GUIDE.md` §1: register the
   end-of-turn hook if the agent has one, add the project's root
   `Taskfile.yml`, then the path's first rules — **greenfield** (no code yet:
   stack, tooling, dev environment and CI decided as the first rules, §3) or
   **retrofit** (existing code: rules gathered incrementally, optionally
   bootstrapped with `/run-analysis --bootstrap`, §4) — and
   `catalyst check`.
5. Tick each ledger item as you complete it. If an item is blocked, mark it
   `[!] blocked: <reason>` and surface it — never silently skip.
6. Record the deployment target (§1 memory row).
7. **Do not commit or push.** Present the deployed tree and wait for explicit
   assent before any git write (hard rule 4).

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
`framework/kernel/INVARIANTS.md` (in a deployed project,
`.criterion/INVARIANTS.md`) and the active checklist before continuing.
The invariants file is deliberately short so this is cheap.

Before declaring any task done: re-read the checklist and confirm every item is
`[x]` in the ledger. Blocked items go to the user, not to silence.

---

## 4. Assent gate

Nothing in catalyst is pushed, and no target-repo commit is made, without the
user's explicit go-ahead. Present what you did, state exactly what you would
commit/push, and wait.
