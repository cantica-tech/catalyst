# The catalyst CLI

The mechanical steps of the framework are code, not prose. Allocating an
ID, drawing a userid, hashing files into the journal, regenerating an
index and checking the traceability chain are deterministic, so an agent
calls the `catalyst` command line for them instead of re-deriving the
procedure each time. What stays prose, in `CODE-OF-CONDUCT.md` and
`Rules-of-Rules.md`, is judgment: which rule a change serves, what its
intent is, whether two rules conflict.

The CLI is agent-agnostic and module-agnostic. It reads the kernel's
entity types (`entities/`) plus the active module's Entity Type
Definitions (`MODULE-SPECIFICATION.md`), so it knows every type a
deployment has without naming any of them. It needs Python 3 and `git`,
and nothing else.

## Invocation

In this document and every procedure that cites it, **`catalyst <args>`**
is shorthand for one of:

| Where | Command |
|---|---|
| A deployed project | `python3 .criterion/bin/catalyst.pyz <args>`, or `task catalyst -- <args>` through the deployed `Taskfile.common.yml` |
| catalyst's own repository | `task catalyst -- <args>`, or `PYTHONPATH=scripts python3 -m catalyst <args>` |

`.criterion/bin/catalyst.pyz` is a single-file zipapp. It ships inside
the kernel release as `bin/catalyst.pyz` and is copied into the working
copy at install (`INSTANTIATION-GUIDE.md`) and on every `/sync-framework`
(`SYNCHRONIZE.md`). From catalyst's own checkout, `task build:cli` builds
it into `dist/catalyst.pyz`.

Every command works on the deployment found at or above the current
directory: the project root holding the `*.catalyst` pointer, and its
working copy reached through `<project root>/.criterion` (INV-6).
`--project <dir>` starts the search elsewhere. `catalyst --version`
prints the CLI's version, which is the kernel version it shipped with.

`--working-copy <dir>` (before the subcommand) opens a bare working copy
instead: a directory holding `version.txt` and `rules/`, with no project
or pointer around it — the criterion repository checked out on its own,
as in its CI. The module is the single one under `<dir>/modules/`
(kernel-only if there is none or several), project files are out of
scope, and journal paths outside the working copy are not checked.
`check`, `validate`, `index`, `journal verify` and `criterion integrity`
work this way.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success. |
| `1` | Failure: a check found errors (or warnings under `--strict`), an argument was rejected, or a git operation failed. The reason is printed. |
| `2` | No deployment found at or above the current directory (or `--working-copy` names no working copy). |

The deployment is found by walking up from the current directory as the
shell sees it, through the `.criterion` symlink, so any directory inside
the project or its working copy works. Run from the agent-owned working
copy's real path (outside the project), the CLI refuses rather than guess
the project.

Outside any catalyst project (no `*.catalyst` pointer), `catalyst check`
exits `0` and `catalyst hook stop` exits `0`, so a fresh clone or a CI
runner is not failed. A project whose pointer exists but whose working copy
is unreachable fails: `check` exits `1`, `hook stop` exits `2`.

### Signer

Commands that write a signed value (`id next`, `id next-rule`,
`journal append`) resolve the registered user signing it
(`CODE-OF-CONDUCT.md` §2): `--as <name|git_username>` when given, else
the only active user. It never guesses from git config: with several
users and no `--as`, the command fails and the agent asks who is
signing. An unregistered user fails with a pointer to `/user-add`.

## Commands

### `catalyst check [--strict] [--json]`

Every check a deployment can run on itself, in one pass: the deployment's
structure, the traceability chain (`validate`), the journal (`journal
verify`) and index freshness (`index regen --check`). Journal warnings on
entries written before the CLI are summarised in one line
(`journal verify --legacy` lists them). Exits `1` on any error, or on any
warning under `--strict`.

### `catalyst validate [--strict] [--json]`

Validates the traceability chain against the entity type definitions.
Findings come in two levels.

**Errors** are structural breaks of the chain, always failing:

| Code | Meaning |
|---|---|
| `duplicate-id` | A rule or artifact ID is defined more than once. |
| `dangling-ref` | A reference field cites an ID that resolves to nothing. |
| `required-field` | A field the ETD marks required is missing or empty. |
| `ungrounded` | An artifact whose type grounds (`required` or `inherited`) has no resolvable grounding link (INV-5). |
| `signer` | `Signed-off-by` is missing or names an unregistered user (INV-16). |
| `id-shape` | An ID is not `<PREFIX>-NNNNNN-<registered userid>`, or its filename does not start with `<PREFIX>-NNNNNN-`. |
| `rule-unindexed` | A rule is not listed in `rules/rules.md` (INV-8). |
| `index-orphan` | An index row registers an ID that has no file. |

**Warnings** are shape mismatches in otherwise sound data; `--strict`
promotes them to errors:

