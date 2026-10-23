# Results — 2026-10-23: catalyst-users, stage one of users and groups out of criteria

The owner asked for Python libraries for user accounts, roles, nested groups, authentication and signed tokens:
simple, very secure, standalone or enterprise. The research led to a decision for catalyst: users and groups move out
of the criterion to Keycloak, used only through standard OIDC, while catalyst keeps its role policy
(`IAM/roles/roles.json`). Stage one is a separate project, governed by catalyst from its first line.

| Repository | What's in it |
|---|---|
| [`cantica-tech/catalyst-users`](https://github.com/cantica-tech/catalyst-users) (public) | The library, its CLI, its FastAPI integration, a pinned local Keycloak, CI |
| `cantica-tech/catalyst-users-kb` (private) | Its knowledge base `KB-000001`, classified Internal: the identity research and the Keycloak decision |
| `cantica-tech/catalyst-users-criterion`, `cantica-tech/catalyst-users-kb-criterion` (private) | The two criteria, shared on branch `criterion` |

## What catalyst-users does

- **A standard-library-only core**, so that catalyst's single-file CLI can carry it in stage two (a test imports it
  with no site-packages):
  - **Login** with the OAuth device flow (open a link, enter a code; Keycloak asks for consent).
  - **Tokens** stored owner-only (`0700`/`0600`, atomic writes), refreshed under 30 seconds of life, revoked on
    logout.
  - **Transport**: HTTPS except to loopback, no redirect followed, a timeout everywhere.
- **The directory in Keycloak**: users, nested groups (a member of `/a/b` counts as a member of `/a`, and roles are
  inherited down the tree), realm roles. Changes are made with the caller's own token, never an admin secret. A user
  is disabled, never deleted, so past signatures stay resolvable (as L7 asks).
- **A signer** is the issuer plus the subject, with a snapshot of username and name: never the username.
- **The `catalyst-users` CLI**: `login`, `whoami`, `token`, `logout`, and `users`, `groups` and `roles`.
- **FastAPI**: `Depends(auth)`, `auth.require_roles(...)`, `auth.require_groups(...)`. A token is accepted only on
  active introspection with this issuer and audience, cached at most 30 seconds and never past its expiry. Answers
  are 401, 403 or 503, and never say more.

## Governance

- Installed with `catalyst init` (software-engineering 3.4.1), with knowledge-base 0.3.1 installed beside it at the
  owner's choice.
- Greenfield path: seven domains, then 19 rules (`env-` toolchain, `id-` identity), all working.
- `REQ-000001` (toolchain and Keycloak), `REQ-000002` (library, CLI, FastAPI), `REQ-000003` (CI): Completed, with
  eight steps and seven tests.
- The knowledge base: `KB-000001` Active, its source, a workflow governing builds, and a gate asking two curators to
  publish a build classified Confidential or above.
- `ADR-000001`: the shared criteria stay without branch protection. GitHub refuses it on private repositories on the
  organisation's free plan, and the owner chose not to upgrade.

## Checks

- 87 tests pass against Keycloak; without Keycloak, 81 pass and 6 are skipped. They cover a real device login
  approved through Keycloak's own pages, refresh and revocation, nested-group role inheritance, directory changes
  refused to a non-admin, and FastAPI decisions on real tokens.
- CI runs on every push and pull request: Ruff and unit tests on Python 3.11 and 3.13, the Keycloak integration, and
  `catalyst trace`. The last run passed all four jobs.
- `catalyst check` and `validate` pass in both deployments.

## Problems along the way

- **Keycloak refused the realm file**: its import rejects unknown keys (a `_comment`).
- **Python's cookie jar keeps `Secure` cookies off plain HTTP**, even on loopback, which browsers allow; the device
  login test helper needs a policy for it.
- **CI on Python 3.13 failed once.** `uv run` rebuilt the venv with `.python-version`'s 3.11 and without the fastapi
  extra. Fixed with `UV_PYTHON` per matrix entry and fastapi in the dev group.
- **`dist/catalyst.pyz` in this repository is stale** (0.46.0): the installs ran catalyst from source.
- **Sharing comes first.** CI's `catalyst trace` reads the shared criterion, so its journal entries must be merged
  before the code that cites them is pushed.

## What's left

- **Stage two**: integrate catalyst-users into catalyst. This means:
  - an identity provider interface (`local` or `oidc`);
  - user records moved out of `IAM/users/users.json`;
  - signer snapshots (issuer and subject) in the journal and in gate records;
  - catalyst's role names mapped to Keycloak realm roles.
- **Key-backed signatures for approvals** (`gitsign` or SSH commit signing): a separate decision.
- **Releases**: `main` and `release` of catalyst-users trail `development` until its first release.
- **The knowledge base** has no build yet (`/kb-build`).
- **`dist/catalyst.pyz`** should be rebuilt (`task build:cli`).
