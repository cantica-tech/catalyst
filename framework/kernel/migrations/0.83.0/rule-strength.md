# 0.83.0 — Rule strength

From `0.82.x` to `0.83.0` (owner decision S).

## What changes

- A rule states its strength on a `**Strength**` line of its text: `must`, `should` or `may` (`FORMAT.md` §5.2). A
  rule that states none is `must`, so every existing rule keeps the strength it had.
- `catalyst check` reports a strength other than the three as `rule-strength` (an error).
- `catalyst view`, `list rule` and `graph` give each rule its `strength`.
- A breach is reported by the rule's strength: a `must` breach is a violation, a `should` breach a warning, a `may`
  breach a note (`/check-rules`, `ANALYSIS-PLAYBOOK.md` step 5).
- The rule template gains the `**Strength**` line.

## Steps

1. `catalyst sync apply --kernel <0.83.0>`: the CLI, the runtime and the recomposed documents (`Rules-of-Rules.md` §5
   says what a strength is).
2. **Judgment:** if the deployment keeps `rules/templates/`, add the kernel's `templates/rule.template.md` as its next
   version (`TEMPLATE-RULE-v<N+1>.md`) with a row in its templates catalog, journaled; never edit an earlier version
   (L6).
3. `catalyst check`. No rule is rewritten: one that should be weaker than `must` gets its line when its owner decides,
   as a journaled change to the rule.
