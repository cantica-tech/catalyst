# Catalyst Invariants

The non-negotiable rules of the catalyst framework, extracted into one lean file
so they can be re-read cheaply and survive context compaction. This is the
**canonical** copy; `BOOTSTRAP.md §0` mirrors it and `INSTANTIATION-GUIDE.md §1`
is the prose origin. If those disagree with this file, this file wins and the
others should be corrected.

Keep this file short. Anything that needs explanation, examples, or rationale
belongs in the guide it came from — not here. A bloated invariants file decays
faster and is the first thing a summarizer mangles.

## Behavioural

- **INV-1 — Repo-scoped references.** Never mention a local drive, folder, or
  path when referring to catalyst. Only the git repository and repository name.
- **INV-2 — Install on first load.** First load into a project ⇒ install
  immediately via the instantiation procedure.
- **INV-3 — Name it "catalyst".** Always "catalyst" / "catalyst framework"
  thereafter, in guidance, memory, and discussion.
- **INV-4 — Assent before push.** Never push anything (project or catalyst)
  without the user's explicit assent. No target-repo commit without assent.

## Structural

- **INV-5 — Chain invariant.** No work without a traceable link down to a
  documented rule: epic → story → task → REQ/BUG/HK → rule → domain. Every
  document, domain, and rule has a stable, permanent, never-reused ID.
