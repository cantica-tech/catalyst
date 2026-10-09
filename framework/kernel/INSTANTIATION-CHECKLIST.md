# Instantiation Checklist

The tickable derivative of `INSTANTIATION-GUIDE.md`. Execute catalyst installs by
working *this* list against a deployment ledger (see
`templates/ledger.template.md`), re-reading `INVARIANTS.md` every 5 items. Each
item is atomic and independently verifiable — that is what stops a long install
from drifting. The guide holds the rationale; this holds the checks.

## Preconditions
- [ ] The user explicitly asked for the install (INV-2) — never on load alone
- [ ] `INVARIANTS.md` read this session
- [ ] Capabilities resolved and fallbacks chosen (`BOOTSTRAP.md §1`); mode stated
- [ ] Path chosen: greenfield — no code yet (`INSTANTIATION-GUIDE.md §3`) /
      retrofit — existing code, no rules yet (`§4`) / neither, skeleton only

## Discover (judgment — `INSTANTIATION-GUIDE.md` §1 steps 1–3)
- [ ] `dev-instructions.yaml` located, or user asked for the project name
- [ ] Project `name` resolved (defaults to target repo name); a leftover
      `layout` key reported to the user as not applied
- [ ] Rule document(s) and short lowercase prefixes chosen per project seams
      (greenfield: plus the dev-environment rule document)
- [ ] Active module chosen — no default; ask the user, listing
      `framework/modules/catalog.md`; its checkout located (`--module-dir`
      unless it sits next to the project or catalyst as `catalyst-<id>`)
- [ ] First user's git username confirmed, name from `git config user.name`
      (registered as Admin, INV-16)

## Install (mechanical — `catalyst init`, `INSTANTIATION-GUIDE.md` §1 step 4)
- [ ] `catalyst init --name <name> --module <id> [--user <name>]
      --git-username <u> --rule-doc <file>:<prefix> ...
      --agent <id> [--commands-dir <dir>] [--test-locations <where>]
      [--kernel <dir>] [--module-dir <dir>]` run from the project root and
      exited `0`; its report shows each of:
      - `CODE-OF-CONDUCT.md`, `rules/Rules-of-Rules.md`, `ACCESS-CONTROL.md`
        and `Taskfile.common.yml` composed from kernel + module (§6)
      - the module seeded whole into `modules/<module-id>/`
      - every entity folder (kernel and module, at the place each ETD
        names) with `templates/` (`README.md`, catalog with a `v1` row,
        `TEMPLATE-<TYPE>-v1.md`), `README.md` and `<folder>.md` index
        (INV-20); `rules/rules.md` and each rule document seeded with
        `## Contents` + `## Linked Artifacts — Quick Index` (INV-8); the
        module's required paths
      - `definitions/<type>.md` for every kernel and module type, plus
        `definitions/README.md` — frozen from here on (INV-23)
      - `IAM/users/users.json` with the first user (userid, Admin) and
        `IAM/roles/roles.json` (INV-16, INV-26)
      - empty `development/journal.jsonl` (INV-17), `version.txt`,
        `DEPLOYMENT.md`, root `README.md`, `bin/catalyst.pyz`
      - the criterion at `$HOME/.catalyst/projects/<name>/criterion` with its
        `.venv` runtime, and `catalyst.toml` at the project root — the only
        file added to the project (no path, INV-6; `journal_since` = the
        project's `HEAD`)
      - command files, one per command of the composed §4, if
        `--commands-dir` was given
      - the working copy's git history initialised and the install journaled
- [ ] Module's `INVARIANTS.module.md` read together with `INVARIANTS.md` (§6.4)

## Wire up (`INSTANTIATION-GUIDE.md` §1 steps 5–8)
- [ ] Where the agent supports them: `catalyst hook start` (session start)
      and `catalyst hook stop` (end of turn) registered per its shim
      (Claude Code: `agents/claude-code/settings.template.json` merged into
      the project's `.claude/settings.json`)
- [ ] No command files (other agents): each command of the composed
      `CODE-OF-CONDUCT.md` §4 exposed as a named procedure and listed in
      the deployed `README.md` (`BOOTSTRAP.md §1`)
- [ ] The project's own `Taskfile.yml` untouched (none created, none
      edited); `catalyst task` lists the criterion's common tasks
- [ ] `catalyst hook install` offered; run only on the user's assent (it
      writes `.git/hooks/commit-msg`); an existing foreign hook left for
      the user to merge
- [ ] If the project has CI: a `catalyst trace <range>` step on new commits
      offered (`--pattern-only` while local-only; `CLI.md`)
- [ ] Any document the module requires at instantiation that still carries
      `{{PLACEHOLDER}}` text populated by the command the module names
- [ ] Root `README.md` extended with the project's structure and links to
      each folder's `README.md`

## Seed content (judgment)
- [ ] Greenfield only (`INSTANTIATION-GUIDE.md §3`): decision areas worked
      with the user (runtime/language, dependency policy, code style,
      testing, CI/CD, local dev environment, repo layout — skip/add per
      project); each area's domain file created before its rules
      (`Rules-of-Rules.md` §7); each rule implemented in the same pass (real
      config files) and its "tested" bar met (tool/CI runs clean);
      `{{TEST_LOCATIONS}}` resolved from the testing decision
- [ ] Retrofit only (`§4`): rules gathered incrementally from the existing
      code, conflicts raised with the user rather than decided silently
- [ ] First rules written with IDs from `catalyst id next-rule`, each listed
      in its document's `## Contents` and in `rules.md` (INV-8)
- [ ] Starter artifacts the active module's meta-rules call for created, tied
      to concrete screens/flows/components — on the greenfield path, the
      dev-environment rule document stands in for them
- [ ] Every seeded rule/domain file follows `<id>-<short-summary>.md` (INV-7)
- [ ] Every change after the install journaled with `catalyst journal append`

## Finalize
- [ ] `dev-instructions.yaml` deleted after successful install
- [ ] Deployment target cached in the memory tool if one is available
      (optional — `<app-name>.catalyst` and `.criterion/DEPLOYMENT.md`
      are read fresh regardless, `INSTANTIATION-GUIDE.md §6`)

## Definition of done
- [ ] Every item above `[x]` in the ledger; no silent skips
- [ ] `catalyst check` reports no errors (warnings reported to the user)
- [ ] Deployed tree presented to user; **no commit/push yet** (INV-4)
- [ ] On the retrofit path, if no work items exist yet, offered to run
      `/run-analysis --bootstrap` (`.criterion/ANALYSIS-PLAYBOOK.md`; not
      applicable on the greenfield path — it reads an existing codebase)
