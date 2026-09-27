# Slash-command file template

> Copy this file to `.claude/commands/{{command-name}}.md` in the target
> project, once per command listed in the deployed `CODE-OF-CONDUCT.md` §4
> (kernel and active-module entries alike), and resolve every
> `{{PLACEHOLDER}}`. See `INSTANTIATION-GUIDE.md` §1 step 5 and `CLAUDE.md`'s "Slash commands" entry — this template exists
> because that entry requires it, not as an optional convenience.

This file becomes the literal prompt Claude Code runs when the user types
`/{{command-name}}`. Keep it a **thin, procedural pointer back to
`CODE-OF-CONDUCT.md` §4** — the canonical behavior spec — rather than
duplicating that spec's prose here. That's what keeps the command correct
across a `/sync-framework` without needing its own edit: if the framework
changes what `/meta-tag` does, the deployed `CODE-OF-CONDUCT.md` gets
synced and this file's instructions ("follow §4") are still accurate
unchanged.

Only use the frontmatter fields below — `description` and
`argument-hint` are long-established and safe. Don't add fancier fields
(`allowed-tools`, named argument lists, etc.) without first confirming
the running Claude Code version actually parses them the way you expect;
an unrecognized field in a command file has in practice caused the whole
command to fail to load, which defeats the point.

```
---
description: {{one-line, matching this command's bullet in CODE-OF-CONDUCT.md §4}}
argument-hint: {{expected arguments, e.g. "<short description> [--flag value]"}}
---

{{One-line restating the command's purpose.}} Full spec:
`.criterion/CODE-OF-CONDUCT.md` §4{{, template: .criterion/<dir>/TEMPLATE-<TYPE>.md — only if this command creates an artifact}}.
Input: $ARGUMENTS

1. {{If this command creates a numbered artifact: resolve the signer
   (CODE-OF-CONDUCT.md §2), then allocate the ID with
   `catalyst id next <PREFIX> --as <signer>` — never guess, compute by
   hand, or reuse a number.}}
2. {{Name any field this artifact type can never leave empty (e.g. a
   rule-linked artifact's Targets, per CODE-OF-CONDUCT.md §1) and what to
   do if the user's input doesn't supply it — ask, don't invent a value.}}
3. {{Copy the relevant TEMPLATE-*.md, fill every field, and use a
   descriptive `<id>-<short-summary>.md` filename — never a bare ID
   (rr-META-003 / INV-7).}}
4. {{Register it with `catalyst index regen`, then journal it with
   `catalyst journal append --command /{{command-name}} --action <action>
   --artifact <id> [--target <rule-id> ...] --intent "<goal>" --file <each touched file>`
   (CODE-OF-CONDUCT.md §4's common ending).}}
5. Report the result. Do not commit or push — leave changes unstaged
   unless the user asks otherwise (`Rules-of-Rules.md` INV-4).

`catalyst <args>` is `python3 .criterion/bin/catalyst.pyz <args>`
(`CODE-OF-CONDUCT.md` §4).
```

Adapt the numbered steps to what the command actually does — don't force
every command through this artifact-creation shape:

- **Query/inspect commands** (`/list`, `/audit`, `/check-rules`,
  `/help`, and any the active module contributes) don't create anything — steps 1–4 become
  "resolve what's being asked for, read the relevant index/rule files,
  report findings" instead (`/check-rules` starts from `catalyst check`).
- **`/sync-framework` and `/run-analysis`** additionally need this
  framework's own repository content (`SYNCHRONIZE.md`,
  `ANALYSIS-PLAYBOOK.md`) that isn't part of the deployed project — fetch
  it if not already available this session, and refer to it only by
  repository name, never a local path (INV-1).
- **`/catalyzer`** resolves plugins against `framework/kernel/plugins/<type>/catalog.md`
  **in this framework's own repository**, not the deployed project — say
  so explicitly in that command's file so it isn't confused with the
  deployed-project-relative paths every other command uses.

## Related docs

- [`../rules-of-development.template.md`](../rules-of-development.template.md) §4 — the canonical command list and per-command behavior spec.
- [`../../../CLAUDE.md`](../../../CLAUDE.md) — the "Slash commands" entry this template exists to satisfy.
- [`../SYNCHRONIZE.md`](../SYNCHRONIZE.md) §6 — what happens to these files on `/sync-framework`.
