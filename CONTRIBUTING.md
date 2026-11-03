# Contributing to catalyst

Thanks for your interest. catalyst is pre-1.0 and changes quickly; please open
an issue to discuss anything larger than a fix before sending a pull request.

## Current focus: beta readiness

catalyst is working towards a public beta. The feature freeze held while
the mechanics moved into code (the `catalyst` CLI, kernel 0.38.0) and
criterion was rebuilt on git (kernel 0.39.0); it is lifted. The bar stays:
prefer changes that make behaviour executable, verifiable or simpler over
new rules for an agent to follow, and propose a new invariant, meta-rule
or entity type as an issue first.

## Prerequisites

- git
- Python 3.11+ with `pip install -r requirements-dev.txt` (pytest)
- [go-task](https://taskfile.dev) 3.x (`task`)
- A coding agent to exercise the framework end to end (Claude Code is the
  only one tested so far)

## Branches

- `development` — where work lands; open pull requests against it.
- `main` — integrated from `development` for each version.
- `release` — what has been tagged and packaged.

## Before you open a pull request

```
task check:all   # the same checks CI runs
task test        # pytest
```

## How kernel changes are versioned

The kernel (`framework/kernel/`) is versioned by the root `version.txt`. A
change that alters what gets deployed into a project also needs:

1. a bump in `version.txt`;
2. a migration under `framework/kernel/migrations/<version>/`, plus a row in
   `framework/kernel/migrations/migrations.md` and an entry in
   `framework/kernel/SYNCHRONIZE.md`;
3. a `CHANGELOG.md` entry.

Then run `python3 scripts/gen_docs.py` (in a governed checkout it journals
the sections it rewrites, `SYNCHRONIZE.md`'s migrations table among them;
`--target <ID> --tier <tier>` names the work), journal every other file
you changed, commit, and run `task check:journaled` before pushing: it
refuses when a commit changes a governed file the journal does not record
(`catalyst unrecorded --strict`). `task release` runs it first.

CI checks the journal too (`.github/workflows/deployment-rules.yml`, job
`journal`): it clones the private criterion with a read-only deploy key
(the secret `CRITERION_DEPLOY_KEY`) and runs `catalyst unrecorded --strict`
and `catalyst trace` over the pushed or proposed commits. A commit's
journal entries reach the shared criterion only when its criterion pull
request is merged, so the order is:

1. push `development` and share the criterion (`catalyst share push`); the
   `journal` job only warns on the development push while the criterion
   pull request is open;
2. merge the criterion pull request;
3. open (or re-run) the code pull request into `main`, then into
   `release`: there the `journal` job is required and fails on any commit
   whose changes the merged criterion does not record.

Without the secret (a fork's pull request) the job says so and checks
nothing.

Every CI job has a `timeout-minutes` of about twice its usual duration.
GitHub's macOS runners now and then stall, ending cancelled or timed out
with no log; `.github/workflows/retry-stalled.yml` then reruns that Tests
run's failed jobs once, from its first attempt only, and only when every
job that did not pass is a cancelled or timed-out macOS job (a real
failure is never retried). It says why in one line;
`scripts/retry_stalled.py` decides, tested by
`tests/test_retry_stalled.py`.

Two hard rules for kernel sources: the kernel names no process module or
module entity (`INVARIANTS.md` INV-30, checked by
`scripts/check_kernel_purity.py`), and it references no downstream product.
Process modules live in their own repositories
(`framework/modules/catalog.md`).

## License

By contributing, you agree that your contributions are licensed under the
Apache License 2.0 (see `LICENSE`).
