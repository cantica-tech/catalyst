# 35 — Providers, pull-request gates, criteria by part (2026-11-22)

Any repository provider chosen at install; pull requests as gates, both ways;
and a criterion for one part of a project, several criteria, or one for the
whole project, split, merged and moved between.

> **Status: decided (owner, 2026-11-22), step by step, as §9 records.** Not
> built. The kernel work is REQ-000125 (providers and gates) and REQ-000126
> (parts, split, merge, move); the software-engineering module's is REQ-000127,
> all in catalyst's criterion (§10). Builds on designs `25` (approval gates),
> `33` (landing) and `34` (`setup`, `init`'s proposal, the machine profile), and
> follows REQ-000123.

## 1. The request

- When installing catalyst, the user decides on a repository provider, and
  whether pull requests are gates for the overall process.
- catalyst builds a criterion for one part of a project, ignoring the others; or
  several independent criteria for different parts; or one criterion for the
  whole project. Parts can be broken off a criterion, and criteria merged.

## 2. Today

| Area | Today | Gap |
| --- | --- | --- |
| Provider | GitHub only: `scripts/catalyst/criterion.py` calls `gh`; `criterion protect` sets GitHub branch protection | No other host, no local server, no plain git |
| Criterion PRs | Design `33`: every criterion batch lands through a pull request, reviewed in catalyst or on the host | No mode without pull requests |
| Product PRs | The commit-msg hook and `catalyst trace` check that commits cite an artifact | A merge never moves an artifact; an artifact's status never blocks a merge |
| Scope | `fw-STRUCTURE-000017`: the folder holding `catalyst.toml` and below, minus nested deployments and `.catalystignore` | No criterion over several folders that are not nested; parts are implicit |
| Split, merge | None | — |

## 3. Repository providers

catalyst works from a provider's **capabilities**, not its name, through one
provider interface (pull requests, reviews, required checks, branch protection,
archiving). Nothing outside it calls a host's tool or API.

| Group | Providers | What catalyst does |
| --- | --- | --- |
| Full | GitHub (cloud, Enterprise Server), GitLab (cloud, self-hosted), Bitbucket (Cloud, Data Center), Azure DevOps, Gitea / Forgejo | Uses the host's pull requests, reviews, required checks and protection |
| Review-based | Gerrit | Maps changes and votes onto the same gates |
| Plain git | A bare repository on disk, or over SSH on any server | Supplies what the host lacks: its own review queue, a `pre-receive` hook it installs, merges read from the branch history |

`setup` asks once, as a default in `~/.catalyst/profile.toml`; `init`'s proposal
confirms it per project, and `catalyst.toml` records it. The product and its
criterion may use different providers.

```text
repository: which provider?
  1) hosted       GitHub, GitLab, Bitbucket, Azure DevOps, Gitea/Forgejo, Gerrit (URL + token)
  2) local server Forgejo in Docker on this machine (pull requests, reviews, checks: all gates work)
  3) plain git    a bare repository on disk or over SSH (catalyst's own review and push hook)
```

Forgejo is the local default: light, open source, with real pull requests, so
every gate behaves locally as it will in production.

## 4. Pull requests as gates

Three gates, each chosen at install:

| Gate | What it does | On plain git |
| --- | --- | --- |
| **(i) Criterion PRs** | Whether the criterion's own changes land through pull requests: design `33`'s landing policy, plus a mode that lands after the check alone (a solo project) | catalyst's review queue, then a fast-forward |
| **(ii) Product merges move artifacts** | A merged product pull request proposes, in the inbox, the status moves its gate rules give the artifacts its commits cite. The artifact's owner confirms each one, so a person signs it (L4) | Merges read from the branch history |
| **(iii) Artifacts gate product merges** | A required `catalyst gate` check fails a product pull request whose commits break the gate rules | The `pre-receive` hook runs the same check |

catalyst learns of a merge through a webhook to `catalyst serve` where there is
one, otherwise by reading the provider at `catalyst sync` and `check`.

**The rules** are a `pull_requests` section added to `IAM/gates.json` (design
`25`). The kernel names no type or status (L9), so **each installed module
contributes its default rules**, as it adds commands to roles. The project may
change them. software-engineering's defaults (REQ-000127):

- (iii): every commit cites an artifact (today's trace), and no cited artifact
  is `Draft`, `Rejected` or `Closed`.
- (ii): a merge proposes a cited STEP → `Done` and a cited BUG → `Fixed`. A REQ
  is closed by hand.

knowledge-base may contribute its own (for example, a merged build proposes
KBUILD → `Published`).

## 5. Parts

A **part** is a name, the paths it covers and excludes, and the criterion that
owns it, declared in the project's root `catalyst.toml`, still the only catalyst
file in the project (L5):

```toml
[parts.api]
paths   = ["services/api/**", "libs/shared/**"]
exclude = ["services/api/vendor/**"]
criterion = "shop-backend"

[parts.worker]
paths = ["services/worker/**"]
criterion = "shop-backend"

[parts.web]
paths = ["apps/web/**"]
criterion = "shop-web"

# docs/, scripts/ and the rest: claimed by no part, so ungoverned
```

| Case | Map |
| --- | --- |
| A criterion for one part, ignoring the rest | One part, e.g. `services/api/**` → `shop-backend` |
| Several independent criteria | Parts pointing at different criteria, each with its own rules, journal, roles and landing policy |
| One criterion for the whole project | One part, `**`: today's default, and what `init` writes when no part is named |

- **Routing:** the commit-msg hook, `trace`, `unrecorded` and `catalyst gate`
  find each file's criterion from the map. A commit touching two criteria cites
  an artifact from each, or is a `chore:`.
- **Checks:** a path two parts claim is an error. A criterion records the parts
  it owns, so `check` reports a map and a criterion that disagree.
- **Ungoverned paths:** `check` ignores them; `catalyst status` lists them.
- **Compatibility:** a nested `catalyst.toml` reads as one part covering its
  folder, so no existing deployment breaks.
- **References across criteria:** `<criterion>:<full ID>` cites another
  criterion's rule or artifact, read only, verified when that criterion is
  reachable. Workspaces already do this for inherited rules.

## 6. Split

```text
catalyst criterion split --parts api,worker --into shop-api
```

```text
catalyst criterion split — proposed (re-run with --yes to apply):
  new criterion    shop-api  (kernel 0.126.0, software-engineering@3.9.0, knowledge-base@0.9.0)
  parts moving     api, worker  (shop-backend keeps: billing)
  rule documents   api-rules.md (api), worker-rules.md (worker) → shop-api
                   shared-rules.md stays in shop-backend, referenced from shop-api
  artifacts        41 move (REQ 12, STEP 23, BUG 6)
                   3 undecided: they target rules on both sides → RECON cases
  people           shop-backend's groups copied to shop-api (developers 4, qa 1, admins 1)
  provider         github, cantica-tech/shop-api-criterion (new repository)
  map              catalyst.toml: parts api and worker → shop-api
```

- **Where an artifact goes:** each rule document is assigned to a part, or to
  none (shared). An artifact follows the rules it targets; a STEP follows its
  REQ, a TEST what it verifies. An artifact targeting rules on both sides is a
  `RECON-` case for a person (L4).
- **IDs never change** (L7). The new criterion's counters start above the
  highest number moved.
- **In the source**, a moved artifact leaves a retired `Moved` stub pointing to
  `shop-api:<ID>`, so old links and history keep working.
- **History** stays in the source journal. The new criterion's first entry
  records the split and the source journal's last hash; `catalyst history`
  follows it back.
- **Signers:** the new criterion gets a copy of the signers its moved artifacts
  name.

## 7. Merge and move

```text
catalyst criterion merge shop-api --into shop-backend
```

```text
catalyst criterion merge — proposed (re-run with --yes to apply):
  absorbing        shop-api → shop-backend
  checks           kernel 0.126.0 both ✓   modules compatible ✓ (software-engineering, knowledge-base)
  parts            api, worker → shop-backend
  rule documents   api-rules.md, worker-rules.md join shop-backend's
  artifacts        38 join (REQ 11, STEP 21, BUG 6); counters continue above the highest of both
  signers          2 people known in both under different userids → one person, both userids kept
  needs a person   domain API means different things in each criterion → RECON case
                   landing policies differ (standard vs reviewed) → RECON case
  afterwards       shop-api retired: read only, its references redirect to shop-backend
  map              catalyst.toml: parts api and worker → shop-backend
```

- **Direction:** one criterion is absorbed into an existing one.
- **IDs stay.** A person has a different userid in each criterion, so full IDs
  do not collide even when numbers match. An exact collision refuses the merge.
- **Signers:** the ledger gets an entry linking a person's userids (same issuer
  and subject); both keep resolving. Nothing is rewritten.
- **Journal:** the absorbed journal stays where it is; the target's merge entry
  records its last hash.
- **Refused:** different kernel versions (sync first), or modules that cannot
  sit side by side (`fw-STRUCTURE-000018`).
- **Decided by a person first** (`RECON-` cases): the same domain code meaning
  different things; different landing policies, gates or main modules.
- **Afterwards:** the absorbed criterion is retired read only, its references
  redirecting to the target. Its repository is archived on the provider only on
  the owner's yes (L3).

**Move** takes parts from one existing criterion to another, a split and a merge
in one proposal:

```text
catalyst criterion move --parts web --to shop-backend
```

## 8. What this does not change

- Grants still come from catalyst-users; nothing here grants a right.
- Nothing is pushed, archived or published without the owner's yes (L3). Each
  command's proposal is that yes only for its local part.
- IDs are never renamed, journals never rewritten, the signers ledger never
  rewritten (L7, `fw-STRUCTURE-000009`, `fw-IDENTITY-000003`).
- A deployment with one nested `catalyst.toml` and no parts works as today.

## 9. Decisions (owner, 2026-11-22)

| # | Question | Decision |
| --- | --- | --- |
| 1 | Which providers | As many as possible, by capability group, including a local server |
| 2 | The local server | Forgejo in Docker by default; a plain bare repository as the other choice |
| 3 | What "PRs as gates" means | All three: (i) criterion PRs, (ii) product merges move artifacts, (iii) artifacts gate product merges |
| 4 | Who signs a status move from a merge | Nobody automatically: proposed in the inbox, confirmed by the artifact's owner |
| 5 | Where the gate rules live | A `pull_requests` section in `IAM/gates.json` |
| 6 | The default rules | (iii) every commit cites an artifact, none `Draft`, `Rejected` or `Closed`; (ii) STEP → `Done`, BUG → `Fixed`, REQ by hand. Contributed by the module (L9) |
| 7 | Where the parts map lives | The root `catalyst.toml` |
| 8 | References across criteria | Allowed, read only, by full ID |
| 9 | Paths no part claims | Ignored by `check`, listed by `status` |
| 10 | What a moved artifact leaves in the source | A retired `Moved` stub |
| 11 | Where a moved artifact's history goes | It stays in the source journal, linked from the new criterion |
| 12 | Merge direction | Absorb into an existing criterion |
| 13 | The absorbed criterion | Retired read only, references redirect; repository archived on the owner's yes |
| 14 | Moving parts between existing criteria | Its own command, `criterion move` |

## 10. The work

| Repository | Requirement | What | New rules (❌ proposed) |
| --- | --- | --- | --- |
| catalyst (kernel) | REQ-000125 | The provider interface and its implementations; the local server in `setup`; gates (i), (ii), (iii); `gates.json` `pull_requests`; module-contributed defaults | `fw-STRUCTURE-000030`, `fw-STRUCTURE-000031` |
| catalyst (kernel) | REQ-000126 | The parts map and routing; references across criteria; `criterion split`, `merge`, `move` | `fw-STRUCTURE-000032`, `fw-STRUCTURE-000033`, `fw-STRUCTURE-000034` |
| catalyst-software-engineering | REQ-000127 (in catalyst's criterion) | Its default pull-request gates | — |

REQ-000125 goes first: REQ-000127 needs its module contribution point, and
REQ-000126's routing uses `catalyst gate`.
