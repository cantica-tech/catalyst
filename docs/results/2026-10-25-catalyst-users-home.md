# Results — 2026-10-25: catalyst-users' home in catalyst's

The owner asked why catalyst-users kept its own `~/.catalyst-users` rather than `~/.catalyst/users`, and to move it.
It had its own dotfolder because catalyst-users began as a standalone library; catalyst is now its main client, and
two homes made one machine's setup two things to find, back up and sandbox.

| What | Where |
|---|---|
| catalyst-users 0.6.0: REQ-000010 (rule `id-PROVIDER-000009`), STEP-000015 | `cantica-tech/catalyst-users` |
| Kernel 0.111.0: REQ-000092 (`fw-IDENTITY-000002` amended), STEP-000119; 0.6.0 vendored | `cantica-tech/catalyst`, `cantica-tech/cantica-tech` |
| catalyst-ui: `spec/` and the desktop app at 0.111.0, the IAM setting's text (development, no UI release) | `cantica-tech/catalyst-ui` |

## What changes

- catalyst-users' settings (`IAM/settings.json`), `config.toml` and credentials live in `~/.catalyst/users`
  (`$CATALYST_HOME/users` when catalyst's home is moved; `CATALYST_USERS_HOME` still names another), beside
  `projects/` and `workspaces/`. A sandbox needs one variable, `CATALYST_HOME`.
- A `~/.catalyst-users` made before is moved there once, the first time it is used, and **a link is left in its
  place**: the deployments' own catalyst CLIs vendor an earlier catalyst-users and read the old path, so a move
  without the link would have broken signing for every deployment not yet synced. Beside an existing new home the
  old one is named as ignored; a sandbox never adopts it.

## On this machine

- The first run of the 0.111.0 CLI moved `~/.catalyst-users` to `~/.catalyst/users` (mode `0700` kept) and left the
  link. catalyst signs through the new home; catalyst-users' deployment, still on 0.110.1, signs through the link.
- Publishing catalyst-users' criterion carried another session's finished, journaled upgrade of that deployment
  (kernel 0.110.1, knowledge-base 0.5.1); that session had ended, so it shipped with this change.

## Checks

- catalyst-users: 156 tests (integration included, as the owner's master admin); CI green on #15 and #16.
- catalyst: 816 tests; kernel purity; `catalyst check`; CI green on #329 and #330.
- catalyst-ui: the spec test; criterion PR #104.

## What's left

- catalyst-users, catalyst-users-kb and catalyst-ui's deployments are still on 0.110.1 and read the old path through
  the link; syncing them to 0.111.0 makes the link unnecessary. Remove `~/.catalyst-users` only after every
  deployment (and any other machine's) is on 0.111.0 or later.
- A catalyst-ui release carrying 0.111.0 is a separate decision.
