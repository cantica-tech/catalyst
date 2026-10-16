# Catalyst Bootstrap

The single entry point for installing **catalyst**: the per-agent files
(`CLAUDE.md`, `AGENT.md`, `SYSTEM.md`) are thin shims that point here. Follow
it top to bottom. It adapts to the running agent, but only **Claude Code** is
tested today; the `catalyst` CLI works from any shell.

---

## 0. The laws (read first, re-read on every re-ground)

Read the ten laws: the top of `framework/kernel/INVARIANTS.md`, up to its
`end of the session brief` marker (in a deployed project, the session start
shows them, with the active module's own law). They are the only rules you
judge for yourself; everything else is enforced by the CLI or explained by
`catalyst why <L1…L10|INV-n|rule>`. If a step below conflicts with a law, the
law wins; if a law conflicts with the user, stop and ask.

---

## 1. Detect your capabilities (silently, then adapt)

Record each choice in the deployment ledger (§3), and tell the user the mode
in one line (e.g. "no sub-agents: analysis passes run one after the other").

| Capability | If present | If absent |
|---|---|---|
| **Parallel sub-agents** | Use them for the four-eyes analysis passes and audits. | Run each pass as a separate turn; no pass sees another's output before reconciliation. |
| **Persistent memory** | Keep a short deployment note (`INSTANTIATION-GUIDE.md` §6). | Nothing lost: `catalyst where` and `catalyst open` read the record each session. |
| **Slash commands** (the deployment's `CODE-OF-CONDUCT.md` §4, listed by `catalyst spec`; never copied elsewhere) | Served by `catalyst mcp` as prompts. | Recognise each `/name` typed in plain text; `catalyst spec <name>` gives its procedure. |
| **Repo file read/write** | — | Required: without it catalyst cannot be installed. |

`/dogfood` exists only in catalyst's own repository (`Rules-of-Rules.md` §13),
never in a deployment.

### 1.1 Switching agents

The criterion's place does not depend on the agent (law L5): a new agent runs
`catalyst open --agent <agent-id>`, recorded for this user in catalyst's home,
never in `catalyst.toml`. A legacy `.criterion` symlink is moved once with
`catalyst move --to-home`.

---

## 2. Install procedure

Only on the user's explicit request (law L8). `catalyst init` does the
mechanical part; the agent keeps the judgment. Read
`framework/kernel/INSTANTIATION-GUIDE.md` and work its tickable form,
`framework/kernel/INSTANTIATION-CHECKLIST.md`, against a deployment ledger
(§3).

1. **Ledger.** Seed it from the checklist, every item `[ ] pending`
   (`catalyst init` moves a project `.criterion` holding only `.ledger/` into
   the criterion).
2. **Work the checklist**: the inputs, asked of the user when not evident;
   `catalyst init`; `catalyst agent install <agent>` once per machine; the
   path's first rules; `catalyst check`. Tick each item when done; a blocked
   one is `[!] blocked: <reason>` and surfaced, never skipped.
3. **Do not commit or push** (§4).

---

## 3. Stay grounded while you work (anti-drift)

Two mechanisms, both mandatory on a long install or analysis:

- **Deployment ledger.** Copy `framework/kernel/templates/ledger.template.md`
  to `.criterion/.ledger/<task>.todo.md` in the target repository. Read it
  before each unit of work; after it, mark the item done or blocked and add
  any subtask found.
- **Re-ground.** After every 5 ledger items, and right after any context
  compaction, re-read the laws (§0; `catalyst hook start` prints them in a
  deployed project) and the checklist.

Nothing is done until every item is `[x]`; blocked items go to the user.

---

## 4. Assent gate

Law L3: present what you did and exactly what you would commit or push, then
wait for the user's yes.
