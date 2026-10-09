# Migration 0.48.0: the criterion in catalyst's home store

> Apply this migration when synchronizing a deployment whose `version.txt`
> is being advanced past `0.47.x` to `0.48.0` or later. See `SYNCHRONIZE.md`
> for the full synchronization procedure. Never re-run on a later sync once
> applied.

Until `0.47.x` a project held its working copy behind a `.criterion` symlink
into the running agent's space, as an in-project directory, or as a git
submodule, beside a `<name>.catalyst` pointer. From `0.48.0` (ADR-010,
INV-6) the criterion lives in catalyst's own space,
`$HOME/.catalyst/projects/<name>/criterion` (`CATALYST_HOME` overrides), and
the project keeps one file, `catalyst.toml`. Legacy deployments are still
read in `0.48.x`; move them before `0.49.0`.

## What changed

1. **Where the criterion is:** `catalyst.toml` names the project; the
   criterion resolves to the home store, else a legacy `.criterion`
   (`catalyst where`).
2. **A runtime per criterion:** `catalyst runtime install` builds the
   runtime once per catalyst version, copies it into the criterion's
   `.venv`, and installs the launcher `$HOME/.catalyst/bin/catalyst`, which
   runs the project's own runtime. **Python 3.11 or later** (the uv-built
   runtime brings one).
3. **`catalyst move --to-home`** moves a legacy deployment into the home
   store — symlink, in-project directory or shared submodule (made a
   standalone repository with its branches, remote and unpushed work);
   `<name>.catalyst` becomes `catalyst.toml`.
4. **Sharing:** the criterion is its own repository with a remote;
   `catalyst criterion join` clones it into a collaborator's home store.
5. **`catalyst sync plan|apply`** does the mechanical half of
   `/sync-framework` (this migration's sync included).

## Steps for every deployment

1. **Synchronize** with `catalyst sync plan|apply --kernel <0.48.0 release>`
   (or as before): it re-vendors the CLI, refreshes the invariants (INV-6
   rewritten) and recomposes.
2. **Runtime and launcher:** `catalyst runtime install` (needs uv, or Python
   3.11+). Put `$HOME/.catalyst/bin` on `PATH` if you want `catalyst`
   anywhere.
3. **Hooks:** point the agent's hooks at the launcher — for Claude Code,
   merge `agents/claude-code/settings.template.json` into the project's
   `.claude/settings.json` (`"$HOME/.catalyst/bin/catalyst" hook start|stop`),
   a product file: commit it with the user's assent. Reinstall the
   commit-msg hook (`catalyst hook install`).
4. **Move:** with the user's assent, `catalyst move --to-home` (it stages
   the product changes; commit them with the user's assent). For a shared
   deployment, in the same product commit, switch product CI to clone the
   criterion into its own `$CATALYST_HOME` (`CLI.md` "`catalyst criterion`"),
   and tell collaborators to run `catalyst criterion join`.
5. **Version and journal:** `catalyst sync apply` set the version and
   journaled the sync; `move` journals itself; `catalyst check`.

## Rollback

Before the move: restore the previous CLI and recompose. After the move:
the criterion keeps its full history; recreate the legacy link by hand
(`ln -s` to the criterion, or `git submodule add` of its remote) and restore
`<name>.catalyst` from `catalyst.toml`.
