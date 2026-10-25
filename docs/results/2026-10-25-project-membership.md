# Results: project membership (design 32), 2026-10-25

The owner asked to finish the membership work. Design 32's phases 1 to 4 are built and released: catalyst-users
0.7.0 and kernel 0.115.0.

## What shipped

### catalyst-users 0.7.0 (REQ-000012-WsHBVWTH, `id-DIR-000006`)

- **The facade's membership calls:** `members`, `is_member`, `add_member` and `remove_member`.
  - `is_member` asks the provider at the moment of the request, never a token's group claims.
  - `add_member` refuses anyone the realm does not know.
  - Each call runs with the caller's rights, or with the system account's (`system=True`), which a server uses once
    it has verified its caller.
- **Keycloak:** a criterion's members are `/criteria/<name>/members`. The group is made with the criterion, covered
  by its admins' permissions, and created when an existing criterion is added again.
- **`catalyst-users criteria members NAME`** lists members. Nothing in catalyst-users changes them.
- **Tested:**
  - 147 unit tests pass.
  - The onboarding integration test passes against a real Keycloak (7 tests). In it, a criterion-admin adds, lists,
    checks and removes members, and is refused another criterion's members.

### Kernel 0.115.0 (REQ-000097-yCNjAMXO, `fw-IDENTITY-000012`, `fw-IDENTITY-000013`)

- **The ledger:** one per criterion, in `catalyst serve`'s database, never in the criterion.
  - Entries are encrypted with ChaCha20-Poly1305 using the criterion's data key.
  - Each entry is chained to the one before it by a salted SHA-256 hash.
  - Each entry is signed with HMAC-SHA-256 using the server's key.
  - Both keys are wrapped by the master key.
- **Fails closed** once the ledger is open:
  - only the identity provider's tokens are accepted;
  - the Admin and the criterion's admins are admitted;
  - anyone else is admitted only when the provider (its answer kept 10 seconds) and the ledger both name them.
- **`catalyst members list|add|remove|adopt`** goes through `GET`/`POST /v1/members`, admins only. A criterion shared
  without a server is refused, so it has admins only.
- **Fingerprints:** once a day, and when the ledger is opened or the break-glass copy is used, the server's own
  journaled batch writes a line to `IAM/membership.fingerprints.jsonl`.
  - A line holds a day and the chain's head, nothing more.
  - A clone pulling that batch passes journal verification.
- **`catalyst serve members open|check|fingerprint`:**
  - `open` asks the Admin to agree to the provider's current members (exit code 3) before adopting them.
  - `check` reports four things: a broken chain, a broken signature, a fingerprint no entry matches (a rewritten
    ledger), and drift between the provider and the ledger.
- **`catalyst serve key init|escrow|recover`:**
  - The master key lives in the host's keychain, or comes from a key-management service's command.
  - The break-glass copy is a set of Shamir shares, one file per holder.
  - Recovering the key records the use in the ledger and the journal, then replaces the key, which voids every share.
- **Cryptography:** pycryptodome only, imported on the server's host only, as the owner decided. The CLI stays
  standard-library only.
- **Tested:**
  - 19 new tests pass; the whole suite is 856 passed.
  - ruff, `gen_docs.py --check`, the kernel purity check and the standards lint all pass.
  - catalyst's own deployment is at 0.115.0.

## Where the build differs from design 32

Recorded in design 32 §5:

- `serve members check` runs on the server's host. `catalyst check` cannot do it, because only the server holds the
  ledger and its keys.
- Signing uses HMAC with the server's key, since the server both signs and verifies its own entries.
- Shares are files with owner-only permissions; each holder keeps theirs as they choose.

## Not tested

- Membership has not been tried against a real Keycloak behind a running `catalyst serve`. The server-side tests use
  a fake provider; the real Keycloak calls are tested in catalyst-users.
- The keychain path of `serve key init` and `recover` is not exercised by the tests, which use a key file's command.

## What's left

- **Design 32 phase 5:** user groups kept on the server. This waits for user groups themselves (design 30 §4.4),
  which are not built; the ledger already has a `user-groups` chain for them.
- **Design 30's visibility model:** classification, clearance, elevations, user groups, and the server's filtered
  reads. Membership is its first piece.
- **Retiring `serve token issue`:** under membership, `cst_` tokens are refused, but the command still exists. Design
  30 removes it.
- **A first real run:** catalyst's own criterion is shared through git, so under design 32 §2.10 it has admins only.
  Membership starts the day a criterion is served by `catalyst serve` with a ledger opened.
