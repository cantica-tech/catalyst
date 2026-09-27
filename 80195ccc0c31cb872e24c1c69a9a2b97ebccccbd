# Synchronize Framework With Deployment

This framework must be kept aligned with the deployed project that uses it.
If the deployed framework is missing, outdated, or has an older version than
this framework, synchronize it before continuing with project work.

## Rule

Whenever a project is active, it must check the catalyst framework for
changes, load the latest version into memory, and, if any changes are
present, offer to apply them using this synchronization process.

Synchronization requires exactly one confirmation from the user before it
starts. After that confirmation, all subsequent framework updates for the
files and folders in the deployed framework directory must proceed without
any further authorization from the user. The synchronization process must
apply the changes automatically and repeatedly as needed to keep the
deployed framework aligned.

If the deployed framework does not exist, or if its version is missing or
lower than the current framework version, apply this synchronization process
immediately.

## Version rule

- Current framework version: see this repository's own
  `development-framework/version.txt`.
- The source of truth for the latest framework version is the `release`
  branch of `git@github.com:oliben67/catalyst.git` (or
  `https://github.com/oliben67/catalyst.git`).
- The deployed framework must have a `version.txt` file.
- If `version.txt` is missing or contains a version lower than this
  framework's own `development-framework/version.txt`, treat the
  deployment as out of date and synchronize it.

## Slash-command behavior for `/sync-framework`

When the command `/sync-framework [latest|<version>] [--force <scope>]` is entered:

1. If the first argument is `latest`, inspect the `release` branch and resolve
   the newest available tagged release. If a specific version is supplied,
   inspect the `release` branch for the matching tagged release. If that tag
   exists, load that version into memory and use it as the synchronization
   target.
2. If no version argument is provided, synchronize against the currently
   installed local version rather than looking up a remote release.
3. Build a diff between the currently installed deployment and the target
   framework version before applying changes, and use that diff as the basis
   for the synchronization plan.
4. If the requested version differs from the version currently deployed,
   synchronize the deployment using the already-present deployment state as
   the baseline, preserving any project-local adjustments that are still
   valid.
5. If the requested version is the same as the currently deployed version,
   load that version into memory, discard the old in-memory copy, and perform
   a synchronization against the already-present deployment contents.
6. If a requested version does not exist as a tag, stop and report that the
   requested release is unavailable rather than silently falling back to an
   unrelated version.
7. Before applying any per-item refresh, inspect the project root `.frozen`
   file. If the target item path is listed there, skip it unless the command
   includes `--force <type>`, `--force <item-id>`, or `--force all`.
8. When an item is refreshed successfully, remove its path from `.frozen` so
   the refreshed version is no longer considered frozen.
9. Before the sync is considered complete, normalize the names and markdown
   filenames of any deployed items whose current names are only the bare ID or
   otherwise lack a summary suffix. Rename them to the required format
   **`<id>-<short-summary>`** and their corresponding files to
   **`<id>-<short-summary>.md`** using their existing title/description
   content, then update every index entry, link, and reference that points to
   the old name or old filename. The same normalization is a hard requirement
   for domain files under `rules/domains/`: any file still named only
   `<prefix>-<CODE>.md` (or `<prefix>-<PARENT>.<SUB>.md` for a sub-domain)
   must be renamed to `<prefix>-<CODE>-<short-summary>.md` (or
   `<prefix>-<PARENT>.<SUB>-<short-summary>.md`), using the domain's own
   `Scope` field as the source for the summary, then every reference to the
   old filename updated accordingly.
10. Check `## Version-specific one-time migrations` below for any entry
    whose "From" version is at or above the project's own `version.txt`
    value *before* this synchronization run started. Run each such entry
    exactly once, as part of this same run, reporting flagged items to the
    user per that entry's own steps rather than applying them silently. Do
    not re-run an entry on a project whose pre-sync `version.txt` already
    reflected a version past that entry's "From" version.
