# Results — 2026-10-24: the criterion-admin

The owner asked for a user role, `criterion-admin`, holding every admin right for one criterion only, unlike the
`catalyst-admin`, who administers every criterion and their admins; then that it apply to any IAM provider and be
part of Keycloak onboarding for catalyst and each of its criteria. Decided along the way:

- a criterion's scope is a **group per criterion**, never a grant (a `cmd:` grant in the token would hold in every
  criterion);
- a criterion-admin also **manages their criterion's members**, appointing its other admins, but creates no user,
  group or role.

| What | Where |
|---|---|
| catalyst-users 0.5.0: REQ-000009 (rules `id-DIR-000005`, `id-PROVIDER-000008`), STEP-000014 | `cantica-tech/catalyst-users` |
| Kernel 0.108.0: REQ-000089 (rule `fw-IDENTITY-000011`), STEP-000113; catalyst-users 0.5.0 vendored | `cantica-tech/catalyst`, `cantica-tech/cantica-tech` |
| The live realm: a criterion per deployment, the owner appointed to each | the local Keycloak, realm `catalyst` |
| Kernel 0.109.0: REQ-000090 (`serve --criterion`), REQ-000091 (the Criterion Admin role, migration 0.109.0) | `cantica-tech/catalyst`, `cantica-tech/cantica-tech` |
| catalyst-ui: `spec/` and the desktop app at 0.109.0 (development, no UI release) | `cantica-tech/catalyst-ui` |

## What catalyst-users does now

- **`whoami` reports `administers`**, the criteria someone administers, whatever the provider (Keycloak: the groups
  `/criteria/<name>/admins`; static: the same, from its people).
- **The facade has criteria**: `criteria`, `add_criterion`, `appoint`, `dismiss`, and
  `catalyst-users criteria list | add NAME [--admin USER] | admins NAME | appoint NAME USER | dismiss NAME USER`. A
  provider that cannot do one says so.
- **Keycloak**: a criterion is `/criteria/<name>`; `/criteria/<name>/admins` holds the realm role
  `criterion-admin`. Fine-grained admin permissions (FGAP v2) give those admins the membership of the groups under
  their criterion, and the sight of users, and nothing else.
- **Onboarding**: setup readies the realm (FGAP, the role, `/criteria`; only what is missing), and
  `setup --criterion NAME` (repeatable) adds criteria with the admin appointed. `realm-catalyst.json` and
  `catalyst-roles.json` declare them; `Criterion Admin` is `"scope": "criterion"` and provisioned without a grant.
  `docs/onboarding.md` describes it, including the existing deployments.

## What catalyst does now

- In the deployment whose `project_name` the signer administers, they hold `cmd:*` and `reconcile:full`; anywhere
  else, administering a criterion grants nothing. `catalyst identity whoami` and the snapshot show `administers`.
- It reads `administers` with a default, so the vendored catalyst-users 0.4.1 (which has none) keeps today's
  behaviour until the next release is vendored.

## Found on the way (Keycloak 26.4)

- A Groups permission on a group does **not** reach its subgroups: each criterion's permission names every group
  under it, and `criteria add NAME` again covers groups added since.
- The admin-permissions resource server decides **unanimously**: one Users permission per criterion let each
  criterion's policy veto the others' admins (403 with two criteria). One affirmative Users permission, shared by
  every criterion's admins, fixes it.
- FGAP can be switched on in an existing realm (`adminPermissionsEnabled`).

## Checks

- catalyst-users: 138 unit tests; the 7 onboarding integration tests on a Keycloak of their own (a criterion-admin
  of `greenfield` manages its members and is refused on `other`, on `/catalyst-admins`, and on users, groups and
  roles; their token carries no `cmd:` grant); the other 8 integration tests on an ephemeral Keycloak importing the
  realm file. Ruff clean; pyright not run (not installed here).
