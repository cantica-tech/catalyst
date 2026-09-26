# Access Control: Roles, Rights, and Automatic Write Authorization

A reference document, deployed verbatim to `.criterion/ACCESS-CONTROL.md`
on first instantiation and refreshed on `/sync-framework` whenever this
kernel version changes it (`INSTANTIATION-GUIDE.md` §1 step 8,
`SYNCHRONIZE.md` item 5) — same treatment as `CODE-OF-CONDUCT.md`/
`Rules-of-Rules.md`. It explains mechanics that already live in
`INVARIANTS.md`, `rules-of-rules.template.md`, and `IAM/roles/roles.json`;
those remain the source of truth. Written because no single place
previously laid out the full read/write picture per role, or answered
"when can the agent write without asking, signed as the identity the
`*.catalyst` pointer names."

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
| Admin | everything | `/user-add`, `/user-remove`, `/user-modify`, `/user-assign-role`, `/user-list`, `/role-add`, `/role-modify`, `/freeze`, `/criterion push` (unrestricted), `/reconcile` | `full` |

The "Write" column is each role's *typical* scope (`IAM/roles/roles.json`'s
`actions` field) — a signal for what to expect and note on mismatch, not an
enforced boundary. Only the "Reconciliation" column is a real gate. The
active process module names its own commands for these typical actions in
its documentation; a deployment may list them in `roles.json` via
`/role-modify`.

**A third, real (non-advisory, non-refusing) role effect** exists alongside
these: **signed-object push scoping** (`rr-META-013`, "Signed-object
scoping"). A non-`Admin` contributor's `/criterion push` only ever pushes
artifact files whose `Signed-off-by` names them — a file someone else signed
is silently excluded from *that push* (reported, not hidden). `Admin` is
exempt and pushes everything. This doesn't refuse the push or gate a specific
write; it changes *how much* one push contains.

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

## 4. Identity: what the `*.catalyst` pointer actually names

The pointer (`DEPLOYMENT.md` in the framework's own terms) carries
exactly **one** human-identity field:
**`created_by`** — and only when the deployment is `repoed: true`. It's set
once, at `/criterion create`'s first call, to whoever ran it
(`rr-META-013`). `criterion_branch` also encodes identity indirectly for a
repoed deployment (a contributor branch is `<branch-safe-name>.criterion`),
but that's *this local checkout's* pushing identity, not necessarily the
identity signing every artifact in it.

**`agent`/`chatAgents` are a different axis entirely** — which AI tool runs
the deployment (`"claude-code"`, a Copilot binding, etc.), resolved by
`agent-launch.ts`/`agent-bridge.ts`. Neither field names a human signer.
"The user detailed in the `*.catalyst` file," read literally, can only mean
`created_by` — a non-repoed deployment's pointer names no user at all, and
signing identity there is purely session-resolved per §3 above.

## 5. When should the agent auto-write signed as `created_by`?

This is the practical question INV-25 raises once identity enters the
picture: given writes proceed without asking, *which* identity does the
agent sign as, without asking that either?

**Safe to default to `created_by` without asking:**
- **Not repoed at all.** There's no contributor model yet — whichever name
  the session already resolved (or `created_by` once one exists) is the only
  plausible signer.
- **Single-maintainer mode** (`criterion_branch` is `criterion` itself).
  `rr-META-013` already refuses this mode's own push path to anyone but
  `created_by` — the deployment's own design assumes one operator. Defaulting
  every write's `Signed-off-by` to them is consistent with a mode that's
  already gated that way.
- **Exactly one active user in `IAM/users/users.json`.** Regardless of
  `created_by`, if there's only one person who *can* plausibly be signing,
  ambiguity doesn't exist.
- **An identity already resolved this session.** Per §3 step 1 — once
  established, INV-25 means never re-asking or re-confirming it for
  subsequent writes in the same session.

**Not safe — resolve identity properly instead of defaulting to
`created_by`:**
- **A real multi-contributor repoed deployment** (`criterion_branch` is
  `<name>.criterion`, not `criterion`) **with more than one active user.**
  `created_by` is whoever *created the repo link*, not necessarily who's
  operating this checkout right now — signing everything as them would
  misattribute a genuine contributor's work. Derive identity from
  `criterion_branch` (strip `.criterion`, reverse the branch-safe transform
  as far as it goes) or ask once and cache it for the session, same as any
  non-repoed deployment's first write.
- **A `git_username` has already been recorded for the actual operator**
  (`rr-META-013`'s identity migration) that differs from `created_by`. Once
  migrated, `git_username` is the correct signer for that person going
  forward — `created_by` on the pointer doesn't update to track it.

In short: `created_by` is a reasonable **zero-configuration fallback** for
the common solo or single-maintainer case, never a substitute for an
already-established or derivable per-contributor identity in a real
multi-user deployment.

## 6. Summary

- Read: unrestricted, always, for everyone.
- Write: advisory by default (INV-25) — proceeds and notes, never asks or
  blocks — except reconciliation resolution (INV-21) and the INV-16
  active-user floor, which are real gates.
- Signing identity: session-resolved once, reused thereafter; `created_by`
  is a safe default only when the deployment has at most one plausible
  signer (unrepoed, single-maintainer, or a single active user) — otherwise
  resolve the actual contributor rather than defaulting to whoever created
  the repo link.
