# Glossary

Every term catalyst invents or uses in a sense of its own, in one place.
Each entry points to where the term is specified; that document wins if the
two ever disagree. Examples use the fictional module entity type `ITEM`
(`MODULE-SPECIFICATION.md`), never a real module's.

## Names that mean more than one thing

- **criterion.** Four related things share the name; the context says which:
  - **`.criterion`** — the *working copy* directory (see below), and the
    path `<project root>/.criterion` through which the project reaches it.
  - **the criterion repository** — the dedicated git repository a *shared*
    deployment publishes its working copy to (`Rules-of-Rules.md` §13).
  - **`/criterion`** — the command that shares a deployment and lands
    changes through it (`/criterion create`/`get`/`push`/`sync`/`status`,
    backed by `catalyst criterion`).
  - **`criterion`, the branch** — only the *default* name of the shared
    branch in the criterion repository (the pointer's `criterion_branch`
    may name another). It is not a separate concept.
- **CODE-OF-CONDUCT.md.** The deployed *rules of development*
  (`rules-of-development.template.md` plus the active module's
  contribution): how development work is proposed, tracked, journaled and
  closed, and the canonical command list (§4). It is **not** a community
  code of conduct about behaviour between people.
- **Frozen.** Two unrelated protections: a deployed *definition* is frozen
  for ever (INV-23), and `/freeze` records an item in the root-level
  `.frozen` file so `/sync-framework` leaves it alone.
- **Module.** Always a *process module* (below) — never a Python module or a
  git submodule, except where "submodule" is said explicitly.

## Terms

- **Adopt.** Accepting an *unrecorded change* (below) into the journal after
  the fact: `catalyst journal adopt <commit>` writes one entry per commit
  with `origin: manual`, the commit's sha and its git author as actor. The
  `/adopt` command drives the choice — adopt, reject (revert, with the
  user's assent) or, when contested, a `RECON-` case
  (`CODE-OF-CONDUCT.md` §9).
- **Agent-owned space.** A per-project data directory the running agent
  already maintains outside the project's tree, computed per machine from
  the agent's own conventions and never written into a tracked file. A
  local-only working copy lives there (INV-6, `BOOTSTRAP.md` §1).
- **ANALYSIS.** `ANALYSIS-NNNNNN`: the record of one four-eyes analysis of
  existing code (`/run-analysis`, `catalyst analysis`) — its scope, mode
  (`bootstrap` / `incremental`), the commit analysed, both passes, the
  reconciled findings (domains, rules, defects) and the user's decision on
  each, in `analyses/` (`ANALYSIS-PLAYBOOK.md`, `CLI.md`).
- **`<app-name>.catalyst` (the pointer).** The one small JSON file the
  product repository tracks at its root: project name, format version,
  kernel version, active module, agent, sharing fields. It holds no path
  (INV-6, `FORMAT.md` §1).
- **Baseline (`journal_since`).** The pointer field naming the product
  commit after which every commit's changes must be in the journal;
  history before it is not checked for *unrecorded changes*. `catalyst
  init` sets it to `HEAD`; `""` means the whole history; absent, nothing is
  checked and `catalyst check` warns (`FORMAT.md` §1).
- **catalyzer.** The plugin manager command, `/catalyzer`
  (`list`/`activate`/`download`/`deactivate`/`upgrade`/`downgrade`); a
  *plugin* (below) is what it manages. The `-catalyzer` commands edit the
  plugin catalog.
- **Chain, the.** The traceability path every piece of work must have:
  module artifact → grounding type (a rule) → domain, extended upward
  through work items when a project-management plugin is active (INV-5).
- **Closed-incomplete.** A `catalyst validate` error: an artifact whose
  status is one of its workflow's closed states still has a field its ETD
  marks `required_when_closed` empty (`CLI.md`,
  `MODULE-SPECIFICATION.md` §4.2).
- **Definition.** A short, versioned prose file per entity type saying what
  it is and what it is for (`definitions/`), distinct from its template's
  field shape. Frozen once deployed; moved forward only by
  `/migrate-definition` (INV-23).
- **Dogfood.** Running catalyst on its own repository: catalyst is itself a
  deployment. `/dogfood` vets that deployment (`/check-rules` plus a
  four-eyes drift check) and exists only in catalyst's repository, never in
  a deployed project (`Rules-of-Rules.md` §13).
- **Domain, sub-domain.** A named group of rules inside a rule document,
  with an uppercase code (`AUTH`) and its own file in `rules/domains/`; a
  sub-domain is `PARENT.SUB` (`Rules-of-Rules.md` §7).
- **Done-bar.** What a new rule needs before it counts as done: gathered,
  implemented, tested and documented (`Rules-of-Rules.md` §2).
- **ETD (Entity Type Definition).** The YAML file declaring one entity
  type: ID prefix, folder, location, grounding, fields and workflow
  (`MODULE-SPECIFICATION.md` §4). The CLI reads ETDs, so it knows every
  type without naming any.
- **Format, format version.** The on-disk format of a deployment — the
  pointer, the working copy's files, entity files, indexes, rules, the
  journal — specified in `FORMAT.md`. The pointer's `format` field names
  the version a deployment is written in (`1.0-rc`, declared `1.0` once
  the multi-user trial needs no change); `catalyst check` verifies the CLI
  reads it. Distinct from the kernel version, which changes far more often.
- **Four-eyes.** A check by a second, independent agent pass that has not
  seen the first pass's reasoning (`ANALYSIS-PLAYBOOK.md`). In an analysis
  it is enforced: two recorded blind passes, a reconciliation that
  accounts for every finding, a human decision on each (`ANALYSIS`).
- **Grounding, grounding type.** An artifact's link down the chain. The
  module's *grounding type* is what its artifacts ground to (the kernel
  rule); each ETD says whether its type grounds directly (`required`),
  through a parent (`inherited`), or not at all (`none`) (INV-5,
  `MODULE-SPECIFICATION.md` §5).
