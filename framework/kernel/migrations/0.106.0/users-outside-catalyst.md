# 0.106.0 — Users, groups and roles outside catalyst

From `0.105.x` to `0.106.0` (design 29, ADR-000049, REQ-000087).

## What changes

- People are catalyst-users': a criterion holds no user or role registry. `IAM/identity.json` points at the
  deployment's catalyst-users configuration (`{"provider": "keycloak", "issuer": …}` or `{"provider": "keycloak",
  "url": …, "realm": …}`); `catalyst check` reports a missing or broken one. `catalyst.toml`'s `identity_*` keys go,
  and so does the `local` mode.
- The signer is the identity catalyst-users verifies at each signature; with no one logged in, this machine's
  system account (the admin `catalyst-users setup` named) signs, if its settings point at the same provider, and says
  so. Each identity's first signature appends its line to `IAM/signers.jsonl` (unchanged since 0.105.0).
- What someone may do is their **grants** from the provider (`cmd:<command>`, `reconcile:<level>`), not a role's
  name or actions. `catalyst user …` and `catalyst role …` refuse, and say to make the change in catalyst-users.
- The logged-in identity is kept per machine as a read-only snapshot with a hash of its content, rewritten at each
  signature; an edited one is discarded and its owner authenticated anew.
- The users, roles and a new groups template describe how people are shown, nothing more.
- `catalyst init` without `--identity-issuer` points at the provider this machine's catalyst-users is set up for.

## Steps

1. `catalyst sync apply --kernel <0.106.0>`, then `catalyst migrate --apply`: `IAM/identity.json` from
   `catalyst.toml`'s `identity_*` keys (an `oidc` deployment); the deployment's roles kept as the roles template's
   next version (their names and ids, for display); `IAM/users/users.json` and `IAM/roles/roles.json` retired in place
   as `*.retired.json` (history: who signed before); the groups templates added.
2. **Judgment, a `local` deployment:** point it at catalyst-users (`catalyst-users setup`, then
   `catalyst identity configure --issuer <url>`): nothing is signed until it is.
3. **Judgment:** provision the deployment's roles into the provider (`catalyst-users roles provision
   <the retired roles.json>`), and import its people (`catalyst-users users import <the retired users.json> --roles
   <the retired roles.json>`), with the owner's agreement. A gate's `role` names the provider's role.
4. **Judgment:** the `user` and `role` definitions gain v2 (an identity catalyst-users verifies; a provider role
   composed of grants): `catalyst definition migrate user 2` and `catalyst definition migrate role 2`. The workflow,
   reconciliation and analysis templates gain a new version (a signer is the ledger's, not a registered user's).
5. `catalyst identity login`; each person who signed before keeps their userid with `catalyst identity link <their
   retired name>` before their first signature (once, only by themselves); then `catalyst check`.
