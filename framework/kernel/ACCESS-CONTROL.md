# Access Control: Roles, Rights, and Automatic Write Authorization

A reference document, deployed verbatim to `.criterion/ACCESS-CONTROL.md`
on first instantiation and refreshed on `/sync-framework` whenever this
kernel version changes it (`catalyst init` in `CLI.md`,
`SYNCHRONIZE.md` item 5) — same treatment as `CODE-OF-CONDUCT.md`/
`Rules-of-Rules.md`. It explains mechanics that already live in
`INVARIANTS.md`, `rules-of-rules.template.md`, and `IAM/roles/roles.json`;
those remain the source of truth. Written because no single place
previously laid out the full read/write picture per role, or answered
"when can the agent write without asking, and signed as whom", and what
actually controls a shared deployment.

## 1. Read is universal. Write is granted by role.

Catalyst has **no read restriction of any kind, for any role.** Nothing in
`INVARIANTS.md`, `Rules-of-Rules.md`, or any command spec gates a read by
who's asking — every user, and the agent itself, can read every file in a
deployment. This isn't an oversight; it follows directly from `rr-META-011`'s
premise ("catalyst has no way to verify who is actually typing") — a system
that can't verify identity has no basis for a read *block*. Writes are
different: each is signed (`Signed-off-by`, the journal), so the signer's
roles decide which commands it may run.

**Write is role-scoped and enforced** (owner decision D5, INV-16): a
writing verb refuses a signer none of whose roles grants the command its
change is for — a `/command` among the role's `actions`, `*`, or the
`Admin` role — and a deactivated signer. `catalyst.toml` `role_check =
"warn"` makes it a warning. Three more checks apply on top:

- **INV-16** — a write that would leave zero active users in
  `IAM/users/users.json` is refused outright (`/user remove`'s last-user
  case).
- **INV-21 / `rr-META-016`** — resolving a `RECON-` reconciliation case is
  gated by the actor's `reconciliation` field (`full`/`propose`/`none`) in
  `IAM/roles/roles.json`. Role genuinely determines whether this write is
  allowed at all, not just whether it's noted.
- **Approval gates** (`rr-META-011`, opt-in) — when a deployment declares
  them in `IAM/gates.json`, `catalyst status set` refuses to move an entity
  into a gated state, and `catalyst check` errors on a gated rule's text,
  until the current version has the gate's approvals (`catalyst approve`)
  from users holding its role, never its author; `--force` does not pass a
  gate. Without the file there is no gate.

All three are enforced by the CLI and the agent, which trust the
self-declared signer. In a
shared deployment (`rr-META-013`), the gates that do not depend on the
agent's good faith are the hosting service's: who may merge into the
shared branch, pull-request review, and the required `catalyst` check,
which `catalyst criterion protect` turns on (§4).

## 2. Per-role rights

| Role | Read | Write (the `/commands` its `actions` grant; the rest describes) | Reconciliation (`/reconcile`, enforced) |
|---|---|---|---|
| Product Owner | everything | create the active module's planning and new-work artifacts, approve/prioritize new work, `/create`, `/status`, `/adopt`, `/journal` | `propose` |
| Scrum Master / Delivery Lead | everything | review the active module's open work, `/status`, `/journal` | `propose` |
| Tech Lead / Architect | everything | approve rule changes and new domains, vet a development artifact's rule target(s), `/create`, `/status`, `/adopt`, `/journal`, `/freeze`, `/migrate-definition`, `/run-analysis` | `full` |
| Developer | everything | create the active module's development artifacts (implementation-driven), implement the active module's development artifacts, `/create`, `/status`, `/adopt`, `/journal`, `/run-analysis` | `propose` |
| QA / Tester | everything | report defects through the active module's development artifacts, verify a rule's verification coverage, `/create`, `/status`, `/adopt`, `/journal` | `propose` |
| Stakeholder | everything | propose ideas and planning items to the active module | `none` |
| Release Manager | everything | `/sync-framework`, `/share`, cutting releases | `full` |
| Admin | everything | `*` | `full` |

