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

## Deploy skeleton (into `.criterion/` at the resolved agent-owned location, INV-6)
- [ ] Agent-owned location resolved (`BOOTSTRAP.md §1`) — agent-owned
      per-project storage if available, computed per machine and never
      recorded in a tracked file, else the in-project fallback
- [ ] Active module chosen and named in the pointer's `module` field — no
      default module; ask the user, listing `framework/modules/catalog.md`
      (`INSTANTIATION-GUIDE.md` §1 step 4)
- [ ] Active module seeded, whole, from its catalogued repository at the
      release matching this kernel version into
      `.criterion/modules/<module-id>/` (`MODULE-SPECIFICATION.md` §2, §6)
- [ ] `CODE-OF-CONDUCT.md` created from `rules-of-development.template.md`,
      with the `## 3.`/`## 4.` sections of the module's
      `code-of-conduct.module.md` inserted at the end of §3/§4 under
      `### From module <module-id>` (§6.2)
- [ ] `rules/Rules-of-Rules.md` created from `rules-of-rules.template.md`,
      with the module's `rules-of-rules.module.md` appended after the
      kernel's sections under `### From module <module-id>` (§6.1)
- [ ] Module's `INVARIANTS.module.md` read together with `INVARIANTS.md`
      (§6.4)
- [ ] For **every** artifact-type folder (INV-20): `templates/` created
      (`README.md`, `templates-<type>.md` catalog seeded with a `v1` row —
      Version | File | Timestamp | Notes — and `TEMPLATE-<TYPE>-v1.md`
      copied in), the folder's own `README.md`, and its `<type>.md`
      instance catalog:
      - `rules/` → exactly one current `rules/templates/TEMPLATE-RULE-v1.md`
        (INV-8); none in rule-type dirs
      - `rules/domains/` → `domains.md` (empty index allowed)
      - one `<folder>/` → `<folder>.md` per active-module entity type,
        at the place its ETD names, templates from the seeded module's
        `templates/` (empty indexes allowed on a fresh deployment)
      - `reconciliations/` → `reconciliations.md` (empty index allowed
        — no `RECON-` yet on a fresh deployment)
      - `workflows/` → `workflows.md` (empty index allowed — no
        `WORKFLOW-` yet on a fresh deployment)
      - `IAM/users/` → `templates/` (`TEMPLATE-USERS-v1.json` from
        `templates/users.template.json`) then `users.json` seeded from
        it (empty array, INV-16)
      - `IAM/roles/` → `templates/` (`TEMPLATE-ROLES-v1.json` from
        `templates/roles.template.json`) then `roles.json` seeded from
        it (default agile-role mapping, INV-16)
      - `development/meta-tags/` → `meta-tags.md`

      `work-items/` is **not** in this list — it's plugin-only
      (`Rules-of-Rules.md` §8, INV-22), not part of core instantiation.
      See `ARTIFACT-LAYOUT.md`'s "Optional, plugin-provided: `work-items/`"
      for what a project-management-type plugin deploys if/when one is
      activated.
- [ ] `definitions/<type>.md` created for every real entity type (INV-23),
      kernel and active module (§6.3), from the current latest
      `definitions/<type>/DEFINITION-<TYPE>-vN.md` of this framework or of
      the module, plus `definitions/README.md` — frozen
      from this point on, never touched again except by
      `/migrate-definition`
- [ ] `/user-add` run for at least one person — deployment is not
      complete with zero active users (INV-16, hard rule, stricter than
      every other on-demand artifact)
- [ ] Any non-artifact file the active module's meta-rules or invariants
      require at instantiation created from the module's `templates/` and
      populated by the command the module names
- [ ] `development/journal.jsonl` created from `templates/journal.template.jsonl`
      (empty) (INV-17) — every command from this point on appends an entry
      as its last step, including the remaining steps of this deploy

