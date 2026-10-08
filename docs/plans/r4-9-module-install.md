# R4.9: `catalyst module install`

**Status:** planned (owner, 2026-10-08). Code only, no new prose (R1.6 freeze).
**Decided:** a deployment can hold several modules; `install` adds one beside
those already there (owner, 2026-10-08; 07 §4.2).

## Why

Today a module reaches a deployment one way: `catalyst init --module <id>
[--module-dir <dir>]` seeds it once, from a checkout next to the project or
catalyst, and a deployment has exactly one module. There is no verb to install
a module into an existing deployment, list what is installed, check that a
module is intact, or upgrade it outside a full `/sync-framework`. The target
architecture (07 §4.2, §10) has several modules per deployment, installed by
`catalyst module install <url|path>`, which verifies the module's hash or
signature.

## Scope

| Verb | Does | Notes |
|---|---|---|
| `catalyst module install <path\|git-url>[@ref]` | fetch → validate → check for collisions → verify → seed into the working copy → recompose → journal → record in the locator | adds the module beside any already installed; refuses on a collision (below) |
| `catalyst module list` | every installed module: id, version, source, hash | reads the locator, no network |
| `catalyst module verify [<id>]` | recompute each installed module's hash and compare it with the record | also a `catalyst check` rule |
| `catalyst module upgrade <id> [<ref>]` | install a newer version of one module through `sync plan\|apply` (R2 W4) | upgrade = migration, never a blind copy |

`init --module` becomes `init` followed by `module install`, so there is one
seeding path. Removing a module is out of scope: its artifacts would need
retiring or migrating, and nobody needs it yet.

### Several modules in one deployment

What two modules must not share, checked by `install` before anything is
written:

| Shared space | Rule |
|---|---|
| Entity types and ID prefixes (`BUG-`, `REQ-`, …) | unique across installed modules and the kernel; a collision refuses the install |
| Entity folders | unique; same rule |
| Slash commands and Taskfile tasks | namespaced by module id when two modules declare the same name (R4.3), otherwise refused |
| Module rules (`CODE-OF-CONDUCT` §4 inserts, rules-of-rules inserts) | namespaced by module id (R4.3); composed in install order after the kernel's |
| Module invariants | all read together with the kernel's (`INVARIANTS.module.md` per module) |
| Module migrations | keyed by module id and version; `sync` runs each module's own |

Composition (`compose.py`) takes a list of modules instead of one; the command
parity and kernel purity checks run per module.

## Steps

| Step | Content | Depends on |
|---|---|---|
| 1. Extract | Move the module seeding that `init` does today (copy into `modules/<id>/`, entity folders, definitions, recompose of CODE-OF-CONDUCT / Rules-of-Rules / Taskfile / command files) into one function, called by `init`; no behaviour change, tests unchanged | — |
| 2. `module install <path>`, first module | Local path into a deployment with no module: validate `module.yaml` with the existing loader, seed, recompose, journal one entry, record id, version, source and `sha256` (hash of the module tree) | step 1 |
| 3. `module list` / `verify` | Read the record; `verify` and a `check` rule fail on a hash mismatch (hand-edited module) | step 2 |
| 4. Git URL | `install <git-url>[@ref]`: shallow clone into a temp dir, then step 2; the commit SHA is recorded too | step 2 |
| 5. Several modules | The record becomes a list; collision checks (table above); `compose.py`, parity and purity per module; a second module installs beside the first | step 2, R4.3 namespacing |
| 6. Locator | Record into `.catalyst/catalyst.toml` (a `[[modules]]` list) instead of the `*.catalyst` pointer once R3.1 lands; legacy deployments keep the pointer's single `module` | R3.1 |
| 7. v3 format | Validate `module.yaml` v3 when R4.3 lands; v2 modules still install | R4.3 |
| 8. Upgrade | `module upgrade <id>` plans and applies through `sync plan\|apply`; each module's migrations run as in `/sync-framework` today | R2 W4 |
| 9. Signature | Verify the release feed's signature in addition to the hash | release feed (07 §10, R7) |

Steps 1–4 can start any time (they only need today's module format); 5–9
follow their dependency. Step 5 is the one that makes "several modules" real;
until it lands, installing into a deployment that already has a module is
refused with a message naming R4.3.

## Tests

- Install from a path and from a local bare git repository into a fresh
  `make_project` deployment; `catalyst check` is clean afterwards.
- The golden corpus example (`example`) re-seeded through `module install`
  yields the same composed CODE-OF-CONDUCT, Taskfile and command set as its
  capture.
- A hand-edited module file fails `module verify` and `check`.
- Two modules (the in-repo `sample-process` and a second fixture module) install
  side by side: both sets of entity types, commands and rules are composed, and
  `check` validates artifacts of both.
- A module whose entity type, ID prefix or folder collides with an installed
  one is refused, and nothing is written.
- Windows and Python 3.9 in the CI matrix, as for every verb.