The "Write" column is each role's `actions` field in `IAM/roles/roles.json`.
Its entries that start with `/` are grants: the writing verbs refuse a
command no role of the signer grants (D5). The descriptive entries grant
nothing until a deployment adds the `/commands` they mean (`catalyst role
modify <role> --action /<command>`); the `Admin` role grants everything. The
active process module names its own commands in its documentation.

Role does not scope what `/share push` carries: every contributor's
push holds their whole change, and the pull request is where it is
reviewed.

## 3. What the check does, concretely

Per `rr-META-011` (mirrored in `CODE-OF-CONDUCT.md` §2):

1. Resolve who's signing — the identity already established this session, or
   ask if none has been (`--as`).
2. A name not in `IAM/users/users.json`, or a deactivated user, is refused.
3. A command none of their roles grants is refused, with the command that
   would grant it (`catalyst role modify`, `catalyst user assign-role`).
   With `role_check = "warn"` in `catalyst.toml` it is a warning and the
   write proceeds. A tier named as the command (`chore`, `fix`, `feature`)
   and a command the deployment does not have are not checked.
4. Fill `Signed-off-by` with the name and write.

The agent never answers a refusal by switching signer: who may do what is
the people's decision (L4).

## 4. Identity and the shared deployment's real controls

`catalyst.toml` names no human signer that anything relies on.
`created_by` (set at install) is informational;
`criterion_branch` names the shared branch everyone lands on, not a person.
**`agent`/`chatAgents`** are a different axis entirely — which AI tool runs
the deployment. Signing identity is session-resolved per §3.

In a shared deployment (`rr-META-013`):

- **Registration comes first.** A contributor is registered with
  `/user add` (which draws their `userid`) before signing anything; the
  registration lands through a pull request like any other change. Their
  `userid` suffixes every ID they allocate, which is what keeps IDs unique
  across contributors (`Rules-of-Rules.md` §6).
- **Identity is still self-declared.** `--as <user>` and `Signed-off-by`
  record who the operator says they are; catalyst cannot verify it, and a
  signature already written is never rewritten.
- **The real controls are the host's.** Who can push to the criterion
  repository, who may merge a pull request into the shared branch, and
  whether review and the `catalyst` check are required. `catalyst criterion
  protect --yes` (GitHub) requires pull requests and the check, and forbids
  force-pushes and deletion of the branch. Without it, anyone with write
  access can push to the shared branch directly, and every gate in this
  document is agent courtesy only.
- **A served criterion verifies identity.** Shared through `catalyst serve`
  (`share = "serve"`), every request carries the user's token, and the
  server refuses a journal entry signed by anyone else and a `RECON-`
  decision beyond the signer's `reconciliation` level. Who holds a token is
  the server host's control (`catalyst serve token`).
- **The AI never applies a merge.** A conflict stops `/share push`; a
  resolution the agent proposes waits as a `RECON-` case, and resolving it
  stays role-gated (§1, `catalyst reconcile`).

## 5. When may the agent sign without asking?

Given writes proceed without asking (INV-25), *which* identity does the
agent sign as, without asking that either?

**Safe without asking:**

- **Exactly one active user in `IAM/users/users.json`.** Nobody else can
  plausibly be signing; the CLI signs as them without `--as`.
- **An identity already resolved this session.** Per §3 step 1 — once
  established, INV-25 means never re-asking or re-confirming it for
  subsequent writes in the same session.

**Otherwise ask once** and reuse the answer for the session. With several
active users the CLI refuses to guess (`--as` required), and neither
`created_by` nor git configuration stands in for the answer.

## 6. Summary

- Read: unrestricted, always, for everyone.
- Write: granted by role (D5) — a writing verb refuses a command none of the
  signer's roles grants — plus reconciliation resolution (INV-21), the
  approval gates a deployment declares (`IAM/gates.json`) and the INV-16
  active-user floor.
- Shared deployments: branch protection, pull-request review and the
  required `catalyst` check are the controls that do not rely on the agent.
- Signing identity: session-resolved once, reused thereafter; asked when
  more than one active user could be signing.
