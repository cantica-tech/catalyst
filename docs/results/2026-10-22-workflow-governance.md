# Results — 2026-10-22: workflow governance

The owner asked whether catalyst can govern workflows. The honest answer was: it governs how work is defined,
approved and recorded, but not as a workflow engine. Three gaps stood out: no condition on a field's value, no due
dates, and a `WORKFLOW-` that was only a document. The owner asked to close them, needing them for knowledge bases.

| Release | What's in it |
|---|---|
| Kernel [0.104.0](https://github.com/cantica-tech/catalyst/releases/tag/0.104.0) | Workflow governance (REQ-000084); a `catalyst migrate` fix (BUG-000028) |
| Kernel [0.104.1](https://github.com/cantica-tech/catalyst/releases/tag/0.104.1) | CI drives the knowledge-base module 0.3.0 |
| The module [`knowledge-base` 0.3.0](https://github.com/cantica-tech/catalyst-knowledge-base/releases/tag/0.3.0) | Knowledge bases governed with it |
| The module [`knowledge-base` 0.3.1](https://github.com/cantica-tech/catalyst-knowledge-base/releases/tag/0.3.1) | `docs/best-practices.md`: current practice for AI knowledge bases, with its sources, and building one from a catalyst criterion |
| The UI 0.59.0 (its own repository) | The inbox shows overdue entities; its types follow 0.104.1 |

## What catalyst does now

- **Conditions on field values.** One line, the same everywhere: `Classification at least Confidential`, `Kind in
  Project, Reflective`, `Owner is set`. Ordered by the field's enum values (so classifications compare), else as
  numbers or dates.
  - A module's guard `holds: <condition>` must hold to enter its state.
  - A gate's `when` makes it apply only where the condition holds: "a confidential build needs two approvals", a
    public one none.
  - `catalyst check` refuses a condition naming a field or a value the type does not have.
- **Due dates that escalate.** A type declares `due` (`Due`, or `Checked + 30 days`). An open entity past it is
  `overdue`: `catalyst inbox` lists it with the role it escalates to, and `catalyst check` warns.
- **A `WORKFLOW-` that governs.** One that names a type (`Governs`) and is `Active` is enforced: its Transitions table
  (`From`, `To`, `Role`, `When`) is every move that type may make. `catalyst status set` refuses any other move, a
  signer without the row's role (an `Admin` holds every role), and a row whose condition fails; `--force` does not
  pass it, like a gate. `catalyst view` (and the Studio's entity page) lists only its moves. `catalyst check`
  reports two workflows governing one type and anything a workflow names wrongly.

Nothing existing changed behaviour: no workflow governs a type until one says so, and no type is due until its
module says so. Catalyst's own deployment took the new workflow template with `catalyst migrate --apply`, its first
real use.

## The knowledge-base module, governed (0.3.0)

- A source falls due at its `Next check` (its last check plus its knowledge base's `Freshness`); past it, it waits in
  the inbox as overdue.
- A knowledge base is `Active` only with its curator; a build is `Published` only once classified.
- `/kb-setup` offers, with the owner's assent, a workflow governing builds (a curator publishes up to `Internal`, an
  `Admin` above) and a gate asking two curators to publish a build classified `Confidential` or above (rr-KB-007,
  `GUIDE.md` "Governance").

## Checks

762 kernel tests pass, 7 new for workflow governance; the second-module test drives the knowledge-base module 0.3.0,
an overdue source included. ruff, pyright (no new warning), purity, frozen surface, token budgets and the generated
documents pass. The UI's checks were run from a clean build. Every pull request merged only after every check passed.

## Problems along the way

- **A bug in `catalyst migrate` (BUG-000028):** found syncing catalyst itself to 0.104.0. It left out the judgment
  steps of a migration starting before the deployment's previous kernel (0.104.0's starts at 0.103.0; the deployment
  was at 0.103.1). Fixed in the same release, with a test.
- **A journaling slip:** my own loop recording three steps at once misread its arguments, so one step's files went
  unrecorded until `check` flagged the commit; they were recorded against the right step.
- **A release script run from the wrong directory** (the round before): it failed at its first step and pushed
  nothing; it now always starts in catalyst's checkout.

## What isn't covered

Catalyst still does not *run* workflows: there are no timers that act, no automatic assignment, no notifications
beyond the inbox and the Studio's unread count, and a condition compares a field with a value, not two fields. A
condition on a proposal is checked against the entity as it stands, not the proposed version.

## What's left

**Your decisions:**

- **A first knowledge base:** a reflective one of the Cantica ecosystem would exercise the whole module, governance
  included: its classification, where its repository and builds live, and whether to take the offered workflow and
  gate.
- **The embedding model:** which local model, and which hosted service (if any) a knowledge base may use up to its
  allowance.
- **The active-status gaps** (`docs/misc/entities-active-statuses.md`): roles, domains, gates and a dropped roadmap
  row have no retired state.
- **This deployment's module templates:** `catalyst migrate --apply --template all`, some, or none.
- **The brand**, and **declaring format 1.0** at the 1.0 release.

**Your time:** the beta trial (RM-026, RM-028, RM-029), and trying the new pieces.

**Waiting on you:** the Marketplace token, the signing credentials, the update feed, trademark counsel, and a public
address for the Linux package.

**Work Claude can do without you:** the two saved notes (`docs/users-registry.md`,
`docs/misc/entities-active-statuses.md`) are journaled but not committed, waiting on your word.

**Blocked on something outside this repository:** module signatures (R4.9 N4) and signed releases (R7) wait on the
signing credentials and the release feed.
