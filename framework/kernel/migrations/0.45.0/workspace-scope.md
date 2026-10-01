# Migration 0.45.0: what a deployment governs

> Apply this migration when synchronizing a deployment whose `version.txt`
> is being advanced past `0.44.x` to `0.45.0` or later. See `SYNCHRONIZE.md`
> for the full synchronization procedure. Never re-run on a later sync once
> applied.

Until `0.44.x` a deployment read every file under its directory, and the
commit-msg hook ran the CLI at the repository top — so several projects in
one repository, or a project with parts that should stay outside catalyst,
could not be kept apart. From `0.45.0` one scope rule applies everywhere.

## What changed

1. **Scope.** A deployment governs the files under it, minus nested
   directories with their own pointer (separate deployments, the inner one
   wins) and minus what a `.catalystignore` opts out — empty: its whole
   directory; with lines: those paths (`FORMAT.md` §11, `CLI.md` "What a
   deployment governs"). Changes outside catalyst, `journal adopt`,
   `trace` and `analysis start` read only the governed files; `init`
   refuses an opted-out directory and `check` reports a pointer in one.
2. **The commit-msg hook routes.** It runs the installing deployment's
   vendored CLI with `hook commit-msg --route`: each deployment owning a
   staged file checks the message and its own staged files with its own
   CLI. The old hook ran `.criterion/bin/catalyst.pyz` at the repository
   top only.
3. **Shared deployments in a subfolder.** `criterion create`, `join` and
   the submodule detection work for a project that is not the repository's
   top (`.gitmodules` at the top, path `<subdir>/.criterion`).

No layout change.

## Steps for every deployment

1. **Re-vendor the CLI.** Replace `.criterion/bin/catalyst.pyz` with the
   release's — before step 2, since the new hook calls `--route`.
2. **Reinstall the hook** where it was installed: `catalyst hook install`
   (it rewrites the hook it wrote; with the user's assent, as it writes
   into `.git/`). In a repository holding several deployments, install it
   from any one that is synced: the others are each checked by their own
   CLI, and keep their old behaviour until they sync.
3. **Opt out what catalyst should not govern** (optional): a
   `.catalystignore` in each directory to leave out. Commit it with the
   user's assent; it is a product file.
4. **Version.** Set `.criterion/version.txt` and the pointer's
   `kernel_version`.
5. **Journal and check.** One `catalyst journal append --command
   /sync-framework --action sync --artifact "kernel <version>" --file …`
   entry, then `catalyst check`.

## Rollback

Restore the previous CLI and reinstall its hook. A `.catalystignore` is
inert to a CLI before `0.45.0`.
