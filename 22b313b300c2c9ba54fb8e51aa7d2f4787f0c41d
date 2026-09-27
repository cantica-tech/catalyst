# Instantiation Checklist

The tickable derivative of `INSTANTIATION-GUIDE.md`. Execute catalyst installs by
working *this* list against a deployment ledger (see
`templates/ledger.template.md`), re-reading `INVARIANTS.md` every 5 items. Each
item is atomic and independently verifiable — that is what stops a long install
from drifting. The guide holds the rationale; this holds the checks.

## Preconditions
- [ ] `INVARIANTS.md` read this session
- [ ] Capabilities resolved and fallbacks chosen (`BOOTSTRAP.md §1`); mode stated
- [ ] Confirmed this is a first load ⇒ install now (INV-2)
- [ ] Path chosen: greenfield — no code yet (`INSTANTIATION-GUIDE.md §3`) /
      retrofit — existing code, no rules yet (`§4`) / neither, skeleton only

## Greenfield path (only if chosen above, `INSTANTIATION-GUIDE.md §3`)
- [ ] Dedicated dev-environment rule document + prefix picked (e.g. `env`),
      added to the rule document list
- [ ] Decision areas worked with the user: runtime/language, dependency
      policy, code style, testing, CI/CD, local dev environment, repo layout
      (skip/add per project)
- [ ] Each area's `rules/domains/<prefix>-<CODE>-<short-description>.md`
      created before its rule bullets (per `Rules-of-Rules.md` §7)
- [ ] Each rule implemented in the same pass (real config files created:
      package manifest, linter config, CI workflow, devcontainer, etc.)
- [ ] Each rule's "tested" bar met — tool/CI runs clean against the scaffold
- [ ] `{{TEST_LOCATIONS}}` for `Rules-of-Rules.md` §2 resolved from the
      testing decision

## Discover
- [ ] `dev-instructions.yaml` located, or user asked for the project name
- [ ] Project `name` resolved (defaults to target repo name)
- [ ] Optional `layout` override read, or default layout selected
- [ ] Rule document(s) and short lowercase prefixes chosen per project seams

## Deploy skeleton (into `.catalyst-proj/` at the resolved `agent-source`, INV-6)
- [ ] `agent-source` resolved (`BOOTSTRAP.md §1`) — agent-owned per-project
      storage if available, else the in-project fallback
- [ ] `CODE-OF-CONDUCT.md` created from `rules-of-development.template.md`
- [ ] `rules/Rules-of-Rules.md` created from `rules-of-rules.template.md`
- [ ] `work-items/rules-of-work-items.md` created from its template
- [ ] For **every** artifact-type folder (INV-20): `templates/` created
      (`README.md`, `templates-<type>.md` catalog seeded with a `v1` row —
      Version | File | Timestamp | Notes — and `TEMPLATE-<TYPE>-v1.md`
      copied in), the folder's own `README.md`, and its `<type>.md`
      instance catalog:
      - `rules/` → exactly one current `rules/templates/TEMPLATE-RULE-v1.md`
        (INV-8); none in rule-type dirs
      - `rules/domains/` → `domains.md` (empty index allowed)
      - `requirements/` → `requirements.md`
      - `features/` → `features.md`
      - `IAM/users/` → `users.json` (from `templates/users.template.json`,
        empty array, INV-16) — **no `templates/` here**: one JSON array,
        nothing to version
      - `IAM/roles/` → `roles.json` (from `templates/roles.template.json`,
        default agile-role mapping, INV-16) — **no `templates/` here**,
        same reason
      - `development/roadmaps/` → `roadmaps.md` (empty index allowed,
        INV-15 — individual named roadmaps created later via
        `/roadmap-add`)
      - `development/bugs/` → `bugs.md`
      - `development/house-keeping/` → `house-keeping.md`
      - `development/meta-tags/` → `meta-tags.md`
      - `work-items/epics/`, `stories/`, `tasks/`, `spikes/` → their
        `<type>.md`
      - `work-items/sprints/` (Scrum flavor) or `work-items/boards/`
        (Kanban/Scrumban flavor) → `sprints.md`/`boards.md` — skip
        whichever the chosen agile flavor doesn't use (`INSTANTIATION-GUIDE.md`
        §2)
      - `work-items/workflows/` → `workflows.md`
      - `work-items/tickets/` → `tickets.md` only — no `templates/`, no
        core template; reserved for plugin population
- [ ] `/user-add` run for at least one person — deployment is not
      complete with zero active users (INV-16, hard rule, stricter than
      every other on-demand artifact)
- [ ] `development/BACKLOG.md` created from `templates/backlog.template.md`
      (INV-14) — a hard requirement, not an artifact type (INV-20 doesn't
      apply — no `templates/` of its own)
- [ ] `development/journal.jsonl` created from `templates/journal.template.jsonl`
      (empty) (INV-17) — every command from this point on appends an entry
      as its last step, including the remaining steps of this deploy

## Seed content
- [ ] First rule document(s) created with `## Contents` + `## Known Bugs — Quick
      Index` headings (INV-8)
- [ ] Starter requirement doc created, tied to concrete screens/flows/components
      — on the greenfield path, the dev-environment rule document stands in for
      this since there is no product behavior yet
- [ ] Every seeded rule/domain file follows `<id>-<short-summary>.md` (INV-7)

## Discoverability
- [ ] Root `README.md` written (structure, deploy path, artifact folders)
- [ ] Per-folder `README.md` written for every artifact-type folder and
      every `templates/` subdirectory (INV-20 — see the Deploy skeleton
      list above for the full set), plus `development/`, `work-items/`,
      and `IAM/`, linked from root
- [ ] One `.claude/commands/<name>.md` created per command in
      `rules-of-development.template.md` §4 (Claude Code), each following
      `templates/slash-command.template.md` — or the documented fallback
      applied and noted in the deployed `README.md` (other agents), per
      `BOOTSTRAP.md §1`

## Finalize
- [ ] `dev-instructions.yaml` deleted after successful deploy
- [ ] `<app-name>.catalyst` written at the target project's own root, from
      `templates/catalyst-pointer.template.json`, `agent-source` set
      (INV-6) — the only catalyst artifact the target project's own repo
      ever carries
- [ ] On the no-owned-space fallback only: `.catalyst-proj/` added to the
      target project's own `.gitignore` — not needed if already there
      from a prior instantiation
- [ ] Deployment target cached in the memory tool if one is available
      (optional — `<app-name>.catalyst` and `.catalyst-proj/DEPLOYMENT.md`
      are read fresh regardless, `INSTANTIATION-GUIDE.md §6`)
- [ ] `version.txt` written to match framework `version.txt`

## Definition of done
- [ ] Every item above `[x]` in the ledger; no silent skips
- [ ] `scripts/check_deployment.py` passes (resolves `.catalyst-proj/` via
      `<app-name>.catalyst`'s `agent-source`, or the in-project fallback)
- [ ] Deployed tree presented to user; **no commit/push yet** (INV-4)
- [ ] On the retrofit path, if no work items exist yet, offered to run
      `ANALYSIS-PLAYBOOK.md` (not applicable on the greenfield path — it reads
      an existing codebase)
