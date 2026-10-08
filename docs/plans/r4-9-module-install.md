# R4.9: `catalyst module install`

**Status:** planned (owner, 2026-10-08). Code only, no new prose (R1.6 freeze).

## Why

Today a module reaches a deployment one way: `catalyst init --module <id>
[--module-dir <dir>]` seeds it once, from a checkout next to the project or
catalyst. There is no verb to install a module into an existing deployment,
list what is installed, check that a module is intact, or upgrade it outside a
full `/sync-framework`. The target architecture (07 §10) names
`catalyst module install <url|path>`, which verifies the module's hash or
signature, but no roadmap item scheduled it.

## Scope

| Verb | Does | Notes |
|---|---|---|
| `catalyst module install <path\|git-url>[@ref]` | fetch → validate → verify → seed into the working copy → recompose → journal → record in the locator | refuses when a different module is already active, unless `--replace` (see the open question) |
| `catalyst module list` | the active module: id, version, source, hash | reads the locator, no network |
| `catalyst module verify` | recompute the installed module's hash and compare it with the locator's | also a `catalyst check` rule |
| `catalyst module upgrade [<ref>]` | install a newer version through `sync plan\|apply` (R2 W4) | upgrade = migration, never a blind copy |

`init --module` becomes `init` followed by `module install`, so there is one seeding path.

## Steps

| Step | Content | Depends on |
|---|---|---|
| 1. Extract | Move the module seeding that `init` does today (copy into `modules/<id>/`, entity folders, definitions, recompose of CODE-OF-CONDUCT / Rules-of-Rules / Taskfile / command files) into one function, called by `init`; no behaviour change, tests unchanged | — |
| 2. `module install <path>` | Local path first: validate `module.yaml` with the existing loader, seed, recompose, journal one entry, record `module`, `module_version`, `module_source`, `module_sha256` (hash of the module tree) | step 1 |
| 3. `module list` / `verify` | Read the record; `verify` and a `check` rule fail on a hash mismatch (hand-edited module) | step 2 |
| 4. Git URL | `install <git-url>[@ref]`: shallow clone into a temp dir, then step 2; the commit SHA is recorded too | step 2 |
| 5. Locator | Record into `.catalyst/catalyst.toml` instead of the `*.catalyst` pointer once R3.1 lands; legacy deployments keep the pointer | R3.1 |
| 6. v3 format | Validate `module.yaml` v3 when R4.3 lands; v2 modules still install | R4.3 |
| 7. Upgrade | `module upgrade` plans and applies through `sync plan\|apply`; module migrations run as in `/sync-framework` today | R2 W4 |
| 8. Signature | Verify the release feed's signature in addition to the hash | release feed (07 §10, R7) |

Steps 1–4 can start any time (they only need today's module format); 5–8
follow their dependency.

## Tests

- Install from a path and from a local bare git repository into a fresh
  `make_project` deployment; `catalyst check` is clean afterwards.
- The golden corpus example (`example`) re-seeded through `module install`
  yields the same composed CODE-OF-CONDUCT, Taskfile and command set as its
  capture.
- A hand-edited module file fails `module verify` and `check`.
- Installing a second, different module without `--replace` is refused.
- Windows and Python 3.9 in the CI matrix, as for every verb.

## Open question

- **Several modules or a replacement.** Today a deployment has one active
  module; 07 §4.2 targets several per deployment. Does `install` add a second
  module (needs namespaced module rules, R4.3), replace the active one (needs
  migrating every artifact of the old module's types), or neither until a
  second production module exists?
