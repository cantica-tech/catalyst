# 32 — Project membership: who belongs to a project, kept safe and confidential (design for the owner, 2026-10-25)

> **Status: decided (owner, 2026-10-25); built** in catalyst-users 0.7.0 (phase 1) and kernel 0.115.0 (phases 2 to
> 4). Answers design `30`'s question 7 (what makes a person a member of a project) and moves `30`'s user groups to the
> server. Builds on designs `19` (`catalyst serve`), `28` (identity providers), `29` (catalyst-users as the facade)
> and `30` (visibility, the realm). §5 says where the build differs from the text above it.

## 1. The owner's answers

1. **The provider is only a provider.** Keycloak is the one used today; catalyst depends on catalyst-users, never on
   a provider.
2. **No ledger in the criterion.** A criterion is cloned onto many systems, where a ledger could be corrupted or
   leak, so membership is kept on the server, encrypted with proven cryptography.
3. **Membership stays within its project**, as much as possible: one ledger per project, and nothing of it goes
   anywhere but that project.
4. **The master key: the Admin alone, with break-glass access for the other admins.**
5. **Fingerprints on a schedule**, daily, whether anything changed or not.
6. **Access fails closed**: the provider and the ledger must both name a person.
7. **User groups** (design `30` §4.4) are kept on the server like membership.
8. **The ledgers sit in the criterion's server database** and open with the criterion's first server (§2.8, §2.9).
9. **No server, no members but admins**: a criterion shared by git alone has only admins (§2.10).

## 2. The model

### 2.1 Three places

| Where                                          | Holds                                                                                                    |
| ---------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| The provider, through catalyst-users            | the groups `/criteria/<name>/admins` and `/criteria/<name>/members`                                       |
| `catalyst serve`                               | each project's membership and user-groups ledgers, encrypted; its member sets in memory                  |
| The criterion (cloned by the Admin and Criterion Admins only) | the ledgers' fingerprints in its journal, nothing else                                     |

catalyst-users is a library, a CLI and a FastAPI dependency, not a service: `catalyst serve` embeds it. Each adapter
maps a project onto its provider's groups; changing provider changes the adapter, not catalyst. The realm (design
`30` §4.0) is the deployment's provider, whichever it is.

### 2.2 Who manages membership

- The Admin, in every project; a Criterion Admin, in their own. Criterion Admins are appointed by the Admin (today's
  `catalyst-users` `appoint`).
- Only people of the realm: adding anyone the provider does not know is refused, with no override.
- Membership lets a person reach the project, within their clearance (design `30` §4.1–4.3). It grants no command:
  grants stay as design `29` has them.

### 2.3 The ledger

- One per project, and one for its user groups; appended, never rewritten (L7).
- **An entry** says who was added or removed, by whom, when and why.
- **Signing**: people hold no signing keys; they prove who they are with a provider token. The server verifies it,
  records a hash of it in the entry, and signs the entry with its own key (Ed25519). A compromised server could add
  entries; it cannot rewrite those already fingerprinted (§3.5).
- **Chaining**: `head = SHA-256(previous head ‖ salt ‖ ciphertext)`, a random salt per entry, so each entry seals
  every one before it.
- **Encryption at rest**: ChaCha20-Poly1305 or AES-GCM, through Python's `cryptography` library, with the project's
  own data key. That key is wrapped by the master key, held in the OS keychain or a key-management service (Vault,
  AWS KMS, Azure Key Vault), never on disk in the clear. No cryptography of catalyst's own.

### 2.4 Fingerprints

Once a day, whether anything changed or not, the server writes the head of each of the project's ledgers into that
project's journal and pushes the criterion. The chain is salted and the schedule fixed, so a fingerprint reveals
nothing: not who changed, not how many changes, not when. No fingerprint goes into another project's criterion.

### 2.5 Access fails closed

On every request, `catalyst serve`:

