# 30 — Visibility: who sees which entities (design for the owner, 2026-10-25)

> **Status: proposed.** Questions 1 to 4 answered by the owner (§2); §8 lists what is still to decide. Builds on
> designs `25` (approval gates), `28` and `29` (people from catalyst-users) and `19` (`catalyst serve`).

## 1. The request

A person who is not an admin signs in and sees their own work: the entities they created, those assigned to them,
and the entities connected to those, even when other people handle them. Everything else in the project can be seen,
but only by asking for it (a query). Visibility stops at the project, unless another project's entities connect to
this one. Classification decides above all: an entity above a person's clearance cannot be seen, unless it is
assigned to them and their rights have been raised for that entity.

## 2. The owner's answers

| #   | Question                                     | Answer                                                                                                                                                                                                                        |
| --- | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | How far "connected" reaches                  | **Direct links only**: an entity's own reference fields and the entities citing it                                                                                                                                            |
| 2   | What a query says about what it may not show | **Nothing**: no count, no placeholder, no hint                                                                                                                                                                                |
| 3   | Who raises a person's rights on an entity    | **The Admin** (who can do anything); **a Criterion Admin** (the project's admin, kernel 0.109.0, `fw-IDENTITY-000011`) in their own project; an entity's **owner** only with a Criterion Admin's or the Admin's authorization |
| 4   | Whether clearance binds admins               | **No**: the Admin sees everything; a Criterion Admin sees everything in their project (read from 3)                                                                                                                           |

## 3. Today

- A person signs in with `catalyst identity login` (the device flow; their account and groups are catalyst-users').
  Their grants (`cmd:<command>`) restrict what they may **run**, so writes are restricted.
- **Nothing restricts what they may read.** A criterion is a git repository: whoever holds a clone reads every
  entity, every index, the whole journal (with each change's content before and after) and its history.
  `catalyst serve` asks for a token, but any valid token reads everything.
- **Only the knowledge-base module classifies anything** (its documents and builds); the kernel's entities carry no
  classification.

So the design is mostly about **where reading happens**: a restriction a local clone holds is no restriction.

## 4. The model

For a person `P` in project `X`, an entity `E` is **visible** when all three hold:

1. **Scope**: `E` belongs to `X`, or to another project and is directly linked to an entity of `X` that `P` may see.
2. **Clearance**: `E`'s classification is at or below `P`'s clearance, or `P` holds an **elevation** on `E` (§4.3).
3. **Not hidden by an admin decision** (none exists today; kept for a later need).

The Admin passes 1 to 3 everywhere; a Criterion Admin passes 2 everywhere in their project.

What a visible entity is **listed** under:

- **Mine**: `E` was created by `P`, or names `P` in a field of kind `user` or `user-list` (Assignee, Curator, Owner,
  whichever the module declares: the kernel names no module, INV-30), **plus** every visible entity directly linked
  to one of those (answer 1).
- **Asked for**: any other visible entity, returned only by a query (`find`, `view <ID>`, a filter).

An entity that is not visible is **absent**: never listed, never returned, never counted (answer 2).

### 4.1 Classification

- A kernel field `Classification` on every entity type, with the deployment's levels (default `Public`, `Internal`,
  `Confidential`, `Restricted`, lowest first), and a project default for an entity that does not say.
- A module that classifies its own content (the knowledge-base module) keeps its rules; an entity's own field is the
  one visibility reads.
- Raising an entity's classification is a journaled change like any other; lowering it is a decision a Criterion
  Admin or the Admin approves (a gate, design `25`).

### 4.2 Clearance

A person's clearance is catalyst-users': a grant `clear:<Level>` on the catalyst client, given by groups like every
other grant, carried in the token and the per-machine snapshot (design `29`). No grant means the lowest level.

### 4.3 Elevation

An elevation raises one person's clearance for one entity, which must be assigned to them (the request's rule):

```json
{
  "userid": "Ab3xR9pQ",
  "entity": "REQ-000042-Cd4yS0tU",
  "up_to": "Confidential",
  "granted_by": "yCNjAMXO",
  "granted": "2026-10-25T10:00:00Z",
  "expires": null
}
```

- Kept in `IAM/elevations.jsonl`, appended and signed, never rewritten (like the signers ledger, L7).
- **The Admin** grants any; **a Criterion Admin** grants in their project; **an entity's owner** may request one,
  and it takes effect only once a Criterion Admin or the Admin approves it (an approval gate, design `25`).
- Withdrawn by a later line; it ends, too, when the entity is no longer assigned to the person.

## 5. Where reading happens: the server is the boundary

A clone cannot hide what it holds, so:

- **Admins and Criterion Admins** keep full clones, as today.
- **Everyone else reads and writes through `catalyst serve`**, which answers each request as the identity in its token
  sees it (§4). They hold no clone of the criterion. Their CLI, agent and UI are clients of the server.
- **Every answer is filtered**, not only entity views: `list`, `view`, `find`, `graph`, `impact`, `backlog`, `inbox`,
  the indexes (an index row names a title), the journal and history (they hold content), `check`'s findings, and the
  reference fields of a visible entity (a link to an absent entity is left out, its ID included).
- **Writes** through the server are checked the same way: a person cannot cite, edit or link what they cannot see.

## 6. What a UI shows

- **My work**, the landing view: Mine (§4), grouped by status, each with its classification; one seen through an
  elevation is marked as such.
- **Find**: a query over what the person may see, returning nothing else.
- **Linked from other projects**: the foreign entities linked to what the person sees, each with its project.
- **Team** and the admin views: for admins only.

## 7. Phases

1. **Classification and clearance**: the kernel field and its levels, `clear:<Level>` grants, `check` and `view`
   aware of them (a person's own CLI already filters what it shows, as a convenience).
2. **The server as the boundary**: every read of `catalyst serve` filtered (§5); a non-admin's CLI and UI work
   through it; `share join` refused to a non-admin.
3. **Elevations**: the ledger, granting, the owner's request through a gate.
4. **Across projects**: foreign entities linked into a project (workspaces), filtered the same way.

Each phase is a kernel release; phase 1 changes the frozen prose surface (a visibility invariant), which needs an
ADR lifting the freeze for it (ADR-017).

## 8. Still to decide

1. **Default classification** of a project, and of the entities that exist before phase 1 (proposed: `Internal`).
2. **Elevations expire?** (proposed: optional, set by whoever grants it).
3. **A non-admin's offline work**: none, since they hold no clone (proposed), or a filtered export they cannot
   push from.
4. **Rules and domains**: always visible to everyone in the project (proposed), or classified like entities.
