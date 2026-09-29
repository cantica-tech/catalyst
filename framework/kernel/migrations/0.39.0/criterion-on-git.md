# Migration 0.39.0: shared deployments on git

> Apply this migration when synchronizing a deployment whose `version.txt`
> is being advanced past `0.38.0` to `0.39.0` or later. See `SYNCHRONIZE.md`
> for the full synchronization procedure. Never re-run on a later sync once
> applied.

Until `0.38.0`, a repoed deployment kept its working copy in agent-owned
space with an `origin` remote, and `/criterion push` was a prose
protocol: per-user `<name>.criterion` branches, pushes scoped to the
actor's own signed files, an agent-vetted and AI-assisted merge into
`criterion`, then an overwrite of the local copy. From `0.39.0` sharing is
plain git, driven by the `catalyst criterion` CLI (`CLI.md`,
`Rules-of-Rules.md` §13).

## What changed

1. **The submodule.** A shared deployment's working copy is a git
   submodule of the product repository at `.criterion`, pointing at the
   criterion repository's shared branch (`criterion_branch`, default
   `criterion`). Every product commit pins the rules in force. A
   local-only deployment keeps the `0.37.0` shape: agent-owned working
   copy, gitignored `.criterion` symlink (INV-6 revised).
2. **Pull requests.** Contributors land changes with
   `catalyst criterion push`: commit, rebase onto the shared branch, check,
   push a topic branch, open a pull request. The journal and the
   generated indexes merge by union (the working copy's
   `.gitattributes`); the merged state is journaled. The criterion
   repository's CI (`.github/workflows/catalyst.yml`) runs
   `catalyst check` and `catalyst criterion integrity` on every pull
   request; `catalyst criterion protect --yes` makes that check and pull
   requests required on GitHub (INV-18 revised).
3. **No AI merge.** A real conflict stops the push with nothing pushed.
   The agent may record a proposed resolution as a `RECON-` case; a human
   accepts it with `/reconcile`.
4. **Withdrawn:** per-user `<name>.criterion` branches, single-maintainer
   mode, `/criterion push --force`, signed-object push scoping, the
   agent's vet-and-merge step, the post-push overwrite of the local copy,
   branching with `/criterion create <name>`, and the identity migration
   that rewrote `Signed-off-by` to `git_username`. `Signed-off-by`
   resolves a user by `name`, `git_username` or `userid`, so nothing is
   rewritten.
5. **Commands.** `/criterion` keeps its name and gains `sync` and
   `status`: `create <url>`, `get` (`catalyst criterion join`),
   `push <message>`, `sync`, `status`.
6. **IDs.** Numbers are unique per entity type and signer: two
   contributors may hold the same number under different userids. Never
   renumber (`Rules-of-Rules.md` §3, §6).
7. **Pointer.** `repoed`, `catalyst_repo_url` and `criterion_branch` in
   `<app-name>.catalyst`, with `.gitmodules`, record sharing.
   `catalyst_repo` and `created_by` are informational and gate nothing.

## Steps for every deployment

1. **Sync the kernel files.** Refresh the deployed `CODE-OF-CONDUCT.md`,
   `Rules-of-Rules.md`, `INVARIANTS.md`, `ACCESS-CONTROL.md` and the
   `Taskfile.common.yml` `criterion` task from the `0.39.0` kernel, and
   the agent's command files (or their fallback, `BOOTSTRAP.md` §1) from
   the recomposed `CODE-OF-CONDUCT.md` §4. Replace
   `.criterion/bin/catalyst.pyz` with the `0.39.0` release's; check it
   with `python3 .criterion/bin/catalyst.pyz criterion --help`. In
   `IAM/roles/roles.json`, replace the Admin role's withdrawn
   "/criterion push (unrestricted — not scoped to own Signed-off-by
   objects)" action with "/criterion create", as in the kernel's roles
   template.
2. **Version.** Set `.criterion/version.txt` and the pointer's
   `kernel_version` to `0.39.0`.
3. **Journal.** Append one entry with
   `catalyst journal append --command /sync-framework --action sync
   --artifact "kernel 0.39.0" --intent "<adopt shared deployments on git>"
   --file <each touched file>`. Never rewrite the journal (INV-17).

A **local-only** deployment (`repoed` false or absent) is done.

## Steps for a repoed deployment

A repoed deployment on the old model has `repoed: true` in the pointer
(or `.criterion/DEPLOYMENT.md`), a `.criterion` symlink to an agent-owned
working copy, and an `origin` remote in that working copy. One person
(anyone with push access to the criterion repository) converts it; the
others then join. Follow the steps below in order; steps 1–3 above run
inside step 2, so the sync lands on the shared branch.

1. **Land pending work.** In the working copy, commit any uncommitted
   change and push it to your old branch (`git push origin HEAD`).
   Every contributor with work that is not yet on `criterion` does the
   same, or carries it over later (step 7).
2. **Start from the shared branch.** `git fetch origin`, then
   `git checkout -B criterion origin/criterion` (or the canonical branch
   the deployment used). Now do steps 1–3 of "Steps for every
   deployment" in this working copy.
3. **Create.** From the product repository, run
   `catalyst criterion create <catalyst_repo_url>` with the URL from the
   pointer. It finds the remote branch already holding this history,
   commits the sync with `.gitattributes` and the CI workflow, pushes
   that as a fast-forward, and replaces the symlink with the submodule.
   It records `criterion_branch: criterion` even if the pointer named a
   per-user branch. If it refuses because the remote branch holds
   commits the working copy lacks, fetch and repeat step 2.
4. **Commit the product changes.** With the user's assent, commit what
   `create` staged in the product repository (`.gitmodules`, the
   `.criterion` gitlink, the pointer, `.gitignore`) and push it (INV-4).
5. **Protect** (optional, recommended). `catalyst criterion protect`
   shows what it would set; `catalyst criterion protect --yes` applies it
   on GitHub. On another host, set the equivalent by hand.
6. **Other contributors join.** Each pulls the product repository (or
   clones it afresh) and runs `catalyst criterion join`. Their old
   agent-owned copy is no longer used; they remove it once step 7 is
   done.
7. **Carry over unmerged work.** A contributor whose old branch holds
   work not on `criterion`, in the joined `.criterion`:
   `git fetch origin <name>.criterion`,
   `git checkout -b <name>/carry-over origin/<name>.criterion`, then
   `catalyst criterion push -m "<message>"`. It rebases onto the shared
   branch and opens a pull request; a conflict stops it for a human to
   resolve.
8. **Retire the per-user branches.** List them with
   `git ls-remote --heads origin '*.criterion'` and show the list to the
   user. They are obsolete; delete each one the user confirms has been
   carried over (`git push origin --delete <branch>`). Never delete a
   branch without that confirmation.

The old agent-owned working copy of the person who ran `create` is left
in place, unused; remove it once satisfied.

## Rollback

Nothing in the criterion repository's history is rewritten and no
journal line changes. Reverting the product repository's commit (remove
the submodule, restore the `.criterion` symlink to the old agent-owned
copy, `/.criterion` in `.gitignore`, and the pointer) and restoring
`version.txt`, the vendored CLI and the kernel files returns the
deployment to the `0.38.0` model. `.gitattributes` and the CI workflow
can stay in the criterion repository; they change nothing for the old
model.