11. Never deactivate an already-active plugin as a side effect of applying a
    new framework version. A plugin stays active across the sync unless its
    entry in the relevant `plugins/<type>/catalog.md` explicitly excludes
    the target framework version via the `Compatibility` field — a bare `*`,
    or an absent field, is never grounds for deactivation. Only deactivate a
    plugin when that field names a version or range that excludes the
    target version, and report which plugin was deactivated and why.
12. Never treat a deployed project's `plugins/<type>/catalog.md` or any
    installed plugin directory under `plugins/<type>/<name>/` as framework
    template content to overwrite wholesale. Once a project has registered
    or activated any plugin, that catalog and those directories are
    project-owned state, not framework state: synchronization may only
    merge into a `catalog.md` — adding rows for newly available plugins
    not yet present there, and refreshing the pinned `Release`/`Tag`/
    `Compatibility` columns of a row that already exists — and must never
    delete an existing row, blank the file, or delete or replace an
    installed plugin's directory contents as a side effect of the sync.
    If a plugin's row or directory would otherwise be missing, that is a
    `/catalyzer activate`/`download` action for the user to take
    afterward; `/sync-framework` must never perform or silently correct it.
13. At the end of the synchronization run, perform a four-eyes verification
   pass: one sub-agent verifies the deployment against the checklist in
   [`INSTANTIATION-GUIDE.md`](INSTANTIATION-GUIDE.md), and a second
   independent sub-agent repeats the verification from a fresh perspective.
   The sync is not complete until both verifiers approve the deployment. If
   their findings conflict or either verifier reports a violation, stop and
   report the issue rather than treating the sync as complete.

## Synchronization checklist

1. Check the framework repository on the `release` branch for the latest
   version and changes.
2. Ask for exactly one confirmation before beginning the synchronization.
3. Compare the deployed framework files with the latest framework state.
4. Copy any changed templates, rules, guidance, or structure needed by the
   deployed project, including plugin content pulled directly from each
   plugin's own repository when plugin updates are required. No plugin may be
   sourced from this repository; every plugin must have its own repository.
   A deployed project's own `plugins/<type>/catalog.md` and installed plugin
   directories are project-owned state, not framework template content —
   merge into them (see item 12 of the slash-command behavior below), never
   overwrite or delete them wholesale.
5. Ensure the deployed project contains a custom root-level `README.md` that
   describes the deployed framework's structure and the project's artifact
   layout.
6. Ensure the deployed project contains the required artifacts:
   - `requirements/requirements.md`
   - `requirements/` individual requirement files
   - `features/features.md`
   - `features/` individual feature files, if any (create the folder and
     index even when empty — see the "Version-specific one-time
     migrations" section below for the one-time `BUG-`→`REQ-`
     reclassification audit that runs alongside this on eligible projects)
   - `bugs/bugs.md`
   - `bugs/` individual bug files
   - `house-keeping/house-keeping.md`
   - `meta-tags/meta-tags.md`
   - `development/BACKLOG.md` (from `templates/backlog.template.md` on
     first deploy; refreshed in full by `/show-backlog`, never
     hand-edited — see `INVARIANTS.md` INV-14). If a deployed project
     predates this requirement and has no `development/BACKLOG.md`,
     synchronizing to a version that includes it creates it from the
     template rather than skipping it as "already deployed."
   - `development/roadmaps/templates/TEMPLATE-ROADMAP-v1.md` and an empty
     `development/roadmaps/roadmaps.md` index (from
     `templates/roadmap.template.md` on first deploy — see
     `INVARIANTS.md` INV-15). Individual `development/roadmaps/<name>.md`
     files are added/updated/retired by `/roadmap-add`/`-update`/`-merge`/
     `-remove`, with Status/Linked columns refreshed by `/show-backlog`;
     synchronization must never overwrite or delete an existing named
     roadmap file, the same non-destructive treatment as an installed
     plugin directory. A deployed project that predates this requirement
     gets the folder/index created from the template on its next sync,
     not silently skipped.
   - `IAM/roles/roles.json` (from `templates/roles.template.json` on
     first deploy; entries added/changed by `/role-add`/`/role-modify` —
     never overwritten by synchronization once it exists, same
     project-owned-state treatment as an installed plugin directory) and
     `IAM/users/users.json` (from `templates/users.template.json` on
     first deploy; entries added/updated by
     `/user-add`/`-remove`/`-modify`/`-assign-role` — see `INVARIANTS.md`
     INV-16). A deployed project that predates this requirement gets both
     created from their templates on its next sync, not silently skipped
     — and if that leaves `users.json` with zero active users, prompt to
     run `/user-add` before considering the sync complete (INV-16's hard
     "at least one active user" requirement applies regardless of how the
     file came to exist).
   - `development/journal.jsonl` (from `templates/journal.template.jsonl`
     on first deploy — see `INVARIANTS.md` INV-17). Append-only: a sync
     may create this file if missing, but must never rewrite, reorder, or
     truncate a single existing line. A deployed project that predates
     this requirement gets it created empty on its next sync — synchronizing
     does not retroactively fabricate entries for history that predates
     the journal's own existence.
   - `version.txt`
   - every documented slash command from `rules-of-development.template.md`
     §4 — the canonical list; this file must never re-enumerate a subset of
     it — must be available in the deployed environment after
     synchronization. Under Claude Code: create any
     `.claude/commands/<name>.md` missing relative to that list (following
     `templates/slash-command.template.md`), and refresh an existing one
     only if this framework version actually changed that command's spec
     in `rules-of-development.template.md` §4 — an unchanged command's file
     is project-owned content like any other synced file, not something to
     overwrite wholesale on every sync.