- **INV-6 — Working copy in agent-owned space; one tracked pointer.** The
  deployment's real working copy is a directory named `.catalyst-proj/`,
  living in **agent-owned space** resolved per the running agent
  (`BOOTSTRAP.md` §1) — never inside the developed project's own tree.
  The target project tracks exactly one file for this: `<app-name>.catalyst`
  (JSON, project root, committed — the only catalyst artifact the
  project's own repo ever carries), whose `agent-source` field names
  where the real working copy actually is. `.catalyst-proj/DEPLOYMENT.md`
  stays the source of record for deployment/repo metadata, inside the
  working copy wherever it's now rooted (unchanged in role — only its
  location moved); `<app-name>.catalyst` mirrors the same `repoed`/
  `catalyst_repo`/`catalyst_repo_url`/`created_by` fields for project-root
  visibility without resolving `agent-source` first. Fallback for an agent with no
  owned-space concept: keep `.catalyst-proj/` directly in the project
  instead, gitignored, never committed. `/thingamabob` (INV-18) is the
  opt-in, repo-backed persistence/sync layer on top of either shape —
  never a commit into the product's own repo. `/project
  create`/`remove`/`export`/`import` (INV-19) manage the lifecycle;
  `Rules-of-Rules.md` §14 has the one-time migration off the pre-pointer
  model.
- **INV-7 — Descriptive naming.** Every rule, dev-artifact, and domain file is
  `<id>-<short-summary>.md` (sub-domain: `<prefix>-<PARENT>.<SUB>-<summary>.md`).
  Bare-ID filenames are invalid.
- **INV-8 — No orphan rules.** Every rule lives in its type directory, appears in
  its local type index, and appears in the global `rules.md`. Exactly one
  *current* `TEMPLATE-RULE-vN.md` (the highest `N`), in `rules/templates/`
  (INV-20) — never at the `rules/` root directly.
- **INV-9 — Requirements, not bugs, for new work.** `FEAT-` entries are
  non-rule-linked roadmap. When work on one starts it becomes a `REQ-` (never a
  `BUG-`), which is vetted against every rule, assigned a domain, and measured.
- **INV-14 — Persisted backlog.** `development/BACKLOG.md` always exists,
  seeded from `templates/backlog.template.md`. It is never hand-edited —
  `/show-backlog` overwrites it in full every run, so it can't drift from
  the real indexes.
- **INV-15 — Machine-maintained roadmap tracking.** `development/roadmaps/`
  and its `roadmaps.md` index always exist (empty is fine); individual named
  roadmaps are created only via `/roadmap-add`. In every
  `development/roadmaps/<name>.md`, the Status/Linked columns are set only
  by the `/roadmap-*` commands and `/show-backlog` — never hand-edited.
  `/roadmap-remove` never deletes a roadmap with linked items; it retires
  it in place.
- **INV-16 — At least one active user; advisory role signing.**
  `IAM/users/users.json` and `IAM/roles/roles.json` always exist, and
  `users.json` must contain **at least one user with `"active": true`** —
  a hard requirement, not optional-if-empty like `roadmaps.md`. Every
  dev-artifact, feature, roadmap item, and work item carries a
  `Signed-off-by` field. Role checks against `roles.json` are advisory — a
  mismatch prompts for confirmation, never a hard block, since catalyst
  cannot verify who is actually typing. `/user-remove` never deletes a
  user's entry; it sets `"active": false`, and refuses (or warns) if doing
  so would leave zero active users.
- **INV-17 — Append-only, replayable journal.** `development/journal.jsonl`
  always exists (empty is fine). Every command that creates, modifies,
  closes, or retires a rule-linked artifact, rule, domain, or work item, or
  changes a `Status` field, appends exactly one entry — timestamp, actor,
  command, action, artifact ID, `targets` (rule IDs, when applicable), one
  or more `intent` statements (the goal driving the change, not just a
  label), and, per touched file, its content hash immediately before and
  immediately after (`git hash-object -w`, written to the object store so
  it's retrievable independent of any commit; `null` for create/delete).
  This makes the journal transaction-log-grade: replaying entries up to
  any timestamp and materializing each file's last `after` hash as of
  that point reconstructs the exact tree state then, via `/journal-restore`
  into a side directory — never overwriting the live tree outright.
  Entries are immutable once written: never edited, deleted, or reordered.
  Complements — does not duplicate — the `catalyst-git` plugin's
  continuous compliance auditing of a *deployed project*; this journal is
  core, applies to catalyst's own deployment too, and records history
  rather than flagging violations.
- **INV-18 — Repoed deployments sync through a dedicated repo.** A
  deployment with `repoed: true` (`.catalyst-proj/DEPLOYMENT.md` — the
  source of record, wherever `.catalyst-proj/` is now rooted; mirrored
  into `<app-name>.catalyst` at the project root per INV-6) mirrors
  `.catalyst-proj/` through a dedicated repository. `/thingamabob create
  <name> <git-info>` establishes it the first time (creates it if it
  doesn't exist, registers it as-is if it does; pushes local
  `.catalyst-proj/` as the `thingamabob` branch — the canonical, master
  version). Run again against the same repo with a different `<name>`, it
  doesn't refuse — it branches: a new branch named `<name>` off the
  current `thingamabob`, without touching `thingamabob` itself or who's
  recorded as `created_by`. `/thingamabob get <repo> <username>` is the
  join path: download `thingamabob`'s current state and check out a new
  branch for `<username>` from it, for a user who doesn't have a local
  copy yet. Both `create`'s first call and `get` also resolve the
  actor's `git_username` and rewrite every existing artifact's
  `Signed-off-by` that named their old registered `name` to it — every
  `Signed-off-by`/journal `actor` written for them from then on uses
  `git_username`, never `name`; the journal itself is never rewritten
  (INV-17), only appended with one new entry describing the migration.
  **This never supersedes INV-6**: `.catalyst-proj/` stays the
  real working copy (wherever it's rooted — agent-owned space or, on the
  fallback, in-project); the dedicated repo is an additional, synced
  backing store.

  **`create`/`get` always ask which branch the current actor will push
  to** — recorded as `thingamabob_branch` in `<app-name>.catalyst` so
  later `push` calls don't ask again. The suggested default is the
  actor's own fixed branch, `<branch-safe-name>.catalyst-proj` — **every
  git ref name derived from a user's identity (this branch, and
  `/thingamabob get`'s `<username>`) is that name's branch-safe form**
  (lowercase, non-alphanumeric runs collapsed to a single `-`, trimmed),
  since a registered display name like "Olivier Steck" is not itself a
  valid git ref component; refuse rather than silently colliding if two
  distinct names would collapse to the same form. Choosing `thingamabob`
  itself instead is valid and changes what `push` does:

  - **`thingamabob_branch` names a real contributor branch** (the
    default case, for multi-contributor deployments): `/thingamabob
    push` is vetted (`/check-rules` plus a four-eyes sub-agent pass) and
    merged into `thingamabob`; both branches are updated with the
    result, and the local `.catalyst-proj/` is refreshed to match.
    `--force` skips vetting and overwrites `thingamabob` directly
    anyway, refused for anyone but the repo's recorded `created_by`.
  - **`thingamabob_branch` is `thingamabob` itself** (single-maintainer
    mode — e.g. catalyst's own self-dogfooding, where `/dogfood`'s own
    audit already served as the vetting step): every `push` overwrites
    `thingamabob` directly, no vetting, no merge — this is the normal
    behavior in this mode, not something `--force` is needed for — still
    refused for anyone but `created_by`.
- **INV-19 — Project lifecycle commands.** `/project create <name>`
  installs a fresh deployment: a working copy in agent-owned space (or
  the in-project fallback) plus its `<app-name>.catalyst` pointer.
  `/project remove <name>` un-links the pointer locally only — the
  working copy, this agent's memory note, and any `thingamabob` repo are
  all left untouched (never delete, retire in place). `/project remove
  <name> force` additionally deletes the local working copy and this
  agent's memory note for the project — confirm explicitly first; never
  touches a `thingamabob` repo, which is a separate, externally-hosted
  artifact out of scope for a local removal. `/project export <name>
  [file]` bundles every file under the working copy into one JSON
  export. `/project import <file>` installs from a bundle, refusing if a
  deployment already exists here; `/project import <file> force`
  overwrites an existing one instead — confirm explicitly first.
- **INV-20 — Uniform artifact-type layout.** Every artifact-type
  directory carries a versioned, catalogued `templates/` subdirectory
  (`README.md`, `templates-<type>.md` catalog with a Timestamp column,
  `TEMPLATE-<TYPE>-vN.md` — files only, never a subfolder, never edited
  in place once a newer version exists) and its own `README.md`; the
  artifact-type root itself accepts files and folders at any depth for
  the actual artifacts. Domains nest under `rules/domains/` (they exist
  only to group rules). `IAM/users/`, `IAM/roles/` replace bare
  `development/users.json`/`roles.json`. `work-items/` gains `BOARD-`
  (Kanban's counterpart to `SPRINT-`) and `WORKFLOW-` (a process
  document, never itself worked) as optional types, plus a `tickets/`
  slot reserved for plugin population — no core `TICKET-` scheme.

## Plugins

- **INV-10 — Activation gate.** A plugin is not loaded unless activated via
  `/catalyzer`, and only if it carries `README.md` + `working-contract.md`.
- **INV-11 — Plugin provenance.** Every plugin has its own repository; no plugin
  is sourced from the framework repository.
- **INV-12 — Contract is canonical + stable.** Every plugin's
  `working-contract.md` carries the six metadata fields (Name, Description,
  UUID, Version, Active, Type). The UUID is generated once and never changes.
  `Version` matches the plugin's own `version.txt` and its catalog pin. The
  framework reads `Active` at startup to decide what loads.
- **INV-13 — Operate on the deployment, not on catalyst.** A plugin's runtime
  target (monitoring, auditing, mutation) is the *deployed project's* repository,
  resolved at activation time — never the catalyst framework's own repository and
  never the plugin's own installation directory under `plugins/<type>/<name>/`.
