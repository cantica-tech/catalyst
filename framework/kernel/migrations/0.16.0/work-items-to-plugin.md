# Migration: `work-items/` moves from core to plugin-territory (INV-22)

> Target version: `0.16.0` — this is the migration that produces the
> shape `0.16.0` introduces. Triggered by `SYNCHRONIZE.md`'s
> "Version-specific one-time migrations" (`From 0.15.0`). Applies once,
> the first time a deployment's `version.txt` advances past `0.15.0` to
> `0.16.0` or later, to any project still on the pre-0.16.0 shape where
> `work-items/` is unconditional core content. Never re-run on a later
> sync once applied.

## What changed

`work-items/` (`epics/`, `stories/`, `tasks/`, `spikes/`, `sprints/`,
`boards/`, `workflows/`, `tickets/`) is no longer part of the core
uniform artifact-type layout (INV-20). It only exists in a deployment
once a project-management-type plugin extending the shared schema at
`plugins/_prototyping/project-management/agile/` (framework repository)
is activated — a new plugin capability, **content-contributing
plugins** (`Rules-of-Rules.md` §17, `INVARIANTS.md` INV-22): a plugin
that materializes artifact-type folders and/or slash commands into the
deployed project on activation, and removes exactly that content on
deactivation, never touching artifact instances the project already
created. The chain invariant (INV-5) is revised to match: without an
agile project-management plugin active, every rule-targeting
development artifact chains directly to `rule → domain`; with one active, the full
`epic → story → task →` prefix is required, same as before this
migration. **No concrete plugin exists yet** — this migration removes
`work-items/` from core; it does not hand you a replacement plugin to
activate.

## Preconditions

- Clean git working tree (or an explicit journal checkpoint) before
  starting — this is a real removal (not purely additive like most
  recent migrations), so a clean starting point makes it trivially
  revertible.
- Resolve the deployment root the normal way (`<app-name>.catalyst`'s
  `agent-source`, or the in-project fallback) before any file operation.
- **Decide what happens to any existing `work-items/` content before
  starting** — this migration does not make that decision for you. A
  deployment with real `EPIC-`/`STORY-`/etc. instances needs an explicit
  choice (see step 2) since there is currently no concrete plugin to
  hand the content to.

## Steps

1. **Remove `work-items/` from what future syncs deploy**: nothing to
   do to an *existing* deployment's own `work-items/` tree yet — this
   step is about the framework's own instantiation/sync procedure no
   longer creating one for a project that doesn't already have it.
2. **Existing `work-items/` content — confirm with the user before
   touching it**: since no concrete plugin exists to take over
   management of it, the practical options are (a) leave it in place,
   frozen — real `EPIC-`/`STORY-`/etc. instances stay, but there is no
   `/create-*` command to add more until a plugin is eventually built
   and activated; or (b) archive/export it (e.g. via a
   deployment-specific export) if the project wants it out of the live
   tree entirely. Do not silently pick one.
3. **`.claude/commands/`**: remove `create-epic.md`, `create-story.md`,
   `create-task.md`, `create-spike.md`, `create-sprint.md`,
   `create-board.md`, `create-workflow.md` if present — they're
   plugin-contributed now, not core, and no concrete plugin currently
   provides them.
4. **Re-sync governing docs**: refresh the deployed `CODE-OF-CONDUCT.md`
   and `rules/Rules-of-Rules.md` against their (now-updated) source
   templates, the same way any other `/sync-framework` pass would — in
   particular §15's "Where every artifact type actually sits" (drops
   `work-items/`), §8 (rewritten to describe the plugin-territory
   schema), and the new §17 (content-contributing plugins).
5. **Journal**: append exactly one entry for this migration (`action:
   "migrate"`, `intent` describing the removal and what happened to any
   existing `work-items/` content per step 2, `files` covering every
   touched/removed path by content hash) — per `Rules-of-Rules.md` §12.
6. **Version**: update the deployment's own `version.txt` to `0.16.0`
   (or later, if synchronizing further than this one migration in the
   same run).

## Rollback

Steps 3-4 are reversible edits/deletes of framework-governed files —
the clean pre-migration git state (or the journal checkpoint from step
5's `before` hashes) is enough to fully revert. Step 2 is the one
genuinely destructive possibility (if "archive/export" was chosen over
"leave in place") — treat that choice itself as needing the same
confirmation tier as any other hard-to-reverse action before executing
it, independent of this migration's own rollback.