- **Identity migration.** A pre-0.39.0 one-time migration that rewrote
  `Signed-off-by` values to git usernames; withdrawn in 0.39.0, since a
  signer resolves by name, git username or userid.
- **INV-N (invariant).** A non-negotiable rule, numbered for ever, in
  `INVARIANTS.md` (the kernel's) or the active module's
  `INVARIANTS.module.md`. Numbers are never reused; a number that moved to
  the module keeps a placeholder in the kernel.
- **Journal.** `development/journal.jsonl`: an append-only,
  transaction-log-grade record of every change — actor, command, action,
  artifact, target rules, intent, tier, and each touched file's git blob
  hash before and after. Written only by `catalyst journal append`; never
  edited (INV-17, `Rules-of-Rules.md` §12).
- **Kernel.** The module-independent part of catalyst (`framework/kernel/`),
  versioned by the repository's root `version.txt`. It names no module
  entity (INV-3, INV-30).
- **Ledger.** The agent's written checklist for a long task, in
  `.criterion/.ledger/<task>.todo.md`, read before and ticked after each
  unit of work, so the procedure is not carried in memory (`BOOTSTRAP.md` §3).
- **Local-only vs shared (repoed).** A *local-only* deployment's working
  copy exists on one machine, in agent-owned space. A *shared* one
  (`repoed: true`) lives in a criterion repository, mounted as the product's
  `.criterion` git submodule, and changes land through pull requests
  (INV-18).
- **Meta-tag.** A lightweight `comment`/`version`/`link-to` annotation
  attached to an existing artifact, stored as `tag-<key>-<artefact-id>`
  (`/meta-tag`).
- **Pin.** Keeping every journaled blob reachable under
  `refs/catalyst/journal`, so `git gc` never prunes the history
  point-in-time restore needs (`catalyst journal pin`, `CLI.md`).
- **Plugin.** Optional capability in its own repository, loaded only once
  activated through `/catalyzer`: *background* (watches a deployed
  project) or *content-contributing* (adds artifact types or commands)
  (INV-10–INV-13, INV-22).
- **Prefix.** Either a rule document's short lowercase ID prefix (`br` in
  `br-AUTH-000003-Ab3xR9pQ`), or an entity type's uppercase ID prefix
  (`ITEM` in `ITEM-000012-Ab3xR9pQ`). Case tells them apart.