7. Update the deployed framework's `version.txt` to the latest released
   version once synchronization is complete.

## Version-specific one-time migrations

Some framework versions introduce a one-time reclassification or cleanup
step for content a project deployed *before* that version, distinct from
the ordinary template/rule copying above. Each entry below runs **exactly
once** — the first time a deployed project's `version.txt` is advanced past
the entry's "From" version — never again on later syncs, even if the
project re-syncs to a still-later version afterward.

### From `0.3.1`: audit `BUG-` items that were actually feature requests

This framework version introduces `features/` (`Rules-of-Rules.md` §9) and
makes explicit that new feature work belongs in a `REQ-NNNNNN` requirement,
never a `BUG-NNNNNN` bug (`rules-of-development.md` §3). A project synchronized
from a framework version at or below `0.3.1` may already contain `BUG-`
items that were filed for what was actually new/desired behavior rather
than an existing rule failing to hold.

When synchronizing such a project up to a version that includes this
section, perform this audit once, as part of that same synchronization run:

1. Read every file in `bugs/` (or the project's equivalent bugs directory).
2. For each one, judge whether its `Description`/`Root cause` describes
   behavior that used to work and regressed (a real bug) versus behavior
   that was never specified or built at all (a feature gap misfiled as a
   bug). A strong signal: a `Targets` rule whose status marker is ❌ "not
   implemented" rather than a regression from a previously ✅ rule.
3. Report every flagged item to the user rather than silently
   reclassifying it. For each one the user confirms, convert it to a
   `REQ-NNNNNN` using `templates/requirements.template.md`, preserving its
   original content and `Opened` date, then retire the `BUG-NNNNNN` in place
   per `Rules-of-Rules.md` §4 with a note pointing at the new `REQ-NNNNNN`.
4. Do not repeat this audit on later syncs once the deployed project's
   `version.txt` already reflects a version that includes this section.

### From `0.10.1`: agent-owned working copy + `<app-name>.catalyst` pointer

Target version `0.11.0`. Full procedure:
`migrations/0.11.0/agent-owned-working-copy.md` (this repository) — not
duplicated here.

### From `0.11.0`: uniform artifact-type layout

Target version `0.12.0`. Full procedure:
`migrations/0.12.0/uniform-artifact-layout.md` (this repository) — not
duplicated here. Touches most of the deployed tree (nested `templates/`,
`domains/` relocation, `IAM/`, new `work-items/` types, 6-digit IDs), so
treat it as its own careful pass rather than folding it into an ordinary
template/rule sync.

## Expected outcome

After synchronization, the deployed framework should reflect the current
framework's rules, templates, and file structure, and its version should be
at least this framework's own `development-framework/version.txt`.
