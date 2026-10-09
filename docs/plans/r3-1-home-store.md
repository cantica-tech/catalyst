# R3.1 (+ R3.1a, R2 W5): the criterion in `$HOME/.catalyst`

**Decided:** ADR-010 (revised 2026-10-08); requirement and owner answers in
`what-is-going-on/13-criterion-home-requirement.md`; sharing backends in `…/14-sharing-backends.md`.

A project's only tracked file is `catalyst.toml` at its root; its criterion lives at
`$HOME/.catalyst/projects/<name>/criterion` (`CATALYST_HOME` overrides `$HOME/.catalyst`, for
tests and CI); each criterion runs from its own `.venv`. Python floor 3.11 (stdlib `tomllib`).
Legacy deployments (`<name>.catalyst` + `.criterion` symlink or submodule) are read for one
minor (ADR-009) and moved with `catalyst move`.

## Stages (each tested, each shippable)

Progress: **A, B done** (`e6d6c50`); **C done** (`dadedc1`); **D done** (`f465a2d`); **E done** (`17a73fa`, `1c98f5d`; catalyst's own deployment moved, `46883e4`); **F done** (sharing in the home store, the hook). Next: the UI repo (its resolver, CI, hooks), then its move; G; H.

| # | Stage | Content | Done when |
|---|---|---|---|
| A | **`catalyst.toml`** | one reader/writer for the project file: `catalyst.toml` (stdlib `tomllib`, imported only when a TOML file is read, so legacy JSON pointers still work on the 3.9 `python3` deployments run today) else the legacy `*.catalyst` JSON, same fields | every command works with either file |
| B | **Resolver** | `catalyst where`: the nearest `catalyst.toml` (or legacy pointer) → `$CATALYST_HOME/projects/<name>/criterion`, else the legacy `.criterion`; `Deployment` and `module_loader`/`check_deployment` resolve through it; journal paths keep the logical `.criterion/` prefix | a deployment with no `.criterion` in the project is found from anywhere inside it |
| C | **Runtime** (R3.1a) + **floor 3.11** | `requires-python >=3.11`, CI matrix 3.11 + 3.13 — only now, when every criterion brings its own Python; `$CATALYST_HOME/runtimes/<version>/`: a venv (uv `--relocatable`, else `python -m venv`) with `catalyst.pyz` in site-packages and a `.pth` naming it; copied into `<criterion>/.venv` when a criterion is created or loaded; launcher `$CATALYST_HOME/bin/catalyst` (POSIX sh, and `.cmd` on Windows) resolves the criterion and runs its `.venv` Python `-m catalyst`; hooks call `catalyst` | two criteria pinned to different versions run side by side; no activation |
| D | **`init` to the home store** | `init` writes `catalyst.toml`, the criterion at `$CATALYST_HOME/projects/<name>/criterion` with its `.venv`, no symlink, no `.gitignore` entry; `--at` and the in-project fallback retired (legacy only); docs (BOOTSTRAP §2, INSTANTIATION-GUIDE, CLI.md, agent shims, INVARIANTS INV-6 wording) | a fresh install leaves exactly one new file in the project |
| E | **`catalyst move`** (R2 W5) | `move --to-home` (legacy → home, `<name>.catalyst` → `catalyst.toml`, symlink/submodule removed), `move --name <new>` (rename), `move --to <machine path>` export/import replaced; journaled | the three legacy deployments can move with one command each |
| F | **Sharing** (git driver, `14`) | the criterion is its own git repository with a remote: `criterion create/join/push/sync` work on the home criterion, no submodule; product CI clones it into its own `$CATALYST_HOME` | a second machine joins with `catalyst criterion join` and finds the same criterion |
| G | **Workspace** (R3.1b) | a VS Code `<name>.code-workspace` → `$CATALYST_HOME/workspaces/<name>/criterion`: members are its folders with a `catalyst.toml`; shared rules/users/roles | deferred until A–F ship |
| H | **Release 0.48.0** | migration `0.48.0/criterion-in-catalyst-home.md`; `catalyst sync` (W4) ships with it | |

## Risks

* **Paths everywhere:** ~20 modules mention `.criterion` or `*.catalyst`. Stage B keeps the logical
  prefix so journal history stays valid; a grep gate in tests forbids new physical `.criterion` joins.
* **Hooks:** the agent's `settings.json` must call the launcher before the symlink disappears
  (stage C before D).
* **Python 3.9 users:** the uv-built runtime brings its own Python; only the plain-venv fallback
  needs a system 3.11+.
