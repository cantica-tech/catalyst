# Migration 0.37.0: computed working-copy location

> Apply this migration when synchronizing a deployment whose `version.txt`
> is being advanced past `0.36.0` to `0.37.0` or later. See `SYNCHRONIZE.md`
> for the full synchronization procedure. Never re-run on a later sync once
> applied.

The `<app-name>.catalyst` pointer used to record the working copy's
location in its `agent-source` field — an absolute, machine- and
user-specific path, copied again as a literal `CRITERION_DIR` into the
project's root `Taskfile.yml`. Both are tracked files, so every other
clone, CI runner and operating system inherited a path that did not exist
there, and personal paths leaked into the project's history. From
`0.37.0`, no tracked file holds a path (`INVARIANTS.md` INV-6).

## What changed

1. **Pointer carries no path.** `<app-name>.catalyst` no longer has an
   `agent-source` field. Every other field is unchanged.
2. **Computed location.** The running agent computes its agent-owned
   location per machine from its own conventions (`BOOTSTRAP.md` §1; each
   agent's shim says how). It is never written into a tracked file.
3. **One access path.** `<project root>/.criterion` is how everything
   reaches the working copy: a symlink to the agent-owned `.criterion/`,
   or, for an agent without owned space or a platform without symlinks,
   the real in-project directory. Either way it is gitignored
   (`/.criterion` in the project's `.gitignore`). The agent creates or
   repairs it at install, `/criterion get`, `/project import` and every
   session start (`BOOTSTRAP.md` §1.1).
4. **Resolution order.** Tools look for the working copy at
   `<project root>/.criterion` first, then — legacy only — at a pointer's
   `agent-source` if it names an existing directory, then at any
   tool-specific fallback (`Rules-of-Rules.md` §14). Pre-0.37.0 pointers
   may still carry `agent-source`; tools honor it until migrated.
5. **Taskfile.** The project's root `Taskfile.yml` includes
   `.criterion/Taskfile.common.yml` with `optional: true` and
   `flatten: true`, passing `AGENT_CMD` as before. There is no
   `CRITERION_DIR` var any more; a clone without `.criterion` still runs
   the project's own tasks.
6. **Agent switch.** `/switch-agent` (and the per-session check) mirrors
   the working copy into the new agent's owned location, repoints the
   symlink, and updates only the pointer's `agent` and `updated`. The
   Taskfile is no longer edited.
7. **Lifecycle.** `/project create` writes the pointer without a path,
   creates the symlink and gitignores `/.criterion`; `/project import`
   creates the symlink instead of recording a path; `/project remove` also
   removes the symlink; `/project export` never exports a path.

## Steps for deployed projects

1. **Locate.** Read the pointer's `agent-source`, if any, and verify the
   working copy exists there. If the field is absent or stale, use the
   running agent's computed owned location instead; if no working copy is
   found at either, stop and ask the user.
2. **Symlink.** Create `<project root>/.criterion` as a symlink to that
   working copy. If `.criterion/` is already a real in-project directory
   (the no-owned-space fallback), leave it as it is. On a platform without
   symlinks, move the working copy into the project as the fallback
   directory instead.
3. **Gitignore.** Add `/.criterion` to the project's `.gitignore` if it is
   not already covered.
4. **Pointer.** Remove `agent-source` from `<app-name>.catalyst`. Rename a
   legacy `framework_version` field to `kernel_version` if still present,
   and bump `updated`.
5. **Taskfile.** In the project's root `Taskfile.yml`, drop the
   `CRITERION_DIR` var and change the include to
   `taskfile: .criterion/Taskfile.common.yml` with `optional: true`
   (keep `flatten: true` and the `AGENT_CMD` var). See
   `INSTANTIATION-GUIDE.md` §1 step 5 for the full snippet. Leave the
   project's own tasks untouched.
6. **Command files.** Refresh the agent's `/project` and `/switch-agent`
   command files (or their fallback, `BOOTSTRAP.md` §1) from the composed
   `CODE-OF-CONDUCT.md` §4, whose specs changed in this version.
7. **Memory.** If the agent keeps a persistent-memory deployment note,
   replace its recorded `agent-source` with the computed working-copy
   location.
8. **Verify.** Run `scripts/check_deployment.py` and resolve every reported
   issue.
9. **Journal.** Append one entry (`action: "migrate"`, `intent`
   describing the move to a computed location, `files` covering the
   pointer, `.gitignore` and `Taskfile.yml` by content hash) — never
   rewrite the journal itself (INV-17).
10. **Version.** Set `.criterion/version.txt` and the pointer's
    `kernel_version` to `0.37.0`.

## Rollback

No artifact inside the working copy is renamed or deleted, and nothing is
moved unless a platform without symlinks forced the working copy into the
project. Deleting the symlink and restoring the pointer, `.gitignore` and
`Taskfile.yml` from the clean pre-migration git state (or the journal's
`before` hashes) reverts the migration.