| Code | Meaning |
|---|---|
| `enum-value` | An enum field holds a value outside the ETD's allowed values. |
| `backref` | A reference with a declared back-reference is not cited back. |
| `ref-type` | A reference resolves, but to a different type than the ETD expects. |
| `cardinality` | A single-reference field holds several values. |
| `retired-target` | A reference cites a retired rule. |
| `index-drift` | An artifact is missing from its index, or its row links another filename. `catalyst index regen` repairs it. |

### `catalyst hook stop [--strict]`

The same pass as `check`, shaped for an agent's end-of-turn hook: it
exits `2` with the failures on stderr so the agent keeps working until
they are fixed, and `0` otherwise. When the hook input says a stop hook
already blocked this stop, it reports the failures without blocking
again, so an unfixable failure cannot loop a session. Without a
deployment it exits `0`. See [Hooks](#hooks).

### `catalyst id next <PREFIX> [--as <user>]`

Prints the next ID for an entity type: `<PREFIX>-NNNNNN-<userid>`, where
`NNNNNN` is one above the highest number ever seen for that prefix (in
artifact files, index rows, table rows and the journal alike, so a
retired or deleted number is never reused) and `<userid>` is the signer's (INV-26).
`<PREFIX>` is any kernel or active-module type, e.g. `RECON`,
`WORKFLOW`, or a module type such as the fictional `ITEM`; an unknown
prefix fails and lists the known ones.

The command allocates nothing: two calls before the file is written
print the same ID. Create the file, then allocate the next one.

The number is unique per type and signer, not across contributors: two
contributors of a shared deployment allocating concurrently can draw the
same number, each under their own userid. Both IDs are valid and neither
is renumbered (`Rules-of-Rules.md` §6, §13).

### `catalyst id next-rule <doc-prefix> <DOMAIN> [--as <user>]`

Prints the next rule ID, `<doc-prefix>-<DOMAIN>-NNNNNN-<userid>`, with
`NNNNNN` one above the highest number the domain has seen, unique within
the domain and signer (`Rules-of-Rules.md` §3). The domain
must be registered in `rules/domains/domains.md` (`META` is always
accepted).

### `catalyst userid gen`

Prints a new userid for `/user-add`: 8 characters drawn uniformly from
`[A-Za-z0-9]` with a cryptographic random source, redrawn if it has no
uppercase letter or collides with a registered userid (INV-26).

### `catalyst journal append`

```
catalyst journal append --command <cmd> --action <action> --artifact <id|description>
                        --intent <text> [--intent <text> ...]
                        --file <path> [--file <path> ...]
                        [--target <id> ...] [--as <user>] [--allow-unchanged] [--json]
```

Appends one entry to `development/journal.jsonl` with the real UTC time,
the signer as `actor`, and each file's `before`/`after` git blob hashes
(`Rules-of-Rules.md` §12). Write the files first, then append.

- `--action` is one of `create`, `update`, `close`, `retire`,
  `status-change`, `sync`; anything else is rejected.
- `--intent` (repeatable, at least one) is the goal of the change, not a
  label for the command.
- `--file` (repeatable, at least one) is a touched path, absolute or
  relative to the current directory; it is recorded per the
  [path convention](#journal-conventions). A deleted file records
  `after: null`.
- `--target` (repeatable) is a rule or artifact ID the change serves.
- A file whose content equals its last journaled state is rejected, since
  it did not change; `--allow-unchanged` accepts it deliberately.
- `--json` prints the written entry.

### `catalyst journal verify [--strict] [--legacy] [--json]`

Checks the journal: every line is a JSON object with the required fields,
timestamps are in order, each file's `before` equals its previous
`after` (the hash chain), every referenced blob exists, CLI-written
blobs are pinned, and no journaled file changed since its last entry
(an unjournaled edit). Problems on CLI-written entries are errors;
problems on legacy entries are warnings, hidden behind a count unless
`--legacy` is given. `--strict` promotes warnings to errors.

### `catalyst journal restore <timestamp> <out>`

Materialises every journaled file as it stood at `<timestamp>` (ISO 8601,
e.g. `2026-09-27T18:00:00Z`; any offset is converted to UTC, and times are
compared as times, not strings) into the side directory `<out>`, at its
journal path. `<out>` must be absent or an empty directory: restore never
touches the live tree, never overwrites and never writes outside `<out>`. Exits `1` and lists the paths whose blob
is missing from the object store.

### `catalyst journal pin`

Pins every blob any journal entry references under `refs/catalyst/journal`
in its repository, so `git gc` can never prune it. `journal append` pins
its own blobs; run `pin` once to backfill entries written before the CLI,
and after cloning or importing a working copy.

### `catalyst index regen [--check [--diff]]`

Rewrites each per-file entity type's `<folder>/<folder>.md` index from
the artifact files themselves: in the index's ID table (the first table
with an `ID` column), one row per artifact in ID order, `ID` linking the
file, `Title` from the artifact's H1, any other column from the artifact
field of the same name. The index's prose, other tables and column
headers are kept; a column with no matching field keeps the old row's
cell; a row whose file is gone is kept as it was, so its ID is never
freed for reuse (`validate` reports it as `index-orphan`). An index is never edited by hand and never merged:
regenerate it. `--check` changes nothing and exits `1` if any index is
out of date; `--diff` also shows what would change.

Free-form types whose items are rows of a hand-edited table (the ETD's
`naming: free-form`) have no generated index; their rows stay prose-edited
per the owning command.

### `catalyst criterion <subcommand>`

Shared deployments on git (`Rules-of-Rules.md` §13, INV-18). A shared
deployment's working copy is a git submodule of the product repository
at `.criterion`, checked out from a dedicated criterion repository on
its **shared branch** (the pointer's `criterion_branch`, default
`criterion`). Contributors land changes through pull requests against
that branch.

Every subcommand fails with exit `1` and a reason on stderr when git
fails or a precondition does not hold; nothing is half-applied in the
product repository.

#### `catalyst criterion create <url> [--branch <name>]`

Turns a local-only deployment into a shared one. `<url>` is the
criterion repository: empty, or already holding this working copy's
history on `<name>` (default `criterion`). In order:

1. Refuses if `.criterion` is already a submodule, or is not a symlink
   to an agent-owned working copy (move an in-project fallback directory
   out and symlink it first).
2. Initialises the working copy as a git repository if it is not one.
3. Writes the working copy's `.gitattributes` (below) and, if absent,
   the CI workflow `.github/workflows/catalyst.yml` (below); commits any
   uncommitted change.
4. Sets `origin` to `<url>`. If `<url>` already has the branch, it must
   be contained in the working copy's history (fetch or merge it
   first), otherwise `create` refuses. Pushes the working copy to the
   branch.
