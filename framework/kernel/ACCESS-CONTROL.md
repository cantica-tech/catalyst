# Access Control: Roles, Rights, and Automatic Write Authorization

A reference document, deployed verbatim to `.criterion/ACCESS-CONTROL.md`
on first instantiation and refreshed on `/sync-framework` whenever this
kernel version changes it (`catalyst init` in `CLI.md`,
`SYNCHRONIZE.md` item 5) — same treatment as `CODE-OF-CONDUCT.md`/
`Rules-of-Rules.md`. It explains mechanics that already live in
`INVARIANTS.md`, `rules-of-rules.template.md`, and the grants catalyst-users
gives each person (`IAM/identity.json` points at it); those remain the
source of truth. Written because no single place previously laid out the
full read/write picture per role, or answered
"when can the agent write without asking, and signed as whom", and what
actually controls a shared deployment.

## 1. Read is universal. Write is granted by the provider.

Catalyst has **no read restriction of any kind, for any role.** Nothing in
`INVARIANTS.md`, `Rules-of-Rules.md`, or any command spec gates a read by
who's asking — every user, and the agent itself, can read every file in a
deployment: the files are on the reader's disk, and a read block there
would be a courtesy, not a control. Writes are different: each is signed
(`Signed-off-by`, the journal) by the identity catalyst-users verifies, so
that identity's grants decide which commands it may run.

**Write is grant-scoped and enforced** (owner decision D5, INV-16): a
writing verb refuses a signer none of whose grants allows the command its
change is for — `cmd:<command>` or `cmd:*`, which the provider composes
into roles and groups; a role's name grants nothing — and a disabled
signer. `catalyst.toml` `role_check = "warn"` makes it a warning. Two more
checks apply on top:

- **INV-21 / `rr-META-016`** — resolving a `RECON-` reconciliation case is
  gated by the actor's reconciliation level (`full`/`propose`/`none`): the
  highest `reconcile:<level>` grant catalyst-users gives them. It genuinely
  determines whether this write is allowed at all, not just whether it's
  noted.
- **Approval gates** (`rr-META-011`, opt-in) — when a deployment declares
  them in `IAM/gates.json`, `catalyst status set` refuses to move an entity
  into a gated state, and `catalyst check` errors on a gated rule's text,
  until the current version has the gate's approvals (`catalyst approve`)
  from users holding its role, never its author; `--force` does not pass a
  gate. Without the file there is no gate.

All are enforced by the CLI where the change is made, against the
identity catalyst-users verifies there. In a shared deployment
(`rr-META-013`), the gates that do not depend on the
agent's good faith are the hosting service's: who may merge into the
shared branch, pull-request review, and the required `catalyst` check,
which `catalyst criterion protect` turns on (§4).

## 2. The default roles and their grants

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

The table is the kernel's roles template (`templates/roles.template.json`),
which `catalyst-users roles provision` writes into the provider once: each
role becomes a provider role composed of a `cmd:<command>` grant per
`/command` of its "Write" column (`*` and the `Admin` role: `cmd:*`) and a
`reconcile:<level>` grant for its reconciliation level. The descriptive
entries grant nothing. From then on a role's grants are changed in the
provider, never in the criterion; the deployment's roles template only
names the roles and shapes how they are shown. The active process module
names its own commands in its documentation.

Role does not scope what `/share push` carries: every contributor's
push holds their whole change, and the pull request is where it is
reviewed.

## 3. What the check does, concretely

Per `rr-META-011` (mirrored in `CODE-OF-CONDUCT.md` §2):

1. Resolve who's signing — the identity catalyst-users verifies now: the
   person logged in on this machine (`catalyst identity login`), or, with
   no one logged in, the machine's system account when its settings point
   at the same provider. With neither, nothing is signed.
2. A disabled identity is refused. An identity signing for the first time
   gets its userid and its line in `IAM/signers.jsonl`.
3. A command none of their grants allows is refused, naming the grant that
   would allow it (`cmd:<command>`, given in catalyst-users). With
   `role_check = "warn"` in `catalyst.toml` it is a warning and the write
   proceeds. A tier named as the command (`chore`, `fix`, `feature`) and a
   command the deployment does not have are not checked.
4. Fill `Signed-off-by` with the name and write.

The agent never answers a refusal by switching signer: who may do what is
the people's decision (L4).

## 4. Identity and the shared deployment's real controls

`catalyst.toml` names no human signer that anything relies on.
`created_by` (set at install) is informational;
`criterion_branch` names the shared branch everyone lands on, not a person.
**`agent`/`chatAgents`** are a different axis entirely — which AI tool runs
the deployment. The signing identity is verified at each signature per §3.

In a shared deployment (`rr-META-013`):

- **People are catalyst-users'.** A contributor is added, disabled and
  granted in the provider catalyst-users fronts (`catalyst-users users …`),
  never in the criterion; `catalyst user` and `catalyst role` refuse.
- **The provider verifies who signs.** The signer is the identity logged in
  with `catalyst identity login`, confirmed by the provider at each
  signature, or, with no one logged in, the machine's system account;
  `--as` names only that identity, and with no verified identity nothing is
  signed. Each identity's first signature draws its `userid` and adds its
  line to `IAM/signers.jsonl`, append-only, so every signature stays
  resolvable (L7); that line lands through a pull request like any other
  change. The `userid` suffixes every ID the identity allocates, which is
  what keeps IDs unique across contributors (`Rules-of-Rules.md` §6).
- **A signature is verified where it is made, not where it lands.** A
  journal entry pushed to a git remote carries the signer it was made by;
  nothing on the remote checks it again, and a signature already written
  is never rewritten.
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
  decision beyond the signer's reconciliation level. Who holds a token is
  the server host's control (`catalyst serve token`); started with
  `--identity-issuer`, the server also accepts the provider's tokens, by
  introspection, and lets a push add ledger lines for its own identity only.
- **The AI never applies a merge.** A conflict stops `/share push`; a
  resolution the agent proposes waits as a `RECON-` case, and resolving it
  stays gated by the reconciliation level (§1, `catalyst reconcile`).

## 5. When may the agent sign without asking?

Given writes proceed without asking (INV-25), *which* identity does the
agent sign as, without asking that either?

**Always the verified identity.** The agent signs as the person logged in
on this machine, or, with no one logged in, as the machine's system
account, which catalyst names on standard error. It never chooses another:
`--as` names only the verified identity, and neither `created_by` nor git
configuration stands in for it.

**When no identity is verified**, nothing is signed: ask the person to log
in (`catalyst identity login`), then carry on as them for the session.

## 6. Summary

- Read: unrestricted, always, for everyone.
- Write: granted by the provider (D5) — a writing verb refuses a command
  none of the signer's grants allows — plus reconciliation resolution
  (INV-21) and the approval gates a deployment declares (`IAM/gates.json`).
- Shared deployments: branch protection, pull-request review and the
  required `catalyst` check are the controls that do not rely on the agent.
- Signing identity: the one catalyst-users verifies at each signature; with
  none, nothing is signed.