1. verifies the token through catalyst-users;
2. asks the provider whether the person is a member now (not the token's group claims, a snapshot taken at login);
3. checks that the ledger names them too (the member set in memory, so no request decrypts anything);
4. filters the answer by their clearance (design `30`).

A person the provider and the ledger do not both name gets `403`.

### 2.6 The master key and break-glass

- The Admin holds the master key.
- A break-glass copy is split among other admins with Shamir's secret sharing (for example any 2 of 3), each share
  sealed to its holder and kept in their own keychain. No holder can act alone.
- Using it is written to every project's ledger, and the Admin is told at once.
- After every use: a new master key, the projects' data keys re-wrapped (the ledgers are not re-encrypted), new
  shares issued.

### 2.7 `catalyst check`, on the server

- each ledger's chain and signatures;
- that each ledger's head matches its criterion's last fingerprint;
- that the provider's groups match the ledger: a difference is reported, grants nothing meanwhile (§2.5), and the
  Admin adopts or undoes it.

### 2.8 Where the ledgers physically sit

`catalyst serve` already keeps one SQLite database per criterion, the criterion named once by its operator
(`meta.criterion`), by default `$CATALYST_HOME/serve/serve.db` (`~/.catalyst/serve/serve.db`) on the server's machine,
anywhere else with `--db`. One ledger per project follows from it.

| What                                         | Physically                                                                                                        |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| The membership and user-groups ledgers       | two tables in the criterion's server database: each row ciphertext, its salt, nonce, signature and head            |
| The project's data key                       | the same database, **wrapped** by the master key: useless alone                                                    |
| The master key and the server's signing key  | never in the database: the server machine's keychain (macOS Keychain, Linux Secret Service), or a key-management service when the server runs in a container or a cloud |
| The member sets                              | the server process's memory, rebuilt from the ledgers when it starts                                               |
| The fingerprints                             | the criterion's journal: every admin's clone and the criterion's remote                                            |

A copy of the database (a backup, a stolen disk) holds ciphertext and a data key it cannot unwrap. The server's
machine is the host the deployment chooses to run `catalyst serve` on: the Admin's own while they are alone, a
machine or container the organization controls once others join. It is backed up; the break-glass shares (§2.6) are
the master key's backup. Losing both the master key and every share leaves the ledgers unreadable: the Admin then
opens new ones from the provider's groups (§2.9), the first entry citing the old ledger's last fingerprint.

### 2.9 When a ledger is opened

1. **Once per server machine**: `catalyst serve key init` makes the master key and the signing key in the keychain;
   `catalyst serve key escrow` (§2.6) follows.
2. **In the provider**: `catalyst-users criteria add NAME --admin alice` makes `/criteria/NAME/admins` and
   `/criteria/NAME/members`.
3. **The criterion's first server start** (`catalyst serve --criterion NAME`) opens its ledgers:
   - makes the project's data key, wrapped by the master key;
   - writes entry 0: "ledger opened by `<Admin>` for NAME, provider `<issuer>`";
   - adopts each person already in the provider's members group, one entry each, reason "member when the ledger
     opened", once the Admin confirms the list (failing closed would otherwise lock every existing member out);
   - writes the first fingerprint at once (every project has one at its opening, so it says nothing), then daily.

### 2.10 No server, no members but admins

A criterion shared by git alone (no `catalyst serve`) has no ledger, and every reader of its remote reads all of it:
membership cannot protect anything there. So such a criterion has **admins only** (the Admin and its Criterion
Admins), as design `30` §5 has every clone holder be an admin. Adding a member who is not an admin needs the
criterion's server first; `catalyst members add` on a criterion without one is refused, naming why.

## 3. Worked examples

The cast: **oliviersteck**, the Admin; **alice**, Criterion Admin of `catalyst-users`; **bob**, a contributor;
**erin** and **carol**, admins of other projects and break-glass holders; **mallory**, someone who should not get in.

### 3.1 alice adds bob

```text
$ catalyst members add bob --project catalyst-users --reason "reviews the onboarding flow"
added bob to catalyst-users (ledger entry 4)
```

1. alice's CLI calls the server with her provider token; her machine never touches the provider's admin API.
2. The server verifies alice is in `/criteria/catalyst-users/admins`, or is the Admin; otherwise `403`, nothing
   recorded.
3. It checks bob is a person of the realm; otherwise `bob is not a person of the realm`.
4. The adapter adds bob to `/criteria/catalyst-users/members`.
5. The ledger gets entry 4. Before encryption:

   ```json
   {"seq": 4, "op": "add", "member": "bob",
    "by": "alice", "by_token": "sha256:5be1…",
    "at": "2026-10-26T09:12:03Z",
    "reason": "reviews the onboarding flow",
    "prev": "sha256:9f2c…"}
   ```

   On the server's disk:

   ```json
   {"seq": 4, "salt": "q0Zk…", "nonce": "Hc1v…", "ct": "kQ9…", "sig": "ed25519:Mx2…", "head": "sha256:e71a…"}
   ```

6. bob's member set is updated in memory. The next daily fingerprint carries the new head.

### 3.2 bob works

bob holds no clone; his CLI, agent and UI are clients of the server. `catalyst view REQ-000012` goes through §2.5.

### 3.3 alice removes bob

```text
catalyst members remove bob --project catalyst-users --reason "review done"
```

The provider drops him, the ledger gets entry 5, and his next request is refused, though his token has not expired.
He leaves holding nothing.

### 3.4 Someone goes around catalyst

A provider operator adds mallory to `/criteria/catalyst-users/members` from the provider's console. mallory gets
`403`: the ledger does not name her. The next check reports:

```text
ERROR   membership drift: catalyst-users: mallory is a member at the provider, but no ledger entry added them
```

The Admin removes her (`catalyst members remove mallory …`) or adopts the change with a reason (`catalyst members
adopt mallory --reason "…"`), which writes the missing entry.

### 3.5 Someone tampers with the ledger

- **Reading it** (a stolen disk, a backup): ciphertext. The data key is wrapped by a master key not on that disk.
- **Deleting an entry** (say, "added mallory"): the ledger's head no longer matches the fingerprint every admin's
  clone and the criterion's remote hold:

  ```text
  ERROR   membership ledger: catalyst-users: head sha256:e71a… does not match the criterion's last fingerprint sha256:40bd…
  ```

- **Rewriting the whole chain**, keys in hand: the fingerprints already pushed cannot be changed.

### 3.6 alice's laptop is stolen

Its clone holds, on membership, a daily list of hashes. Entities still name people (`Assignee`, `Signed-off-by`),
which design `30` handles by keeping non-admins off clones.

### 3.7 The Admin is unreachable

Set up once by the Admin:

```text
catalyst serve key escrow --holders alice,erin,carol --threshold 2
```

Used when needed:

```text
alice$ catalyst serve key recover --reason "Admin unreachable, membership frozen"
waiting for 1 more holder…
erin$  catalyst serve key recover --reason "confirm"
master key recovered
```

Then §2.6: the use written to every ledger, the Admin told, a new master key, new shares.

### 3.8 Another provider

1. An adapter for the new provider in catalyst-users, mapping `/criteria/<name>/members` onto its groups.
2. The groups recreated from the ledger, the record of who is a member.
3. `catalyst check` confirms the provider and the ledger agree.

catalyst and the criteria do not change. The ledger names people by catalyst's own user IDs, not the provider's.

## 4. Phases

1. catalyst-users: a membership interface and the Keycloak adapter's `/criteria/<name>/members`.
2. `catalyst serve`: `serve key init`, the ledger tables and their opening (§2.9), `catalyst members
   add|remove|adopt|list`, access failing closed, members refused without a server (§2.10).
3. Fingerprints: the daily journal entry; `check`'s chain, fingerprint and drift findings.
4. Break-glass: `catalyst serve key escrow|recover`, rotation.
5. User groups moved from the criterion to the server (design `30` §4.4).

## 5. As built (2026-10-25)

- **Cryptography**: pycryptodome alone (the owner, 2026-10-25): ChaCha20-Poly1305 for the entries and the wrapped
  keys, Shamir's secret sharing for break-glass, imported on the server's host only; the CLI stays
  standard-library only.
- **Signing**: HMAC-SHA-256 with the server's own key, wrapped by the master key in the server's database: the
  server both signs and verifies its entries, so no public key is needed.
- **The check** is `catalyst serve members check`, on the server's host, rather than `catalyst check`: only the
  server holds the ledger and its keys.
- **Fingerprints** are journaled by the server's own batch, signed by whoever opened the ledger, in
  `IAM/membership.fingerprints.jsonl`.
- **Phase 5** (user groups on the server) waits for user groups themselves (design `30` §4.4, not built): the
  ledger keeps a `user-groups` chain beside `members` for them.
- **Shares** are files, one per holder, written with owner-only permissions; a holder keeps theirs as they choose.