5. Replaces the `.criterion` symlink with a submodule on that branch,
   drops `/.criterion` from the product's `.gitignore`, and records
   `repoed: true`, `catalyst_repo_url` and `criterion_branch` in
   `<app-name>.catalyst`.
6. Stages `.gitmodules`, the gitlink, the pointer and `.gitignore` in the
   product repository. It commits nothing: commit them when ready.

The old agent-owned copy is left in place, unused; remove it once
satisfied. Creating the remote repository itself happens on the hosting
service, beforehand.

#### `catalyst criterion join`

In a fresh clone of the product repository: initialises the `.criterion`
submodule and checks out the shared branch, so the working copy is on a
branch rather than a detached gitlink. Fails if the project has no
`.criterion` submodule. Prints the checked-out commit.

#### `catalyst criterion status [--fetch]`

Prints the mode (`submodule` or `local`), the remote, the shared branch,
the current branch, the count of uncommitted changes and, when the
remote has the shared branch, how far the working copy is ahead of and
behind it. `--fetch` fetches first. Always exits `0`.

#### `catalyst criterion push -m <message> [--as <user>] [--no-pr]`

Lands the working copy's changes as a pull request against the shared
branch. `<message>` is the commit message and pull request title; the
signer is resolved as in [Signer](#signer), and its `git_username` (else
`name`) is the commit author name and the topic branch's prefix. In
order:

1. Refuses if the working copy has no remote (`create` first). Fetches.
2. Switches to a topic branch, `<user>/<UTC timestamp>`, unless one is
   already checked out (any branch other than the shared one) whose pull
   request is still open — a topic whose branch was merged or deleted is
   replaced by a new one. If the remote topic branch holds commits this
   working copy lacks (a reviewer's suggestion), it refuses: pull them
   first. Rewrites `.gitattributes`; commits every change with
   `<message>`.
3. Rebases onto the shared branch. A conflict aborts the rebase and
   fails with the conflicting files: nothing is pushed. Resolve by hand,
   or record a proposed resolution as a `RECON-` case for a human to
   accept (`/reconcile`); never apply one automatically.
4. Regenerates the indexes (`index regen`) and, when the union merge or
   the regeneration changed an index, appends one journal entry
   (`command: "catalyst criterion push"`, `action: "update"`) recording
   their merged state, and commits it.
5. Runs `catalyst check`, then `integrity` against the shared branch
   (nothing it records may be missing). Either failing pushes nothing.
6. With no commit ahead of the shared branch, prints `nothing to push`
   and exits `0`.
7. Pushes the topic branch with an explicit lease (the remote branch must
   still be what the push built on), shares the journal pins, and, unless
   `--no-pr`, opens a pull request with `gh` (or reports the one
   already open for the branch). Without `gh`, it prints the branch to
   open a pull request from.

Once the pull request is merged, `sync` brings the result back.

#### `catalyst criterion sync`

Fast-forwards the working copy to the shared branch. Refuses while the
working copy has uncommitted changes, or commits that no remote branch
contains — at HEAD or on the local shared branch, even with HEAD
detached (`push` them first) — so it never loses local work. `join`
applies the same guard. It then
checks out the shared branch at `origin/<shared branch>`. In a product
repository, the `.criterion` gitlink has moved: commit it to pin these
rules for the product.

#### `catalyst criterion integrity [--head <rev>] [--parent <rev> ...]`

Fails (exit `1`) if a merge lost anything: every journal line, every
defined entity ID and rule ID, and every index row that a parent
recorded must still be recorded at `<rev>` (default `HEAD`). Parents
default to `<rev>`'s own parents, which fits a pull request's merge
commit in CI; `--parent` (repeatable) compares against given revisions
instead. It reads revisions straight from git, so it needs no checkout
of them.

#### `catalyst criterion protect [--yes]`

Branch protection for the shared branch on GitHub: pull requests
required (with no minimum number of approving reviews — raise it on the
host to require review), the `catalyst` status check required (strict:
up to date with the branch), no force-push, no deletion. Repository
administrators keep their override. Without `--yes`, prints the API call it
would make and changes nothing; with `--yes`, applies it with `gh api`.
Fails for a non-GitHub remote: on another host, set the equivalent by
hand. Protection is what makes the gates real — without it, anyone with
write access can push to the shared branch directly.

#### Merge-safe storage: `.gitattributes`

`create` and `push` keep one block in the working copy's `.gitattributes`,
headed by a `# catalyst:` comment, marking `merge=union` for the files
that are append-only or regenerated: `development/journal.jsonl` and
every per-file entity type's `<folder>/<folder>.md` index
(`rules/rules.md` is hand-maintained, so concurrent edits to it conflict
instead). A union merge keeps both sides' lines; `push` then regenerates
the indexes in ID order and journals every file the rebase merged. The
team's own lines in the file are kept. Everything else merges normally, and a
conflict there stops the push.

#### The CI workflow

`create` writes `.github/workflows/catalyst.yml` into the criterion
repository (never overwriting an existing one). On every pull request
against, and every push to, the shared branch it checks out the full
history and runs, from the working copy's own vendored CLI:

```
python3 bin/catalyst.pyz --working-copy . check
python3 bin/catalyst.pyz --working-copy . criterion integrity   # pull requests only
```

The job is named `catalyst`, the status check `protect` requires.

## Journal conventions

These apply to every entry the CLI writes (`Rules-of-Rules.md` §12).

- **Paths are relative to the project root.** A working-copy file is
  written `.criterion/<path>` and hashed into the working copy's own git
  repository; every other path is hashed into the project's repository.
  No path is absolute or machine-specific (INV-1, INV-6).
- **Legacy paths are normalised on read, never rewritten.** Bare paths
  (working-copy relative, the pre-0.38.0 schema), `<repo>:path` prefixes
  and absolute paths in older entries are read as their canonical form.
  The journal is append-only (INV-17): old entries stay as written.
- **Writer.** Every CLI-written entry carries
  `"writer": "catalyst/<version>"`. `verify` holds such entries to its
  errors; entries without it are legacy and only warned about.
- **Pinning.** Every journaled blob is kept reachable under
  `refs/catalyst/journal`: a commit chain whose tree holds each blob
  under its own hash. Unreachable blobs are otherwise pruned by `git gc`,
  which would break point-in-time restore.
- **Entries are written with `catalyst journal append`, never by hand.**

## Hooks

An agent that supports an end-of-turn hook registers
`catalyst hook stop` as that hook, so every turn ends with a deployment
that passes `catalyst check`. How to register it is agent-specific: the
agent's shim says how (for example, a settings template under
`agents/<agent>/` in this repository, merged into the project's agent
settings at install). An agent without hook support runs `catalyst check`
at the end of every artifact-changing command instead
(`CODE-OF-CONDUCT.md` §4).

## Related docs

- [`rules-of-rules.template.md`](rules-of-rules.template.md) §12 — the journal's schema and immutability.
- [`rules-of-development.template.md`](rules-of-development.template.md) §4 — the commands that call the CLI.
- [`INSTANTIATION-GUIDE.md`](INSTANTIATION-GUIDE.md) — vendoring the CLI and registering the hook at install.
- [`migrations/0.38.0/catalyst-cli.md`](migrations/0.38.0/catalyst-cli.md) — bringing an existing deployment onto the CLI.
- [`rules-of-rules.template.md`](rules-of-rules.template.md) §13 — shared deployments, what `catalyst criterion` guarantees.
- [`migrations/0.39.0/criterion-on-git.md`](migrations/0.39.0/criterion-on-git.md) — moving a repoed deployment onto the submodule model.
