# Rules of Rules — template

> Copy this file to `{{RULES_DIR}}/Rules-of-Rules.md` in the target
> project and resolve every `{{PLACEHOLDER}}`. Delete this notice once
> instantiated. See [`INSTANTIATION-GUIDE.md`](INSTANTIATION-GUIDE.md).

Meta-rules governing how any rule gets added to, changed in, or retired
from one of this project's rule documents: {{RULE_DOCS_LIST}}. These
apply to the *process* of maintaining those documents and the code they
describe, not to the app's behavior itself. Binding on anyone (human or
agent) adding to any of them, at any point after this file exists.

Each rule must belong to a rule type directory under `{{RULES_DIR}}/`, be
stored as its own markdown file in that directory, be listed in the
corresponding type index, and be referenced from the global index
`{{RULES_DIR}}/rules.md`. There must be exactly one template file at
`{{RULES_DIR}}/TEMPLATE-RULE.md` and no `TEMPLATE-RULE.md` files inside the
rule-type directories. No rule may be orphaned by missing a type, a local
index entry, or a global index entry.

---

## 1. `rr-META-001` Check for conflicts before adding a new rule

Before a new rule is implemented, check it against the rules already
recorded in **every** rule document in {{RULE_DOCS_LIST}} — not just the
document that seems most relevant, since the same underlying behavior is
sometimes governed from more than one angle (e.g. a UI-visible
enabled/disabled state and the backend constraint it's supposed to
reflect), and a change to one side can silently break the other. Check,
in order:

1. The same functionality area in whichever document(s) are relevant.
2. Each document's Cross-Cutting Notes heading (or equivalent).
3. Each document's `## Linked Artifacts — Quick Index` heading — a "new" rule is
   sometimes actually a conflicting rewrite of an existing one.

If the new rule **contradicts, narrows, silently overrides, or would
break** an existing ✅ rule in any document, **stop and prompt for a
decision** — do not silently override it, and do not silently implement
both side by side and let whichever runs last win.

## 2. `rr-META-002` A new rule is never done until it's gathered, implemented, tested, and documented

All four, no exceptions:

- **Gathered** — the rule's actual current/intended behavior is
  understood and written down before code changes.
- **Implemented** — the rule actually exists in the code, not just in a
  comment, commit message, or this documentation.
- **Tested** — it has **at least one test** exercising it. Name the
  project's test locations here: {{TEST_LOCATIONS}}. A rule with zero
  test coverage is not "done" — it's "implemented but untested," and
  should be marked as such (see status markers below), not treated as an
  acceptable end state.
- **Documented** — added to the correct rule document, under the
  functionality domain it belongs to and the right rule category, with a
  `file:line` citation and a status marker, in the same format every
  existing entry already uses.

**Status markers**: ✅ working · ⚠️ buggy/incomplete · ❌ not implemented
/ regressed · 🗑 retired (see §4).

## Which document does a rule belong in?

Project-specific tiebreaker guidance goes here — e.g.:

- **{{RULE_DOC_1}}**: {{tiebreaker description}}.
- **{{RULE_DOC_2}}**: {{tiebreaker description}}.

