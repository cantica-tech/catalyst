# Results — 2026-10-23: identity providers (stage two), and four smaller items

The owner asked for five things after stage one (`docs/results/2026-10-23-catalyst-users.md`):

1. stage two;
2. catalyst-users' first release;
3. protecting its `main` and `release`;
4. rebuilding `dist/catalyst.pyz`;
5. the knowledge base's first build.

They decided four questions on stage two (design `28`, ADR-000048).

| What | Where |
|---|---|
| Kernel [0.105.0](https://github.com/cantica-tech/catalyst/releases/tag/0.105.0): identity providers (REQ-000086) | `cantica-tech/catalyst`; the distribution repository `cantica-tech/cantica-tech` |
| catalyst-users 0.1.0 | [`cantica-tech/catalyst-users`](https://github.com/cantica-tech/catalyst-users/releases/tag/0.1.0) |
| Build 1.0.0 of the identity-design knowledge base (`KBUILD-000001` of catalyst-users) | The curator's machine (Internal) |

## What catalyst does now

- **A deployment chooses who signs.** `catalyst.toml` `identity = "local"` (the default) keeps
  `IAM/users/users.json`, exactly as before. `identity = "oidc"` makes an OIDC provider's accounts its people
  (`catalyst identity configure`).
- **A verified signer.**
  - `catalyst identity login` runs the device flow (open a link, confirm the code).
  - Every writing verb signs as the logged-in identity, confirmed by the provider.
  - `--as` names only that identity.
  - With no verified identity, nothing is signed (owner decision A); the read verbs still work.
  - `catalyst user …` refuses: people are managed in the provider.
- **Signatures stay permanent (L7).** An identity's first signature appends a line to `IAM/signers.jsonl`: a
  userid, its issuer and subject, and a name snapshot (owner decision B).
  - The ledger is append-only: `check` reports a changed or removed line.
  - A shared criterion merges it by union.
  - Its userids end the IDs the person creates.
- **Roles from the provider.** A role's `provider_role` maps the provider's role to it (owner decision C).
  - An approval records the approver's roles, and the gate counts it with them.
  - `check` warns of an unmapped role.
- **`catalyst serve` with the provider's tokens** (owner decision D).
  - The server accepts them by introspection: active, from this issuer, meant for its API client, cached 30 seconds
    at most.
  - A push is signed by the ledger line of the token's identity, and may add ledger lines for that identity only.
  - An `oidc` client sends its provider token.
- **The OIDC code is catalyst-users' core**, vendored at 0.1.0 under `scripts/catalyst/identity/`, its hashes checked
  by a test. The zipapp stays standard-library only.

## The four smaller items

- **catalyst-users 0.1.0** went through development → main → release by pull request, each merged after CI passed.
  The tag and release `0.1.0` were found already published, by a second session (below), and match the CHANGELOG.
- **`main` and `release` of catalyst-users are protected.** Each needs a pull request with the four CI jobs passing
  and up to date; no force-push, no deletion.
- **`dist/catalyst.pyz`** is rebuilt (it was 0.46.0).
- **Build 1.0.0 of the knowledge base:**
  - 1 document, 35 chunks, 384-dimension vectors from `sentence-transformers/all-MiniLM-L6-v2`, run locally.
  - Verified before publishing: checksums, nothing above Internal, and sample queries returning the right sections.
  - Published on the curator's machine only, with owner-only file modes.

## Checks

- The identity tests: 26 with a fake provider, and 4 for the vendored code.
- An end-to-end run against a real Keycloak (catalyst-users' dev realm), recorded as TEST-000001: login, signing, the
  ledger, roles, a gate, a serve import and push, forged and missing tokens, a rewritten ledger, and logged out.
- `task check:all`: deployment valid, command parity and kernel purity pass, 791 tests pass locally. The release's
  CI ran pytest on Ubuntu, macOS and Windows with Python 3.11 and 3.13, plus the standards lint and the deployment
  check, on each pull request (#311 into `main`, #312 into `release`): all passed.
- **Windows found one test assuming POSIX file modes.** The first CI run of #311 failed on Windows only, where a
  token file reads `0o666`; the mode is now asserted on POSIX only. Windows keeps a user's home private by its own
  access-control lists.
- Pyright: 0 errors. 4 new warnings, all in the vendored code; they are fixed in catalyst-users and arrive with its
  next release.

## Problems along the way

- **A second Claude Code session worked on the same items in parallel.** It published release `0.1.0` and created
  `KBUILD-000001` seconds before this session did the same. This session's duplicate build record,
  `KBUILD-000002`, is withdrawn with its reason. The owner closed the other session.
- **The end-to-end run found two bugs**, both fixed before release:
  - `identity configure` left `catalyst.toml` unjournaled;
  - a server's first push (an import) was refused for carrying other signers' ledger lines.
- **A refused journal append was hidden** by piping it through `tail`: one step was closed before its vendored files
  were journaled. They were journaled right after.
- **Two steps were opened late.** The provider step was opened after its code was started; its record says so.
- **REQ-000085 does not exist.** A refused first attempt reserved the number; the requirement is REQ-000086.
- **Journal time-order warnings** appear wherever several actors' shards meet (`check` compares timestamps across
  shards in file order). This already happened after a merge and is not caused here.

## What's left

- **catalyst-users 0.1.1** (the vendored code's typing fix), then vendor it again.
- **Migrating a `local` deployment's users into a provider:** a later command.
- **Key-backed signatures for approvals** (`gitsign`, SSH commit signing): a separate decision.
- **The UI** may want `catalyst identity` and the new spec schemas (`identity-whoami`, `identity-status`,
  `approve.roles`, `role.provider_role`).
- **The journal's time-order warning across shards** could take shard order into account.
- **catalyst's `development/BACKLOG.md`** was last refreshed on 2026-09-29: a `/show-backlog` of its own.
- **catalyst-users' `compose.yaml`** gained, outside this session, a volume keeping Keycloak's H2 database at
  `./.keycloack/data`: uncommitted, the path spelled "keycloack", and not yet in `.gitignore`.
