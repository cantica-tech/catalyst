# 0.93.0 — Roles grant commands

From `0.92.x` to `0.93.0` (owner decision D5, roadmap R4.6).

## What changes

- A writing verb refuses a signer none of whose roles grants the command its change is for. A role grants each
  command its `actions` name with a leading `/` (`/status on tasks` grants `status`; `/user-add` grants that alias;
  `/user` grants all of `/user`'s aliases), and everything with `*`. The `Admin` role grants everything. Descriptive
  actions grant nothing.
- Not checked: a tier named as the command (`chore`, `fix`, `feature`), and a command the deployment's §4 does not
  have. Reconciliation and approval gates keep their own checks.
- `--as` refuses a deactivated user.
- `catalyst.toml` may set `role_check = "warn"`: a refusal becomes a warning and the change is made.
- The kernel's roles template gives each role the `/commands` its description means; `Admin` has `*`.

## Steps

1. `catalyst sync apply --kernel <0.93.0>`: the CLI, the runtime and the recomposed documents. An `Admin` runs it.
2. **Judgment:** for each role in `IAM/roles/roles.json` held by an active user who is not an `Admin`, add the
   `/commands` its descriptive actions mean, with the owner's agreement, by
   `catalyst role modify <role> --action /<command>` (journaled). The kernel's `templates/roles.template.json` is a
   starting point. A deployment whose users are all `Admin`s has nothing to do.
3. **Judgment, only if the owner asks:** set `role_check = "warn"` in `catalyst.toml` while the roles are reviewed.
4. `catalyst check`.
