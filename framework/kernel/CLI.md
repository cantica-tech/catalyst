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
deployment has without naming any of them. It needs Python 3.11 or later
(a criterion's own runtime brings one, `catalyst runtime install`) and `git`,
and nothing else.

## Invocation

In this document and every procedure that cites it, **`catalyst <args>`**
is shorthand for one of:

| Where | Command |
|---|---|
| A deployed project | `$CATALYST_HOME/bin/catalyst <args>`, the launcher (`runtime install`); a legacy deployment: `python3 .criterion/bin/catalyst.pyz <args>` |
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
prints the CLI's version, which is the kernel version it shipped with;
a zipapp built from a git checkout appends its build, as
`<version>+g<12-char sha>`, plus `.dirty` when the sources it packed
differed from that commit.

A revision or range argument (`trace`, `unrecorded`, `journal adopt`)
that starts with `-` is rejected, so it can never reach `git` as an
option.

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

Outside any catalyst project (no `*.catalyst` pointer), `catalyst check`,
`catalyst hook stop` and `catalyst hook commit-msg` exit `0`, so a fresh
clone or a CI runner is not failed. A project whose pointer exists but whose working copy
is unreachable fails: `check` exits `1`, `hook stop` exits `2`.

### Signer

Commands that write a signed value (`id next`, `id next-rule`,
`journal append`) resolve the registered user signing it
(`CODE-OF-CONDUCT.md` §2): `--as <name|git_username>` when given, else
the only active user. It never guesses from git config: with several
users and no `--as`, the command fails and the agent asks who is
signing. An unregistered user fails with a pointer to `/user-add`.

## Commands

### `catalyst init`

```
catalyst init --name <name> --module <module-id> [--user <name>] [--git-username <u>]
              [--rule-doc <file>:<prefix> ...] [--test-locations <where>]
              [--agent <id>] [--no-runtime]
              [--kernel <framework/kernel>] [--module-dir <dir>]
```

Installs catalyst into the project (the current directory, or
`--project <dir>` given before `init`) — only ever on the user's explicit
request (INV-2); nothing runs it on load. It is the mechanical half of
`INSTANTIATION-GUIDE.md` §1 (step 4 lists everything it writes); the agent
decides its inputs and does the judgment steps after it.

- `--name` names the project; the pointer is `<name>.catalyst`.
- `--module` is the active module's id; there is no default. Without it,
  `init` installs nothing and lists the modules it finds in sibling
  checkouts named `catalyst-<id>` (next to the project or to catalyst);
  one elsewhere is given with `--module-dir`.
- `--user` and `--git-username` register the first user, as Admin, with a
  fresh userid (INV-16, INV-26). `--user` defaults to the project's
  `git config user.name`, `--git-username` to `--user`.
- `--rule-doc <file>:<prefix>` (repeatable) seeds a rule document and its
  ID prefix, e.g. `business-rules:br` (`.md` is added). Default: one
  document, `<name>-rules.md`, prefix `br`.
- `--test-locations` fills `{{TEST_LOCATIONS}}` in `Rules-of-Rules.md` §2.
- The criterion goes to `$CATALYST_HOME/projects/<name>/criterion` (default
  `$HOME/.catalyst`) and `catalyst.toml` is the only file added to the project
  (INV-6); a name already used on this machine is refused. Its runtime fills
  the criterion's `.venv` (`--no-runtime` defers it to `catalyst runtime
  install`). Legacy, for one minor: `--at <dir>` builds it in agent-owned
  space behind a gitignored `.criterion` symlink and a `<name>.catalyst`
  pointer.
- `--agent` is recorded in the pointer's `agent` field. `init` writes no
  agent file into the project: `catalyst agent install <agent>` wires the
  agent once per machine, at user level.
- `--kernel` is the `framework/kernel` directory of a catalyst checkout or
  kernel release. It defaults to the checkout the CLI runs from, so it is
  required when running a vendored `catalyst.pyz`.

It refuses (exit `1`, nothing written) if the project already has a
`catalyst.toml` (or legacy pointer) or a `.criterion` — one holding only the
install ledger (`.ledger/`) is moved into the criterion — or the criterion's
directory is not empty. On success it prints one line per step, commits nothing in the
project repository, gives the working copy its own git history, and
journals the install as the first entry. The pointer's `journal_since` is
the project's `HEAD` at install (`""` with no commit yet): the baseline
after which [changes made outside catalyst](#catalyst-unrecorded-range---json)
are checked.

### `catalyst recompose --base-kernel <dir> --base-module <dir> --kernel <dir> [--module-dir <dir>] [--check]`

Brings the deployed `CODE-OF-CONDUCT.md`, `rules/Rules-of-Rules.md`,
`ACCESS-CONTROL.md` and `Taskfile.common.yml` up to new kernel and module
templates without losing the deployment's own edits: it composes each
document from the old templates (`--base-*`, the versions the deployment
was built from) and from the new ones, and merges the difference into the
deployed file (`git merge-file`). The composition parameters (meta-rule
signer, rule documents) are read back from the deployment. A conflict is
left marked (`<<<<<<<`) and reported; exit `1` if any remains. `--check`
changes nothing and exits `1` if a document would change. Used by
`/sync-framework`; the old templates come from the previous kernel
release (or `git archive <old tag> framework/kernel`).

### `catalyst spec [<command>] [--budget <words>]`

Prints only what one command needs from the deployed `CODE-OF-CONDUCT.md`
§4 — its bullet and its "When the user enters `/<command>`" procedure —
followed by a one-line reminder of the common ending (signer, IDs, index
regeneration, journal). The canonical text is still §4; `spec` only
selects it, so an agent reads a command's few hundred words instead of the
whole document. The `catalyst mcp` prompts return it for each command;
the full document is read only when the spec points elsewhere or a
judgment needs the Rules-of-Rules sections it cites. `<command>` may be
given with or without its `/`; without one, `spec` lists every command.
An unknown command exits `1`.

`--budget <words>` checks every command's spec against a word budget and
exits `1`, listing each command over it. catalyst holds its own deployment
to **1,000 words** per command: its end-of-turn check runs
`catalyst spec --budget 1000` (`SPEC_BUDGET` in `scripts/stop_hook.py`), so a
command whose procedure outgrows the budget is split or tightened, not
left to grow.

### `catalyst check [--strict] [--json]`

Every check a deployment can run on itself, in one pass: the on-disk
format version, the deployment's structure, the traceability chain
(`validate`), the journal (`journal verify`), changes committed outside
catalyst (`unrecorded`) and index freshness
(`index regen --check`). Journal warnings on entries written before the
CLI are summarised in one line (`journal verify --legacy` lists them).
Exits `1` on any error, or on any warning under `--strict`.

**Format check.** The pointer's `format` field declares the on-disk format
the deployment is written in (`FORMAT.md`). A pointer with no `format` is
a **warning** (a deployment from before format `1.0-rc`; migration
`0.41.0` adds the field). A `format` this CLI does not read is an
**error**: update the vendored CLI, or migrate the deployment. A bare
working copy (`--working-copy`) has no pointer and skips this check.

**Unrecorded changes.** Each commit after the pointer's `journal_since`
with an [unrecorded change](#catalyst-unrecorded-range---json) is reported
at that command's level: a warning during the beta, an error from format
`1.0` or under `"strict_journal": true`. A pointer with no `journal_since`
is a warning (history not checked; migration `0.42.0` adds the field). A
bare working copy skips this check. Uncommitted changes are read only
where the deployment governs ([What a deployment governs](#what-a-deployment-governs));
OS clutter (`.DS_Store`, `Thumbs.db`, `desktop.ini`) is never reported.

### `catalyst validate [--strict] [--json]`

Validates the traceability chain against the entity type definitions.
Findings come in two levels.

**Errors** are structural breaks of the chain, always failing:

| Code | Meaning |
|---|---|
| `duplicate-id` | A rule or artifact ID is defined more than once. |
| `dangling-ref` | A reference field cites an ID that resolves to nothing. |
| `required-field` | A field the ETD marks required is missing or empty. |
| `closed-incomplete` | The artifact's `Status` is one of its workflow's closed states, but a field the ETD marks `required_when_closed` is empty (`MODULE-SPECIFICATION.md` §4.2). |
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

### `catalyst hook stop [--strict] [--format exit2|json|gemini|cursor]`

The same pass as `check`, shaped for an agent's end-of-turn hook: it
exits `2` with the failures on stderr so the agent keeps working until
they are fixed, and `0` otherwise. When the hook input says a stop hook
already blocked this stop, it reports the failures without blocking
again, so an unfixable failure cannot loop a session. Without a
deployment it exits `0`. It fails closed: an unexpected error inside the
hook (a corrupt journal, say) exits `2` with the reason, never `1`,
which agents treat as non-blocking. See [Hooks](#hooks).

While `catalyst.toml` says `governance = "suspended"` (an owner's
decision), it reports that and exits `0` without checking.

`--format` says how to block, in the agent's terms: `exit2` (the default,
Claude Code) as above; `json` prints `{"decision": "block", "reason": ...}`
and exits `0` (Codex, Copilot CLI and VS Code, Claude Code); `gemini` the
same with `"deny"` (Gemini CLI's end-of-turn hook); `cursor`
`{"followup_message": ...}`. The project is the hook input's `cwd` (or
Cursor's `workspace_roots`) when `--project` is not given.

### `catalyst hook start [--format text|json|cursor]`

The agent's session-start hook: prints the working copy's `INVARIANTS.md`
and, when the module ships one, `INVARIANTS.module.md` (both copied there
by `init`), so a deployed project's sessions start grounded. It never
blocks a session: it always exits `0`, prints nothing outside a
deployment, and one line when the working copy is unreachable.
`--format json` wraps the text as `hookSpecificOutput.additionalContext`
(Codex, Copilot, Gemini CLI), `cursor` as `additional_context`.

### `catalyst mcp`

A stdio MCP server, for any agent that speaks the Model Context Protocol;
registered once per machine at user level (`catalyst agent install`), it
writes nothing into a project. It serves the project of the client's roots,
else `CLAUDE_PROJECT_DIR`, else its working directory, else a tool call's
`cwd`:

- **prompts** — one per command of the composed `CODE-OF-CONDUCT.md` §4,
  read when listed (module commands included, named by nothing else); each
  returns the command's `catalyst spec` and its arguments. Clients that split
  typed arguments on whitespace (Claude Code) get word slots, joined back;
- **tools** — `catalyst` (`args`, optional `cwd`) runs the CLI through the
  launcher in the project's root, so each project runs its own pinned
  version; `command` (`name`, `arguments`, `cwd`) returns a command's
  procedure, or the list, for clients without MCP prompts;
- **instructions** — the deployment's invariants, as `hook start` prints them.

Through the launcher, `mcp` always runs the newest installed runtime.

### `catalyst agent install|uninstall <agent>`, `catalyst agent status`

Wires catalyst into an agent at user level — never into a project — or
removes it: `claude-code` (`claude mcp add --scope user` and the Stop hook
in `~/.claude/settings.json`), `copilot` (`~/.copilot/mcp-config.json`,
`~/.copilot/hooks/catalyst.json` — read by VS Code's agent too), `vscode`
(the user profile's `mcp.json`), `cursor` (`~/.cursor/mcp.json`,
`hooks.json`), `codex` (`[mcp_servers.catalyst]` in `~/.codex/config.toml`,
`~/.codex/hooks.json`), `gemini` (`~/.gemini/settings.json`). Only
catalyst's entries change (found by the launcher path); each file is backed
up once as `<file>.before-catalyst`; a file that is not plain JSON is left
alone and the snippet to add is printed. `agents/claude-code/plugin` is the
same wiring as a Claude Code plugin. `status` reports each agent.

### What a deployment governs

A deployment — the directory holding its `*.catalyst` pointer — governs
the files under it, except those under a nested directory with a pointer
of its own (another deployment, isolated: the inner one wins) and those a
`.catalystignore` opts out (`FORMAT.md` §11). An empty `.catalystignore`
(blank lines and `#` comments aside) opts its directory and everything
below out of catalyst; one with lines opts out those paths, relative to
its directory — a file, or a directory and everything below it;
`/`-separated, no wildcards. Changes outside catalyst (`unrecorded`,
`journal adopt`, the hook's staged files), `trace` and `analysis start`
read only what the deployment governs; `init` refuses an opted-out
directory, and `check` reports a pointer in one. The working tree's
current layout decides.

### `catalyst hook commit-msg <message-file> [--route]`

A git `commit-msg` hook: every product commit traces to the chain (INV-5
at commit granularity). It exits `0` when the message

- cites an artifact or rule ID that resolves in the deployment — in full
  (`ITEM-000012-Ab3xR9pQ`, `br-AUTH-000003-Ab3xR9pQ`) or short
  (`ITEM-000012`, `br-AUTH-000003`: the full ID with its userid dropped,
  matching one that exists); or
- has a subject line starting `chore:` or `chore(<scope>):` (any case):
  a chore changes no rule's behaviour and needs no artifact
  (`CODE-OF-CONDUCT.md` §9).

Otherwise it exits `1` and says why on stderr: no ID cited, or IDs cited
that resolve to nothing. Lines starting `#` (git's comment lines) are
ignored. A merge commit (git is concluding a merge) is let through, as
`trace` skips merges. Outside a deployment, or with its working copy
unreachable, it lets the commit through. `git commit --no-verify`
bypasses it once; `catalyst trace` in CI still catches the commit.

`--route` (what the installed hook calls, from the repository top): each
staged file goes to the deployment that owns it (nearest pointer above
it, unless opted out), and each owning deployment checks the message and
its own staged files with its own vendored CLI; the commit passes only if
all of them pass. With no owned file staged, the repository top's
deployment checks the message, if there is one; otherwise the commit
passes. So a commit spanning two projects must trace in both.

A traced message is then checked for staged product files whose content
no journal entry records ([unrecorded changes](#catalyst-unrecorded-range---json)):
a warning on stderr during the beta, a refusal (exit `1`) from format
`1.0` or under `"strict_journal": true`. Journal them first, or adopt the
commit afterwards (`catalyst journal adopt HEAD`). No `journal_since` in
the pointer: not checked.

### `catalyst hook install`

Writes the `commit-msg` hook above, executable, into the project
repository's `hooks/commit-msg` under its git directory
(`.git/hooks/commit-msg`) — one hook for every deployment the repository
holds. The hook, a short Python script, runs the installing deployment's
vendored CLI (its path from the repository top is written into the hook;
the nearest vendored CLI to a staged file when that one is gone) with
`hook commit-msg --route`, so it follows every re-vendored CLI. It refuses (exit `1`) when a
`commit-msg` hook already exists that catalyst did not write — merge the
two by hand — and rewrites its own. It writes into `.git/`, so it runs
only with the user's assent; it is offered after install
(`INSTANTIATION-GUIDE.md`). A repository that sets `core.hooksPath` must
call the hook from there.

### `catalyst trace [<range>] [--pattern-only]`

Checks that every commit in a git revision range traces, by the same rule
as `hook commit-msg`: `<range>` is anything `git log` accepts
(`main..HEAD`, `<sha>~1..<sha>`, `HEAD` for the whole history; default
`HEAD~1..HEAD`). Merge commits are skipped: they carry their parents'
trace. With a working copy, a commit that changes files but none the
deployment governs is skipped too — another project's commit in a shared
repository; a commit that changes no file at all is checked. Prints one `ERROR <sha> '<subject>': <reason>` line per commit
without a trace, then a summary; exits `1` if any, and on a bad range.

With a working copy (not `--pattern-only`) and a `journal_since` in the
pointer, it also prints one `unrecorded-change` line per commit of the
range (after the baseline) with [unrecorded changes](#catalyst-unrecorded-range---json),
as `WARNING` during the beta and `ERROR` from format `1.0` or under
`"strict_journal": true`; only at error level do they fail the trace.

`--pattern-only` needs no deployment: it accepts any well-formed full or
six-digit short ID (`<PREFIX>-NNNNNN[-<userid>]`,
`<doc-prefix>-<DOMAIN>-NNNNNN[-<userid>]`) without resolving it. Use it
where CI has no working copy — the product repository of a local-only
deployment, whose `.criterion` is gitignored. With a working copy (a
shared deployment, submodule checked out), run it without the flag so
each ID must resolve. The repository is the project root, or the current
directory with `--pattern-only` (`--project <dir>` before `trace` picks
another).

In CI, check the commits a push or pull request adds. Existing history
is not checked: start from the commit the check was introduced at. On
GitHub Actions (checkout with `fetch-depth: 0`):

```sh
if [ "$EVENT" = "pull_request" ]; then range="$BASE_SHA..$HEAD_SHA"          # the PR's commits
elif [ "$BEFORE" != "0000000000000000000000000000000000000000" ]; then
  range="$BEFORE..$SHA"                                                    # a push
else range="$SHA~1..$SHA"; fi                                              # a new branch's first push
python3 .criterion/bin/catalyst.pyz trace "$range"                          # or: trace --pattern-only
```

with `EVENT`, `BASE_SHA`, `HEAD_SHA`, `BEFORE` and `SHA` set from
`github.event_name`, `github.event.pull_request.base.sha`,
`github.event.pull_request.head.sha`, `github.event.before` and
`github.sha`. Without a working copy, run the zipapp from a catalyst
release instead of `.criterion/bin/`.

### `catalyst report [--since <date>] [--json]`

What a deployment's history says about how it is used — the measurement
side of a trial:

- journal entries and active days; entries per actor, per tier
  (`untiered` for entries without one) and per command (top ten);
- commits traced: of the product repository's non-merge commits (the
  last 200 reachable from `HEAD`, or all since `--since`), how many trace
  by the `hook commit-msg` rule;
- artifacts per entity type and `Status`; the number of reconciliation
  cases;
- commits with changes outside catalyst: those after `journal_since`
  still unrecorded, and those adopted (entries with `origin: manual`);
- `validate`'s error and warning counts.

`--since` (ISO 8601) limits journal entries and commits to that time on.
`--json` prints the same as one JSON object (`entries`, `actors`,
`tiers`, `commands`, `active_days`, `artifacts`, `reconciliations`,
`errors`, `warnings`, `commits`, `commits_traced`, `unrecorded_commits`,
`adopted_commits`). Exits `0`.
With `--working-copy` there is no product repository: commits are `0`.

### `catalyst where`, `catalyst runtime install|status`

- `where` names the project file (`catalyst.toml`, or a legacy
  `<name>.catalyst`) and the criterion it resolves to:
  `$CATALYST_HOME/projects/<name>/criterion` (`CATALYST_HOME` defaults to
  `$HOME/.catalyst`), else a legacy `.criterion`. Exit `1` when none is found.
- `runtime install` builds this version's runtime once per machine in
  `$CATALYST_HOME/runtimes/<version>/` (uv `--relocatable` when uv is
  installed, else Python's `venv`; `catalyst.pyz` sits in its site-packages),
  installs the launcher `$CATALYST_HOME/bin/catalyst` (and `catalyst.cmd`),
  and copies the runtime into the criterion's `.venv` (git-ignored). The
  launcher runs the `.venv` of the project it is called from — no activation
  — or a legacy deployment's vendored CLI. `runtime status` reports all three.

### `catalyst task [<name> [-- <arguments>]]`

Runs one of the criterion's `Taskfile.common.yml` tasks (one per command of
`CODE-OF-CONDUCT.md` §4) with [Task](https://taskfile.dev), from the
project's root; with no name, lists them. catalyst never creates, includes
or edits a project's own `Taskfile.yml`. `AGENT_CMD` (the agent's
non-interactive command) comes from `catalyst.toml`'s `agent` —
`claude-code` runs `claude -p` — unless the `AGENT_CMD` environment
variable is set. Exit: Task's own, or `1` without a criterion or Task.

### `catalyst workspace init|status <name>.code-workspace`

A VS Code workspace is a `<name>.code-workspace` file (comments and trailing
commas allowed); its members are its folders holding a `catalyst.toml`.

- `init` creates the meta criterion `$CATALYST_HOME/workspaces/<name>/criterion`
  — rules and domains, users and roles (the first user, Admin: `--user`,
  default `git config user.name`), its own journal and git repository, no
  process module — and writes `workspace = "<name>"` into each member's
  `catalyst.toml` (not committed). A member of another workspace is left
  alone; a workspace name already used on the machine is refused.
- `status` lists the folders and which are members.

A member also sees the workspace's rules, domains and users, read-only: its
artifacts may target a workspace rule, and a workspace user may sign. Its own
entries win on a clash. `catalyst where` names the workspace.

### `catalyst move --to-home | --name <new>`

- `--to-home` moves a legacy deployment into the home store
  (`$CATALYST_HOME/projects/<name>/criterion`): a `.criterion` symlink into
  agent space (its target moves), an in-project `.criterion` directory, or a
  `.criterion` git submodule — which becomes a standalone repository with its
  branches, remote and unpushed work, the product dropping the submodule.
  `<name>.catalyst` becomes `catalyst.toml`, `/.criterion` leaves
  `.gitignore`, the runtime fills the criterion's `.venv` (`--no-runtime`
  defers it), and the move is journaled. Product changes are staged, never
  committed. A name already used on the machine is refused.
- `--name <new>` renames a home-store project: its criterion directory and
  `project_name` in `catalyst.toml`.

### `catalyst sync plan|apply --kernel <dir|zip> [--module <dir|zip>]`

The mechanical half of `/sync-framework`. `--kernel` is a catalyst
checkout's `framework/kernel` or a `kernel-vX.Y.Z.zip`; `--module` the
module's checkout (reduced to what its release ships) or zip. The base the
deployment was composed from is found next to a release zip
(`…/v<deployed>/kernel-v<deployed>.zip`), or from the checkout's git tag of
the deployed version; `--base-kernel` names it otherwise.

- `plan` lists what would change — CLI, invariants, the kernel documents
  copied as they are (`ANALYSIS-PLAYBOOK.md`, `definitions/README.md`), module
  tree, governing documents (recompose), the agent files an older catalyst wrote
  into the project to retire (`.claude/commands/`, or `--commands-dir`, and the
  hooks in `.claude/settings.json`), definitions of new types, versions — and the kernel and module
  migrations between the two versions, in order. It writes nothing.
- `apply` does it and journals one `/sync-framework` entry. A command file catalyst wrote
  but that was edited locally, or a kernel document edited locally, is reported, never removed or overwritten; a recompose conflict stops
  the sync before anything is written; a plugin catalog is never touched.
  The migrations' judgment steps stay with the agent.

### Administration: `user`, `role`, `freeze`, `unfreeze`, `definition migrate`

Each refuses what its slash command refuses, writes, and journals one entry
(`--as`, `--intent`, `--json`; exit `1` and no change on a refusal).

- `catalyst user add <name> <role> [--git-username <u>]`, `user remove
  <name>` (deactivates; never the last active user), `user modify <name>
  <field> <value>` (not `name`, `registered`, `userid`, `roles`), `user
  assign-role <name> <role>`. A new user gets a drawn userid (INV-26).
- `catalyst role add <role> --action <a>... [--reconciliation
  full|propose|none]` (default `propose`), `role modify <role> --action <a>...`.
- `catalyst freeze <item>` / `unfreeze <item>`: an artifact ID, entity type,
  template name or working-copy path, listed in (or removed from) the
  working copy's `.frozen`.
- `catalyst definition migrate <type> <version> [--kernel <dir>]`: overwrite
  `definitions/<type>.md` with that version from the kernel's or the
  deployed module's `definitions/<type>/`; refuses a version that does not
  exist (INV-23).

### Writing verbs: `new`, `status set`, `link`

The mechanical half of creating and changing artifacts, from the entity type
definitions. Each signs (`--as`, else the only active user), keeps
back-references, regenerates the indexes and writes one journal entry
(`--intent` repeatable, `--command` names the slash command it runs for,
`--tier`). Each takes `--json` and exits `1`, changing nothing, on a refusal.

- `catalyst new <type> --title <t> [--field NAME=VALUE ...]`: the next ID,
  the type's latest template with its fields filled (ID, name, file name,
  initial status, dates, signer, the given fields; references as
  comma-separated IDs, checked to exist). Refuses a missing required field.
  The sections below the field table stay for the agent to write.
- `catalyst status set <ID> <status> [--force]`: a status the type allows
  and, when the ETD declares transitions, one it can reach; `--force` writes
  any value. A `RECON-` case is refused: only `/reconcile` changes one.
- `catalyst link <ID> <field> <ID>...`: cite IDs in a reference field and,
  when the field declares a back-reference, cite this artifact back.

### Read-only views: `list`, `view`, `backlog`, `journal show`

Computed from the working copy and the entity type definitions; none of them
writes. Each takes `--json`.

- `catalyst list <type> [--filter KEY=VALUE ...] [--type <family>]`:
  artifacts of an entity type (its prefix, name or folder), or `rule`,
  `user`, `role`, `template` (`--type` narrows to one family), or `all`.
  A filter keeps items whose field matches, with `*`/`?` wildcards. An
  unknown type exits `1` and names the known ones.
- `catalyst view <ID>`: one artifact or rule, its fields, the IDs it links
  to, the artifacts linking to it and its journal entries.
- `catalyst backlog`: open items per type and status ("open" is any status
  outside the ETD's closed states), open items missing a required link, and
  rules no open item targets.
- `catalyst journal show [--since <date>] [--artifact <id>] [--actor <name>]
  [--rule <id>]`: journal entries in time order, filtered.

### `catalyst unrecorded [<range>] [--json]`

Lists the **unrecorded changes**: non-merge product commits that change a
file to a git blob that was not its latest journaled `after` as of the
commit (a hand revert to an older journaled state counts), unless that
commit was adopted — work written by hand, straight into git (`CODE-OF-CONDUCT.md` §9, "Changes made outside
catalyst"). Only history after the pointer's `journal_since` baseline is
checked (a commit; `""` for the whole history); `<range>` (anything `git
log` accepts) narrows it further. Paths are relative to the project, also
when it is a subdirectory of its repository. A baseline this clone does
not have (a shallow checkout, rewritten history) is reported, not
crashed on: history is then not checked until the full history is
fetched (`check` and `trace` warn; `unrecorded` exits `1`). The working copy (`.criterion`) is never
a product file. Prints one line per commit — sha, author, subject, the
files — then a count; `--json` prints a list of `{commit, author,
subject, files: [{path, before, after}]}`.

Severity follows the format rollout: a **warning** while the pointer's
`format` is a release candidate (`1.0-rc`, the beta), an **error** from
format `1.0`, or earlier when the pointer sets `"strict_journal": true`.
Exits `1` only when something is found at error level (and on a bad range,
a standalone working copy, or a pointer with no `journal_since` and no
`<range>`); `0` otherwise. `/adopt` resolves each one.

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
                        [--target <id> ...] [--tier chore|fix|feature]
                        [--as <user>] [--allow-unchanged] [--json]
```

Appends one entry to the signer's shard
(`development/journal/<actor>@<machine>/<YYYY-MM>.jsonl`), under the
criterion's journal lock, with the real UTC time,
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
- `--target` (repeatable) is a rule or artifact ID the change serves. A
  change that serves no rule has none: its entry carries `targets: []`.
- `--tier` records the change's ceremony tier in the entry's `tier` field:
  `chore` (no rule's behaviour changes; needs no artifact), `fix`
  (restores a documented rule's behaviour) or `feature` (new or changed
  behaviour). Anything else is rejected. What each tier requires beyond the
  entry is the active module's (`CODE-OF-CONDUCT.md` §3, §9); the tier is
  omitted from entries that do not state one.
- A file whose content equals its last journaled state is rejected, since
  it did not change; `--allow-unchanged` accepts it deliberately.
- `--json` prints the written entry.

### `catalyst journal adopt`

```
catalyst journal adopt <commit> [<commit> ...] | <A>..<B>
                       --intent <text> [--intent <text> ...]
                       [--target <id> ...] [--artifact <id|description>]
                       [--tier chore|fix|feature] [--as <user>] [--json]
```

Records commits made outside catalyst in the journal after the fact: for
each commit, oldest first, one entry with its unrecorded changes
(`command: "/adopt"`, `action: "update"`, each file's `after` the
commit's blob), `origin: "manual"` and `commit: <sha>`
(`Rules-of-Rules.md` §12). A file whose journal chain has not moved past
the commit continues it: `before` is its last journaled state (else the
parent's blob). A file journaled again since the commit is recorded as
history only — `superseded: true`, `before` the parent's blob — so it
never becomes the file's current state and `journal verify` keeps it out
of the chain. The actor is the commit's git author
unless `--as` names one; `--artifact` defaults to `commit <sha>`.
`--intent` is required, as for `append`. Named commits are adopted alone,
a range commit by commit. Files already recorded are skipped; a commit
with nothing unrecorded writes nothing. Adopting several commits oldest
first keeps each file's hash chain unbroken. Rejecting a change instead
means reverting it (`/adopt`).

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
journal path: a file's latest journaled `after` at or before `<timestamp>`, or,
for a file first journaled later, that first entry's `before` (a file created
later is absent). `<out>` must be absent or an empty directory: restore never
touches the live tree, never overwrites and never writes outside `<out>`. Exits `1` and lists the paths whose blob
is missing from the object store.

### `catalyst journal pin`

Pins every blob any journal entry references under `refs/catalyst/journal`
in its repository, so `git gc` can never prune it. `journal append` pins
its own blobs; run `pin` once to backfill entries written before the CLI,
and after cloning or importing a working copy.

`--share` also merges each repository's pins with its `origin`'s and pushes
the result — the working copy's and the product repository's — so every
clone holds every blob the journal references. `catalyst criterion push`
shares the working copy's pins on its own; run `pin --share` when you push
the product repository (it pushes only the pin ref, never a branch).

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

### `catalyst analysis <subcommand>`

The four-eyes analysis of existing code (`ANALYSIS-PLAYBOOK.md`,
`/run-analysis`): an `ANALYSIS-` record in `analyses/`, its reports in
`analyses/reports/<ID>/`. Each subcommand moves one phase, refuses to skip
one, and journals the record and its reports. Every subcommand fails with
exit `1` and a reason on stderr when a precondition does not hold.

- **`start [<path>...] [--mode bootstrap|incremental] [--name <name>] [--as <user>]`**
  — allocates the record (Status `Extracting`) and writes
  `inventory.json`: every tracked file under the paths (default: the whole
  project, never `.criterion`) with its blob hash, and the product's `HEAD`
  as the code state. `incremental` (the default) also lists the rules,
  domains and rule-grounded artifacts already recorded; `bootstrap`
  refuses when rules exist.
- **`record <ID> --pass A|B <file> [--replace]`** — validates one pass's
  findings (`ANALYSIS-PLAYBOOK.md`, "Findings format": kind, title,
  statement, confidence; a rule's status; in-scope file and line evidence;
  a defect's `breaks`, an existing rule or a rule finding of the same
  pass) and stores it once as `A.json` or `B.json`. Warns when both passes
  are identical.
- **`diff <ID>`** — needs both passes: pairs findings (same kind; wording
  and shared evidence) and writes `diff.json` — `agreed`, `conflicting`
  (paired, but a different rule status or broken rule), `a_only`,
  `b_only`. Status `Reconciling`.
- **`reconcile <ID> <file>`** — accepts the reconciler's `{"findings",
  "dropped"}` only if every finding of both passes is in exactly one final
  finding's `sources` (`A:<id>`, `B:<id>`) or dropped with a reason, and
  every final finding that is not a plain agreement has a `verification`
  other than `both passes`. Writes `reconciled.json`; Status `Deciding`.
- **`decide <ID> <finding> accept|reject [--artifact <ID>] [--reason <text>] [--as <user>]`**
  — records the user's decision in `decisions.json`. `accept` needs the
  artifact the finding became, and it must exist: a registered DOMAIN code,
  a rule ID, or an artifact ID. A later decision on the same finding
  replaces the earlier one.
- **`close <ID>`** — refuses while a finding is undecided or an accepted
  finding's artifact is missing; sets Status `Closed` and the date, and
  writes the summary.
- **`abandon <ID> --reason <text>`** — Status `Abandoned`, with the reason.
- **`status <ID>`** — the phase, the passes, the diff counts, how many
  findings are decided, and anything keeping the record from its phase.

`catalyst check` applies the same rules to every record: a record in
`Reconciling` or later without both passes and the diff, in `Deciding` or
later without a complete reconciliation, or `Closed` with an undecided
finding or a missing artifact, is an error.

### `catalyst share info|status|pull|push`

The criterion's sharing, whichever driver holds the shared copy (roadmap
R3.2). `catalyst.toml` may name the driver (`share = "git"`); without it a
criterion with a git remote, or a project file naming its repository, uses
`git`, any other `local`.

- `info [--json]`: the driver, where the shared copy is, the shared branch,
  and what the driver can do.
- `status [--fetch] [--json]`: unpublished local changes, and how far this
  criterion is ahead of or behind its shared copy.
- `pull`: bring in what the shared copy has; refuses while local work is
  unpublished (git: `criterion sync`).
- `push -m <message> [--as <user>] [--no-pr] [--json]`: publish this
  criterion's changes (git: `criterion push`, a topic branch and a pull
  request).

Drivers: `local` (not shared: `pull` and `push` say how to share it) and
`git` (below). The working form behind every driver is the criterion's
store — read, list, append, lock (`scripts/catalyst/store.py`); a server
driver implements the same verbs.

### `catalyst criterion <subcommand>`

Shared deployments on git (`Rules-of-Rules.md` §13, INV-18). The criterion
repository has a **shared branch** (`criterion_branch`, default
`criterion`); contributors land changes through pull requests against it.

**In the home store (ADR-010, the default since R3.1)** the criterion is its
own repository at `$CATALYST_HOME/projects/<name>/criterion`; nothing of it
is in the product:

- `create <url>` pushes the criterion there and records `repoed`,
  `catalyst_repo_url` and `criterion_branch` in `catalyst.toml` (staged,
  journaled). No submodule, no `.gitignore` change.
- `join [<url>]` clones the criterion repository named in `catalyst.toml`
  (or `<url>`) into this machine's home store on the shared branch, or
  brings an existing clone up to date; a same-named criterion with another
  remote is refused. It fills the criterion's runtime.
- `push`, `sync`, `status` (mode `home`), `integrity` and `protect` work on
  the criterion as below.
- **Product CI** clones it into its own home store, then runs its CLI:

  ```yaml
  - env:
      CATALYST_HOME: ${{ runner.temp }}/catalyst
    run: |
      read -r name url branch < <(python3 -c 'import tomllib; d = tomllib.load(open("catalyst.toml", "rb")); print(d["project_name"], d["catalyst_repo_url"], d.get("criterion_branch") or "criterion")')
      git clone -q -b "$branch" "$url" "$CATALYST_HOME/projects/$name/criterion"
      python3 "$CATALYST_HOME/projects/$name/criterion/bin/catalyst.pyz" trace "$range"
  ```

  (a private criterion repository needs a read-only deploy key or token
  for the clone).

**Legacy, for one minor:** a shared deployment whose working copy is a git
submodule of the product repository at `.criterion` keeps working as
described below; `catalyst move --to-home` turns it into the form above.

Every subcommand fails with exit `1` and a reason on stderr when git
fails or a precondition does not hold; nothing is half-applied in the
product repository.

#### `catalyst criterion create [<url>] [--branch <name>]`

Turns a local-only deployment into a shared one. `<url>` is the
criterion repository: empty, or already holding this working copy's
history on `<name>` (default `criterion`).

Without `<url>`, only items 1–3 below run: the working copy becomes a git
repository on the shared branch, with its `.gitattributes` and CI
workflow committed, and stays behind the `.criterion` symlink with no
remote. The pointer records `criterion_branch` (staged, journaled).
Nothing leaves the machine. The first `push`, `sync` or `join` then
needs the criterion repository: it takes `--url <url>`, or asks for it
on an interactive terminal, and runs items 4–6 before carrying on;
elsewhere it fails with exit `1`, naming `--url`. It refuses when the
working copy already has a remote.

With `<url>`, in order:

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

#### `catalyst criterion join [--url <url>]`

In a fresh clone of the product repository: initialises the `.criterion`
submodule and checks out the shared branch, so the working copy is on a
branch rather than a detached gitlink. Prints the checked-out commit.

A product with no `.criterion` submodule yet needs the criterion
repository (`--url`, or asked for on an interactive terminal). Where this
machine holds the local working copy (the symlink), it is published there
as by `create <url>`. Otherwise the repository — which must already have
the shared branch — is added as the submodule, `/.criterion` leaves
`.gitignore`, the pointer records `repoed`, `catalyst_repo_url` and
`criterion_branch`, and those product files are staged and journaled in
the working copy (land the entry with the next `push`). A local working
copy that already has a remote is not converted: `create <url>` does
that.

#### `catalyst criterion status [--fetch]`

Prints the mode (`submodule` or `local`), the remote, the shared branch,
the current branch, the count of uncommitted changes and, when the
remote has the shared branch, how far the working copy is ahead of and
behind it. `--fetch` fetches first. Always exits `0`.

#### `catalyst criterion push -m <message> [--as <user>] [--no-pr] [--url <url>]`

Lands the working copy's changes as a pull request against the shared
branch. `<message>` is the commit message and pull request title; the
signer is resolved as in [Signer](#signer), and its `git_username` (else
`name`) is the commit author name and the topic branch's prefix. In
order:

1. With no remote (a local-only deployment), publishes first to `--url`
   (asked for on a terminal; otherwise it fails naming `--url`), as
   `create <url>` does. Fetches.
2. Switches to a topic branch, `<user>/<UTC timestamp>`, unless one is
   already checked out (any branch other than the shared one) whose pull
   request is still open — a topic whose branch was merged or deleted is
   replaced by a new one. If the remote topic branch holds commits this
   working copy lacks (a reviewer's suggestion), it refuses: pull them
   first. Rewrites `.gitattributes`; commits every change with
   `<message>`.
3. Rebases onto the shared branch (after fetching the other contributors'
   journal pins, so their entries verify). A conflict aborts the rebase and
   fails with the conflicting files: nothing is pushed. Resolve by hand,
   or withdraw your side and record a proposed resolution as a `RECON-`
   case for a human to accept (`/reconcile`); never apply one
   automatically. To withdraw a conflicting edit: take the shared version
   of the file (`git -C .criterion checkout origin/<shared> -- <file>`),
   journal and commit that, open the `RECON-` case with your proposed
   content, then `push` again.
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

#### `catalyst criterion sync [--url <url>]`

Fast-forwards the working copy to the shared branch; a local-only
deployment is published first, to `--url` (or the URL asked for), as by
`push`. Refuses while the
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
that are append-only or regenerated: the journal (its shards and the
legacy `development/journal.jsonl`) and
every per-file entity type's `<folder>/<folder>.md` index
(`rules/rules.md` is hand-maintained, so concurrent edits to it conflict
instead). A union merge keeps both sides' lines; `push` then regenerates
the indexes in ID order and journals every file the rebase merged. The
team's own lines in the file are kept. Everything else merges normally, and a
conflict there stops the push.

A hosting service's merge button does not apply `merge=union`, so a pull
request that has fallen behind the shared branch may show conflicts there:
run `push` again (it rebases, where the union applies). Branch protection's
"up to date before merging" rule (`protect` sets it) makes this the normal
path. Each union merge also leaves `concurrent-edit` notes in `journal
verify`: history of merged work, never a warning or an error, and they do
not fail `--strict`.

#### The CI workflow

`create` writes `.github/workflows/catalyst.yml` and
`bin/catalyst.pyz.sha256` into the criterion repository; `push` refreshes
both when they change. The change under review cannot change its own
gate: the workflow runs on `pull_request_target`, so its definition comes
from the base branch, with read-only permissions. It checks the base out
as `gate/`, verifies `gate/bin/catalyst.pyz` against the hash the base
records, checks the pull request's merge result out as `change/` (as
data: nothing in it runs), and runs the base's checker on it:

```
python3 "$GITHUB_WORKSPACE/gate/bin/catalyst.pyz" --working-copy . check
python3 "$GITHUB_WORKSPACE/gate/bin/catalyst.pyz" --working-copy . criterion integrity   # pull requests only
```

A pull request that changes the workflow itself is therefore checked by
the previous workflow; the new one applies once it is merged.

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
  which would break point-in-time restore. This writes objects and that
  one ref into the **product repository's** `.git` too (never a commit
  or a branch, nothing pushed); the first time the ref is created in a
  repository, `journal append` and `init` say so. The ref stays local
  until `journal pin --share`; `git update-ref -d refs/catalyst/journal`
  removes it (restore then loses the blobs `git gc` prunes).
- **Entries are written with `catalyst journal append`, never by hand.**

## Hooks

An agent that supports a session-start hook registers
`catalyst hook start` as that hook, so every session starts from the
invariants. An agent that supports an end-of-turn hook registers
`catalyst hook stop` as that hook, so every turn ends with a deployment
that passes `catalyst check`. `catalyst agent install <agent>` registers
both, in the agent's own format (`--format`), at user level — never in
the project. An agent without hook support runs `catalyst check`
at the end of every artifact-changing command instead
(`CODE-OF-CONDUCT.md` §4).

The git side is agent-independent: `catalyst hook install` puts
`catalyst hook commit-msg` in the project repository's `commit-msg` hook,
so every commit traces whoever — or whatever — makes it, and
`catalyst trace` re-checks the same rule in CI. Commits that bypass the
journal are caught the same way, by the hook, `trace` and `check`, and
resolved with `/adopt`.

## Related docs

- [`FORMAT.md`](FORMAT.md) — the on-disk format every command reads and writes.
- [`migrations/0.42.0/changes-outside-catalyst.md`](migrations/0.42.0/changes-outside-catalyst.md) — changes made outside catalyst: `unrecorded`, `journal adopt`, the pointer's `journal_since`.
- [`migrations/0.41.0/traced-commits-and-format.md`](migrations/0.41.0/traced-commits-and-format.md) — traced commits, the commit-msg hook, the pointer's `format`.

- [`rules-of-rules.template.md`](rules-of-rules.template.md) §12 — the journal's schema and immutability.
- [`rules-of-development.template.md`](rules-of-development.template.md) §4 — the commands that call the CLI.
- [`INSTANTIATION-GUIDE.md`](INSTANTIATION-GUIDE.md) — what `catalyst init` does, and the judgment steps around it.
- [`migrations/0.40.0/explicit-install-and-tiers.md`](migrations/0.40.0/explicit-install-and-tiers.md) — explicit install, ceremony tiers, `catalyst spec`.
- [`migrations/0.38.0/catalyst-cli.md`](migrations/0.38.0/catalyst-cli.md) — bringing an existing deployment onto the CLI.
- [`rules-of-rules.template.md`](rules-of-rules.template.md) §13 — shared deployments, what `catalyst criterion` guarantees.
- [`migrations/0.39.0/criterion-on-git.md`](migrations/0.39.0/criterion-on-git.md) — moving a repoed deployment onto the submodule model.
