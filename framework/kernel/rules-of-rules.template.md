# Rules of Rules — the handbook

> The kernel's handbook, composed into the criterion as
> `{{RULES_DIR}}/Rules-of-Rules.md` with the active module's part appended.

The rules a person or an agent must judge for themselves when they change
this project's rules or do work under them: {{RULE_DOCS_LIST}}. They sit
under the ten laws (`INVARIANTS.md`; `catalyst why L1`), never restate what
the CLI enforces, and link to formats rather than repeat them. Documents
named here that are not in the criterion — `FORMAT.md`, `CLI.md`,
`ARTIFACT-LAYOUT.md` and the like — are the kernel's, under
`framework/kernel/` in the `catalyst` repository.

Meta-rule IDs are written short in the kernel (`rr-META-012`); the
deployed copy carries them widened and signed with the installer's userid,
like every other rule ID (§20). A number that moved to the active module, or
was parked, keeps a one-line placeholder; numbers are never reused.

## Which document does a rule belong in?

Project-specific tiebreaker guidance goes here — e.g.:

- **{{RULE_DOC_1}}**: {{tiebreaker description}}.
- **{{RULE_DOC_2}}**: {{tiebreaker description}}.

Not a hard wall — a rule may have entries in two documents (one for how it
is surfaced, one for the constraint it enforces), cross-referencing each
other.

## 1. `rr-META-001` Check for conflicts before adding a new rule

Before adding or changing a rule, read every rule document for a rule it
would contradict, duplicate or weaken. On a conflict, stop and ask the user
which rule wins; never resolve it silently by editing either. A rule that
refines another names it as its parent (`[-parent-id]`, §3).

## 2. `rr-META-002` A new rule is never done until it's gathered, implemented, tested, and documented

**Gathered**: written in its rule document, with its domain and ID.
**Implemented**: the code does what it says, through a tracked artifact
(law L2). **Tested**: a test, or an explicit verification, shows it holds.
**Documented**: the project's user-facing documentation says so where it
applies. Until all four hold the rule is not done; its status markers
(`FORMAT.md` §5.2) say which part is missing.

## 3. `rr-META-003` Every rule has a unique, stable ID

A rule is a heading in a rule document under `{{RULES_DIR}}/` —
`<doc-prefix>-<DOMAIN>-NNNNNN[-parent-id]-<userid>` then its title — or its
own file, `<ID>-<slug>.md`, that a rule document lists; either way it is
listed in `{{RULES_DIR}}/rules.md` (`FORMAT.md` §5, INV-8). Keep one shape
per rule document. Take the number from
`catalyst id next-rule <doc-prefix> <DOMAIN> --as <signer>`, never by hand.
Add `[-parent-id]` only for a true sub-case of one existing rule. A rule
document's file may be renamed to a more descriptive name; an ID never
changes (L7).

## 4. `rr-META-004` Retiring a rule

Retire in place: mark the rule retired (`FORMAT.md` §5.2), say why and what
replaces it, and keep it — never delete a rule, never reuse its number.
Retiring a rule never closes the work that targeted it, and closing work
never retires a rule.

## 5. `rr-META-005` Rules use typed documents and one index

Every rule document lives under `{{RULES_DIR}}/`, every rule appears in
`rules.md`, and the rule template is the highest-numbered
`TEMPLATE-RULE-vN.md` in `{{RULES_DIR}}/templates/`. `catalyst check`
reports anything orphaned: fix the document, never the check.

## 6. `rr-META-006` Work has its own IDs, and a tier

Every artifact the active module defines gets
`<PREFIX>-NNNNNN-<userid>` from `catalyst new` (or `catalyst id next`),
never by hand, before work on it starts (L2). Each change is one of three
tiers: a **chore** changes no rule's behaviour and needs no artifact, only
its journal entry (`--tier chore`, no target); a **fix** restores a
documented rule's behaviour; a **feature** adds or changes behaviour. What a
fix and a feature need is the active module's (below). State the tier
before starting; escalate it (chore → fix → feature) as soon as the work
turns out bigger, opening what the new tier needs at that point — never the
other way round after the fact. When unsure, take the higher tier.

## 7. `rr-META-007` Defining a new domain

A domain groups rules; create one only when no existing domain fits. Check
it for conflicts as you would a rule (§1), register its code in
`{{RULES_DIR}}/domains/domains.md` — the registry `id next-rule` reads —
and write its domain file (`FORMAT.md` §5.4) stating its scope and how it
relates to its neighbours. A code is permanent. A sub-domain
(`<PARENT>.<SUB>`, one level deep) splits a domain that has grown several
distinct seams; its rules carry the full code (`cor-CORE.INGEST-000001-…`).

