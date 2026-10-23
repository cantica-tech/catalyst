# 28 — Identity providers: users and groups out of the criterion (design for the owner, 2026-10-23)

> **Status: decided (owner, 2026-10-23): A, B and C as recommended; D: the CLI and `catalyst serve` in one release.** Stage two of the work started in
> `cantica-tech/catalyst-users` (stage one, released 0.1.0 on 2026-10-23).

## 1. Today

A deployment's people live in its criterion: `IAM/users/users.json` (`name`, `userid`, `git_username`, `roles`,
`active`), changed only by `catalyst user …`, journaled. Every signed operation goes through one function,
`ids.resolve_signer`: `--as` names a registered, active user, else the only active one; its roles must grant the
command (`permissions`). The signer's `userid` ends every ID it creates (INV-26); gates compare approvers with the
author by name, `git_username` or userid (`gates._same`); `catalyst serve` issues its own tokens, keyed by userid.

On git, identity is declared, not verified (`Rules-of-Rules.md` §13): anyone can pass `--as` anyone.

## 2. What changes

A deployment chooses its **identity provider** in `catalyst.toml`:

- `identity = "local"` (the default): exactly today. `IAM/users/users.json` is the registry; nothing changes for an
  existing deployment.
- `identity = "oidc"`: people are the provider's (Keycloak, Entra ID, Okta, any OIDC provider). Catalyst verifies who
  is signing instead of trusting `--as`.

```toml
identity = "oidc"
identity_issuer = "https://id.example.com/realms/catalyst"   # the provider's issuer URL
identity_client = "catalyst-cli"                             # a public client with the device grant
```

## 3. Signing with a provider

- `catalyst identity login` runs the device flow (open a link, enter a code); the tokens are kept owner-only in
  catalyst's home (`$CATALYST_HOME/identity/<issuer hash>.json`), never in a criterion or a project.
  `identity whoami`, `identity logout` (revokes) and `identity status` complete it.
- `resolve_signer`, in `oidc` mode, signs as **the logged-in identity**: its token is refreshed when it has less than
  30 seconds left, and the provider is asked who it is (userinfo). `--as` is accepted only when it names that same
  identity; anything else is refused. An agent signs as the person whose login it runs under, as today.
- The signer's roles are **the provider's roles**, mapped to the deployment's roles (§5); a disabled account cannot
  log in, so `active` is the provider's.

## 4. IDs and signatures stay permanent (L7)

IDs end with an 8-character userid, and every signature must stay resolvable after the provider forgets the person.
In `oidc` mode catalyst keeps an **append-only signers ledger**, `IAM/signers.jsonl`, one signer per line (a shared
criterion merges it by union, like the journal, so two first signatures on two machines never conflict):

```json
{"userid": "Xk3pQ9aB", "iss": "https://id.example.com/realms/catalyst", "sub": "3c154a14-…", "username": "alice", "name": "Alice Developer", "first_signed": "2026-10-23"}
```

- Written by catalyst the first time an identity signs, journaled; never edited, never shortened.
- The person is keyed by `iss` + `sub` (never the username); `username` and `name` are a snapshot.
- `check` accepts its userids where it accepts `users.json`'s (INV-26); the gates compare by userid.

It is not a directory: no roles, no `active`, no way to add a person by hand. The people, their groups and their
roles stay in the provider.

## 5. Roles

Each role in `IAM/roles/roles.json` may name the provider role that grants it:

```json
{"name": "Tech Lead / Architect", "provider_role": "tech-lead", "actions": ["…"], "reconciliation": "full"}
```

A signer holds a catalyst role when their token carries its `provider_role` (Keycloak: a realm role, inherited
through nested groups). A role without `provider_role` is held by nobody in `oidc` mode; `check` warns. The role
definitions (what each role may run) stay in the criterion, journaled and gated as today.

## 6. Code: catalyst-users vendored

The kernel stays one standard-library-only zipapp. catalyst-users' core (`config`, `http`, `oidc`, `identity`,
`credentials`, `session`) is standard-library only by its own rule (`env-RUNTIME-000002`), so catalyst **vendors**
it, at a released version, under `scripts/catalyst/identity/` with a `VERSION` file. A check confirms the copy matches
that release; a change is made in catalyst-users first, released, then vendored again.

## 7. The owner's decisions

| # | Question | Recommended | Alternative |
|---|---|---|---|
| A | Signing when the provider cannot be reached | **Refuse to sign** (read-only commands still work) | A grace period on the last verified identity |
| B | Where signers are recorded | **`IAM/signers.jsonl`, append-only** (§4) | A userid derived from `iss`+`sub` with no ledger (simpler, but nothing resolves it offline) |
| C | Role mapping | **`provider_role` per role in `roles.json`** (§5) | A table in `catalyst.toml` |
| D | Scope of this release | **The CLI: login, signing, roles, gates, `check`** | Also `catalyst serve` accepting the provider's tokens by introspection (later release) |

## 8. Out of scope

- Key-backed signatures for approvals (`gitsign`, SSH commit signing): a separate decision.
- Migrating a `local` deployment's users into a provider: `users.json` stays as their history; a migration command
  can follow.
