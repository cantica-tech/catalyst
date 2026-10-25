# 31 — Who creates, edits and deletes what, and through which workflow (design for the owner, 2026-10-25)

> **Status: decided (owner, 2026-10-25)**: the request (§1), deleting is retiring (§5), IDs never editable (§2a), and
> §7's four questions as proposed. Builds on designs `25` (approval gates), `26` (proposals), `27` (`catalyst try`),
> `29` (people and grants from catalyst-users) and `30` (visibility, the realm). What a UI shows for it is the UI's
> own design.

## 1. The request

- **Admins** (the Admin, and a Criterion Admin in their project) create, edit and delete entities directly, from a
  UI as from the CLI; if a change would break anything, they are told before it becomes permanent.
- **Everyone else** creates only some types (those of the modules running in the criterion). They edit or delete an
  entity directly only when it is linked to no other item; when it is linked, the change goes through a defined
  workflow, defined:
  1. at the criterion's level;
  2. at the entity type's level;
  3. for a tag: a **tag workflow** targets entities carrying one or more given tags, and the people who hold the right
     to run that workflow take part in it.

## 2. Today

- Every write is a catalyst verb, journaled (L1): `new`, `rename`, `status set`, `link`, `restore`, `propose`.
- A person's grants (`cmd:<command>`, from catalyst-users) decide which commands they may run, not which types.
- A **governing workflow** (`WORKFLOW-` with `Governs: <type>`, kernel 0.104.0) lists the status moves a type may
  make, each with the role that makes it and a condition; it governs status moves only, not edits.
- **`catalyst try <verb …>`** makes one change on a scratch copy and reports the `check` findings it adds and clears,
  keeping nothing (design `27`). **`catalyst propose`** opens a review case carrying a change, applied on acceptance
  (design `26`).
- **Nothing is deleted**: L7, an entity is retired in place, its ID never reused. Entities carry **no tags**.

## 2a. What no one edits

**An entity's ID is never editable**, by anyone, the Admin included (the owner, 2026-10-25; L7). Nor is what catalyst
derives: `Name` and `Filename` follow the title (`catalyst rename`), back-referenced fields follow their sources
(`catalyst link`, `repair derived`), `Signed-off-by` is the verified signer, and `Status` moves only through
`status set` and its workflow. A UI's editor offers these read-only; the verbs refuse them.

## 3. Admins: direct, forewarned

- An admin's create, edit or delete runs as `try` first: the UI (or the CLI with `--preview`) shows what it would
  change and every `check` finding it would add (a dangling reference, a broken chain, a guard no longer holding, an
  index out of date), then asks.
- **Nothing added**: one confirmation, then the verb runs, journaled. **Something added**: the findings are listed
  first, and confirming says so in the journal entry ("forewarned: …"). Nothing is permanent before that confirmation.
- The Admin does this in every project; a Criterion Admin in their own. Both remain bound by design `30`'s realm rule.

## 4. Everyone else

### 4.1 Creating

A person creates an entity of a type when **both** hold:

- the type belongs to a module running in the criterion (the kernel's own types, `WORKFLOW-`, `RECON-`, `ANALYSIS-`,
  stay admins'), and the module lets contributors create it (`contributors_create: true` on the type in
  `module.yaml`, the default for a module's work types);
- their grants allow it: `create:<TYPE>` (or `cmd:/create`, which allows every type the module lets them create).

### 4.2 Editing and deleting

- **Unlinked** (no reference field of the entity cites anything, and nothing cites it): the person edits it, or
  deletes it (§5), directly, as the creator or an assignee of it (design `30`: they can see it).
- **Linked**: the change becomes a **proposal** (design `26`) that the governing workflow takes through its states;
  it is applied, journaled, only at the workflow's final move. A change of a linked entity never lands directly.

### 4.3 Which workflow governs a change

Three levels, the most specific first:

| Level         | Declared by                                                                                        | Applies to                             |
| ------------- | -------------------------------------------------------------------------------------------------- | -------------------------------------- |
| **Tag**       | a `WORKFLOW-` with `Kind: tag-workflow` and `Tags: <tag>[, <tag>…]`                                | an entity carrying any of its tags     |
| **Type**      | a `WORKFLOW-` with `Governs: <TYPE>` (today's governing workflow, extended to edits and deletions) | every entity of the type               |
| **Criterion** | the criterion's default workflow (`Governs: *`)                                                    | every entity no other workflow governs |

A tag workflow's **participants** are the people holding the right to run it: a grant `workflow:<WORKFLOW-id>` (or a
role its Transitions name). They make its moves, whatever their other rights; others cannot.

### 4.4 Tags

- A kernel field `Tags` on every type: lowercase words, a list.
- **Removing a tag that a tag workflow targets is itself a change that workflow governs**: a tag cannot be dropped to
  escape it. Adding a tag is a plain edit.

## 5. Deleting is retiring (the owner's answer, 2026-10-25)

To delete an entity is to **retire** it: it moves to its type's closed state (`Retired`, `Withdrawn`…), its file
stays, everything citing it still resolves, and its ID is never reused. L7 holds as it is: nothing is ever removed.
A UI's "Delete" runs that retirement, under §3 (admins) and §4.2 (an unlinked entity directly, a linked one through
its workflow).

## 6. Phases

1. Admins forewarned: `try` behind every write a UI offers, `--preview` on the CLI's writing verbs.
2. Contributors' creation: `contributors_create`, `create:<TYPE>` grants.
3. Edits and deletions: linked or not; proposals through the governing workflow; workflows governing edits and
   deletions.
4. Tags and tag workflows, with their participants.

## 7. Decided (owner, 2026-10-25)

1. **Two tag workflows on one entity** (it carries tags of both): `check` refuses it.
2. **"Linked"**: any reference in or out.
3. **A criterion with no workflow at all**: a linked entity's change waits for an admin.
4. **Contributors' types**: the module's default plus grants.
