# 34 — One-stop install (design for the owner, 2026-11-20)

`catalyst setup`, a one-command `init`, modules from their releases, and roles
every module shares.

> **Status: decided (owner, 2026-11-20), step by step, as §9 records.** Not
> built. The kernel work is REQ-000123, the software-engineering module's is
> REQ-000124 (both in catalyst's criterion), catalyst-users' and
> knowledge-base's are a requirement each in their own criteria (§10). Builds on
> designs `21` (installing modules), `28` and `29` (identity, grants from
> catalyst-users) and `33` (landing). It adds no right: who may do what stays
> `29` and `31`'s.

## 1. The request

Standing catalyst up for a new project failed with `catalyst: module
'software-engineering' not found — pass --module-dir`, and getting past it
needed knowledge of where the module was checked out. The owner asked for one
place that installs catalyst, initializes a project, and makes the right modules
reachable, with knowledge-base always installed by default.

## 2. Today

| Step | Command | Gap |
| --- | --- | --- |
| Catalyst on the machine | A checkout, `task build:cli`, then `catalyst runtime install` for the `~/.catalyst/bin` launcher | The launcher exists only after the first run, so the first `init` needs the `.pyz`'s path |
| The agent | `catalyst agent install <agent>` | Separate, and nothing says it was done |
| Identity | `catalyst identity login --issuer <url>` | Assumes a catalyst-users provider already runs |
| The module | A `catalyst-<id>` checkout next to the project or catalyst, else `--module-dir` | Depends on folder layout. Run from the `.pyz`, the "next to catalyst" place does not exist |
| Init | `catalyst init --name … --module … --rule-doc … --agent …` | One module only; up to nine inputs |
| A second module | `catalyst module install <dir \| zip \| git URL[@ref]>` | A second command. Its recorded source is a zip name with no commit, so `module available` and `upgrade` cannot reach its repository |
| Roles | `catalyst role document`, then `catalyst-users roles provision` by hand | knowledge-base's Knowledge Curator is in neither the kernel's roles nor the module's `roles`: it was added to the shared realm by hand, so a fresh install cannot provision it |
| Groups | The realm file's fixed tree (`cantica-tech/catalyst/developers`, …) and `criteria/<name>/admins` | Not derived from what is installed |
| Judgment steps | A ledger the agent copies from `INSTANTIATION-CHECKLIST.md` by hand | Mechanical items (landing policy, hook, path detection) are left to the agent |

## 3. Per machine: `catalyst setup`

One command, safe to re-run. Each part checks first, does only what is missing,
and reports what it found:

```text
catalyst setup
  ✓ launcher       ~/.catalyst/bin/catalyst (on PATH)
  ✓ agent          claude-code wired (mcp, Stop hook, session-start hook)
  ✓ identity       logged in to <issuer> as <you>
  ✓ git access     the catalog's module repositories reachable
  ✓ profile        ~/.catalyst/profile.toml: default_modules = ["knowledge-base"], issuer, agent
```

- **Launcher:** installed from the running catalyst, whether it is a release
  `.pyz` or a checkout.
- **Agent:** `catalyst agent install <agent>`, the agent detected or asked.
- **Identity:** when no catalyst-users provider is reachable, `setup` offers
  three ways (§6): local, server, existing.
- **Git access:** `git ls-remote` against each module repository in
  `framework/modules/catalog.md`. A refusal is reported with the URL and what to
  fix (an SSH key, an access request); it does not stop the other parts.
- **Profile:** `~/.catalyst/profile.toml`, the machine's defaults, read by
  `init`: the default modules, extra module repositories (`repositories`, for a
  private module), the issuer and the agent. `default_modules` is where
  "knowledge-base by default" lives. It is a machine setting, outside the
  kernel, so the kernel still names no module (L9).

## 4. Modules come from their releases

- A module is **a git repository at a release tag**.
- `--module <id>` (a bare id) is looked up in the profile's `repositories`, then
  in `framework/modules/catalog.md`, for its repository. The release is **the
  newest tag whose `module.yaml` `kernel_version` accepts the kernel being
  installed** (`fw-STRUCTURE-000016`).
- `--module <git URL>@<tag>` is used exactly as given, for a module outside the
  catalog or a pinned release.
- `--module-dir <path>` stays, as a development override, recorded as such.
- The deployment records **the git URL, the tag and the commit**, never a zip
  name. `module available` and `module upgrade` then always have a repository to
  read.
- The fetch is temporary: the criterion keeps its own copy under
  `modules/<id>/`.
- `--module` is repeatable, and `init` adds the profile's `default_modules` to
  the ones named.

**Main and side modules.** `catalyst.toml`'s `module` is the **main** module:
the first one named, or, when none is named, the first default module. A
knowledge-base-only project (catalyst-docs) has knowledge-base as its main
module. The others are **side** modules, in `modules/modules.json`. A module
works as either (`fw-STRUCTURE-000018`).

## 5. Per project: `catalyst init`

- **Runs `setup`'s checks first**, so one command works on a fresh machine.
- **Inputs:**

  | Input | Source |
  | --- | --- |
  | Project name | The folder's name, confirmed |
  | Main module | Asked: the one real choice |
  | Side modules | The profile's `default_modules` |
  | Rule documents | Asked, offering `<name>-rules.md:br` |
  | Identity issuer, agent | The profile |
  | User, git username | git config |
  | Kernel | This catalyst's |
  | Test locations | Later, in the judgment steps |

  Every flag stays, so an agent or CI can run `init` without prompts.
- **Asking:** in a terminal, `init` prompts for what is missing. Under an agent
  it **exits `3` with its proposal**, and the agent shows it to the user and
  re-runs with `--yes` once they agree:

  ```text
  catalyst init — proposed (re-run with --yes to apply):
    name             my-project            (folder name)
    modules          software-engineering@3.8.0 (main), knowledge-base@0.8.0 (default)
    rule documents   my-project-rules.md:br
    identity         <issuer> as <you>, Admin
    roles            provisioned from the role document (kernel roles + the modules' commands)
    groups           criteria/my-project/{admins, product-owners, developers, …}
    landing policy   standard
    commit-msg hook  install
    path             retrofit (code found) → /run-analysis --bootstrap offered after init
  ```

- **Applying, once agreed:**
  - The criterion and the modules (§4).
  - Roles provisioned and groups created (§7), with the installer as Admin.
  - `catalyst landing init --policy standard` (design `33`). The proposal is the
    Admin's assent to it.
  - The commit-msg hook installed (on by default, in the proposal). An existing
    `commit-msg` hook is left for the user to merge, as today.
  - Greenfield or retrofit detected: existing code means retrofit.
  - **The deployment ledger seeded** from `INSTANTIATION-CHECKLIST.md`, with the
    items `init` did ticked.
- **Finishing:** `init` runs `catalyst check` and reports it. What the ledger
  leaves is judgment work: module placeholders, the README, the first rules, and
  `/run-analysis --bootstrap` for a retrofit. Nothing is committed or pushed
  (L3).

## 6. When there is no catalyst-users provider

`setup` (and so `init`) offers:

```text
identity: no catalyst-users provider reachable
  1) local       Keycloak in Docker on this machine (development; no TLS)
  2) server      a host you name: Postgres + Keycloak behind a reverse proxy (production)
  3) existing    an issuer URL someone already runs → log in
```

- **Local:** catalyst-users' dev `compose.yaml` and `catalyst-users setup`, as
  its README's quick start does.
- **Server:** `setup` **generates the `deploy/` bundle**: `.env` filled from the
  answers, the secrets (`make-secrets.sh`'s), `compose.yaml` and the
  provisioning, plus the steps to run on the host and the reverse proxy and TLS
  steps. `setup` never reaches the host itself. The owner runs the bundle there,
  then `setup` resumes with option 3.
- **Existing:** `catalyst identity login --issuer <url>`.

Whichever way, provisioning ends the same (§7).

## 7. Roles every module shares, and groups from what is installed

- **The kernel's roles are the common list.** Every module, main or side, uses
  only them. A module adds its commands to a kernel role (`fw-IDENTITY-000014`)
  and never declares a role of its own. So knowledge-base works the same alone
  and beside software-engineering, and neither names the other (L9).
- **A new kernel role, `curator`:** a person answerable for a body of content.
  It exists for knowledge-base's Knowledge Curator, in a generic form that any
  module with owned content can use. The kernel does not know which module uses
  it.
- **A module lists every kernel role it uses**, with the commands it adds or
  with none (`- id: developer`).
  - software-engineering lists product-owner, scrum-master, tech-lead,
    developer, qa, release-manager and stakeholder.
  - knowledge-base lists curator (with `/kb-setup` and `/kb-build`, which only
    the curator or an Admin creates with, REQ-000114) and stakeholder for its
    readers. An existing `knowledge-curator` realm role stays, as an alias of
    `curator`.
- **Groups follow the listed roles**, named by the role's id in the plural
  (`developers`): a criterion gets `criteria/<name>/admins` and one group per
  kernel role its installed modules list. This replaces the realm file's fixed
  group tree for new criteria. Existing groups stay.
- **Re-provisioning follows the module set:** `init`, `module install` and
  `module upgrade` provision the role document again (adding only, never
  deleting) and say so in their proposal. The manual "re-provision the provider"
  migration step goes.

## 8. What this does not change

- Grants still come from the provider (`fw-IDENTITY-000008`). catalyst still
  grants nothing itself.
- `init` still refuses where catalyst is installed, and adds only
  `catalyst.toml` to the project.
- Nothing is committed, pushed or sent to a host without the owner's yes (L3).
  The exit-3 proposal is that yes for the local, mechanical part, and only for
  that.
- `--module-dir`, sibling checkouts and every existing flag keep working.

## 9. Decisions (owner, 2026-11-20)

| # | Question | Decision |
| --- | --- | --- |
| 1 | Install from releases or from checkouts | Releases. A module is a git URL at a release tag; a checkout is a development override |
| 2 | Per-machine steps | One command, `catalyst setup`, safe to re-run |
| 3 | Where "knowledge-base by default" lives | The machine profile (`default_modules`), not the kernel or the catalog |
| 4 | Does `init` run `setup`'s checks | Yes |
| 5 | Can knowledge-base be the main module on its own | Yes |
| 6 | How `init` asks under an agent | Exit `3` with the proposal; `--yes` once agreed |
| 7 | Does `init` seed the ledger | Yes, with its own items ticked |
| 8 | Does `init` set roles and the landing policy | Yes: the installer as Admin, `standard` |
| 9 | The commit-msg hook | On by default, in the proposal |
| 10 | Installing catalyst-users | `setup` offers local, server or existing |
| 11 | Modules' roles | The kernel's roles are the common list. Side modules do not borrow the main module's roles (L9) |
| 12 | knowledge-base's curator | A new generic kernel role, `curator` |
| 13 | Groups per criterion | Only for the roles the installed modules list, plus `admins` |
| 14 | A module lists every kernel role it uses | Yes, with or without commands |
| 15 | The server option | `setup` generates the bundle; it never reaches the host |
| 16 | Where the profile lives (2026-11-21) | `~/.catalyst/profile.toml` |
| 17 | Can the profile add module repositories (2026-11-21) | Yes (`repositories`), looked up before the catalog |
| 18 | Does software-engineering list stakeholder (2026-11-21) | Yes: seven roles |
| 19 | Group names (2026-11-21) | The role's id in the plural: `developers` |
| 20 | knowledge-base's readers (2026-11-21) | `stakeholder`, with no command |
| 21 | The existing `knowledge-curator` realm role (2026-11-21) | Kept as an alias of `curator` (a composite holding it); no holder moved |

## 10. The work

| Repository | Requirement | What |
| --- | --- | --- |
| catalyst (kernel) | REQ-000123 | `catalyst setup` and its profile; `init` with modules from git releases (repeatable, defaults, main and side), the exit-3 proposal, roles, landing and hook, path detection, ledger seeding and the closing check; `module install` and `upgrade` record URL, tag and commit and re-provision; the `curator` kernel role; a module lists every kernel role it uses |
| catalyst-software-engineering | REQ-000124 (in catalyst's criterion, as REQ-000118 was) | `roles` lists the seven kernel roles it uses |
| catalyst-users | its own requirement | Groups generated from the role document's listed roles; the `deploy/` bundle generator `setup` calls |
| catalyst-knowledge-base | its own requirement | `roles` lists `curator` (with `/kb-setup` and `/kb-build`) and `stakeholder` for its readers; `knowledge-curator` kept as an alias; the hand-provisioning note retired |

The kernel goes first: the other three depend on the `curator` role and on "a
module lists every kernel role it uses".
