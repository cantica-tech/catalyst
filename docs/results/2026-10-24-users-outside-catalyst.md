# Results — 2026-10-24: users, groups and roles outside catalyst (kernel 0.106.0)

The owner asked to continue design 29 (people are catalyst-users'), which a previous session had left half done and
uncommitted, and decided along the way:

- **H** — with no one logged in, catalyst signs as the machine's system account (the admin catalyst-users' setup
  names), when its settings point at the same provider;
- catalyst's own deployment is the pilot: it moves onto the local Keycloak first;
- a person who signed before keeps their userid (`catalyst identity link`).

| What | Where |
|---|---|
| Kernel 0.106.0: design 29 (REQ-000087), BUG-000029, BUG-000030 | `cantica-tech/catalyst` |
| catalyst-users 0.4.0 vendored (the provider registry, setup's settings, the system account) | `scripts/catalyst/identity/` |
| catalyst's own deployment on the local Keycloak | `~/.catalyst/projects/catalyst/criterion` |

## What catalyst does now

- **A criterion points at catalyst-users.** `IAM/identity.json` names the provider; `catalyst check` reports a
  missing or broken one. `catalyst identity configure --issuer <url>` writes it; `catalyst init` without
  `--identity-issuer` takes the provider this machine's catalyst-users is set up for. The `local` mode, the
  `identity_*` keys of `catalyst.toml` and `provider_role` go.
- **The signer is verified.** The logged-in person, or, with no one logged in, the machine's system account (said on
  standard error); `--as` names only that identity (its username, name or subject).
- **Grants decide.** `cmd:<command>`, `cmd:*` and `reconcile:<level>` from the provider; a role's name grants
  nothing. `catalyst user …` and `catalyst role …` refuse and point to catalyst-users.
- **The ledger keeps userids.** Each identity's first signature appends its line to `IAM/signers.jsonl`;
  `catalyst identity link <retired user>` (or `configure --link`) lets a person who signed before keep their userid,
  once, only for themselves.
- **A read-only snapshot per machine**, with a hash of its content; an edited one is discarded.
- **Display only:** the users, roles and a new groups template; the user and role definitions gain v2.
- **Migration 0.106.0:** the pointer from `catalyst.toml`, `users.json` and `roles.json` retired as `*.retired.json`,
  the roles kept as a display template, the groups templates; judgment: point a `local` deployment at catalyst-users,
  provision its roles, import its people, link userids, the definitions' v2.
- **Fixed on the way:** `catalyst spec` filed a procedure's numbered list under the command its first line named
  (BUG-000029); reading several journal shards, an entry that only creates files overtook an earlier one waiting on
  its own chain, and catalyst's own journal reported 1,472 entries out of time order (BUG-000030).

## The pilot: catalyst's own deployment

- `catalyst identity configure --issuer http://localhost:8080/realms/catalyst --link "Olivier Steck"`: the pointer,
  and the owner's Keycloak account linked to userid `yCNjAMXO`, signed by the system account.
- `catalyst sync apply` (CLI and kernel from the committed tree), `catalyst migrate --apply`, the user and role
  definitions at v2.
- BUG-000030, the first ID made after the move: `BUG-000030-yCNjAMXO`, the same userid as before.
- Not provisioned: catalyst's retired roles, whose actions predate 0.93; the realm holds the kernel's current roles.
- `catalyst check` with the deployed CLI: passes, 12 warnings.

## Checks

- The previous session's work as found: 28 tests failed, 4 errored, the identity suite did not load.
- Final tree: the full suite, ruff check and format, the kernel purity check, the generated documents, the token
  budgets.
- The kernel's prose documents rewritten for design 29 (a subagent, its report reviewed); the laws' wording of L4
  ("verified") and L7 ("the signers ledger is never rewritten") follows design 29 §4.

## What's left

- **The other deployments** (catalyst-users, its knowledge base, the UI project) still sign with their registries:
  each is migrated the same way, a judgment step with the owner.
- **The UI** reads `users.json` and `roles.json` in places, and the `identity` schemas in `spec/` changed: it needs
  its own update before its deployments migrate.
- **Logging in as a person:** so far only the system account has signed; `catalyst identity login` (the device
  flow) is the next thing to try on the pilot.
- **catalyst's retired roles** were not provisioned into the realm: the owner decides whether any of their actions
  should become grants.
- **The local Keycloak is a dev setup** (dev mode, loopback, a local database): fine for one person on this
  machine, not for a team.
