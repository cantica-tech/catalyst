# Results — 2026-10-24: kernel 0.106.1, and every deployment's people catalyst-users'

| What                                                                                              | Where                                                     |
| ------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| [0.106.1](https://github.com/cantica-tech/catalyst/releases/tag/0.106.1) (BUG-000031, BUG-000032) | `cantica-tech/catalyst` (PRs 317, 318); distribution repo |

- **BUG-000031**: migration 0.106.0 kept roles under ids slugged from their names (`Admin` as `admin`, the provider's
  being `catalyst-admin`); a kept role now takes the kernel template's id, and `catalyst migrate --apply` corrects a
  deployment already migrated.
- **BUG-000032**: reading several journal shards, an entry recording a file unchanged (as `catalyst init` records the
  files it finds) was overtaken by a source producing the same content later, so a moved deployment read out of time
  order (9 `time-order` warnings in the knowledge base). BUG-000033 was opened as its duplicate in error and closed
  `WontFix`.
- **Every deployment signs through catalyst-users** (the local Keycloak, realm `catalyst`): catalyst's own (the pilot),
  catalyst-users', its knowledge base's, and the Studio's. Each linked the owner's Keycloak account to the userid it
  already had (`catalyst identity configure --link`), migrated, and published in two steps where the shared
  criterion's gate still ran an older checker (BUG-000011). Each then took the released 0.106.1 CLI.
- Checks: every pull request's jobs passed before its merge (Linux, macOS and Windows tests); each deployment's
  `catalyst check` passes with its own CLI (0 errors; the knowledge base 0 warnings).

## What's left

- **The local Keycloak must be up** for any signed command in any deployment (`docker compose up -d` in
  catalyst-users); a reset realm loses the owner's account (it was recreated with the same subject once today).
- **Module upgrades** are separate: one deployment still runs software-engineering 3.2.0 (3.4.1 is out).
- **Other people** join through `catalyst-users users import`; none yet.
