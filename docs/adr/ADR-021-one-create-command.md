# ADR-021: One `/create <type>`, a command with parts; meta-tags dropped (R2)

**Date:** 2026-10-15  
**Status:** Accepted; as recorded in catalyst's criterion, `ADR-000045-yCNjAMXO`  
**Author:** Olivier Steck (owner: "let's finish R2", 2026-10-15; decision B4, 2026-10-08)  
**Affected scope:** kernel, SE module

## Context

After ADR-020 a deployment had 23 commands; R2 aims at about 16. Seven of them were create commands, one per
artifact type: five written by the software-engineering module, one generated from its `module.yaml`, and the
kernel's `/meta-tag`. ADR-020 left one `/create <type>` for later because each type's command carries its own
judgment (which fields to prompt for, which rule to target), and one command reading every type's procedure would
cost more per call than the seven did. Decision B4 (2026-10-08) drops meta-tags: no deployment uses them.

## Decision

1. **A command may have parts.** In §4, a bullet whose head is `/<command> <part>` and names an alias
   `/<command>-<part>` is a part of `<command>`. `catalyst spec <command> <part>`, `catalyst spec <command>-<part>`
   and the MCP prompt `/<command> <part> …` read the command's shared text and that part's bullet and procedure
   only; `catalyst spec <command>` reads every part's bullet and no part's procedure. `spec --budget` checks each
   part.
2. **`/create <type> <title>`** is a kernel command with no part of its own. Each module adds one part per type
   (`/create bug <title>` (`/create-bug`)), hand-written or generated from `module.yaml`. One `create` task replaces
   the per-type tasks, so a module ships no create task.
3. **Meta-tags are dropped (B4).** No `/meta-tag`, no `META-TAG` type, definition or template. `catalyst sync apply`
   removes a deployment's `development/meta-tags/` and `definitions/meta-tag.md` when the folder holds no tag, and
   keeps them when it holds some (L7).

A deployment with the software-engineering module goes from 23 commands to 17. The old names stay aliases.

## Consequences

- **Positive:** one create command for every type of every module; the prompt list shrinks; a part costs what the
  old command cost (the largest, `create feature`, about 536 tokens).
- **Negative:** `catalyst task create-bug` is gone (`catalyst task create -- bug "<title>"`); the §4 parser now has a
  notion of parts, which a module author must follow to keep a part's text out of the others'.
- **Trade-offs:** the `tags:` field B4 names as the replacement is not built: it is new behaviour, left for when a
  deployment asks for it.

## Alternatives Considered

1. **One `/create` reading every type's procedure:** simplest, but over 2,500 tokens per call.
2. **Keep the seven commands:** no parser change, but R2's target missed by seven.

## Related

- ADR-020 (aliases), ADR-017 (prose freeze); decision B4 in `10-questions-and-decisions`