- **Process module.** A separately versioned repository contributing a
  deployment's development-artifact types — ETDs, templates, definitions,
  commands, meta-rules, invariants, tasks, migrations — composed into it
  at install and sync (`MODULE-SPECIFICATION.md`). A deployment has exactly
  one active module, named in its pointer.
- **RECON (reconciliation case).** `RECON-NNNNNN`: the durable record of two
  diverging versions of an entity and the human decision settling it,
  resolved with `/reconcile` (INV-21).
- **Re-ground.** Re-reading `INVARIANTS.md` and the active checklist after
  every five ledger items and after any context compaction, so the rules
  are not diluted out of the agent's context (`BOOTSTRAP.md` §3).
- **Rule.** A documented, ID'd statement of expected behaviour, e.g.
  `br-AUTH-000003-Ab3xR9pQ` (document prefix, domain, number, signer's
  userid). Never deleted — retired in place (`Rules-of-Rules.md` §3, §4).
- **Rules of rules, `rr-META-NNN`.** The meta-rules governing rules,
  domains, IDs and artifacts (`rules/Rules-of-Rules.md`, from
  `rules-of-rules.template.md` plus the module's contribution). Each
  section carries a stable `rr-META-NNN` ID, signed in a deployment
  (`rr-META-0000NN-<userid>`).
- **Signer, userid.** The registered user an artifact or journal entry is
  signed by (`Signed-off-by`, `--as`), and that user's 8-character userid,
  appended to every ID they create (INV-16, INV-26).
- **Spec (of a command).** Only the part of `CODE-OF-CONDUCT.md` §4 one
  command needs, printed by `catalyst spec <command>` — the canonical text,
  selected, within a 1,000-word budget (`CLI.md`).
- **Tier (ceremony tier).** How much ceremony a change carries, chosen and
  stated by the agent before starting and recorded with `catalyst journal
  append --tier`: **chore** (no rule's behaviour changes: no artifact, a
  journal entry with no targets), **fix** (restores a documented rule's
  behaviour), **feature** (new or changed behaviour). The active module
  says what each tier requires (its `CODE-OF-CONDUCT.md` §3 contribution);
  when unsure, the higher tier.
- **Traced commit.** A product commit whose message cites an artifact or
  rule ID that resolves in the deployment (full, or short without the
  userid), or whose subject starts `chore:`: the chain (INV-5) at commit
  granularity. Checked by `catalyst hook commit-msg` and `catalyst trace`
  (`CLI.md`).
- **Unrecorded change.** A product commit after the *baseline* that changes
  a file to a state (git blob) no journal entry records: work written by
  hand, straight into git. Listed by `catalyst unrecorded`, reported by
  `check`, `trace` and the commit-msg hook; a warning during the beta, an
  error from format `1.0`. Resolved by *adopting* or reverting it
  (`CODE-OF-CONDUCT.md` §9).
- **WORKFLOW.** `WORKFLOW-NNNNNN`: a repeatable multi-step procedure other
  entities may reference to guide their process; never itself work
  (INV-24).
- **Working copy.** The deployment's governance record for a project — the
  directory named `.criterion/` holding rules, artifacts, definitions,
  users, the journal and the vendored CLI. Never part of the product's own
  tree: it lives in agent-owned space (local-only) or in the criterion
  repository (shared) (INV-6).