Not a hard wall — some rules legitimately have entries in more than one
document (one for how it's surfaced, one for the constraint it enforces)
and should cross-reference rather than pick just one.

## 3. `rr-META-003` Every rule has a unique, stable ID

Format: **`(DOC_PREFIX)-(DOMAIN)-(NNNNNN)[-(parent-id)]-(userid)`**

- **`DOC_PREFIX`** — which rule document the rule lives in. Define one
  short lowercase prefix per document in {{RULE_DOCS_LIST}} (e.g. `ui`,
  `br`), plus the fixed `rr` prefix reserved for this file itself.
- **Name format** — every rule name and development entity must carry a name summarizing its purpose. The canonical rule name format is **`<rule-id>-<short-summary>`**, where the suffix is a lowercase slug that briefly describes what the rule is about. Example: `br-AUTH-000003-login-flow`. Similarly, every development entity (rules, domains, reconciliations, workflows, the active module's entity types, etc.) contains an explicit **Name** field (`**Name**` in field tables or rule metadata) that summarizes the purpose of the entity. This is a hard requirement for all new rules and development entities and must also be applied retroactively to existing deployed items during framework deployment or synchronization. Existing names that are only the ID must be renamed to include a summary suffix, and every index entry and link that references the old name must be updated.
- **`DOMAIN`** — a short, stable mnemonic code for the `##` functional
domain the rule sits under. Fixed once assigned — renaming a domain's
prose heading does not change its code, since existing IDs (in code
comments, tests, linked-artifact indexes, cross-references) must keep
resolving.
- **`NNNNNN`** — a zero-padded **6-digit** sequence number, unique within
  that `DOMAIN`, assigned in document order the first time IDs are
  retrofitted (or in creation order thereafter). Never reused, never
  renumbered, even if an earlier rule in the same domain is later
  deleted/retired. Zero-padding is always applied before the `userid`
  suffix (rr-META-020) is appended — never after, and never left
  half-done across a document (a mix of 3-digit and padded 6-digit IDs
  breaks lexicographic sort).
- **`[-parent-id]`** — optional. Used two ways: (a) a rule that is a
  specialization/consequence of another rule references that rule's full
  ID (including its own `userid` suffix) as its own suffix; (b) a
  numbered sub-item inside a single rule bullet that enumerates several
  concretely distinct behaviors gets the parent's ID plus its own
  position (e.g. `br-EVTO-000015-1`, before that rule's own `userid` is
  appended). Prefer this over inventing a new top-level rule when the
  sub-items are only meaningful in the context of the parent bullet.
- **`(userid)`** — always the final segment, after any `[-parent-id]`.
  See rr-META-020 for the full mechanism and the rule/domain
  authorship limitation.

Rules with no sub-items or parent never have that trailing segment —
it's absent, not empty. The `userid` segment, by contrast, is never
absent once rr-META-020 applies.

### Domain codes — {{RULE_DOC_1}}

| Code | Domain |
|------|--------|
| `{{CODE}}` | {{Domain name}} |

### Domain codes — {{RULE_DOC_2}}

| Code | Domain |
|------|--------|
| `{{CODE}}` | {{Domain name}} |

### Domain code — this file

| Code | Domain |
|------|--------|
| `META` | This file's own numbered rules (`rr-META-NNN`) |

### Adding a new rule

1. Pick (or confirm) the `DOMAIN` it belongs to.
2. Take the next unused `NNN` in that domain — check both the domain's
   existing bullets and the Linked Artifacts quick index.
3. Only add `[-parent-id]` if the rule is a numbered sub-case of one
   existing bullet, or an explicit specialization of another rule.

## 4. `rr-META-004` Retiring a rule

A rule ID, once assigned, is **never deleted and never reused** —
deleting the bullet outright breaks every cross-reference to it with no
trace of why. Instead, retire it in place:

1. Change its status marker to **🗑 retired**.
2. Leave the rule's text as-is (don't rewrite it to match new behavior —
   that's a *new* rule with a *new* ID) and append a one-line reason plus
the date, e.g. `🗑 retired {{DATE}} — superseded by \`{{new-id}}\``.
3. If something replaces it, the replacement is a normal new rule (next
   `NNN` in its domain) — retirement does not imply the new rule
   inherits the old number, even via `[-parent-id]`.
4. Never repurpose a retired rule's ID for an unrelated rule later, even
   in the same domain.
5. A retired rule can still be a valid target for dev-artifact work (e.g.
   an artifact explaining why it had to be retired) — retirement is a status
   change, not removal from the graph of things development work can
   cite.

## 5. `rr-META-005` Rules use typed directories and indexes

Every rule must live in a type-specific directory under `{{RULES_DIR}}/`, for
example `business/`, `ui/`, or `infra/`. This is a hard requirement. Each
rule must be stored as its own markdown file in that directory, and that file
must be listed in the corresponding local type index and the global
`{{RULES_DIR}}/rules.md` index. A rule that is not present in its type index
or the global index is considered invalid until it is added to both. The
only rule-template file is the current
`{{RULES_DIR}}/templates/TEMPLATE-RULE-vN.md` (§15 — versioned, catalogued,
nested under `templates/`, never at the rules root directly); concrete
rule files belong under the type folders, not under `templates/` or the
rules root. Aggregating multiple rules into one file or relying on
unindexed notes is not permitted.

## 6. `rr-META-006` Development artifacts have their own ID scheme

If the deployed framework is missing `version.txt`, or if its version is
lower than this framework's own `version.txt`, the
deployed framework must be synchronized before further work proceeds. See
[`SYNCHRONIZE.md`](SYNCHRONIZE.md).

Format: **`<PREFIX>-(NNNNNN)`** — one `<PREFIX>` per development-artifact
entity type of the active module (its `module.yaml` `entity_types`); see
[`rules-of-development.template.md`](rules-of-development.template.md).
`NNNNNN` is a zero-padded 6-digit sequence number, global within its own
type, assigned in creation order, never reused. Every rule-linked member
carries its own `Targets`/`Domain` and is subject to
`rules-of-development.md` §1 ("no development without a targeted
rule"). Which prefixes belong to this format, and any separate,
non-rule-linked schemes the module also defines, are the active
module's meta-rules (`MODULE-SPECIFICATION.md` §6.1).

## 7. `rr-META-007` Defining a new `##` domain

A development artifact of the active module is not required to fit an
existing domain — it may propose a new one, but only by following this standard, in every rule
document.

**Domains are defined in their own directory, not inline in the rule
document.** `{{RULES_DIR}}/domains/` is nested under the rules directory
(not a top-level sibling — domains exist to group rules, so they live
where rules live) and follows the same uniform shape as every other
artifact type (§15): its own `templates/`, `README.md`, `domains.md`
catalog, and free-form space for the actual domain files. Each domain
gets one file at
`{{RULES_DIR}}/domains/{{DOC_PREFIX}}-{{CODE}}-{{short-description}}.md` (e.g.
`domains/br-REDIS-caching-layer.md`). This is a hard requirement, the same as
for artifact and work-item filenames (see `INSTANTIATION-GUIDE.md` §1): the
bare `{{DOC_PREFIX}}-{{CODE}}.md` is not a valid filename, the file must carry
a short description of what the domain covers as part of its name. The
`{{CODE}}` used inside rule IDs (`{{DOC_PREFIX}}-{{CODE}}-{{NNN}}`) is
unaffected by this — only the on-disk filename gains the description suffix.
See [`templates/domain.template.md`](templates/domain.template.md) → the
current `{{RULES_DIR}}/domains/templates/TEMPLATE-DOMAIN-vN.md`, for the
exact file structure (`Document`, `Defined`, `Parent`, `Sub-domains`,
`Scope`, `Relationship to other domains`).

### Sub-domains

A domain may be split into sub-domains when its scope is genuinely
large enough that "which part of GATE does this rule belong to" stops
being obvious from the flat list — not by default, and not just to make a
domain file shorter.

- **Code**: `{{PARENT}}.{{SUB}}` — parent code, a literal `.`, then a
  short sub-mnemonic (e.g. `GATE.DOCKER`). This is still one `DOMAIN`
  value for ID purposes: a rule under it is
  `{{DOC_PREFIX}}-{{PARENT}}.{{SUB}}-{{NNN}}` (e.g. `ui-GATE.DOCKER-004`),
  with `NNN` scoped to the sub-domain, not the parent.
- **File**: `domains/{{DOC_PREFIX}}-{{PARENT}}.{{SUB}}-{{short-description}}.md`,
  alongside (not nested under) the parent's own
  `domains/{{DOC_PREFIX}}-{{PARENT}}-{{short-description}}.md` — the
  directory itself stays flat; the nesting is expressed by the code and by
  the `Parent`/`Sub-domains` fields cross-linking the two files.
- **Parent file** lists every child in its `Sub-domains` field. **Child
  file** names its `Parent` and inherits the parent's Scope/Relationship
  statements unless it explicitly narrows or overrides them.
- A sub-domain is subject to every other rule in this domain (conflict
  check, permanence, retirement) exactly like a top-level domain — it is
  not a lesser or informal category, just a narrower one.
- Sub-domains do not nest further than one level. If a sub-domain needs
  its own sub-domains, that's a sign the parent domain should be split
  into multiple top-level domains instead.

The `##` heading in the rule document itself carries only a one-line
pointer back to this file, not the full metadata:

```
## {{Domain name}}

> **Domain:** `CODE` — see [`domains/{{DOC_PREFIX}}-{{CODE}}-{{short-description}}.md`](domains/{{DOC_PREFIX}}-{{CODE}}-{{short-description}}.md).
```

This keeps the rule document itself readable (just rules) while the
domain's scope/conflict metadata lives in one findable, greppable place
per domain — `{{RULES_DIR}}/domains/` is the authoritative index of
every domain that exists across every rule document, independent of
which document's prose you happen to be reading.

### Creating a new domain

1. **Conflict check first**, at the domain level: does an existing
domain already cover this scope, even partially, under a different
name? Check `{{RULES_DIR}}/domains/` directly — it's the complete
list. Extend the existing domain instead of duplicating it.
2. **Pick a code** — uppercase mnemonic, 3–7 characters, not already used
   as a `DOMAIN` code in the same document.
3. **Add the code to the canonical table** in this file, and create its
   `domains/{{DOC_PREFIX}}-{{CODE}}-{{short-description}}.md` file, in the
   same change that adds the domain.
4. **Write the domain file's Scope and Relationship-to-other-domains**,
declaring either no conflict or the specific supersede/amend/
contradict relationship to named existing rule IDs.
5. Add the one-line pointer under the `##` heading in the rule document.
6. Only then add the domain's first rule bullet(s), `NNN` starting at
   `001`.

A domain's code is permanent, same as a rule ID — never reused for an
unrelated domain even if the original is later emptied out or retired
(its `domains/` file gets the same 🗑 retired treatment as a rule, §4).

## 8. `rr-META-008` Scrum/agile work items are plugin-territory, not core

The kernel version is tracked in `version.txt` at the catalyst repository root.
If a deployed framework has no `version.txt`, or its version is lower than
this framework's own `version.txt`, it is considered
out of date and must be synchronized using [`SYNCHRONIZE.md`](SYNCHRONIZE.md).

**`work-items/` is not part of the core deployed layout.** Unlike
`rules/`/`reconciliations/`/`workflows/`/`IAM/` or the active module's
own artifact-type folders, no
deployment gets it by default. It only exists once a
project-management-type plugin extending the agile schema at
`plugins/_prototyping/project-management/agile/` (framework repository)
is activated (INV-13, INV-22) — that schema defines
`(EPIC|STORY|TASK|SPIKE)-(NNNNNN)`, `SPRINT-(NNN)`, and the one further
optional type below, but defines them as *what a plugin deploys*, not
as content core instantiation writes. See `INVARIANTS.md` INV-22 for the
activation mechanism (§17 below defines it here) and INV-5 for the
chain invariant's plugin-conditional wording. No concrete plugin extends
this schema yet — it exists so the shape is ready to build against.
(`WORKFLOW-(NNNNNN)` used to be part of this schema too; it's core now
— see §19.)

The schema's one further, optional type:

- **`BOARD-(NNNNNN)`** — the Kanban-flavor structural counterpart to
  `SPRINT-NNN`: a trackable container with its own `Status`
  (`Active`/`Archived`) that `STORY-`/`TASK-` items reference instead of
  sprint membership. Relevant only under the Kanban/Scrumban flavor (§2
  of `INSTANTIATION-GUIDE.md`) — a pure-Scrum deployment has no need for
  it, the same way a pure-Kanban one has no need for `sprints/`.

**`TICKET-(NNNNNN)` is deliberately not a defined type even within the
schema.** A `work-items/tickets/` folder, if a plugin deploys one,
carries no prescribed semantics — its actual population and lifecycle
(e.g. syncing from an external tracker) is that plugin's own concern.

## 9. `rr-META-009` — owned by the active module

`rr-META-009` — owned by the active module (`MODULE-SPECIFICATION.md`
§6.1); never reused.

## 10. `rr-META-010` — owned by the active module

`rr-META-010` — owned by the active module (`MODULE-SPECIFICATION.md`
§6.1); never reused.

## 11. `rr-META-011` Users and roles are advisory, not access control

`IAM/users/users.json` (`templates/users.template.json`) is the registry
of people who can sign work — a JSON array of `{name, roles, registered,
active, notes, userid}` objects, kept as data rather than a hand-edited
document because it is managed exclusively by commands:
`/user-add`/`/user-remove`/`/user-modify`/`/user-assign-role`/`/user-list`
— see `rules-of-development.md` §4. `IAM/roles/roles.json`
(`templates/roles.template.json`) maps each role to the actions/commands
it typically performs — a JSON array of `{name, actions, reconciliation}`
objects (`reconciliation` is `full`/`propose`/`none` — see §16, the one
field in this file that's genuinely enforced rather than advisory), seeded
with a default agile-role mapping and then extended via `/role-add`
(new role) and `/role-modify` (change an existing role's actions).
`IAM/users/` and `IAM/roles/` each follow the same uniform shape as every
other artifact type (§15) — their own `templates/` and `README.md`.

**`userid` generation (`/user-add`, INV-26).** Draw 8 characters, each
independently and uniformly from the 62-character alphabet
`[A-Za-z0-9]`, using whatever cryptographically-secure random source
the running agent's environment provides (e.g. Python's
`secrets.choice`) — this is an agent-followed procedure, not a
specific library dependency, since catalyst itself has no fixed
runtime. Redraw if the result contains no uppercase letter (this
closes a real parsing ambiguity in host UIs that derive an id from a
filename: an 8-letter, all-lowercase summary word like `database` must
never be mistakable for a `userid` suffix — see rr-META-020). Check
the candidate against every existing `userid` already in `users.json`
(including any assigned earlier in the same batch operation); redraw
from scratch on any collision, never patch a colliding draw. Assign
once unique. A `userid`, once assigned, never changes — the same
"never retroactively changes" posture as `Signed-off-by` below.

**`IAM/users/users.json` must contain at least one entry with `"active":
true`.** This is a hard requirement, unlike registries that may
legitimately start empty: a project with zero active users has nobody to sign work, so
deployment is not complete until `/user-add` has registered at least one
person. `/user-remove` refuses if removing the last active user would
leave zero — this specific case isn't advisory, since it would break
this file's own hard existence requirement (INV-25's
fundamental-invariant exception to acting without asking).

Catalyst has no way to verify who is actually typing, so beyond that one
hard existence requirement, this scheme is **advisory**: before an
artifact-creating or status-changing command completes, the agent
resolves who is signing it, checks their role(s) against `roles.json`,
and — if the action isn't one their role covers, or they aren't
registered at all — proceeds anyway (INV-25), noting the mismatch rather
than pausing for confirmation or refusing outright. Every entity of the
active module's entity types, and every work item, carries a `Signed-off-by`
field recording the outcome (`rules-of-development.md` §2); at the same
moment, that resolved signer's `userid` is appended as the entity's own
id suffix (INV-26, rr-META-020) — never resolved separately or later.

`/user-remove` never deletes a user's entry, the same "never delete,
retire in place" principle as §4: it sets `active` to `false` so
every `Signed-off-by` reference already recorded against that name stays
resolvable. A changed or removed role in `roles.json` likewise never
retroactively changes a `Signed-off-by` value already recorded — that
value reflects who signed it under the mapping in effect at the time.

## 12. `rr-META-012` The journal is transaction-log-grade, not a changelog

`development/journal.jsonl` — one JSON object per line, strictly
append-only. A "changelog" narrates what happened; this journal is
precise enough to **replay**: every entry carries exact content pointers,
not just prose, so a point in time is mechanically reconstructable, not
just describable.

### Entry schema

Shown for the fictional `example-process` module's `ITEM` entity
(`MODULE-SPECIFICATION.md`); a real entry names the active module's own
command, entity and files.

```json
{
  "timestamp": "2026-08-23T19:00:00Z",
  "actor": "<name from IAM/users/users.json>",
  "command": "/create-item",
  "action": "create | update | close | retire | status-change | sync",
  "artifact": "ITEM-000001",
  "targets": ["fw-STRUCTURE-003"],
  "intent": ["one or more sentences — the goal driving this change, not a label"],
  "files": [
    {"path": "items/ITEM-000001-foo.md", "before": null, "after": "a1b2c3...(40 hex)"},
    {"path": "items/items.md", "before": "d4e5f6...", "after": "g7h8i9..."}
  ]
}
```

- **`targets`** — the rule ID(s) this change relates to, when applicable;
  `[]` for non-rule-linked artifacts (users, roles, and any
  non-rule-linked entity type of the active module). This
  is the machine-readable half of the chain invariant (INV-5) — every
  entry either names the rule(s) it serves or explicitly carries none,
  never leaves it ambiguous.
- **`intent`** — the *why*, as one or more full statements of purpose
  (what the actor was trying to achieve), not a terse label. Plural
  because one atomic change sometimes serves more than one goal (e.g.
  "close a gap found while retrofitting a different rule" *and* "satisfy
  the rule being retrofitted").
- **`files[].before`/`files[].after`** — the `git hash-object` SHA-1 of
  that file's content immediately before and immediately after this
  change, computed **and written to the git object store** with
  `git hash-object -w <path>` (not just computed) so the blob is
  retrievable via `git cat-file -p <hash>` independent of whether
  anything was ever committed or staged — this command never commits or
  stages on its own (`INVARIANTS.md` INV-4). `null` means the file didn't
  exist before (create) or doesn't exist after (delete).

### Point-in-time restore

To reconstruct the tree as of timestamp `T`: for every file path that
appears in any entry with `timestamp <= T`, take that file's `after` hash
from its **latest** such entry (or treat it as absent if that latest
`after` is `null`), then materialize each into a side directory via
`git cat-file -p <hash> > <side-dir>/<path>` — **never overwrite the live
working tree directly**; that's the user's call once they've reviewed the
reconstruction. `/journal-restore <timestamp>` performs exactly this.

### What must append an entry

Every command that creates, modifies, closes, or retires a rule-linked
artifact, rule, domain, or work item, or changes a `Status` field
(`CODE-OF-CONDUCT.md` §9) — resolve every touched file's `before` hash
*before* editing it, make the edit, then compute+write its `after` hash,
append one entry covering every file the command touched, then report the
result. This is the last step of the command, after everything else it
already does — it does not replace any of a command's existing steps.

### Complements, does not duplicate, `catalyst-git`

The `catalyst-git` plugin continuously audits a *deployed project* for
rule violations and writes pass/fail reports to `audits/` (INV-13: never
catalyst's own repository). This journal is kernel
infrastructure — it applies to catalyst's own self-deployment too — and
it records history for reconstruction, not violations for alerting. A
project may have both: the journal answers "what changed and why, and can
I get back to how it was," `catalyst-git` answers "did anything just
break a rule."

## 13. `rr-META-013` Repoed deployments: `criterion` and per-user branches

Every deployment's `.criterion/` is a **local working copy**
(`INVARIANTS.md` INV-6 — that never changes; it stays out of the
developed code structure, gitignored in the target project). A
deployment additionally becomes **repoed** when
`.criterion/DEPLOYMENT.md` records `repoed: true`, `catalyst_repo`,
`catalyst_repo_url`, and `created_by`: from then on, its
canonical, shared state also lives in a dedicated repository, letting
multiple users/instances of the same deployed project converge on one
agreed-upon `.criterion/` rather than silently diverging. This is
opt-in — most deployments never need it.

### Bootstrap and branching: `/criterion create <name> <git-info>`

**First call for this deployment** (not yet repoed): establishes the
dedicated repo. If `<git-info>` doesn't already exist, create it there
(named `<name>`, conventionally `<project-name>-criterion` but not
enforced); if it already exists, register it as-is rather than
recreating it — but if it already has *unrelated* content (a different
project's own `.criterion/` deployment, not this one's), that's not
a same-deployment rejoin: stop and confirm explicitly with the user
before doing anything, the same way a second, independent repo for one
deployment would need confirmation. Record `repoed: true`, `catalyst_repo:
<name>`, `catalyst_repo_url: <git-info>`, `created_by: <the current
Signed-off-by actor>` in `.criterion/DEPLOYMENT.md`, **ask which
branch this actor will push to** (§"Choosing a branch" below) and record
it as `criterion_branch`, then push the current local
`.criterion/` state as the first commit on a branch named
`criterion` — the **master version**: the canonical branch every
subsequent push targets, and, if the chosen `criterion_branch` *is*
`criterion` itself, also the branch this actor will keep pushing to
going forward. Nothing is vetted on this first push; there's nothing yet
to vet it against.

**Called again, already repoed:** does not refuse. If `<git-info>`
matches the already-registered `catalyst_repo_url`, this **branches the
repo**: create a new branch, named `<name>` in its branch-safe form (see
below), seeded from `criterion`'s current state — a fresh line of work
that doesn't touch `criterion` or `created_by`. If `<git-info>` names a
*different* repo than the one already registered, that's unusual enough
to confirm explicitly with the user before proceeding (adding a second,
independent dedicated repo for one deployment, rather than the ordinary
branching case) rather than silently doing either.

### Joining: `/criterion get <repo> <username>`

For a user who doesn't have a local `.criterion/` copy of an
already-repoed deployment yet — the "join" path, distinct from `create`
(which is for establishing or branching the repo itself). Validate
`<username>` per the branch-safe-name rule below, refusing with a
suggested alternative if it doesn't survive sanitization uniquely.
Download `<repo>`'s current `criterion` branch content and check out a
new branch for it named `<username>.criterion` (in its branch-safe
form) — this materializes as this user's local `.criterion/`, ready
for `/criterion push` from there on. **Ask which branch this actor
will push to** (§"Choosing a branch" below — the just-created
`<username>.criterion` is the natural default, but not the only
option) and record it as `criterion_branch`. This is a valid
alternative to the normal `INSTANTIATION-GUIDE.md` install flow when the
project is already repoed elsewhere: join what exists rather than
re-instantiating from the framework templates.

### Choosing a branch: `criterion_branch`

`create`'s first call and `get` both ask which branch the current actor
will push to, rather than silently deriving one — the answer is recorded
as `criterion_branch` in `<app-name>.catalyst` so later `/criterion
push` calls don't need to ask again (a deployment created before this
field existed asks once, on its next push, then remembers). The
suggested default is the actor's own fixed branch,
`<branch-safe-name>.criterion`, but choosing `criterion` itself
instead is valid and changes what `push` does — see "Sync" below.
Re-running `create`/`get` later (e.g. to switch modes) asks again and
updates the recorded value.

### Branch-safe names

Every git ref name this mechanism derives from a person's identity — the
`<name>` in a branching `/criterion create` call, `/criterion get`'s
`<username>`, and (before a user has a `git_username` — see below) the
push-branch name derived from `Signed-off-by` — uses that name's
**branch-safe form**: lowercase, every run of characters that
isn't `[a-z0-9]` collapsed to a single `-`, leading/trailing `-` trimmed.
A registered display name like "Olivier Steck" is not itself a valid git
ref component (`olivier-steck` is); this is deterministic and applied
uniformly, never skipped because a name happens to already look
git-safe. If two distinct registered names would collapse to the same
branch-safe form, refuse and ask for a manual override rather than
silently colliding two people's branches.

### Identity migration: `git_username`

The moment a user's real git identity becomes known to catalyst — the
current actor running `/criterion create` (resolved from `git config
user.name`, branch-safe form applied), or a joining user via
`/criterion get <repo> <username>` (`<username>` *is* their git
identity, given explicitly) — that value is written as `git_username` on
their `IAM/users/users.json` entry, alongside (not replacing) `name`.
**From that point on, every `Signed-off-by` field and every journal
`actor` field this framework writes for that user uses `git_username`
instead of `name`.**

Existing artifacts are handled differently from the journal, deliberately:

- **Artifacts** (the active module's entity instances, work items,
  reconciliation cases) are living documents, not a log. Every existing
  `Signed-off-by` occurrence that currently names this user's old `name`
  is rewritten in place to their new `git_username` — this is what "the
  signature of everything done before is updated" means concretely.
- **The journal is never rewritten.** INV-17 makes it immutable —
  entries are never edited, deleted, or reordered, full stop, and that
  guarantee does not bend for identity migration either. Instead, the
  migration itself gets **one new entry appended**: `command:
  "/criterion create"` (or `"/criterion get"`), `action: "update"`,
  `intent: ["migrate <old name>'s signing identity to git_username
  <git_username> for all operations henceforth"]`, and `files` covering
  every artifact file actually rewritten, with real before/after hashes
  like any other change. The history before the migration still reads
  "signed by `<name>`," truthfully — that's what happened at the time —
  and the migration entry is what makes the *why* of the shift
  reconstructable later, consistent with the whole point of §12.

### Sync: `/criterion push`

Refuses if this deployment isn't repoed yet (point to `/criterion
create`). If no `criterion_branch` is recorded yet (a deployment from
before this field existed), ask now (§"Choosing a branch" above) and
record it before proceeding. What happens next depends on that value:

**`criterion_branch` is a real contributor branch** (the default —
`<git_username>.criterion` once the actor has one, otherwise the
branch-safe form of `name`): push the local `.criterion/` state
there (creating the branch on this actor's first push) — scoped to this
actor's own objects unless they hold the `Admin` role (see "Signed-object
scoping" below) — then:

1. **Vet** the incoming branch against `criterion`: run `/check-rules`
   against the merged-in state, plus an independent four-eyes sub-agent
   pass checking whether that state still matches what its own rules
   claim. Disagreement between the two sub-agents, or a rule violation
   either flags, is not silently resolved — surface it and stop short of
   merging. (This is the same procedure `/dogfood` runs standalone when
   developing catalyst itself — see the note below; it isn't available
   in an ordinary deployment, so this step describes it directly rather
   than depending on that command existing.)
2. **Merge** using AI where a plain merge can't resolve it: attempt a
   normal merge of the branch into `criterion` first; only where that
   leaves a conflict — git-level, a vetting-flagged semantic clash, or a
   **rights-mismatch** (the actor's role doesn't cover this entity's
   type/action per `rr-META-011`'s advisory mapping in
   `IAM/roles/roles.json`) — does a sub-agent propose a resolution
   guided by `rr-META-001`'s own conflict-check principle, never
   silently dropping either side's rule-compliant intent. Where that
   proposal is itself contested, or the conflict is genuinely
   irreconcilable, open a `RECON-NNNNNN` instead of guessing which side
   wins (`rr-META-016`): `Trigger` records which of the three kinds it
   was, `Baseline` = `criterion`'s current content for that entity,
   `Proposed` = the incoming branch's content. That one entity stays
   unmerged pending resolution (`/reconcile`); everything else in the
   push proceeds normally.
3. **Update both branches** with the merged result: `criterion` gets
   the merge commit, and the contributor's own push branch is
   fast-forwarded to match, so their next push starts from the
   already-merged state instead of re-triggering the same merge.
4. **Refresh the local copy**: pull the updated `criterion` down and
   overwrite the local `.criterion/` directory (and this session's own
   in-memory record of it) to match — the local copy never silently drifts
   from what was just agreed upon remotely.

### Signed-object scoping

A contributor-branch push (not single-maintainer mode, not `--force`)
only ever pushes artifact files whose own `Signed-off-by` names the
current actor (`git_username` once migrated, else `name`) — a file
signed by someone else is left out of *this* push rather than swept up
wholesale, so pushing your own local state can never be the vehicle for
carrying someone else's un-vetted change. An actor holding the `Admin`
role (`IAM/roles/roles.json`) is exempt from this scoping and pushes
everything, same as before this rule existed. The scoping applies only
to individually-signed artifact files — shared registries/indexes
(`rules.md`, the active module's instance catalogs and generated
reports, `IAM/users/users.json`, `IAM/roles/roles.json`) and the journal aren't
signed by one person and are never filtered on their own; they only
ever carry entries the actor was already entitled to add through the
command that wrote them. If scoping excludes anything, report exactly
which files and why — a smaller-than-expected push is never silent.
This narrows what a push contains; it doesn't refuse the command itself
(`rr-META-011`'s advisory-roles principle) — a non-`Admin` actor's push
still succeeds, just scoped to what they signed.

**`criterion_branch` is `criterion` itself** (single-maintainer
mode): push the local `.criterion/` state directly onto
`criterion`, overwriting it — no vetting, no merge, every time, not
just under `--force`. This is the normal behavior in this mode, not a
shortcut: it's appropriate when there's exactly one actor keeping the
canonical state current (catalyst's own self-dogfooding is the
motivating case, where `/dogfood`'s own four-eyes audit already served
as the vetting step before the push happens at all) — refused for anyone
other than the repo's recorded `created_by`, same gate as `--force`
below. A repo intended to stay in this mode should only ever grow the
one `criterion` branch — no per-contributor branches ever get created
against it.

### `--force`

`/criterion push --force`, on a contributor branch, skips vetting and
merging for *this one push* and overwrites `criterion` directly with
the local state anyway — the same destructive-shortcut shape as
`/sync-framework --force`, and gated the same way access to anything
destructive is gated in this framework: **refused for anyone other than
the repo's recorded `created_by` user.** Every other contributor only
ever gets the vetted-and-merged path. Meaningless (and unnecessary) in
single-maintainer mode, where every push already behaves this way by
default.

### What this is not

Not a replacement for `/sync-framework` (that synchronizes the *framework
template* into a deployment; this synchronizes one deployment's *own
state* across its contributors) and not a substitute for the journal
(§12) — a `criterion` merge is itself a change subject to the same
journaling rule as any other, once it lands locally.

### `/dogfood` is catalyst-development-only

The vetting procedure above (`/check-rules` + a four-eyes drift check) is
also available as a standalone command, `/dogfood` — but only when
developing catalyst itself, never as part of what an ordinary deployment
exposes. It isn't listed in `CODE-OF-CONDUCT.md` §4 and
`INSTANTIATION-GUIDE.md`/`SYNCHRONIZE.md` never materialize a
`.claude/commands/dogfood.md` for a deployed project; it exists only in
catalyst's own repository, for verifying catalyst's own rules against
catalyst's own actual state. `/commands list` (§4) surfaces it when
running in that context, and stays silent about it everywhere else.

**After every `/dogfood` run that ends clean, or ends with fixes applied
and reverified**, offer to sync — `/criterion push` if this deployment
is already repoed, `/criterion create` if it isn't. Never run either
automatically (INV-4: no push without explicit assent) — offer it, the
same way any other next step gets offered, and proceed only once the
user says to. This is what makes single-maintainer mode (above) coherent
for catalyst's own repo specifically: `/dogfood` is the vetting step,
already run standalone before the offer even appears, so the push it
leads to can safely overwrite `criterion` directly without repeating
that check.

## 14. `rr-META-014` Agent-owned working copy, the tracked pointer, and project lifecycle

INV-6 (revised): the working copy — a directory always named
`.criterion/` — is not built inside the target project's own tree. It
builds in **agent-owned space**: a per-project data location the running
agent already maintains, outside the project being governed. Its location
is computed per machine by the running agent from its own conventions
(`BOOTSTRAP.md` §1; each agent's shim says how) and is never written into
a tracked file. The target project tracks exactly one file for it, at its
root: **`<app-name>.catalyst`** (JSON, from
`templates/catalyst-pointer.template.json`), which holds no path. This is
the only catalyst artifact the target project's own repo ever carries —
small, safe to commit, no rule/artifact/journal content in it, identical
on every machine.

**One access path.** `<project root>/.criterion` is how everything —
agents, tools, the project's own `Taskfile.yml` — reaches the working
copy: a **symlink** to the agent-owned `.criterion/`, always gitignored
(`/.criterion` in the project's `.gitignore`). The agent creates or
repairs it at install, at `/criterion get` and `/project import`, and at
every session start (`BOOTSTRAP.md` §1.1). Every document path written
`.criterion/...` therefore means the same thing on every machine and for
every agent. Tools resolve the working copy in this order: (1)
`<project root>/.criterion` (symlink followed, or a real directory); (2)
legacy — a pointer's `agent-source` field, if present and an existing
directory (pre-0.37.0 pointers may still carry `agent-source`; tools
honor it until migrated); (3) any tool-specific extra fallback. The
project root is the directory holding the `*.catalyst` pointer.

`.criterion/DEPLOYMENT.md` (§13) keeps its existing role unchanged —
the source of record for `repoed`, `catalyst_repo`, `catalyst_repo_url`,
`created_by` — inside the working copy. `<app-name>.catalyst` mirrors those
same four fields at the project root; any command that writes them
(`/criterion create`, `/criterion push --force`) updates both files in
the same step. If they ever disagree, `.criterion/DEPLOYMENT.md` wins —
it is the source of record.

**No agent owned-space concept available, or no symlinks on this
platform:** fall back to building `.criterion/` directly inside the
target project as a real directory, gitignored there, never committed.
`<app-name>.catalyst` still gets written at the project root, unchanged.
Every mechanism below (migration, export, import) treats this fallback
as just another shape of `<project root>/.criterion`, not a special case.

### Migration from the pre-pointer-file model

A deployment installed before this section existed has `.criterion/`
sitting directly in the project root, with no `<app-name>.catalyst`
anywhere. Detect this (a `.criterion/` dir at the project root and no
`*.catalyst` pointer file beside it) and offer the migration — it is a
structural change, so confirm with the user before proceeding, the same
courtesy as `/criterion create`:

1. Resolve the agent-owned location per `BOOTSTRAP.md` §1. If the
   running agent has no owned-space concept, there is nothing to move —
   stop here; the in-project fallback shape already **is** the target
   shape, it just still needs its `<app-name>.catalyst` pointer written
   (step 3 below, skipping step 2).
2. **Move**, not copy, the entire existing `.criterion/` tree from
   the project root to the resolved agent-owned location, then create
   the `.criterion` symlink at the project root pointing at it.
3. Write `<app-name>.catalyst` at the project root (no path in it);
   `repoed`/`catalyst_repo`/`catalyst_repo_url`/`created_by` carried over
   from the existing `.criterion/DEPLOYMENT.md` if one exists, else
   left at their unset defaults.
4. Make sure `/.criterion` is in that project's `.gitignore` — the
   symlink (or the fallback directory) is never committed.
5. Append one journal entry, in the working copy's new location, for the
   migration itself (`action: "migrate"`, `intent` describing the move,
   `files` covering the old and new `DEPLOYMENT.md`/pointer locations by
   content hash) — this is exactly what the journal (§12) exists to
   record, and its immutability means the pre-migration history stays
   readable at its old hashes regardless of where the tree now lives.
6. Report the result. Per hard rule 4, nothing is committed
   automatically — but note explicitly that `<app-name>.catalyst` is now
   something the user will want tracked, unlike anything that came before
   it.

### Agent switching procedure

When a session starts or an agent assumes governance of a project previously managed by another agent (detected when the running agent's identity differs from the `agent` field in `<app-name>.catalyst`):
1. Resolve the running agent's own owned location per `BOOTSTRAP.md` §1 (or the in-project fallback `.criterion/`).
2. If the `.criterion/` working copy existed at a previous location (the current `.criterion` symlink's target, or a legacy pointer's `agent-source`), mirror it into the new location: the new location ends up an exact copy of the old one — every file the old one had, none it didn't — overwriting anything already at the new location that conflicts, and removing anything at the new location the old one doesn't have. Never a partial merge.
3. Repoint the `.criterion` symlink at the project root to the new location (skip on the in-project fallback), keeping `/.criterion` in the project's `.gitignore`.
4. Update `<app-name>.catalyst`: set `agent` to the current agent's identifier and `updated` to the current date string (`YYYY-MM-DD`) — nothing else; the pointer holds no path, and the project's `Taskfile.yml` needs no edit.
5. Update persistent framework memory (and deployment notes) with the current agent name, resolved working-copy location, and update timestamp.

`/switch-agent [agent-id]` runs this same procedure on demand, unconditionally
(steps 1–5 above, without first checking whether identity actually differs)
— the manual escape hatch for when the automatic per-session check above is
skipped (e.g. dropped by a compacted session) or only partially applies (one
field updated, another left stale). Full command spec: `CODE-OF-CONDUCT.md`
§4.

### `/project create`/`remove`/`export`/`import`

The lifecycle commands for this model (full command spec:
`CODE-OF-CONDUCT.md` §4).

- **`create <name>`** is the explicit, named entry point for the
  instantiation procedure (`INSTANTIATION-GUIDE.md`) — resolves the
  agent-owned location, builds a fresh working copy there, writes
  `<app-name>.catalyst` (no path in it), creates the `.criterion`
  symlink, and adds `/.criterion` to the project's `.gitignore`. Refuses if a pointer file or an in-project
  `.criterion/` already exists here — that's `/project import
  --force`'s job, not `create`'s.
- **`remove <name>`** un-links locally only: deletes the project's
  `<app-name>.catalyst` and the `.criterion` symlink (on the fallback,
  it stops treating the in-project `.criterion/` as active). The working copy itself, this
  agent's memory note, and any `criterion` repo are all left exactly as
  they are — never delete, retire in place (`rr-META-004`), same
  principle as user retirement (§11).
- **`remove <name> force`** additionally deletes the working copy (agent-owned,
  or the in-project fallback) and this agent's memory note for the project. This is
  the one genuinely destructive path here — confirm explicitly before
  proceeding, the same as `/criterion create`'s repo creation or
  `--force` push. It never touches a `criterion` repo: that's a
  separate, externally-hosted, possibly multi-contributor artifact, well
  outside the blast radius of a local removal.
- **`export <name> [file]`** reads every file under the working copy and
  writes one JSON bundle — relative path → file content, plus the
  pointer fields (never a path, which is meaningless outside the
  exporting machine — a legacy `agent-source` is dropped). Default
  filename when omitted: `<name>-catalyst-export-<UTC timestamp>.json`,
  written to the current directory.
- **`import <file>`** installs a bundle into the current project — same
  refusal condition as `create` if a deployment already exists here.
  Resolves this agent's own owned location on this machine (never the
  exporting machine's), writes every bundled file there, creates the
  `.criterion` symlink (with `/.criterion` gitignored), writes
  `<app-name>.catalyst` with the bundle's pointer fields carried over
  as-is, and appends one journal entry for the import.
- **`import <file> force`** is the one case allowed to proceed even when
  a deployment already exists here — it overwrites it. Warn what's about
  to be replaced and confirm explicitly first, same tier of
  destructiveness as `remove ... force`.

## 15. `rr-META-015` Every artifact type has the same directory shape

Hard rule, no exception: **every artifact-type directory carries a
versioned, catalogued `templates/` subdirectory**, and both it and the
artifact-type directory itself always have a `README.md`.

```
<artifact-type>/
  templates/
    README.md
    templates-<type>.md      # catalog: Version | File | Timestamp | Notes
    TEMPLATE-<TYPE>-v1.md
    TEMPLATE-<TYPE>-v2.md    # a new version when the template's content
    ...                      # changes meaningfully — never overwritten in place
  README.md
  <type>.md                  # catalog of actual artifact instances
  [...]                      # actual artifact files/folders — free-form,
                              # any depth, this artifact type's own choice
                              # of sub-organization
```

`templates/` accepts **files only** — a new template version is a new
file (`TEMPLATE-<TYPE>-v2.md`, never an edit to `v1`), never a
subdirectory. The artifact-type root above it accepts files *and*
folders at arbitrary depth, precisely because different artifact types
need different sub-organization (e.g. rule documents nested by domain,
one file per named instance of some module entity type) — this rule fixes the *shape*
`templates/` + `README.md` + `<type>.md` provide, not how the actual
artifacts underneath are arranged.

**Versioned and timestamped**, per the hard rule this section exists to
satisfy: `TEMPLATE-<TYPE>-vN.md`'s `N` is the version; the *timestamp*
lives in `templates-<type>.md`'s catalog table — one row per version,
recording when it was introduced and what changed, so template history
is inspectable without diffing file content. The **current** version is
always the highest `N` present; nothing below `templates/` ever gets
edited in place once a newer version exists — that would defeat the
point of versioning it at all.

**Exactly one exception to "everything nests under an artifact-type
folder": documents that govern the artifact type itself** —
`Rules-of-Rules.md`, `rules-of-work-items.md`, and each artifact type's
own `templates-<type>.md` catalog — sit flat alongside `README.md` and
the instance catalog, siblings to `templates/`, not inside it and not
inside the free-form `[...]` area. This is already the existing shape of
`rules/Rules-of-Rules.md`; §15 generalizes it, it doesn't change it. A
`work-items/` folder, if a project-management plugin deploys one, uses
the same shape for its own `rules-of-work-items.md` (§8, INV-22).

### Where every artifact type actually sits

- `rules/` — `templates/`, `domains/` (itself shaped exactly like an
  artifact type: `templates/`, `README.md`, `domains.md` catalog,
  free-form domain files — nested here because a domain exists only to
  group rules, never as a top-level sibling), `README.md`,
  `Rules-of-Rules.md`, `rules.md`, free-form rule documents (`[...]`,
  typically nested by domain, e.g. `business/business-rules.md`).
- The active module's artifact-type folders (`<folder>/`, one per entity
  type, from each entity type's ETD `folder`) — top-level siblings of
  `rules/` unless the module places them under `development/`, each with
  the full `templates/` treatment. Where each one sits is the active
  module's meta-rules (`MODULE-SPECIFICATION.md` §6.1).
- `reconciliations/` — top-level folder, sibling of the module's
  artifact-type folders, not nested under `work-items/`: `RECON-NNNNNN`
  cases are triggered by `/criterion push`'s own mechanism (§13), not
  agile process (§8), and are never themselves work (§16).
- `workflows/` — top-level folder, sibling of `reconciliations/`:
  `WORKFLOW-NNNNNN` process-definition documents, core (not gated behind
  any plugin) and never themselves work (§19).
- `IAM/` — new top-level folder replacing bare
  `development/users.json`/`roles.json`; holds `users/` and `roles/`,
  each shaped exactly like any other artifact type (§11), including the
  `templates/` treatment. `TEMPLATE-USERS-v1.json`/`TEMPLATE-ROLES-v1.json`
  version the registry's *seed shape* (the array a fresh deployment
  starts from), not a per-instance document — `users.json`/`roles.json`
  are each one JSON array, not one-file-per-instance, so there is
  exactly one live instance per type, versioned the same way any other
  type's template is.
- `plugins/` — unchanged (INV-10..13): `<type>/<name>/`, each activated
  plugin's own install, sourced from its own repository. Not subject to
  the `templates/`+catalog shape — a plugin owns its own internal
  structure.
- `development/` — `meta-tags/` promoted to a full artifact-type folder
  (previously meta-tags lived as loose files directly under
  `development/`), plus any module artifact-type folders the active
  module places here; `README.md`, `journal.jsonl` (and any generated
  report the module adds) stay flat, cross-cutting, not artifact types
  themselves.
- `work-items/` — **not part of the core layout** (§8, INV-22). Only
  exists once a project-management-type plugin extending
  `plugins/_prototyping/project-management/agile/`'s schema is
  activated; that plugin's own `## Contributes` section then defines
  which of `boards/`/`epics/`/`spikes/`/`sprints/`/`stories/`/`tasks/`/
  `tickets/` it deploys, alongside `README.md` and
  `rules-of-work-items.md`.

See `INSTANTIATION-GUIDE.md` §1 for the full deployed layout tree and
`INSTANTIATION-CHECKLIST.md` for the tickable deploy-skeleton steps.

## 16. `rr-META-016` Reconciliation of diverging entity versions

`/criterion push`'s merge step (§13) already has to handle two versions
of the same entity disagreeing — a git-level conflict, a
vetting-flagged semantic clash, or a rights-mismatch against
`rr-META-011`'s advisory role mapping. `RECON-NNNNNN` is the durable,
chainable record of that disagreement and how it got settled, instead
of the resolution living only in an ephemeral sub-agent proposal.

**Never itself work.** Like `WORKFLOW-` (§19), a `RECON-` carries no
`Targets` rule field and is exempt from the chain invariant's
epic→story→task→active-module artifact→rule path — its chain
runs sideways, via an `Entity` field naming the artifact actually in
dispute, not downward to a rule.

**May optionally name a guiding workflow.** A `Workflow` field can cite
a `WORKFLOW-NNNNNN` (§19) whose `## Steps`/`## Gates / exit criteria`
describe how this specific, recurring kind of conflict should be
resolved — read it before choosing a `/reconcile` verb, when present.
Most cases won't have one: the fixed verb set below already *is* the
procedure for the ordinary case.

**Opened** by `/criterion push` itself (automatically, when its merge
step hits one of the three trigger kinds above) or manually by any
actor who wants a second opinion recorded before landing a change.
`Trigger` records which: `rights-mismatch`, `merge-conflict`, or
`manual`. `Baseline` captures `criterion`'s current content for the
entity at open time; `Proposed` captures the version being contested.
Opening one never blocks the rest of the push — only the disputed
entity stays unmerged; everything else proceeds.

**Revised, not re-filed.** Each round of back-and-forth (a counter-edit,
a clarifying question, a revised proposal) is a new row appended to the
same file's `## Revisions` section — never a new file per round, unlike
`templates/`'s own `TEMPLATE-<TYPE>-vN.md` versioning. The file is
edited in place across its lifecycle the same way the active module's
living artifacts already are, and every edit is journaled with its before/after content hash
(INV-17) — that already gives the audit trail; no second versioning
scheme is needed on top.

**Resolved** via `/reconcile <id> accept|accept-with-edits|reject|propose
<text>`: `accept` merges `Proposed` into the `Entity` as-is;
`accept-with-edits` merges the latest `## Revisions` row's content
instead; `reject` leaves `criterion` unchanged and flags the proposer's
local copy as needing to pull the rejection down; `propose <text>`
appends `<text>` as a new `## Revisions` row without resolving anything.
`Status` moves `Open` → `Under Review` → one of `Resolved-Accepted` /
`Resolved-Accepted-with-Edits` / `Resolved-Rejected` → `Closed`.

**Who can do what is genuinely gated by role — the one deliberate
exception to `rr-META-011`'s advisory-only principle.** Each role in
`IAM/roles/roles.json` carries a `reconciliation` field: `full` may use
every verb, including the three resolving ones; `propose` may only use
`propose <text>` — moving `Status` to `Under Review` — and is refused
outright on `accept`/`accept-with-edits`/`reject`, told a `full`-level
actor must finish it; `none` is refused on every verb immediately, told
to ask a `full` or `propose` actor to act on their behalf. This differs
from every other role check in the framework in that the command
genuinely stops rather than asking for confirmation and proceeding
anyway. The trust boundary is unchanged — catalyst still can't verify
who's typing — but letting anyone finish a reconciliation regardless of
role would defeat the reason `RECON-` exists: the `Resolver` field and
the journal entry it produces are only meaningful as a record of *who
was actually allowed to decide*, not just who happened to type the
command.

**Layout and ID**: `reconciliations/`, top-level, sibling to
the active module's artifact-type folders (§15's "Where every artifact type actually
sits"), full `templates/`+catalog treatment (INV-20). ID format
`RECON-(NNNNNN)`, 6 digits, its own global sequence, never reused —
same scheme as every other numbered type (§3).

## 17. `rr-META-017` Content-contributing plugins

Every `repository`-type plugin only *observes* the deployed project —
it reads the project's own repository and writes its own output (e.g.
an audit trail), but never adds a core artifact type or a slash
command (INV-13). A **content-contributing plugin** is the other shape:
on activation, it
materializes deployable content — an artifact-type folder (with the
standard `templates/`+catalog treatment, INV-20) and/or slash-command
files — into the target project; on deactivation, it removes exactly
that same content.

**Declared via `## Contributes`**, a new optional section in
`working-contract.md` (`TEMPLATE-WORKING-CONTRACT.md`), naming:

- the artifact-type folder(s) it deploys, and where their templates
  resolve from (its own repository, or — while still under
  `plugins/_prototyping/` — a shared prototype schema there, never
  vendored as a stale local copy);
- the slash-command file(s) it deploys into `.claude/commands/`.

**`/catalyzer activate <name> <version>` materializes this content**,
the same mechanism first-load instantiation already uses to copy core
templates into a fresh deployment (`INSTANTIATION-GUIDE.md` §1): create
the named artifact-type folder(s) with their `templates/`+catalog+
`README.md`, and copy the named command file(s) into `.claude/commands/`.
**`/catalyzer deactivate <name>` removes exactly what activation
added** — the templates/ scaffolding and the command files — and
**never touches artifact instances the deployment already created**
with them (real `EPIC-NNNNNN`/etc. files, and their index entries, are
deployment content, not plugin content, the same non-destructive
posture `/project remove` already uses for the working copy, §14). A
deployment with existing instances but no active plugin simply can't
create *more* until reactivated.

**Two or more content-contributing plugins of the same category must
not both be active** if their `## Contributes` sections would deploy
the same artifact-type folder — that's a content conflict, not
additive; refuse the second activation and point at deactivating the
first.

**Plugins under `plugins/_prototyping/`** are exempt from INV-11's
"every plugin has its own repository" — a prototyping plugin's content
lives in catalyst's own repository until it graduates into a top-level
plugin-type directory (e.g. `repository/`, `project-management/`), at
which point INV-11 applies to it like any other plugin.

## 18. `rr-META-018` Recreation drift check

`/dogfood`'s base procedure (§13's `### /dogfood` subsection) verifies
that catalyst's actual state still matches what its own rule document
*claims* — for an existing rule, is the cited evidence still accurate.
It cannot catch a different failure: an invariant gets added to
`INVARIANTS.md` but never actually gets retrofitted into any rule at
all, so there is nothing existing there for the base check to evaluate
in the first place. This section defines a second, opt-in mode that
catches exactly that — independently re-deriving `INV-N` coverage from
`INVARIANTS.md` and the actual codebase, blind to the live deployment's
rule document, then comparing. Both checks keep running; neither
replaces the other.

### Trigger: `/dogfood recreate`

Opt-in, not part of the default `/dogfood` run — this spawns a full,
careful codebase read, expensive relative to the base check. Suggested
cadence: before cutting a release, not on every invocation. Because the
isolation mechanism below operates on a git worktree, this audits the
last **committed** state, not uncommitted working-tree edits — a
non-issue at the suggested cadence, where the tree should already be
clean.

### The isolated agent

Spawned via the `Agent` tool with `isolation: "worktree"` — one agent,
not a four-eyes pair (see "Why not four-eyes" below). Since
`.criterion/` lives entirely outside this repository, in agent-owned
space reached only through the gitignored `.criterion` symlink at the
repository root (INV-6), a worktree checkout has no path to it — the
symlink is untracked, so absent there, though `catalyst.catalyst` itself
is a tracked file and will still be present in the checkout. The agent's
prompt must therefore state explicit, forceful prohibitions, not rely on
the worktree's isolation alone: never compute the agent-owned location,
never resolve any `*.catalyst` pointer's legacy `agent-source` field, and
never read anything under a path so resolved; never read anything named
`.criterion/` under any form it might be reached; never consult `git
log` or commit messages, which narrate exactly what changed in the
live deployment — current file content only.

**The prompt handed to this agent must be hand-authored and
self-contained, never `/dogfood`'s own text forwarded verbatim** — the
base procedure above names
`.criterion/rules/framework/fw-framework-rules.md` by literal path;
reusing that text would leak exactly what blindness is meant to hide.

**Deliverable**: for each `INV-N` in `INVARIANTS.md`, found or
not-found, plus evidence — a `file:line` citation, or "behavioral, not
machine-checkable" for something no script can verify. Not a full
retrofit-quality rewritten rule document; the comparison below only
needs a coverage judgment per invariant, not finished prose, IDs, or
domain assignment.

### Why not four-eyes

`ANALYSIS-PLAYBOOK.md`'s own stated principle is that four-eyes matters
most for exactly this kind of extract-what-exists-in-code work — this
section is a deliberate, reasoned departure from that principle, not an
oversight. The second opinion this whole check exists to provide
already comes from comparing the isolated agent's findings against the
live deployment; pairing the isolated agent with a second one on top of
that duplicates cost for a periodic drift check, unlike a one-time
bootstrap (`INSTANTIATION-GUIDE.md` §4), where the playbook's full
four-eyes remains the right tool.

### Comparison

Done by the orchestrating session itself, after the isolated agent
returns — unlike the generation/research side, comparing two
already-produced documents doesn't need blindness. **This is a
judgment-based read, never a literal string search for `INV-N`.** Many
existing rules cite only an `INVARIANTS.md:<line>` pointer and never
spell out the bare `INV-N` label in their own text, and cited line
numbers drift as `INVARIANTS.md` grows without the underlying rule
being wrong — matching requires reading each rule's content and its
cited evidence, not grepping for a label or trusting an exact line
number.

Two flat-severity outcomes per `INV-N`, neither weighted above the
other regardless of whether the invariant is machine-checkable or
behavioral:

- the isolated agent found supporting evidence, but the live deployment
  has no rule covering that `INV-N` at all;
- the live deployment claims coverage for an `INV-N`, but the isolated
  agent's independent read found no supporting evidence for it.

### Reporting only

Never fix anything automatically, same as the base `/dogfood` policy —
this surfaces drift for the user's or a follow-up command's call, it
does not resolve it.

### Out of scope

Stays catalyst-development-only, the same boundary §13 already draws
for `/dogfood` itself. Not a mechanism any other deployed project gains
access to.

## 19. `rr-META-019` Workflow entity for guided procedures

`WORKFLOW-NNNNNN` (`templates/workflow.template.md`) is a
process-definition document, not a unit of work: it documents a
repeatable multi-step procedure (e.g. how one of the active module's
artifacts moves from triage to resolution, or how to work through a particular recurring kind of
reconciliation). It carries `Status` (`Active`/`Deprecated`) reflecting
whether the process is currently in use, never a work-tracking
lifecycle, and is never itself "done." Used to live inside
`work-items/`'s plugin-territory schema (§8); it's core now — its own
top-level `workflows/` folder, sibling of `reconciliations/`, always
present, full INV-20 treatment, no plugin required (`INVARIANTS.md`
INV-24).

**Its purpose is to be referenced, not just filed.** A core entity may
optionally name a `WORKFLOW-` by ID to guide its own process — `RECON-`
reconciliation is the first to do this (§16's optional `Workflow`
field): when a case names one, the resolver reads its `## Steps`/
`## Gates / exit criteria` before choosing a `/reconcile` verb, the same
way a documented procedure guides a human through an otherwise
ambiguous judgment call. Most reconciliations won't need one — `/reconcile`'s
fixed verb set already *is* the procedure for the ordinary case; a
`Workflow` is for a project that wants a documented, repeatable
escalation path for a specific recurring kind of conflict.

No dedicated creation command (no `/create-workflow` in core) — like
`RECON-`, a workflow is authored occasionally, not through a frequent,
form-driven flow; an agent creates one ad hoc from
`templates/workflow.template.md` and registers it in `workflows/workflows.md`
the same way any other artifact type's instance gets registered.

## 20. `rr-META-020` Entity IDs carry their signer's userid

Once a registered user has a `userid` (§11, INV-26), every rule,
`WORKFLOW-`, `RECON-`, and active-module `<PREFIX>-` ID carries that
user's `userid` as a trailing `-XXXXXXXX` segment — always the final segment of the id, after any type-specific suffix a section
above already defines (a rule's `[-parent-id]`, §3). Assigned once, at
the same moment the entity's `Signed-off-by` (or, for a rule, the
authorship resolved below) is determined; never reassigned, never
changed if the signer is later deactivated or their role changes — the
same immutability posture `Signed-off-by` itself already has (§11).

**Hard ordering.** No entity may be assigned a suffixed id until its
signer already has a `userid`. Never generate a userid and an entity
suffix in the same breath if the signer isn't already registered with
one — register the user first, confirm the `userid` exists, then
proceed.

**For a type with a resolvable signer** (every type above except
rules): the `userid` is exactly that resolved signer's — the same
person `rules-of-development.md` §2's signer-resolution procedure names
in `Signed-off-by`. No separate lookup, no separate decision.

**For a rule** (and, by extension, a domain's own code, which is
never suffixed — see below): no rule or domain template carries an
authorship field of any kind, so there is nothing today recording who
added a given rule. Until a dedicated field is designed, use the sole
registered active user; if more than one is active, use whichever was
most recently registered. **This is a known, documented limitation**,
not a permanent design choice — a deployment with real multi-author
rule authorship will get an inaccurate attribution under this fallback,
and should treat adding a real per-rule authorship field as its own
future tracked maintenance item once that limitation actually bites.

**Domains are out of scope.** A domain has no numeric sequence — it's
identified by its `CODE` alone (§7), embedded as a substring inside
every rule id that cites it. There is no id to suffix.

**Cross-reference impact.** Renaming an id (retroactive migration, or
the initial rollout of this rule) means updating every place that id is
cited by exact string: its own heading/field, its type's index/catalog
row, every structured cross-reference field (`Targets`, `Entity`,
`Workflow`, and every `ref` field the active module's ETDs define), and
every free-text citation in `## Related`/`## Notes`/prose — there is no
dedicated cross-reference-checking script today (`/check-rules` and
`/audit` are agent-judgment procedures), so this is the agent's
responsibility to verify by direct search, not something CI catches
automatically. A rename must never touch `development/journal.jsonl`
(INV-17 — append-only; historical entries correctly keep citing the
pre-rename form forever), nor hand-edit any machine-regenerated report
(INV-14) — regenerate it with its own command after the rename instead.

## 21. `rr-META-021` — owned by the active module

`rr-META-021` — owned by the active module (`MODULE-SPECIFICATION.md`
§6.1); never reused.

## 22. `rr-META-022` — owned by the active module

`rr-META-022` — owned by the active module (`MODULE-SPECIFICATION.md`
§6.1); never reused.

## 23. `rr-META-023` Artifact updates happen atomically, as work happens

Every catalyst artifact — an active-module artifact's own record, a
`Status` field, a journal entry — is updated **as the work it describes
actually happens**, at the smallest atomic unit practical, not
reconstructed retroactively in one batch once work is already done. This
applies to every artifact update, whether the agent or a user is
narrating their own manual work: an artifact recording a unit of work is
opened when that work starts and closed when it finishes, not
backfilled after the fact (the active module's meta-rules may state
this narrowly for its own entity types); a journal entry is appended as each
qualifying action completes (§12), never accumulated and appended in
bulk at session end; a `Status` field moves the moment the real-world
state it tracks moves.

**Delayed, batched updating is allowed — but only when explicitly
stated before the work begins.** Whoever is about to do the work (agent
or human) says so up front — "I'll batch these updates and record them
afterward" — before starting, not as a retroactive justification once
the work is already underway or finished. Absent that explicit
statement, real-time, atomic updating is the default; silently
batching bookkeeping for later convenience is not a judgment call left
to the agent.

**Added 2026-09-20**
(`framework/kernel/migrations/0.32.0/atomic-artifact-updates.md`).
Behavioural only — no existing artifact's shape or content changes;
nothing here to retroactively backfill.