- catalyst: 799 tests; ruff clean on the changed files.
- `catalyst check` passes in both deployments.
- The compose Keycloak on port 8080 refuses its documented bootstrap password, so its integration tests cannot run
  there; nothing was run against the `catalyst` realm the deployments sign through.

## How it shipped

- catalyst-users 0.5.0: criterion PR #20, then #13 (main) and #14 (release), every check green, tagged `0.5.0`. The
  owner's pending onboarding work (the guide, its test, the fixtures, the research moved to `docs/development/`)
  shipped with it, at their choice.
- Kernel 0.108.0: another session was releasing 0.107.0 from the same checkout, so the work waited on a branch in a
  worktree (the revert journaled after that session's `catalyst check` caught it) and landed on top of 0.107.0;
  criterion PR #140, then #321 and #322, tagged `0.108.0`; the deployment's CLI built from a clean worktree;
  published to the distribution repository (the module zips repackaged byte-identical).
- The live realm: `catalyst-users setup --force --criterion …` with the machine's unchanged settings; the system
  account now administers catalyst, catalyst-ui, catalyst-users and catalyst-users-kb.

## The follow-up: kernel 0.109.0

The owner asked to continue with what 0.108.0 left.

- **`catalyst serve --criterion <name>`** (REQ-000090): the server records the criterion its database serves, once
  (another name refused, `GET head` reports it), and a push's signer who administers it holds every grant and
  `full` there. The operator names it, never a push: a client's `catalyst.toml` is only its word, and a criterion's
  admin elsewhere could otherwise claim the name.
- **The Criterion Admin, shown** (REQ-000091): the kernel's roles template lists it (it grants nothing by itself);
  `catalyst migrate --apply` adds it to a deployment's roles template once, never again if any version held it.
  catalyst's own deployment is migrated (`TEMPLATE-ROLES-v5`).
- **The display name in Keycloak**: the owner ran `catalyst-users login` and `roles provision`; `criterion-admin`
  carries `catalyst.name` "Criterion Admin" and composes no grant.
- Shipped: criterion PR #142, then #323 and #324 (every check green), tagged `0.109.0`; the distribution repository
  with knowledge-base 0.5.1 (released meanwhile by another session); catalyst-ui at 0.109.0 on development.

## Then: UI 0.64.1, the Marketplace, the local Keycloak tests

The owner chose all three remaining items.

- **catalyst-ui 0.64.1** (a patch: the desktop app ships kernel 0.109.0, `spec/` follows it): checked from a clean
  build (lint, format, typecheck, every package's tests, the Studio bundle), then criterion PR #103, #176 and #177,
  tagged `0.64.1`; its `.vsix` in the distribution repository.
- **The Marketplace**: `CanticaTech.catalyst-host-vscode` 0.64.1, listed about six minutes after publishing; the
  first since 0.51.0 (0.52 to 0.64 had never been published there).
- **The local Keycloak tests**: the persistent dev Keycloak's master realm has no `admin` (the owner removed it; its
  admin is `cantica-admin`). A first fix re-created `admin` with compose.yaml's documented password through
  `kc.sh bootstrap-admin` (Keycloak stopped about 90 seconds, its database backed up first); told the owner had
  removed it on purpose, it was deleted again. Instead the integration tests take the master admin from the
  environment (`CATALYST_USERS_IT_ADMIN`, `CATALYST_USERS_IT_ADMIN_PASSWORD_COMMAND`, compose.yaml's admin by
  default, as CI uses), in catalyst-users `c64e1ec` and `3046956`; with the owner's settings all 153 tests pass
  locally.
- **An incident**: inspecting the owner's keychain helper printed the `oliviersteck` password into the session's
  transcript. The owner changed it in Keycloak and the keychain; signing was refused between the two (about 20
  minutes, which blocked another session's release) and works again.

## What's left

- A deployment shared through `catalyst serve`: restart the server with `--criterion <project_name>` (migration
  0.109.0's judgment step); none of the current deployments is.