## Seed content
- [ ] First rule document(s) created with `## Contents` + `## Linked Artifacts — Quick Index`
      (the rule-document shape (`Rules-of-Rules.md` §6, INV-8)
- [ ] Starter artifacts the active module's meta-rules call for created, tied
      to concrete screens/flows/components — on the greenfield path, the
      dev-environment rule document stands in for them since there is no
      product behavior yet
- [ ] Every seeded rule/domain file follows `<id>-<short-summary>.md` (INV-7)

## Discoverability
- [ ] Root `README.md` written (structure, deploy path, artifact folders)
- [ ] `ACCESS-CONTROL.md` copied verbatim from
      `framework/kernel/ACCESS-CONTROL.md`, linked from root README
- [ ] Per-folder `README.md` written for every artifact-type folder and
      every `templates/` subdirectory (INV-20 — see the Deploy skeleton
      list above for the full set), plus `development/`, `IAM/` and
      `modules/<module-id>/`, linked from root
- [ ] One `.claude/commands/<name>.md` created per command in the composed
      `CODE-OF-CONDUCT.md` §4 — kernel plus active module (Claude Code),
      each following
      `templates/slash-command.template.md` — or the documented fallback
      applied and noted in the deployed `README.md` (other agents), per
      `BOOTSTRAP.md §1`
- [ ] `Taskfile.common.yml` deployed from
      `templates/Taskfile.common.template.yml` into `.criterion/` (agent-owned
      space per INV-6 — not this project's own tree; one task per command in
      the composed §4), with the module's `Taskfile.module.yml` tasks
      appended (`MODULE-SPECIFICATION.md` §6.5), and a project root
      `Taskfile.yml` exists resolving the deployed agent's CLI binary from
      the `*.catalyst` pointer, with
      `includes: common: {taskfile: .criterion/Taskfile.common.yml, optional: true, flatten: true, vars: {AGENT_CMD: ...}}`
      and no machine-specific path
      (see `INSTANTIATION-GUIDE.md` §1 step 5 for the full snippet) plus
      this project's own operational tasks
- [ ] catalyst CLI vendored at `.criterion/bin/catalyst.pyz` — the kernel
      release's `bin/catalyst.pyz`, or `task build:cli` from catalyst's own
      checkout (`CLI.md`) — and the deployed `Taskfile.common.yml` carries
      the `catalyst` pass-through task
- [ ] If the agent supports end-of-turn hooks: `catalyst hook stop`
      registered per its shim (Claude Code: `agents/claude-code/settings.template.json`
      merged into the project's `.claude/settings.json`)

## Finalize
- [ ] `dev-instructions.yaml` deleted after successful deploy
- [ ] `<app-name>.catalyst` written at the target project's own root, from
      `templates/catalyst-pointer.template.json`, `module` set and no
      path in it (INV-6) — the only catalyst artifact the target project's
      own repo ever carries
- [ ] `.criterion` symlink created at the target project's root, pointing
      at the agent-owned working copy (on the no-owned-space or
      no-symlink fallback, `.criterion/` is the real directory instead)
- [ ] `/.criterion` in the target project's own `.gitignore` — not needed
      if already there from a prior instantiation
- [ ] Deployment target cached in the memory tool if one is available
      (optional — `<app-name>.catalyst` and `.criterion/DEPLOYMENT.md`
      are read fresh regardless, `INSTANTIATION-GUIDE.md §6`)
- [ ] `version.txt` written to match framework `version.txt`; active module
      id and version recorded in `DEPLOYMENT.md`

## Definition of done
- [ ] Every item above `[x]` in the ledger; no silent skips
- [ ] `scripts/check_deployment.py` passes (resolves the working copy
      through the project-root `.criterion`)
- [ ] `catalyst check` reports no errors (warnings reported to the user)
- [ ] Deployed tree presented to user; **no commit/push yet** (INV-4)
- [ ] On the retrofit path, if no work items exist yet, offered to run
      `ANALYSIS-PLAYBOOK.md` (not applicable on the greenfield path — it reads
      an existing codebase)
