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

## 0. The laws (read first, re-read on every re-ground)

Read the ten laws now: the top of `framework/kernel/INVARIANTS.md`, up to
its `end of the session brief` marker (in a deployed project, the session
start shows them, with the active module's own law). They are the only
rules you must judge for yourself and they apply for the whole session;
everything else is enforced by the CLI or explained on demand by
`catalyst why <L1…L10|INV-n|rule>`. That file is the canonical copy — this
one does not restate it.

If any step below conflicts with a law, the law wins. If a law conflicts with
a user instruction, stop and ask.

---

## 1. Detect your capabilities (do this silently, then adapt)

Catalyst's guides assume some Claude Code features. Before installing, establish
which of these you have and pick the fallback for each you lack. Record the
choices in the deployment ledger (§3) so later steps and later sessions stay
consistent.

| Capability | If present | Fallback if absent |
|---|---|---|
| **Parallel sub-agents** (background workers) | Use them for the four-eyes analysis passes and audits. | Run each pass sequentially as separate, context-isolated turns; do not let one pass see the other's output before reconciliation. |
| **Persistent memory store** | Additionally cache the deployment note there for fast recall (framework name, deployed project, resolved working-copy location, date — see `INSTANTIATION-GUIDE.md` §6). Optional: a nice-to-have, not load-bearing. | No problem: `catalyst.toml` (project root, always tracked) and the criterion's `DEPLOYMENT.md` are read fresh each session regardless (`catalyst where` finds the criterion). |
| **Slash commands** (every command in the deployment's `CODE-OF-CONDUCT.md` §4 — kernel, active module and activated plugins; `catalyst spec` lists them. Never keep a copy of that list here or anywhere else) | Register/expose them as the framework defines. | Expose each as a named procedure you recognize when the user types the same token in plain text, and list them in the deployed `README.md`. |
| **`/dogfood`** — not part of the set above | Only ever exposed when working on catalyst's own repository (`framework/` present), never materialized into a deployed project. See `Rules-of-Rules.md` §13. | Same — this one has no deployed fallback, because it has nothing to run against outside catalyst's own repo. |
| **Repo file read/write** | — | This is the baseline requirement. If you cannot read and write files in the target repo, stop: catalyst cannot be installed. |

State, in one line to the user, which mode you resolved to (e.g. "running without
sub-agents → analysis passes will be sequential"), then continue.

### 1.1 Switching agents

The criterion's place does not depend on the agent (law L5): a new agent
runs `catalyst open --agent <agent-id>`, which records it for this user in
catalyst's home — never in `catalyst.toml`. A legacy deployment (`.criterion`
symlink into another agent's space) is moved once with
`catalyst move --to-home`.

---

## 2. Install procedure

Run this only on the user's explicit request (law L8). The mechanical
part is one command, `catalyst init` (`framework/kernel/CLI.md`); the agent
keeps the judgment. Read first, from this repository: `framework/kernel/INVARIANTS.md`
(in full), `framework/kernel/README.md`, `framework/kernel/INSTANTIATION-GUIDE.md`
and `framework/kernel/INSTANTIATION-CHECKLIST.md` (the tickable version you
work against). Then:

1. **Ledger.** Create the deployment ledger from the checklist (§3), every
   item `[ ] pending`. `catalyst init` moves a project `.criterion` that
   holds only that `.ledger/` into the criterion.
2. **Resolve the inputs** — judgment, asked of the user when not evident:
   - the project name: from a project-local `dev-instructions.yaml`'s `name`
     if present (deleted after a successful install), else ask, defaulting
     to the repository name;
   - the active module: no default; `catalyst init` without `--module`
     lists the ones it finds — propose one and ask;
   - the rule document(s) and a short lowercase prefix for each, one per
     natural seam of the project (`INSTANTIATION-GUIDE.md` §1);
   - the first user's git username (the name defaults to `git config
     user.name`), who becomes Admin;
3. **Run `catalyst init`** from the project root with those inputs
   (`--name`, `--module`, `--git-username`, `--rule-doc <file>:<prefix>`
   per document, `--agent <id>`). It builds the
   whole skeleton: composed governing documents, the seeded module, every
   entity folder with its index and templates catalog, frozen definitions,
   the first user with a userid, the journal, the vendored CLI, the
   criterion in `$HOME/.catalyst/projects/<name>/criterion` with its own
   runtime, and `catalyst.toml` — the only file it adds to the project.
   It also copies `INVARIANTS.md` into the working copy, for the
   server and session-start hook of step 4 to re-inject.
   It refuses if catalyst is already installed.
4. **Finish the judgment work** per `INSTANTIATION-GUIDE.md` §1: wire the
   agent once per machine, at user level, with `catalyst agent install
   <agent>` (the `catalyst mcp` server, whose prompts are the §4 commands,
   and the end-of-turn `catalyst hook stop`) — never writing command
   files, hooks or a `Taskfile.yml` into the project, then the path's first rules — **greenfield** (no code yet:
   stack, tooling, dev environment and CI decided as the first rules, §3) or
   **retrofit** (existing code: rules gathered incrementally, optionally
   bootstrapped with `/run-analysis --bootstrap`, §4) — and
   `catalyst check`.
5. Tick each ledger item as you complete it. If an item is blocked, mark it
   `[!] blocked: <reason>` and surface it — never silently skip.
6. Record the deployment target (§1 memory row).
7. **Do not commit or push.** Present the deployed tree and wait for explicit
   assent before any git write (law L3).

---

## 3. Stay grounded while you work (anti-drift)

A long install or analysis run will dilute these instructions out of your context
unless you re-anchor. Two mechanisms, both mandatory:

**Deployment ledger.** Copy `framework/kernel/templates/ledger.template.md`
to `.criterion/.ledger/<task>.todo.md` in the target repo (`init` moves it into the criterion). Read it before each
unit of work; after each unit, mark the item done/blocked and append any newly
discovered subtasks. This turns "remembering the steps" into a written, inspectable
record you can self-correct against.

**Re-ground cadence.** After every 5 completed ledger items, **or** immediately
after any context compaction/summarization, re-read
the laws (the top of `framework/kernel/INVARIANTS.md`; in a deployed
project, `catalyst hook start` prints them) and the active checklist before
continuing. The laws are deliberately short so this is cheap.

Before declaring any task done: re-read the checklist and confirm every item is
`[x]` in the ledger. Blocked items go to the user, not to silence.

---

## 4. Assent gate

Nothing in catalyst is pushed, and no target-repo commit is made, without the
user's explicit go-ahead. Present what you did, state exactly what you would
commit/push, and wait.
