# ADR-020: Fewer slash commands, the old names kept as aliases (R2)

**Date:** 2026-10-15  
**Status:** Accepted  
**Author:** Olivier Steck (owner: "go with the recommendations", 2026-10-15)  
**Affected scope:** kernel, SE module

## Context

Roadmap R2 aims at about 16 slash commands; a deployment had 34 (23 from the kernel, 11 from the software-engineering
module). Most of the surplus is one command per verb of the same thing: five `/user-*` commands, two `/role-*`, four
`/roadmap-*`. Each command is a prompt every agent session lists and a bullet every agent may read. The feature
register's command rows (R1.3, CMD-01 to CMD-38) propose the merges this records. The prose freeze (R1.6, ADR-017)
lists the commands, so changing them needs this record.

## Decision

Commands that act on one thing become one command whose first word is the verb, and the old names stay as aliases:
`catalyst spec <old>` and the catalogue's procedures still resolve them, and an agent asked for `/user-add` finds
`/user`. In the kernel:

| Command | Absorbs |
|---|---|
| `/user add\|remove\|modify\|assign-role\|list` | `/user-add`, `/user-remove`, `/user-modify`, `/user-assign-role`, `/user-list` |
| `/role add\|modify` | `/role-add`, `/role-modify` |
| `/check-rules [<file>]` | `/audit` |
| `/help [<command>]` | `/commands` |
| `/journal … \| restore <timestamp>` | `/journal-restore` |

The kernel goes from 23 commands to 15, and its command specs from 8,494 tokens to 6,958, though a merged command's own
spec is longer. The software-engineering module's four `/roadmap-*` commands become `/roadmap` in its next release.

An alias needs no Taskfile task: the parity check counts the command a bullet defines, the first name before its "—".

## Consequences

- **Positive:** fewer prompts per session; one place per subject; nothing anyone types stops working.
- **Negative:** `catalyst task user-add` and the other removed task names are gone (`catalyst task user -- add …`);
  an agent's prompt list (`/catalyst:user-add`) changes.
- **Trade-offs:** `/meta-tag` stays for now: decision B4 drops it, but its entity type has to be retired with it.

## Alternatives Considered

1. **One `/create <type>` for every create command:** the larger cut (to about 16), but each type's command carries its
   own judgment; left for when generated commands carry that judgment.
2. **Remove the old names outright:** a clean list, but breaks every habit and script; aliases cost one line each.

## Related

- ADR-017 (prose freeze), ADR-018 (the command catalogue)
- `docs/feature-register.md`, rows CMD-01 to CMD-38
