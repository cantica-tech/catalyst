# `rule` — entity definition (v1)

| Field | Value |
|---|---|
| **Entity type** | `rule` |
| **Version** | 1 |

## Description

A rule is the unit implementation is measured against: one concrete, testable
statement of expected behavior, filed under its rule-type directory within
`rules/` and assigned to exactly one domain. Every grounded artifact of the
active module must trace to at least one rule (the chain invariant) — nothing
ships without a documented rule backing it. Rules whose id starts `rr-` are
self-governing process rules about how rules themselves are authored, not
product rules.
