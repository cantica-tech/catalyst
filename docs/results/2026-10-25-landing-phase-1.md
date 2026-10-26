# Results: landing, phase 1 (design 33), 2026-10-25

The owner asked for a process by which non-admins' changes, made in a catalyst session or explicitly, reach a
criterion's git repository: defined per project in one JSON document with a standard default, chosen at onboarding
with the roles. Design 33 proposed it, the owner decided its six questions as recommended, and phase 1 is built for
kernel 0.116.0 (REQ-000099, STEP-000124). It is not released yet.

## What was built

- **Every journal entry says how its change was made** (`fw-STRUCTURE-000022`): `via` is `agent`, `person` or
  `server`.
  - `CATALYST_VIA` says it outright: a UI's host sets `person`.
  - `catalyst mcp` and `catalyst agent run` set `agent` for what they run, and an agent's own variables (`AI_AGENT`,
    `CLAUDECODE`, `GEMINI_CLI`) count too.
  - The server's fingerprint entry says `server`.
  - Earlier entries are not rewritten.
- **A criterion declares how its changes land** (`fw-STRUCTURE-000023`): `IAM/landing.json`, with its schema and
  four kernel policies (`standard`, `open`, `reviewed`, `host`).
  - Without the file, the `standard` policy applies.
  - `catalyst landing init` (an admin's) writes a policy, journaled as the Admin's assent to every landing it allows.
  - `catalyst landing show` says which policy applies, and where it comes from.
  - `catalyst check` errors on a malformed policy and warns when a criterion shared through a server names no landing
    credential.
- **Onboarding:** the guide's step 6 is now people, roles and landing, worked together, with its checklist item.
- **Migration `0.116.0/landing.md`:** nothing is mechanical; the judgment step is choosing a policy with the user.

## Checked

- `tests/test_catalyst_landing.py`: 18 tests pass. The whole suite: 874 pass.
- ruff (0.16.10) check and format, markdownlint, the generated docs, kernel purity, command parity and the frozen
  surface all pass; typecheck reports 0 errors.
- `catalyst check` on catalyst's own deployment: 0 errors.

## What's left

- **Release 0.116.0:** waits on kernel 0.115.0 (PR 337, project membership), then the version bump, CHANGELOG and the
  release cycle.
- **Phase 2, the server lands:** held batches, the server's credential (`serve landing connect`, a GitHub App on
  GitHub), topic branches and pull requests, `merge: auto`, a conflict turned into a `RECON-` case. Its invariant
  touches the frozen prose surface, so it needs an ADR lifting the freeze.
- **Phase 3, review in catalyst:** the inbox's `landing` kind, approving a held batch, grouping by session (the Stop
  hook says a session ended) and by time window.
- **Phase 4:** review on the host's pull request, and the remaining templates' behaviour end to end.
- **catalyst's own deployment** has no `IAM/landing.json` yet, so it runs on `standard`. Choosing its policy is the
  owner's call (`catalyst landing init`).
