# 29 — Users, groups and roles outside catalyst: catalyst-users as the facade (design for the owner, 2026-10-23)

> **Status: decided (owner, 2026-10-23): A–D as answered (§2); E, F and G as recommended (§5).** The owner's request of
> 2026-10-23.
> Supersedes, once decided, part of design `28` (ADR-000048): the `local` mode and the roles in `roles.json`.

## 1. The request

Users and roles are no longer handled by catalyst but by catalyst-users. The users, roles (and a new groups) templates
stay, for display and formatting only. A criterion's `IAM/` holds only a pointer to a valid catalyst-users
configuration; the logged-in user is the one catalyst-users authenticates, and their roles and groups are read-only.
Changing the user triggers an authentication and a refresh of their roles and groups; so does any change to the roles
and groups. catalyst-users is the facade for whatever manages the people (Keycloak today; Entra ID, Okta, LDAP behind
Keycloak, or another backend later).

## 2. The owner's answers

| # | Question | Answer |
|---|---|---|
| A | Where the logged-in user lives | **Per machine**: `IAM/` holds the pointer only; each person's user, roles and groups are cached in their catalyst home, refreshed from the provider |
| B | What a catalyst-users "instance" is | **A configuration**: the pointer names the provider and its clients; catalyst keeps embedding catalyst-users' code (no service in between) |
| C | Where role definitions live (what a role may run, its reconciliation level) | **In catalyst-users**, that is in the provider behind it; `roles.json` goes |
| D | L7 and the `local` mode | **Keep the signers ledger, drop `local`**: every deployment points at a catalyst-users configuration |

## 3. Design

### 3.1 The pointer: `IAM/identity.json`

```json
{"provider": "keycloak", "issuer": "https://id.example.com/realms/catalyst", "client": "catalyst-cli", "catalyst_client": "catalyst"}
```

The only people-related file a criterion holds besides the ledger. It replaces `catalyst.toml`'s `identity_*` keys
(the project file stays free of it) and `IAM/users/users.json` and `IAM/roles/roles.json`. `check` validates it;
changing it is a journaled, gated change like any other (a deployment may gate `IAM` changes).

### 3.2 The facade: catalyst-users' provider interface

catalyst-users gains a `Provider` interface: `login`, `logout`, `whoami` (the identity, its groups, its roles, its
**grants**), `users`, `groups`, `roles` (read-only lists). `KeycloakProvider` implements it with today's code; another
backend is another class, chosen by `IAM/identity.json` `provider`. catalyst calls only the interface.

### 3.2a A `static` provider, for tests only

catalyst's own test suite signs thousands of operations with declared people and no network. catalyst-users also
gives a `static` backend: people, groups, roles and grants declared in a JSON file, nothing verified. catalyst
refuses it unless `CATALYST_ALLOW_STATIC_IDENTITY=1` is set, which only the tests set; `check` reports a deployment
whose pointer names it. It is never a way back to `local`.

### 3.3 Roles and their grants, in the provider (C)

A token carries what a person may do, so no CLI needs an admin secret:

- **Each catalyst command is a client role** of the client `catalyst` (`cmd:create`, `cmd:status`, `cmd:approve`, …),
  plus the reconciliation levels (`reconcile:full`, `reconcile:propose`).
- **Each catalyst role** ("Tech Lead / Architect", "Developer", …) is a realm role, a **composite** of the commands it
  grants and its reconciliation level.
- **Groups** hold roles, as today; subgroups inherit them.
- The token's `resource_access.catalyst.roles` is the **effective grants** (Keycloak resolves composites and groups),
  `realm_access.roles` the roles, `groups` the groups. `permissions` reads the grants, `reconcile` the level, a gate's
  `role` a realm role.
- `catalyst-users roles provision` writes the kernel's roles template into the provider once (realm roles, the
  command client roles, the composites); changing a grant afterwards is done in the provider.

### 3.4 The logged-in user, cached per machine (A)

- `$CATALYST_HOME/identity/<issuer hash>.json`: the tokens (as today) and a read-only snapshot: userid (from the
  ledger), username, name, groups, roles, grants, and when they were verified.
- **Every signed operation verifies**: the token is refreshed when it has under 30 seconds left, the provider confirms
  the identity, and the snapshot is rewritten (so a change of roles or groups in the provider is seen at the next
  signature).
- **A changed snapshot triggers a refresh**: the snapshot carries a hash of its content; one that does not match (it
  was edited) is discarded and re-authenticated, never trusted.
- **Changing the user** (`catalyst identity login` as someone else, or `logout`): a new authentication, a new snapshot.

### 3.4a The machine's system account, when no one is logged in (owner, 2026-10-23)

catalyst-users 0.4.0 holds a machine's local system account: the admin `catalyst-users setup` named, in
`~/.catalyst-users/IAM/settings.json` (its username and a password command, never a secret). When no person is logged
in to the pointer's provider, catalyst signs as that account, through the vendored facade's `system_whoami`, provided
the machine's settings point at the same issuer; it says so on standard error, and the account gets its own ledger
line like anyone (L7), so its signatures are told apart from a person's. A person logged in always signs as
themselves; `--as` never names the system account for them.

### 3.5 The templates, for display only

`IAM/users/templates/`, `IAM/roles/templates/` and a new `IAM/groups/templates/` (`TEMPLATE-GROUPS-v1.json`) describe
how users, roles and groups are shown (`catalyst identity whoami`, `catalyst list users|roles|groups`, the UI): the
fields, their labels and order. They hold no person and grant nothing.

### 3.6 Signatures stay permanent (D, L7)

`IAM/signers.jsonl` stays as in 0.105.0: append-only, keyed by issuer and subject, the userid every ID ends with.

### 3.7 Migration

- A deployment at 0.105.x gets `IAM/identity.json` from its `catalyst.toml` `identity_*` keys, or, if it was `local`,
  must be pointed at a provider (a judgment step: no deployment can sign until it is).
- `users.json` and `roles.json` are retired in place (kept, renamed `*.retired.json`, read for history: who signed
  before); their people go into the provider by hand or with `catalyst-users users import`.
- A gate's `role` becomes the provider's role name.

## 4. Consequences the owner should weigh

- **Every deployment needs a provider to sign anything**, catalyst's own included: a solo user runs the local
  Keycloak of catalyst-users (or another provider). Offline, nothing is signed (decision A of design 28).
- **CI is unaffected**: `catalyst check` and `trace` sign nothing.
- **Agents** sign as the logged-in person, as today; with no one logged in, as the machine's system account (§3.4a).
- **Laws and invariants change**: INV-16 (no users.json; the provider's accounts), INV-26 (userids only from the
  ledger), INV-21 and rr-META-011 (grants and reconciliation levels from the token). L4's "who signs is declared,
  never guessed" becomes "verified".
- A breaking change of the deployed layout: a minor release with a migration that has a judgment step.

## 5. Still to decide

| # | Question | Recommended |
|---|---|---|
| E | Grants as client roles composed into realm roles (§3.3) | **Yes** (the token carries everything; no admin secret anywhere) |
| F | Where the pointer lives | **`IAM/identity.json`** in the criterion, not `catalyst.toml` |
| H | Who signs when no one is logged in | **The machine's system account** (owner, 2026-10-23; catalyst-users 0.4.0): §3.4a |
| G | Release plan | **catalyst-users 0.2.0** (the facade, provisioning, import) first, then **kernel 0.106.0** (the pointer, no `local`, grants from the token, migration); vendored at catalyst-users 0.4.0, the system account included |
