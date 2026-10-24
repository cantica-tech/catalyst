# 0.109.0 — The Criterion Admin, shown; `catalyst serve` knows the criterion it serves

From `0.108.0` to `0.109.0` (REQ-000090, REQ-000091).

## What changes

- The kernel's roles template shows catalyst-users' `criterion-admin` as `Criterion Admin` (`scope: criterion`). Like
  every role in it, it grants nothing by itself: what a criterion's admin may do comes from catalyst-users
  (`administers`, `fw-IDENTITY-000011`).
- `catalyst serve --criterion <name>` names the criterion a server's database serves, once; a push's signer who
  administers it holds every grant and reconciliation level `full` there. A server started without it gives a
  criterion's admins nothing more, as before.

## Steps

1. `catalyst sync apply --kernel <0.109.0>`, then `catalyst migrate --apply`: the roles template gets the kernel's
   `Criterion Admin` as its next version, unless a version it holds has ever had a role with the id
   `criterion-admin` (a team that removed it keeps it removed).
2. **Judgment, a criterion shared through `catalyst serve`:** restart the server with `--criterion <the deployment's
   project_name>` for its admins to hold their rights on pushes.
