# 0.120.0 — One shape for the identity pointer; one login per provider

From `0.119.2` to `0.120.0` (BUG-000057, BUG-000058, REQ-000107, REQ-000108, REQ-000109).

## What changes

- `IAM/identity.json` names its provider by its `issuer` (fw-IDENTITY-000007). A pointer written from catalyst-users'
  settings named it by `url` and `realm` instead; catalyst reads both, and `catalyst check` warns of the second. The
  tokens of a login are kept per provider as one provider is named (`canonical_issuer`: no trailing `/`, a loopback
  host spelled `localhost`), so a login under either shape or spelling carries to the other.
- The signers ledger compares issuers the same way: one person signing in at `localhost` and at `127.0.0.1` keeps one
  line and one userid. No line is rewritten (L7): the spelling it was first written with stays.
- With no one logged in, the system account is found when catalyst-users' settings name the same provider, however
  its issuer is spelled (catalyst-users 0.11.0's `system_pointer`).
- `catalyst identity login --password` (catalyst-users 0.11.0, vendored); one login serves `catalyst-users login`
  and `catalyst identity login` when catalyst-users is set up for the same provider; `catalyst hook start` says when
  no one is logged in.
- A token file kept under a pointer's old `url` + `realm` shape is no longer read: log in again once
  (`catalyst identity login`).

## Steps

1. `catalyst sync apply --kernel <0.120.0>`, then `catalyst migrate --apply`: a pointer naming its provider by `url`
   and `realm` is written with its `issuer` (`<url>/realms/<realm>`), every other key kept; journaled.
