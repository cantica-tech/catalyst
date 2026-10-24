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
| catalyst-users REQ-000009 (rules `id-DIR-000005`, `id-PROVIDER-000008`), STEP-000014 | `cantica-tech/catalyst-users`, unreleased |
| Kernel REQ-000089 (rule `fw-IDENTITY-000011`), STEP-000113 | `cantica-tech/catalyst`, unreleased |

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

## What's left

- Release catalyst-users (0.5.0), vendor it into catalyst, release the kernel; then the rules turn ✅ and the steps
  and requirements close.
- Onboard the live realm: `catalyst-users criteria add <name> --admin <admin>` for catalyst, catalyst-ui,
  catalyst-users and catalyst-users-kb, then `roles provision`, as the catalyst-admin.
- `catalyst serve`: a push's signer gets no criterion-admin grant, since the served database does not know its
  `project_name` (REQ-000089's open question).
- The kernel's roles template could show `Criterion Admin`, which needs a migration.