## 8. `rr-META-008` — parked

Agile work items, with the plugins (roadmap R4.7); never reused.

## 9. `rr-META-009` — owned by the active module

Never reused.

## 10. `rr-META-010` — owned by the active module

Never reused.

## 11. `rr-META-011` Users and roles are advisory, except reconciliation

Every signature names a registered user, declared (`--as`) and confirmed
with the user when more than one could sign — never guessed from git
configuration (L4). Roles describe who usually does what: a role mismatch
is noted and the work proceeds, since catalyst cannot verify who types —
except for reconciliation (§16). At least one user stays active; a user
who leaves is deactivated, never deleted (`catalyst user remove`).

## 12. `rr-META-012` The journal is transaction-log-grade, not a changelog

Every change to a governed file is journaled when it is made (L1): one entry
per change, its targets the rules it serves, its intent a goal — "reset
links expire after 30 minutes again" — never a label like "update". The CLI
writes the entries, the hashes, the pins and the order (`FORMAT.md` §7);
the judgment is yours: the tier, the targets, the intent. A change made
outside catalyst (`catalyst unrecorded`) is listed to the user, who decides
whether it is adopted (`/adopt`) or reverted — never one or the other on
your own. Every commit names the artifact or rule it serves, or is a
`chore:`; never bypass the commit hook without the user's say-so.

## 13. `rr-META-013` Shared deployments

A criterion is shared through `catalyst share` (git today; `catalyst.toml`
names the driver). Publishing — `share push`, `share create` — shows what
would leave and waits for the user's yes (L3). Work lands through a pull
request on the shared branch, whose CI runs `catalyst check`, including
that a merge lost nothing. A conflict stops the push with nothing pushed:
never apply a merge yourself; propose a resolution as a `RECON-` case
(§16) for a human to decide (L4). Identity is declared, not verified:
branch protection and review are the real controls (`ACCESS-CONTROL.md`).

## 14. `rr-META-014` Session start, agents and the criterion's place

Every session starts with `catalyst hook start`: where the project stands,
then the laws. `catalyst open` makes the project ready on a machine (it
joins a shared criterion and fills its runtime); `catalyst open --agent
<id>` records this user's agent. The criterion lives in catalyst's home,
never in the project (L5): nothing writes files into the project for
catalyst but `catalyst.toml`. A legacy deployment is moved once with
`catalyst move --to-home`.

## 15. `rr-META-015` Every artifact type has the same directory shape

Each type has its folder, its index and a versioned `templates/` catalog
(`ARTIFACT-LAYOUT.md`, INV-20). A new artifact starts from its type's
latest template (`catalyst new`). A template is never edited once a newer
version exists — add a version. Never hand-edit an index or another
generated file (L6): regenerate it (`catalyst index regen`).

## 16. `rr-META-016` Reconciliation of diverging entity versions

When two versions of an entity disagree — a conflict that stopped a push,
a change outside someone's role, a contested change made outside catalyst —
open a `RECON-` case naming the entity, both versions and why they differ.
The agent may propose; only a human decides, with `catalyst reconcile <id>
accept|accept-with-edits|reject|propose|close`, which enforces the
signer's `reconciliation` level from `IAM/roles/roles.json`: `full`
decides, `propose` only proposes, `none` neither. Each round is a new row
in the case's `## Revisions`; applying an accepted version to the entity is
ordinary, journaled work; a closed case is final (`definitions/
reconciliation`).

## 17. `rr-META-017` — parked

Content-contributing plugins, with the plugins (roadmap R4.7); never
reused.

## 18. `rr-META-018` — catalyst development only

The recreation drift check of catalyst's own rules (`/dogfood recreate`)
lives in the `catalyst` repository, not in deployments; never reused.

## 19. `rr-META-019` Workflows guide; they are never work

A `WORKFLOW-` documents a recurring procedure. When an artifact or a case
names one, read it before acting. A workflow has no target and is never
itself done (`definitions/workflow`).

## 20. `rr-META-020` Entity IDs carry their signer's userid

Every ID ends with the userid of the user who created it, assigned once and
never changed (L7). Register a user (`catalyst user add`) before they sign
anything. The kernel's meta-rule IDs are short in the kernel's copy and
widened and signed with the installer's userid when the deployment is
composed.

## 21. `rr-META-021` — owned by the active module

Never reused.

## 22. `rr-META-022` — owned by the active module

Never reused.

## 23. `rr-META-023` Artifact updates happen atomically, as work happens

An artifact's status, its records of the work and the journal follow the
work as it happens, in the smallest unit practical — never reconstructed in
one batch afterwards (L1). Batching is allowed only when it is announced
before the work starts.
