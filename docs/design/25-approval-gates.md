# 25 — Approval gates, opt-in (design for the owner, 2026-10-17)

> **Status: decided (owner, 2026-10-17), all five choices as recommended (§6).** Owner decision G (2026-10-16,
> [decisions](../decisions.md)): approval gates are a 1.0 feature, opt-in — no gate unless a deployment declares one.

## 1. Today

One person signs each artifact (`Signed-off-by`, a registered user, checked by `check`). Roles are advisory
(`Rules-of-Rules.md` §11): a role mismatch is noted, the work proceeds — except reconciliation, where only a role
with full rights decides a case. Nothing requires two people, or a given role, before a change takes effect.

## 2. Declaring a gate

A gate lives in the deployment's IAM, beside users and roles: `IAM/gates.json`. No file, no gate.

```json
{
  "gates": [
    {
      "id": "security-rules",
      "covers": { "rules": { "domain": "SECURITY" } },
      "approvals": 2,
      "role": "Tech Lead / Architect"
    },
    {
      "id": "req-activation",
      "covers": { "type": "REQ", "to": "Active" },
      "approvals": 1,
      "role": "Product Owner"
    }
  ]
}
```

A gate covers either the rules of one domain (their text) or an entity type entering one state. Its `role` is one
of `IAM/roles/roles.json`. The file changes like any governed file — journaled — so adding or removing a gate is
itself on the record; `/role` and `/user` gain nothing.

## 3. Recording an approval

`catalyst approve <ID> --gate <gate> [--as <user>] [--intent …]` journals one entry (action `approve`) naming the
entity, the gate and the content it approves: the entity file's blob, the same hash the journal already keeps.
An approval is of **a version**: once the text changes, earlier approvals no longer count for it.

An approval counts when its signer is an active user holding the gate's role, is not the person whose change it
approves (the actor of the entry that wrote that version: four eyes, law L4), and has not already approved that
version.

## 4. Enforcing it

| Where | What happens |
|---|---|
| `catalyst status set` into a gated state | Refused until the gate's approvals for the entity's current version are recorded; the refusal names how many are missing and from which role |
| A gated rule's text | Rules are edited in their documents, so the edit itself is not stopped: `check` reports an error while the current text of a gated rule lacks its approvals, and the end-of-turn hook stops on it like any other error |
| `--force` | Does not pass a gate: a gate that must be passed is removed in `IAM/gates.json`, a journaled change everyone can see |
| `catalyst inbox` | A new kind, `approval`: each gated change waiting, with the gate, the approvals recorded and missing, and `catalyst approve` as the verb that settles it |

`serve` gives the same through `inbox` and `check`; a UI's host may run `approve` for the person who confirms it.

## 5. What it is not

Not a workflow engine: one gate, one count, one role; no sequence of reviewers, no expiry, no delegation. Not a
substitute for review where the work is done (pull requests): it records, inside the criterion, that the people the
deployment named approved this version.

## 6. Choices to confirm

1. **Where gates are declared**: `IAM/gates.json` (recommended: beside users and roles, opt-in by its absence), or a
   section of `Rules-of-Rules.md`.
2. **An approval is of a version** (recommended), or of the entity whatever its later text.
3. **The author does not count** among the approvers of their own change (recommended, law L4).
4. **`--force` does not pass a gate** (recommended); removing the gate is the visible way out.
5. **What a gate covers at 1.0**: a rule domain, or an entity type entering a state (recommended: only these two).

## 7. Steps once confirmed

| Step | Content |
|---|---|
| A1 | `IAM/gates.json` read and checked (`check`: an unknown role, type or state is an error); its schema |
| A2 | `catalyst approve`; approvals read back from the journal per entity and version |
| A3 | `status set` refuses into a gated state; `check` errors on a gated rule's unapproved text |
| A4 | `inbox` kind `approval`; `serve` and the schemas; `CLI.md`, `Rules-of-Rules.md` §11 (roles advisory except reconciliation and gates) |

About 3–4 sessions, one kernel release per two steps.
