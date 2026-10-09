# Access Control: Roles, Rights, and Automatic Write Authorization

A reference document, deployed verbatim to `.criterion/ACCESS-CONTROL.md`
on first instantiation and refreshed on `/sync-framework` whenever this
kernel version changes it (`INSTANTIATION-GUIDE.md` §1 step 8,
`SYNCHRONIZE.md` item 5) — same treatment as `CODE-OF-CONDUCT.md`/
`Rules-of-Rules.md`. It explains mechanics that already live in
`INVARIANTS.md`, `rules-of-rules.template.md`, and `IAM/roles/roles.json`;
those remain the source of truth. Written because no single place
previously laid out the full read/write picture per role, or answered
"when can the agent write without asking, and signed as whom", and what
actually controls a shared deployment.

## 1. Read is universal. Write is advisory, with two genuinely enforced exceptions.

Catalyst has **no read restriction of any kind, for any role.** Nothing in
`INVARIANTS.md`, `Rules-of-Rules.md`, or any command spec gates a read by
who's asking — every user, and the agent itself, can read every file in a
deployment. This isn't an oversight; it follows directly from `rr-META-011`'s
premise ("catalyst has no way to verify who is actually typing") — a system
that can't verify identity has no basis for a read *block* either, only for
advisory notes on writes it can at least attribute after the fact via
`Signed-off-by`.

**Write is role-scoped, but almost entirely advisory** (INV-25): acting
outside your role's typical actions never blocks the write — it proceeds,
noted rather than gated. Two things are hard exceptions, enforced regardless
of role or identity:

- **INV-16** — a write that would leave zero active users in
  `IAM/users/users.json` is refused outright (`/user-remove`'s last-user
  case).
- **INV-21 / `rr-META-016`** — resolving a `RECON-` reconciliation case is
  gated by the actor's `reconciliation` field (`full`/`propose`/`none`) in
  `IAM/roles/roles.json`. This is the *one* place role genuinely determines
  whether a write is allowed at all, not just whether it's noted.

Both are enforced by the agent, which trusts the self-declared signer. In a
shared deployment (`rr-META-013`), the gates that do not depend on the
agent's good faith are the hosting service's: who may merge into the
shared branch, pull-request review, and the required `catalyst` check,
which `catalyst criterion protect` turns on (§4).

## 2. Per-role rights

| Role | Read | Write (advisory — proceeds either way, per INV-25) | Reconciliation (`/reconcile`, enforced) |
|---|---|---|---|
| Product Owner | everything | create the active module's planning and new-work artifacts, approve/prioritize new work | `propose` |
| Scrum Master / Delivery Lead | everything | review the active module's open work, `/status` | `propose` |
| Tech Lead / Architect | everything | approve rule changes and new domains, vet a development artifact's rule target(s) | `full` |
| Developer | everything | create the active module's development artifacts (implementation-driven), implement them, `/status` on tasks/stories | `propose` |
| QA / Tester | everything | report defects through the active module's development artifacts, verify a rule's verification coverage, `/status` on verification items | `propose` |
| Stakeholder | everything | propose ideas and planning items to the active module | `none` |
| Release Manager | everything | `/sync-framework`, `/catalyzer`, cutting releases | `full` |
| Admin | everything | `/user-add`, `/user-remove`, `/user-modify`, `/user-assign-role`, `/user-list`, `/role-add`, `/role-modify`, `/freeze`, `/criterion create`, `/reconcile` | `full` |

The "Write" column is each role's *typical* scope (`IAM/roles/roles.json`'s
`actions` field) — a signal for what to expect and note on mismatch, not an
enforced boundary. Only the "Reconciliation" column is a real gate. The
active process module names its own commands for these typical actions in
its documentation; a deployment may list them in `roles.json` via
`/role-modify`.

Role does not scope what `/criterion push` carries: every contributor's
push holds their whole change, and the pull request is where it is
reviewed.

## 3. What "advisory" actually means, concretely

Per `rr-META-011`'s steps (mirrored in `CODE-OF-CONDUCT.md` §2):

1. Resolve who's signing — the identity already established this session, or
   ask if none has been (this one question is information-gathering, not
   authorization — INV-25 doesn't touch it).
2. If that name isn't in `IAM/users/users.json`, proceed anyway, noting it.
3. If their role doesn't cover the action, proceed anyway, noting it.
4. Fill `Signed-off-by` with the name (carrying any note from 2–3) and write.

No step here ever produces a confirmation prompt or a refusal — that's what
changed under INV-25. The note itself (not a block) is the accountability
mechanism: a mismatch is visible in the artifact and in the journal entry
that records the write, same principle `rr-META-016` gives reconciliation's
`Resolver` field.

## 4. Identity and the shared deployment's real controls

The `*.catalyst` pointer names no human signer that anything relies on.
`created_by` (set by the pre-0.39.0 `/criterion create`) is informational;
`criterion_branch` names the shared branch everyone lands on, not a person.
**`agent`/`chatAgents`** are a different axis entirely — which AI tool runs
the deployment. Signing identity is session-resolved per §3.

In a shared deployment (`rr-META-013`):

- **Registration comes first.** A contributor is registered with
  `/user-add` (which draws their `userid`) before signing anything; the
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
- **The AI never applies a merge.** A conflict stops `/criterion push`; a
  resolution the agent proposes waits as a `RECON-` case, and resolving it
  stays role-gated (§1).

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
- Write: advisory by default (INV-25) — proceeds and notes, never asks or
  blocks — except reconciliation resolution (INV-21) and the INV-16
  active-user floor, which the agent enforces.
- Shared deployments: branch protection, pull-request review and the
  required `catalyst` check are the controls that do not rely on the agent.
- Signing identity: session-resolved once, reused thereafter; asked when
  more than one active user could be signing.
