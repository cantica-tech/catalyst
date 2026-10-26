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

The criterion vendors the CLI as `bin/catalyst.pyz`, a single-file
zipapp: it ships inside the kernel release, is copied into the criterion at
install (`INSTANTIATION-GUIDE.md`) and on every `/sync-framework`
(`SYNCHRONIZE.md`), and fills the criterion's `.venv` (`catalyst open`), which
the launcher runs. From catalyst's own checkout, `task build:cli` builds
it into `dist/catalyst.pyz`.

Every command works on the deployment found at or above the current
directory: the project root holding `catalyst.toml` (a legacy
`*.catalyst` pointer is still read), and its criterion in catalyst's home
(`catalyst where`; INV-6).
`--project <dir>` starts the search elsewhere. `catalyst --version`
prints the CLI's version, which is the kernel version it shipped with;
a zipapp built from a git checkout appends its build, as
`<version>+g<12-char sha>`, plus `.dirty` when the sources it packed
differed from that commit.

On an interactive terminal, a command ends with one status line on stderr:
`catalyst · <project> · checked 14:08 · 0 error(s), 3 warning(s)`, the last
`catalyst check`'s result as recorded in the criterion's git directory,
never a new check. It is never printed to a pipe, with `--json`, or after
`check`, `hook`, `mcp`, `serve`, `init`, `agent` or `spec`;
`CATALYST_FOOTER=0` turns it off.

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
| `3` | Not done for lack of the user's assent (INV-4): a command that publishes (`share push`, `share create`, `criterion push`, `criterion create <url>`, a first `--url` on `criterion sync`) printed what it would publish; show it to the user and re-run with `--yes` once they agree. On a terminal it asks instead. |

The deployment is found by walking up from the current directory to the
nearest `catalyst.toml`, so any directory inside the project works. Run
from inside a criterion itself (outside any project), give `--project` or
`--working-copy`: the CLI never guesses the project.

Outside any catalyst project (no `*.catalyst` pointer), `catalyst check`,
`catalyst hook stop` and `catalyst hook commit-msg` exit `0`, so a fresh
clone or a CI runner is not failed. A project whose pointer exists but whose working copy
is unreachable fails: `check` exits `1`, `hook stop` exits `2`.

### Signer

Commands that write a signed value (`id next`, `id next-rule`,
`journal append`) sign as the identity catalyst-users verifies at that
moment (`CODE-OF-CONDUCT.md` §2; `IAM/identity.json` points at it): the
person logged in with `catalyst identity login`, or, with no one logged in,
this machine's system account, when its settings point at the same
provider (said on standard error). `--as <username>` names only that
identity. It never guesses from git config: with no verified identity the
command fails, signs nothing, and points to `catalyst identity login`.

## Commands

<!-- generated: cli-index (scripts/gen_docs.py; do not edit by hand) -->

Every command and its options, from the CLI itself; the sections below describe each.

| Command | What it does | Options |
|---|---|---|
| `catalyst validate` | validate the traceability chain against the ETDs | `--json`, `--strict` |
| `catalyst init` | install catalyst into this project (explicit only, INV-2) | `--agent`, `--at`, `--catalyst-client`, `--git-username`, `--identity-client`, `--identity-issuer`, `--kernel`, `--module`, `--module-dir`, `--name`, `--no-module`, `--no-runtime`, `--rule-doc`, `--test-locations`, `--user` |
| `catalyst check` | run every check: structure, chain, journal, indexes | `--json`, `--strict` |
| `catalyst hook stop` | end-of-turn hook: block the stop with the failures | `--format`, `--strict` |
| `catalyst hook commit-msg <message_file>` | git commit-msg hook: the message must trace to the chain | `--route` |
| `catalyst hook install` | install the commit-msg hook in the project's git repository | — |
| `catalyst hook start` | session-start hook: print the invariants, record the session's baseline | `--format`, `--quiet` |
| `catalyst report` | usage report: actors, tiers, traced commits, open artifacts | `--json`, `--since` |
| `catalyst audit` | the audit pack: each rule's chain and the record's integrity | `--html`, `--json` |
| `catalyst badge` | a README badge: an SVG of check's result or of the rules in use | `--metric`, `--out` |
| `catalyst unrecorded <range>` | commits whose product changes the journal does not record | `--json` |
| `catalyst trace <range>` | check that every commit in a range cites an artifact or rule ID | `--pattern-only` |
| `catalyst recompose` | merge kernel/module template changes into the deployed documents, keeping local edits (three-way) | `--base-kernel`, `--base-module`, `--check`, `--force`, `--kernel`, `--module-dir` |
| `catalyst spec <command> <part>` | print only what one command needs from CODE-OF-CONDUCT §4 | `--budget`, `--general`, `--json` |
| `catalyst id next <prefix>` | next <PREFIX>-NNNNNN-<userid> for an entity type | `--as`, `--count` |
| `catalyst id next-rule <doc_prefix> <domain>` | next <doc-prefix>-<DOMAIN>-NNNNNN-<userid> rule ID | `--as` |
| `catalyst journal append` | append one entry with real hashes and time | `--action`, `--allow-unchanged`, `--artifact`, `--as`, `--command`, `--file`, `--intent`, `--json`, `--target`, `--tier` |
| `catalyst journal adopt <revs>` | record commits made outside catalyst in the journal (origin manual) | `--artifact`, `--as`, `--intent`, `--json`, `--target`, `--tier` |
| `catalyst journal verify` | check hash chains, blobs, pins and unjournaled edits | `--json`, `--legacy`, `--strict` |
| `catalyst journal restore <timestamp> <out>` | materialise journaled files as of a timestamp | — |
| `catalyst journal show` | read-only: journal entries, filtered, in time order | `--actor`, `--artifact`, `--content`, `--json`, `--rule`, `--since` |
| `catalyst journal redact <blob>` | redact journaled content: a tombstone entry, the blobs out of the pins | `--as`, `--intent`, `--json`, `--tier` |
| `catalyst journal pin` | pin every referenced blob so git gc keeps it | `--share` |
| `catalyst list <type>` | read-only: artifacts of a type, rules, users, roles or templates | `--filter`, `--json`, `--type` |
| `catalyst view <id>` | read-only: one artifact or rule, its links both ways and its history | `--json` |
| `catalyst backlog` | read-only: open work by type and status, missing links, idle rules | `--json` |
| `catalyst repair derived` | every derived field (another type's back-reference) from its sources, journaled | `--as`, `--json`, `--tier` |
| `catalyst graph` | read-only: every rule, domain and artifact with its links, and the entity types | `--json` |
| `catalyst new <type>` | create an artifact from its type's latest template, signed, indexed, journaled | `--as`, `--command`, `--field`, `--forewarned`, `--intent`, `--json`, `--preview`, `--tier`, `--title` |
| `catalyst rename <id>` | a new title: heading, Name, Filename and file follow; the ID stays | `--as`, `--command`, `--forewarned`, `--intent`, `--json`, `--preview`, `--tier`, `--title` |
| `catalyst edit <id>` | change an entity's fields and sections; never its ID, Name, Filename, Signed-off-by or Status (design 31) | `--as`, `--command`, `--field`, `--forewarned`, `--intent`, `--json`, `--preview`, `--section`, `--section-file`, `--tier` |
| `catalyst approve <id>` | approve an entity's current version under a gate (IAM/gates.json), journaled | `--as`, `--forewarned`, `--gate`, `--intent`, `--json`, `--preview`, `--tier` |
| `catalyst approvals <id>` | the gates covering an entity: approvals counted and missing | `--json` |
| `catalyst landing init` | choose the landing policy: the Admin's assent to the landings it allows | `--as`, `--force`, `--intent`, `--json`, `--policy` |
| `catalyst landing show` | read-only: the landing policy in force and where it comes from | `--json` |
| `catalyst restore <id>` | write an entity back as it stood at a time: a new journaled change | `--as`, `--command`, `--forewarned`, `--intent`, `--json`, `--preview`, `--tier`, `--to` |
| `catalyst status set <id> <status>` | set Status, checked against the type's statuses and transitions | `--as`, `--command`, `--force`, `--forewarned`, `--intent`, `--json`, `--preview`, `--through`, `--tier` |
| `catalyst link <id> <field> <ids>` | cite IDs in a reference field, keeping the back-reference | `--as`, `--command`, `--forewarned`, `--intent`, `--json`, `--preview`, `--tier` |
| `catalyst user add <name> <role>` | refuses: add people in catalyst-users | `--as`, `--git-username`, `--intent`, `--json` |
| `catalyst user remove <name>` | refuses: disable people in catalyst-users | `--as`, `--intent`, `--json` |
| `catalyst user modify <name> <field> <value>` | refuses: change people in catalyst-users | `--as`, `--intent`, `--json` |
| `catalyst user assign-role <name> <role>` | refuses: grant roles in catalyst-users | `--as`, `--intent`, `--json` |
| `catalyst role add <name>` | refuses: provision roles in catalyst-users | `--action`, `--as`, `--intent`, `--json`, `--provider-role`, `--reconciliation` |
| `catalyst role modify <name>` | refuses: change what a role grants in catalyst-users | `--action`, `--as`, `--intent`, `--json`, `--provider-role` |
| `catalyst freeze <item>` | protect an item from /sync-framework (.frozen) | `--as`, `--intent`, `--json` |
| `catalyst unfreeze <item>` | remove an item from .frozen | `--as`, `--intent`, `--json` |
| `catalyst definition list` | each deployed definition: its slug, version and description | `--json` |
| `catalyst definition migrate <entity> <version>` | move definitions/<type>.md to a version that exists (INV-23) | `--as`, `--intent`, `--json`, `--kernel` |
| `catalyst sync plan` | list what a sync would change, and the migrations to run | `--as`, `--base-kernel`, `--cli`, `--commands-dir`, `--intent`, `--json`, `--kernel`, `--module` |
| `catalyst sync apply` | do the mechanical half of /sync-framework, then journal it | `--as`, `--base-kernel`, `--cli`, `--commands-dir`, `--intent`, `--json`, `--kernel`, `--module` |
| `catalyst inbox` | what waits for a person, with its evidence and what settles it (read-only) | `--json` |
| `catalyst impact <id>` | what an entity rests on and what rests on it, transitively (read-only) | `--depth`, `--down`, `--json`, `--up` |
| `catalyst module list` | each installed module: id, version, source, commit, hash (no network) | `--json` |
| `catalyst module install <source>` | install a module into a deployment that has none (seeded as init does) | `--as`, `--intent`, `--json`, `--kernel` |
| `catalyst module available <id>` | the releases at the module's recorded repository (the network) | `--json` |
| `catalyst module upgrade <id> <source>` | move the installed module to another release, through `sync plan\|apply` | `--as`, `--base-kernel`, `--intent`, `--json`, `--kernel`, `--plan` |
| `catalyst module verify <id>` | recompute each module's hash and compare it with the record (exit 1 on a difference) | `--json` |
| `catalyst where` | the project's criterion: the home store, or a legacy working copy | `--json` |
| `catalyst agent install <agent>` | add catalyst to the agent's user-level configuration | — |
| `catalyst agent uninstall <agent>` | remove catalyst's entries from it | — |
| `catalyst agent status` | which agents have catalyst | `--json` |
| `catalyst agent run <command> <arguments>` | dispatch a command to the project's agent; stream what it does and what it cost | `--agent`, `--json` |
| `catalyst agent runs` | this user's logged runs for the project, with what each cost | `--json`, `--limit` |
| `catalyst mcp` | serve catalyst to an agent over MCP (stdio): its commands, CLI, invariants | — |
| `catalyst task <name> <task_args>` | run a criterion task (Taskfile.common.yml) from the project's root | — |
| `catalyst runtime install` | build this version's runtime, install the launcher, fill the criterion's .venv | — |
| `catalyst runtime status` | runtimes, launcher and the criterion's runtime version | `--json` |
| `catalyst move` | move a legacy deployment into $HOME/.catalyst, or rename a project | `--as`, `--name`, `--no-runtime`, `--to-home` |
| `catalyst migrate` | what this deployment is behind on (legacy layout, templates, judgment steps); --apply takes the mechanical part | `--apply`, `--as`, `--intent`, `--json`, `--kernel`, `--no-runtime`, `--since`, `--template` |
| `catalyst workspace init <file>` | create the meta criterion and make the folders with a catalyst.toml members | `--catalyst-client`, `--git-username`, `--identity-client`, `--identity-issuer`, `--kernel`, `--user` |
| `catalyst workspace status <file>` | the workspace's criterion and which folders are members | `--json` |
| `catalyst index regen` | rewrite every <folder>/<folder>.md index | `--check`, `--diff` |
| `catalyst analysis start <scope>` | open an analysis: scope, mode, code state, inventory | `--as`, `--mode`, `--name`, `--passes` |
| `catalyst analysis record <id> <file>` | store one independent pass's findings (JSON) | `--as`, `--pass`, `--replace` |
| `catalyst analysis diff <id>` | match the two passes: agreed, conflicting, A-only, B-only | `--as` |
| `catalyst analysis reconcile <id> <file>` | store the reconciler's list (every finding accounted for) | `--as` |
| `catalyst analysis decide <id> <finding> <verdict>` | record the user's decision on one reconciled finding | `--artifact`, `--as`, `--reason` |
| `catalyst analysis close <id>` | close once every finding is decided and accepted ones exist | `--as` |
| `catalyst analysis abandon <id>` | stop an analysis, with the reason | `--as`, `--reason` |
| `catalyst analysis status <id>` | an analysis's phase and what it still needs | `--json` |
| `catalyst analysis list` | every analysis in brief, newest first | `--json` |
| `catalyst reconcile <case> <verb>` | decide a reconciliation case (role-gated: full, propose, none) | `--as`, `--forewarned`, `--from`, `--intent`, `--preview`, `--text` |
| `catalyst try <change>` | make one change on a scratch copy of the criterion and say what it would do (nothing is kept) | `--as`, `--json`, `--keep`, `--proposal` |
| `catalyst propose <id>` | propose a change to an entity or rule document, decided by someone else | `--as`, `--forewarned`, `--from`, `--intent`, `--json`, `--preview`, `--tier`, `--title` |
| `catalyst why <item>` | explain a law (L1…), an invariant (INV-n), a meta-rule or an ID | — |
| `catalyst open` | make the project ready on this machine (join, runtime) and say where it stands | `--agent`, `--fetch`, `--json` |
| `catalyst share info` | the driver, where the shared copy is, what it can do | `--json` |
| `catalyst share status` | this criterion against its shared copy | `--fetch`, `--json` |
| `catalyst share pull` | bring in what the shared copy has (refuses with unpublished work) | — |
| `catalyst share push` | publish this criterion's changes (git: a topic branch and a pull request) | `--as`, `--json`, `--message`, `--no-pr`, `--yes` |
| `catalyst share create <url>` | publish a local-only criterion for the first time (git, or a server) | `--as`, `--branch`, `--driver`, `--protect`, `--yes` |
| `catalyst share join <url>` | bring a shared criterion to this machine (a project with catalyst.toml) | — |
| `catalyst share login <url>` | keep this user's token for a catalyst serve server (in catalyst's home) | `--token` |
| `catalyst serve token <action> <who>` | issue, list or revoke the tokens users sign with | — |
| `catalyst serve key <action>` | the master key of the membership ledger: init, escrow, recover (fw-IDENTITY-000013) | `--holder`, `--key-command`, `--out`, `--reason`, `--share`, `--threshold` |
| `catalyst serve members <action>` | the membership ledger: open, check, fingerprint (fw-IDENTITY-000012) | `--json`, `--reason`, `--yes` |
| `catalyst members <action> <member>` | a served criterion's members, through its server: list, add, remove, adopt (design 32) | `--json`, `--reason` |
| `catalyst criterion status` | the working copy against the shared branch | `--fetch` |
| `catalyst criterion create <url>` | version the working copy for sharing; with a URL, publish it as the .criterion submodule | `--branch`, `--yes` |
| `catalyst criterion join` | check out a shared deployment in a clone of the product | `--url` |
| `catalyst criterion push` | commit, rebase, check, push a topic branch, open a pull request | `--as`, `--message`, `--no-pr`, `--url`, `--yes` |
| `catalyst criterion sync` | fast-forward to the shared branch (refuses with local work) | `--url`, `--yes` |
| `catalyst criterion integrity` | fail if a merge lost any ID, index row or journal line | `--head`, `--parent` |
| `catalyst criterion protect` | branch protection for the shared branch (GitHub) | `--yes` |
| `catalyst identity configure` | point the deployment at catalyst-users (writes IAM/identity.json) | `--as`, `--catalyst-client`, `--client`, `--intent`, `--issuer`, `--link`, `--provider` |
| `catalyst identity login` | log in with a code shown in your browser (the device flow) | `--client`, `--issuer`, `--json` |
| `catalyst identity logout` | revoke your session and delete your tokens | `--client`, `--issuer` |
| `catalyst identity whoami` | who catalyst-users says you are: userid, groups, roles, grants (verified now) | `--as`, `--client`, `--issuer`, `--json` |
| `catalyst identity status` | the provider, and whether you are logged in (no network) | `--client`, `--issuer`, `--json` |
| `catalyst identity link <user>` | keep a retired user's userid as yours, once (migration 0.106.0) | `--as` |
| `catalyst userid gen` | draw a new unique userid (INV-26) | — |

<!-- end generated: cli-index -->

### `catalyst init`

```
catalyst init --name <name> (--module <module-id> | --no-module) [--identity-issuer <url>]
              [--user <name>] [--git-username <u>] [--rule-doc <file>:<prefix> ...] [--test-locations <where>]
              [--agent <id>] [--no-runtime]
              [--kernel <framework/kernel>] [--module-dir <dir>]
```

Installs catalyst into the project (the current directory, or
`--project <dir>` given before `init`) — only ever on the user's explicit
request (INV-2); nothing runs it on load. It is the mechanical half of
an install; the agent decides its inputs and does the judgment steps after
it (`INSTANTIATION-GUIDE.md` §1).

- `--name` names the project; the pointer is `<name>.catalyst`.
- `--module` is the active module's id; there is no default. Without it,
  `init` installs nothing and lists the modules it finds in sibling
  checkouts named `catalyst-<id>` (next to the project or to catalyst);
  one elsewhere is given with `--module-dir`. `--no-module` installs the
  kernel's types only; `catalyst module install` adds a module later, by
  the same code, and leaves the same criterion.
- `--identity-issuer <url>` (with `--identity-client`, `--catalyst-client`)
  points the deployment at catalyst-users (`IAM/identity.json`, INV-16);
  without it, at the provider this machine's catalyst-users is set up for.
  The installer is the identity catalyst-users verifies there: log in first
  (`catalyst identity login --issuer <url>`), or, with no one logged in, the
  machine's system account signs. Nothing is installed without a verified
  identity. The installer's first signature draws its userid (INV-26).
- `--user` and `--git-username` name the installer in `DEPLOYMENT.md` and
  the criterion's git configuration. `--user` defaults to the project's
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

What it writes, in order (the tree: `ARTIFACT-LAYOUT.md`):

- the composed `CODE-OF-CONDUCT.md` (the kernel's
  `rules-of-development.template.md` with the module's
  `code-of-conduct.module.md` §3/§4 under `### From module <id>`),
  `rules/Rules-of-Rules.md` (the kernel's template with the module's
  `rules-of-rules.module.md` appended), `ACCESS-CONTROL.md` (verbatim) and
  `Taskfile.common.yml` (one task per §4 command), with `{{RULES_DIR}}`,
  `{{RULE_DOCS_LIST}}` and `{{TEST_LOCATIONS}}` resolved and the meta-rule
  IDs signed by the installer (`MODULE-SPECIFICATION.md` §6);
- the whole module, into `modules/<module-id>/`;
- every entity folder, kernel and module, at the place its type names,
  each with `templates/` (`README.md`, the catalog with a `v1` row,
  `TEMPLATE-<TYPE>-v1.md`), `README.md` and its index (INV-20); `rules/`
  with `rules.md` and each rule document seeded with `## Contents` and
  `## Linked Artifacts — Quick Index` (INV-8); every path the module
  requires;
- the latest definition of every type at `definitions/<type>.md`, with
  `definitions/README.md`, frozen from then on (INV-23);
- `IAM/identity.json`, the pointer to catalyst-users; `IAM/signers.jsonl`
  with the installer's line; `IAM/users/`, `IAM/roles/` and `IAM/groups/`,
  each with its display template (INV-16, INV-26);
- `version.txt`, `DEPLOYMENT.md`, a root `README.md` stub,
  `ANALYSIS-PLAYBOOK.md`, `INVARIANTS.md` (what `catalyst mcp` and the
  session-start hook re-inject) and the CLI at `bin/catalyst.pyz`;
- the criterion's runtime and git history, `catalyst.toml`, and the
  install as the journal's first entry.

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

`--json` gives the same as data: without a command, every command with how
it is typed (`usage`), its one-line `summary` (the MCP prompts' own
descriptions), its `aliases` and its `parts`, each part with its own usage,
summary and aliases (`spec/commands.schema.json`); with one, `{command,
part, text}` (`spec/command-spec.schema.json`). A command palette reads
these, never a list of its own.

`--budget <words>` checks every command's spec against a word budget and
exits `1`, listing each command over it. catalyst holds its own deployment
to **1,000 words** per command: `tests/test_token_budgets.py` runs
`catalyst spec --budget 1000` on a fresh install of the in-repo sample
module, and of a production module whose checkout is beside catalyst, so a
command whose procedure outgrows the budget is split or tightened, not left
to grow.

### `catalyst check [--strict] [--json]`

Every check a deployment can run on itself, in one pass: the on-disk
format version, the deployment's structure, the traceability chain
(`validate`), the journal (`journal verify`), changes committed outside
catalyst (`unrecorded`), index freshness
(`index regen --check`) and, when the criterion's own HEAD is a merge, its
integrity (`criterion integrity`: nothing either side recorded is lost;
kept per HEAD, so the end-of-turn check stays cheap). Journal warnings on entries written before the
CLI are summarised in one line (`journal verify --legacy` lists them).
Exits `1` on any error, or on any warning under `--strict`. With `--json`:
`ok`, the `errors` and `warnings` as lines, and the same as `findings`, each
with its `level`, `text` and the `entity` it is about — the one whose file
it names, else the first known entity ID in it, else null — so a client can
mark drift where it shows that entity (`spec/check.schema.json`).

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
| `derived` | A derived field (another type's `backref`) disagrees with its sources: it misses an artifact that cites it, or cites one that does not cite it back. `catalyst repair derived` rewrites it. |
| `ungrounded` | An artifact whose type grounds (`required` or `inherited`) has no resolvable grounding link (INV-5). |
| `signer` | `Signed-off-by` is missing or names no known signer: none in the signers ledger, nor in a retired users registry (INV-16). |
| `id-shape` | An ID is not `<PREFIX>-NNNNNN-<a signer's userid>`, or its filename does not start with `<PREFIX>-NNNNNN-`. |
| `rule-unindexed` | A rule is not listed in `rules/rules.md` (INV-8). |
| `rule-strength` | A rule states a strength other than `must`, `should` or `may` (`FORMAT.md` §5.2). |
| `rule-file-heading` | A file named as a rule (`<ID>-<slug>.md`) also holds a rule heading (`FORMAT.md` §5.2). |
| `index-orphan` | An index row registers an ID that has no file. |

**Warnings** are shape mismatches in otherwise sound data; `--strict`
promotes them to errors:

| Code | Meaning |
|---|---|
| `enum-value` | An enum field holds a value outside the ETD's allowed values. |
| `unknown-user` | A `user` or `user-list` field names someone who is not a known signer. |
| `guard` | An artifact is in a state whose guards it fails (`MODULE-SPECIFICATION.md` §4.3); it may predate the guard. |
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

A session blocks on what it broke, not on what it found (ADR-002). When
the hook input carries the agent's session id (`session_id`, `sessionId`,
`conversation_id`) and `catalyst hook start` recorded a baseline for that
session, a failure that was already there when the session started is
reported but does not block, and only new failures block; the message
counts the older ones. Without a session id or a baseline, every failure
blocks, and the message says why.

While `catalyst.toml` says `governance = "suspended"` (an owner's
decision), it reports that and exits `0` without checking.

`--format` says how to block, in the agent's terms: `exit2` (the default,
Claude Code) as above; `json` prints `{"decision": "block", "reason": ...}`
and exits `0` (Codex, Copilot CLI and VS Code, Claude Code); `gemini` the
same with `"deny"` (Gemini CLI's end-of-turn hook); `cursor`
`{"followup_message": ...}`. The project is the hook input's `cwd` (or
Cursor's `workspace_roots`) when `--project` is not given.

### `catalyst hook start [--format text|json|cursor] [--quiet]`

The agent's session-start hook: prints where the project stands (the
report of [`catalyst open`](#catalyst-open---fetch---agent-id---json),
changing nothing and touching no network), then the laws — the top of the
criterion's `INVARIANTS.md` and, when the module ships one,
`INVARIANTS.module.md`, up to their `end of the session brief` marker (a file
without the marker is shown whole) — so a deployed project's sessions start
grounded. It never blocks a session: it
always exits `0`, prints nothing outside a project, and only the report
(with `catalyst open` as its to-do) when the criterion is not on this
machine.
`--format json` wraps the text as `hookSpecificOutput.additionalContext`
(Codex, Copilot, Gemini CLI), `cursor` as `additional_context`.

When the hook input carries the agent's session id, it also records what
`catalyst check` fails on as the session's baseline, for `catalyst hook
stop`: in the criterion's git directory (`catalyst/sessions/`), never shared
and never in the project; baselines older than a week are removed. A
failure to record changes nothing else. `--quiet` records the baseline and
prints nothing, for an agent whose session already carries the laws
(Claude Code, through the MCP server's instructions).

### `catalyst why <L1…L10 | INV-n | rr-META-n | rr-<NS>-n | ID>`

Explains one item, read from the criterion (roadmap R4.1): a law with the
invariants it absorbs (`why L3`, `why SE-L1`); an invariant with its law,
what enforces it, and its full text (`why INV-17`; an invariant the module
owns is shown from the module's file, `INV-<NS>-n` included); a meta-rule's
section of `Rules-of-Rules.md`, the kernel's or the module namespace's, by
its short or signed ID (`why rr-META-012`, `why rr-SE-001`); an old ID the
module lists under `aliases:`, as the ID it now is; or, for any other ID,
the artifact or rule as `view` shows it. Exits `1` when nothing matches.

### `catalyst open [--fetch] [--agent <id>] [--json]`

Makes the project ready on this machine and says where it stands — the one
step after `git clone` (roadmap R3.5). It writes only in catalyst's home,
never in the project:

- a criterion missing on this machine is cloned from the repository
  `catalyst.toml` names (as `share join`), with the product's journal pins;
- the criterion's runtime (`.venv`) is filled from its own vendored CLI when
  missing or different, and the launcher is installed when missing;
- `--agent <id>` records this user's agent (`$CATALYST_HOME/projects/<name>/agent`),
  which `catalyst task` dispatches to — the whole agent switch;
- `--fetch` fetches the shared copy (and the product's pins) first.

It then reports the criterion, the kernel `catalyst.toml` pins against the
criterion's, the runtime, the agent, the shared copy (ahead/behind, changes
not published) and a to-do list of exact commands — a legacy deployment to
move, a version drift, a pull to make. Exits `0` when nothing is left to do,
`1` otherwise, `2` outside a project.

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
- **instructions** — the deployment's laws (kernel and module), as `hook start` prints them;
  `catalyst why` explains the rest.

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

### `catalyst agent run <command> [<arguments>…] [--agent <id>] [--json]`

Dispatches one command of the deployment's `CODE-OF-CONDUCT.md` §4 to the
project's agent (the one `catalyst open --agent` records for this user;
`--agent` for one run), non-interactively, from the project's root. The
agent is given the command's procedure — the text the `catalyst mcp`
prompts give — and runs under the user's own agent settings: catalyst
passes no flag that widens its permissions, so a tool the settings do not
allow is refused and reported as denied (laws L3, L4).

Its output is normalized to events (`spec/run-event.schema.json`): `start`
(agent, command, arguments), `session` (model, session), `text`, `tool` (a
one-line summary of the call), `tool_result`, and `end` — `ok`, `turns`,
token `usage` (`input`, `output`, `cache_read`, `cache_write`),
`cost_usd`, `duration_ms`, the `denied` tools and the agent's last word.
A run whose agent the user's settings denied a tool is not `ok`: it did not
do its work, whatever the agent says; the tools are named, to be allowed in
the agent's own settings.
`--json` prints them one per line; without it, a person reads them, the
cost last. Exit `0` when the agent reports success, `1` when it does not
(or stops without a result, whose reason is the `end` event's), `2` when
the run cannot start: an unknown command, an agent without an adapter, or
its CLI not on `PATH`. Claude Code's adapter reads its stream-json (`claude
-p … --output-format stream-json`): every event, usage and cost. GitHub
Copilot's (`copilot -p …`) and Gemini CLI's (`gemini -p …`, owner decision
B2) pass on what they print as text, `ok` when the agent exits `0`, and
report no tool call, usage or cost: their `end` event says `measured: false`. No route of `catalyst serve`
starts a run (roadmap R5.5; whether the UI launches agents is open).

### `catalyst agent runs [--limit <n>] [--json]`

This user's logged runs for the project, oldest first: each `agent run`
appends one line to `$CATALYST_HOME/projects/<name>/runs.jsonl` — when, who
(the project's `git config user.name`), the agent, the command and its
arguments, `ok`, turns, token `usage`, `cost_usd`, `duration_ms` and the
`denied` tools. The log is the user's own, beside their agent choice: never
in the criterion or the project, never shared, and a log that cannot be
written never fails a run. Without `--json`, one line per run and the total
cost (`spec/runs.schema.json`).

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
where CI has no criterion — the product repository of a local-only
deployment. With the criterion available (a shared deployment, cloned into
the runner's catalyst home as `catalyst open` does), run it without the
flag so each ID must resolve. The repository is the project root, or the current
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
catalyst trace "$range"                                                     # or: trace --pattern-only
```

with `EVENT`, `BASE_SHA`, `HEAD_SHA`, `BEFORE` and `SHA` set from
`github.event_name`, `github.event.pull_request.base.sha`,
`github.event.pull_request.head.sha`, `github.event.before` and
`github.sha`. `catalyst` is the criterion's vendored CLI
(`$CATALYST_HOME/projects/<name>/criterion/bin/catalyst.pyz`) or, without a
criterion, the zipapp of a catalyst release.

### `catalyst badge [--metric check|chain] [--out <file>]`

A README badge (R6.28): one small SVG, `label | value`, its colour green,
amber or red and its text saying it all (`aria-label`, `<title>`).
`check` (the default): `passing`, amber when there are warnings, or the
number of `catalyst check`'s errors. `chain`: the rules in force that
something rests on, of all of them, meta-rules and retired rules left out
(green from 80%, amber from 50%). It is a file for a
CI job to publish beside the code; nothing is served, so no server answers an
anonymous request for it.

### `catalyst audit [--json] [--html <file>]`

The audit pack (R6.27): what the deployment runs (its project, kernel and
modules, the catalyst that made the pack, the criterion's commit), the
record's integrity (`journal verify`'s errors and warnings, `check`'s with
its first errors, and the gated rules whose current text lacks its
approvals), who signed how many entities, and each rule with its status,
strength and domain and everything that rests on it, transitively, nearest
first, each with the field that brought it in (`impact`'s chain downstream,
so no type is named). A rule nothing rests on is said; a meta-rule (in
`Rules-of-Rules.md`) is marked as one and counted with neither, since no
work rests on it. `--json` prints it
(`spec/audit.schema.json`); `--html <file>` writes a self-contained page,
no script and no remote file, printable to a PDF. `catalyst serve --local`
answers `GET /v1/audit`; a shared server has no such read, the integrity
checks needing the criterion's git. Nothing is written but the file asked
for.

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
  — rules and domains, the pointer to catalyst-users and the signers
  ledger (`--identity-issuer`, as for `init`; the installer is the identity
  it verifies), its own journal and git repository, no process module —
  and writes `workspace = "<name>"` into each member's
  `catalyst.toml` (not committed). A member of another workspace is left
  alone; a workspace name already used on the machine is refused.
- `status` lists the folders and which are members.

A member also sees the workspace's rules, domains and signers, read-only:
its artifacts may target a workspace rule, and it inherits the workspace's
pointer to catalyst-users when it has none of its own. Its own entries win
on a clash. `catalyst where` names the workspace.

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

### `catalyst migrate [--apply] [--template <TYPE>] [--since <version>] [--kernel <dir|zip>] [--json]`

What the deployment is behind on, and the mechanical part of catching up (R3.4). Without `--apply` it writes
nothing and lists, in order:

- `layout`: a legacy deployment (a `*.catalyst` pointer, a `.criterion` in the project, a symlink or a submodule),
  moved to the home store as `move --to-home` does.
- `template`: each templates folder that does not hold the template the kernel or its module ships today, to be
  added as its next version (`TEMPLATE-<T>-v<N+1>`, with a catalog row). A copy the deployment already holds, as any
  version and even copied raw, counts as held, so a team's own later version stays the latest. The kernel's are
  taken by `--apply` (its migrations require them where templates are kept); a module's are optional, as its
  migrations say, and taken only with `--template <prefix or name>` (repeatable, or `all`).
- `judgment`: each step the migrations since the kernel before the last sync (or `--since <version>`) leave to a
  person, with its qualifier ("optional", "only if the owner asks") and its migration. Never taken.

`--apply` takes the layout and the kernel's template steps, and the module templates asked for, journaled as one
`catalyst migrate` entry; a second run finds nothing more to add. `--kernel` is a catalyst checkout's
`framework/kernel` or a kernel release (directory or zip); from a checkout it defaults to the checkout's own. Without
one, the kernel's templates and migrations are not compared.

### `catalyst sync plan|apply --kernel <dir|zip> [--module <dir|zip|git-url>]`

The mechanical half of `/sync-framework`. `--kernel` is a catalyst
checkout's `framework/kernel` or a `kernel-vX.Y.Z.zip`; `--module` the
module's checkout (reduced to what its release ships), its zip, or a git
repository with an optional `@<ref>` (see `module install`). The base the
deployment was composed from is found next to a release zip
(`…/v<deployed>/kernel-v<deployed>.zip`), or from the checkout's git tag of
the deployed version; `--base-kernel` names it otherwise.

- `plan` lists what would change — CLI, invariants, the kernel documents
  copied as they are (`ANALYSIS-PLAYBOOK.md`, `definitions/README.md`), module
  tree, governing documents (recompose), the agent files an older catalyst wrote
  into the project to retire (`.claude/commands/`, or `--commands-dir`, and the
  hooks in `.claude/settings.json`), definitions of new types, versions — and the kernel and module
  migrations between the two versions, in order. It writes nothing.
- `apply` does it and journals one `/sync-framework` entry, the module's
  record (`modules/modules.json`) with it.
- With several modules installed, `--module` moves the one its source
  names and leaves the others as they are; a source naming a module that
  is not installed is refused. Without `--module`, the governing documents
  are recomposed with every installed module. A command file catalyst wrote
  but that was edited locally, or a kernel document edited locally, is reported, never removed or overwritten; a recompose conflict stops
  the sync before anything is written; a file no release ships is never
  touched.
  The migrations' judgment steps stay with the agent; `catalyst migrate` lists
  them and adds the template versions they ask for. A criterion with its
  own runtime (`.venv`) has it brought to the vendored CLI, so the launcher
  and the hooks run the version just deployed.
- Both refuse a module that needs a kernel newer than the one the shared
  criterion's gate runs (the `version.txt` of the shared branch as last
  fetched, when the criterion has the CI workflow): the gate checks every
  pull request with the CLI of its base branch, which could not read that
  module. Sync the kernel alone, publish and merge it, pull, then sync the
  module.

### `catalyst module install <source>[@<ref>] [--kernel <dir>]`

Installs a module into a deployment, as its first module or beside those
it has, only ever on the user's explicit request (INV-2). `<source>` is the module's directory, a release
zip, or a git repository (a URL, or a bare repository on this machine) with
an optional `@<ref>`: a branch, a tag or a commit. A repository is cloned
shallow into a temporary directory, removed afterwards. `--kernel` is the
`framework/kernel` of the release the deployment is at (default: this
checkout's).

It seeds the module as `init --module` does — its tree and record, a folder
per entity type, its definitions and invariants — merges the module's part
into the governing documents, names the module in the project file, and
journals one entry (`--as`, `--intent`, `--json`).

It refuses, before writing anything, when the module's kernel range
excludes the deployed kernel, or the one the shared criterion's gate runs;
when `--kernel` is not the deployed version; when the merge into a
governing document would conflict with local edits; when a URL or ref
could be read by git as an option; or when the module shares with the
kernel or an installed module something two modules must not share:

- its id (it is already installed: `module upgrade` moves it);
- an entity type prefix, an entity folder, or a definition;
- a namespace, or a meta-rule ID;
- a slash command, listed or generated;
- a tier id with another artifact or commit prefix (a module that declares
  no tier has the default ones);
- or when it grounds on another type than the modules already there.

**Several modules.** A deployment loads every module under its `modules/`,
in install order (the order of `modules/modules.json`); the project file
names the first. Entity types, tiers, aliases and namespaces are the union
of the modules'. The catalogue, the handbook and the Taskfile carry each
module's part under its own `From module <id>` heading, in install order.
The first module's invariants sit at the criterion's root
(`INVARIANTS.module.md`); a module installed beside it keeps its own in
its folder, and the session brief and `catalyst why` read them all.
`catalyst check` reports its scope as `modules <id>, <id>`.

### `catalyst module upgrade <id> [<source>[@<ref>]] [--kernel <dir>] [--plan]`

Moves one installed module to another release through `sync plan|apply`
(the kernel and the other modules stay): `--plan` lists what would change and writes nothing.
Without `<source>`, the repository its record names is fetched; a record
that names a directory or a zip gives nothing to fetch, and the source must
be passed. Every refusal of `sync` applies.

### `catalyst module list|verify [<id>] [--json]`

The modules a criterion holds. `init` and `sync apply` seed a module the
same way — what its release ships, with the manifest a release carries —
and record it in `modules/modules.json`: id, version, source (a repository
URL, a release file's name or a directory's name, never a path), the commit
when the source is a git checkout, and the sha256 of the deployed tree
(text files counted with LF line endings, so every platform agrees).

- `list` prints the record; no network.
- `verify` recomputes each tree's hash and exits `1` when one differs from
  its record, or when a recorded module's folder is gone. `catalyst check`
  reports both as errors.
- A deployment installed before the record existed is listed as not
  recorded, which is not an error: its next `sync apply` records it (the
  source stays empty when that sync names no `--module`).

### `catalyst module available <id> [--json]`

The releases of an installed module: the version tags (`1.2.3` or `v1.2.3`)
at the repository its record names, read with `git ls-remote` (the
network), newest first, each marked `installed` or `newer`
(`spec/module-releases.schema.json`). A module installed from a directory
or a zip has no repository to list, and an unreachable one is refused,
exit `1`. `catalyst serve --local` answers `GET /v1/modules` (`module list
--json`), `GET /v1/modules/<id>/available` (this) and `GET
/v1/modules/<id>/plan?to=<tag>` (`module upgrade <id> <its repository>@<tag>
--plan --json`, for a tag this lists, never another source); a shared server
has none of them.

### Administration: `user`, `role`, `freeze`, `unfreeze`, `definition migrate`

Each refuses what its slash command refuses, writes, and journals one entry
(`--as`, `--intent`, `--json`; exit `1` and no change on a refusal).

- `catalyst user add|remove|modify|assign-role` and `catalyst role
  add|modify` always refuse, exit `1`: people, roles and what each role
  grants are catalyst-users' (design 29). The refusal names where to make
  the change: `catalyst-users users …` for people, `catalyst-users roles
  provision` to write the roles template into the provider; a grant is then
  changed in the provider.
- `catalyst freeze <item>` / `unfreeze <item>`: an artifact ID, entity type,
  template name or working-copy path, listed in (or removed from) the
  working copy's `.frozen`.
- `catalyst definition migrate <type> <version> [--kernel <dir>]`: overwrite
  `definitions/<type>.md` with that version from the kernel's or the
  deployed module's `definitions/<type>/`; refuses a version that does not
  exist (INV-23).

### Writing verbs: `new`, `status set`, `link`, `restore`

The mechanical half of creating and changing artifacts, from the entity type
definitions. Each signs as the verified identity (Signer, above), keeps
back-references, regenerates the indexes and writes one journal entry
(`--intent` repeatable, `--command` names the slash command it runs for,
`--tier`; without `--tier`, the tier the artifact's type opens when exactly one
tier names it, so a requirement's change is a feature's without saying so).
Each takes `--json` and exits `1`, changing nothing, on a refusal. An
`--intent` of fewer than three words once IDs are left out ("work starts",
"R4.8") is warned about on stderr, as by `journal append`; the change is
still made (R4.8).

- `catalyst new <type> --title <t> [--field NAME=VALUE ...]`: the next ID,
  the type's latest template with its fields filled (ID, name, file name,
  initial status, dates, signer, the given fields; references as
  comma-separated IDs, checked to exist). Refuses a missing required field.
  The sections below the field table stay for the agent to write.
- `catalyst status set <ID> <status> [--force]`: a status the type allows,
  one it can reach when the ETD declares transitions, and one whose guards
  hold (`workflow.guards`: the refusal names each failing condition);
  `--force` writes any value and passes a failing guard, which the journal
  entry records. With `--through`, a status the declared transitions reach
  only through other states is reached through the shortest such path, each
  state's gates and guards checked, in one journal entry naming the path
  (never with `--force`). A `RECON-` case is refused: only `/reconcile`
  changes one.
- `catalyst repair derived [--as <user>] [--tier <tier>]`: rewrite every
  derived field (another type's `backref`) that disagrees with its sources,
  in one journal entry (by default the module's tier with no artifact).
  Run again, it changes nothing.
- `catalyst link <ID> <field> <ID>...`: cite IDs in a reference field and,
  when the field declares a back-reference, cite this artifact back.
- `catalyst restore <ID> --to <timestamp|#N>`: write the entity's file back
  as it stood after the last journal entry at or before the timestamp, or
  after its `N`th change (`#1` is the first; exact when timestamps tie, as
  `journal show --artifact <ID>` lists them). Its derived fields are then
  recomputed from their sources. A new journaled change: no entry is
  rewritten. Refused, saying why: a rule that shares its document with
  other rules, no version at that time, a version redacted or no longer
  held, a file already as it stood then.

### Identity providers: `catalyst identity`

Who signs (design 29). A criterion holds no user or role registry:
`IAM/identity.json` points at the deployment's catalyst-users configuration
(`{"provider": "keycloak", "issuer": "https://id.example.com/realms/catalyst"}`,
`FORMAT.md` §6), and people, roles and groups are catalyst-users':

- `identity configure --issuer <url> [--provider keycloak] [--client <id>]
  [--catalyst-client <id>]` writes the pointer, signed (`--as`) by the
  identity the new pointer verifies, or the one before it, and journaled.
  `check` reports a missing or broken pointer; a workspace member may
  inherit its workspace's.
- `identity login` (the device flow: open the link, confirm the code),
  `identity logout` (revokes), `identity whoami` (userid, groups, roles and
  grants, verified now), `identity status` (no network). With `--issuer
  <url>` each works outside any deployment, e.g. before `catalyst init`.
  Tokens are kept owner-only under `$CATALYST_HOME/identity/`, never in a
  criterion or a project.
- Every writing verb signs as the identity catalyst-users verifies: the
  logged-in person, refreshed and confirmed by the provider, or, with no one
  logged in, this machine's system account (the admin `catalyst-users
  setup` named), when its settings point at the same provider; catalyst says
  so on standard error. `--as` names only that identity. With no verified
  identity (not logged in and no system account, the provider unreachable)
  nothing is signed, and the read verbs still work. An identity's first
  signature appends its line to `IAM/signers.jsonl` (`FORMAT.md` §6); its
  userid ends every ID it creates and the journal's `actor` is the ledger's
  username.
- The logged-in identity is kept per machine as a read-only snapshot
  (username, name, groups, roles, grants) with a hash of its content,
  rewritten at each signature; an edited one is discarded and its owner
  authenticated anew. A change of roles or groups in the provider is seen
  at the next signature.
- What a signer may do is their grants from the provider: `cmd:<command>`,
  `cmd:*`, and `reconcile:<level>` for `catalyst reconcile`; a role's name
  grants nothing. An approval records the signer's roles, and its gate
  counts it with them.
- `user …` and `role …` refuse: people and roles are managed in
  catalyst-users. The users, roles and groups templates
  (`IAM/{users,roles,groups}/templates/`) only shape how people are shown.

The OIDC code is catalyst-users' standard-library core, vendored under
`scripts/catalyst/identity/` at a release (`VERSION`); it is changed there, then
vendored again with `scripts/vendor_identity.py`.

### Approval gates: `approve`, `approvals`

Opt-in (decision G): a deployment declares its gates in `IAM/gates.json`
(`framework/kernel/schemas/gates.schema.json`); without the file there is
no gate. A gate covers the rules of one domain, or an entity type entering
one state, and asks for a number of approvals from one role: a role of
the deployment's roles template, held as the provider's role of that name.
A type's gate may carry `"when"`, a condition on the
entity's fields (`"Classification at least Confidential"`, below): it then
applies only to an entity for which it holds. `catalyst check` reports a
malformed gate, or one naming an unknown role, domain, type, state, field
or value, as an error.

- `catalyst approve <ID> --gate <gate> [--as <user>] [--intent <why>]`:
  one journal entry (action `approve`, no file changed) naming the gate and
  the version approved: the blob of the entity's file as it is now. Refused,
  saying why: a gate that does not cover the entity, a signer who is not
  active or does not hold the gate's role, the author of that version (the
  actor of the entry that wrote it: an author never approves their own
  change), or a second approval of the same version by the same person.
- `catalyst approvals <ID> [--json]`: each gate covering the entity, the
  approvals that count for its current version and how many are missing
  (`spec/approvals.schema.json`). Once the text changes, earlier approvals
  no longer count.

Gates are enforced (`Rules-of-Rules.md` §11):

- `catalyst status set` into a gated state is refused until the gate's
  approvals for the entity's current version are recorded; the refusal
  names how many are missing and from which role. `--force` passes the
  module's guards, never a gate: a gate that must be passed is removed in
  `IAM/gates.json`, a journaled change. `catalyst new` refuses an initial
  status a gate covers, and `catalyst restore` a version whose Status
  enters a gated state without its approvals. A malformed `IAM/gates.json`
  refuses every move until it is fixed.
- `catalyst check` reports one error (`gates unapproved`) per rule of a
  gated domain whose current text lacks its approvals; a retired rule is
  left out.
- `catalyst inbox` lists what waits (kind `approval`), and
  `GET approvals/<id>` answers `catalyst approvals <id> --json`.

### Landing: `landing init`, `landing show`

How an accepted change reaches the criterion's repository (design 33,
fw-STRUCTURE-000023): `IAM/landing.json`
(`framework/kernel/schemas/landing.schema.json`) holds ordered rules, each
matching a change (`via`, `who`, `change`, `types`) and saying what one pull
request carries (`group`: `change`, `session`, `window`), who must approve
it (`review`: `none`, or approvals from a role in catalyst's inbox or on the
host) and how it merges (`merge`: `auto`, `admin`). The first rule that
matches decides; `default` decides when none does. Without the file, the
kernel's `standard` policy applies. Phase 1 declares and checks the policy;
nothing lands through it yet.

- `catalyst landing init [--policy standard|open|reviewed|host] [--force]
  [--as <admin>]`: writes the kernel's policy to `IAM/landing.json`,
  journaled as the Admin's assent (L3) to every landing it allows (decision
  33.1). An admin's only; an existing file is replaced only with `--force`.
  Onboarding runs it with the roles (`INSTANTIATION-CHECKLIST.md`).
- `catalyst landing show [--json]`: the policy in force and where it comes
  from (`spec/landing-show.schema.json`).
- `catalyst check` reports a malformed policy, or one naming an unknown role
  or type, as a `landing:` error, and warns when a criterion shared through a
  server names no `target.credential`.

Every journal entry also says how its change was made, `via`
(fw-STRUCTURE-000022): `agent` in an agent's session (`catalyst mcp` and
`catalyst agent run` set `CATALYST_VIA=agent` for what they run; `AI_AGENT`,
`CLAUDECODE` or `GEMINI_CLI` in the environment), `person` otherwise, and
`server` on a server's own entries. `CATALYST_VIA=person` or `=agent` says it
outright: a UI's host running a verb for the person who clicked sets
`person`.

### Workflow governance: conditions, due dates, governing workflows

- **A condition** on an entity's fields is one line: `<Field> is|is not
  <value>`, `<Field> in|not in <value>, …`, `<Field> at least|at most
  <value>` (ordered by the field's enum values, else as numbers, else as
  dates), `<Field> is set|is empty`. A module's guard `holds: <condition>`
  must hold to enter its state; a gate's `when` makes it apply only where
  one holds; a governing workflow's `When` column limits a move to it.
- **A due date:** a type's `due` (`Due`, or `Checked + 30 days`) makes an
  open entity past it `overdue`: `catalyst inbox` lists it (kind
  `overdue`: its status, the date field, the date, the days past it and the
  role its governing workflow escalates to) and `catalyst check` warns. A
  `due` naming a field that is not a date is a `check` error.
- **A governing workflow:** a `WORKFLOW-` that names a type (`Governs`) and
  is `Active` lists the moves that type may make in its `## Transitions`
  table (`From`, `To`, `Role`, `When`; `From` may be `*`). `catalyst status
  set` refuses a move it does not list, one whose `Role` the signer does not
  hold (an `Admin` holds every role) and one whose `When` does not hold;
  `--force` does not pass it. `Escalates to` names the role an overdue
  entity of the type is escalated to. `catalyst check` reports, as errors,
  two active workflows governing one type, a state, role, field or value
  the type or the deployment does not have, and a governing workflow with
  no move.

### Proposals: `propose`

A change offered for review before it lands (decision P, design 26): a
reconciliation case with `Trigger: proposal`.

- `catalyst propose <ID> --from <file> [--title <t>] [--as <user>]
  [--intent <why>] [--json]`: opens the case, naming the entity, its file's
  blob now (`Baseline`, the base) and the proposed content, kept beside the
  case as `reconciliations/<RECON-id>.proposed` (`Proposed`, its blob); one
  journal entry, the entity's file untouched. A rule is proposed as its
  rule document, whole. `-` reads the content from standard input. Needs a
  `propose` or `full` reconciliation level (a `reconcile:<level>` grant).
- `catalyst reconcile <case> accept` writes the proposed content to the
  entity (its derived fields recomputed), journaled by the acceptor with
  `proposal` and `proposed_by` (the proposed version's author); refused
  when the entity's file is no longer the base, for that author (law L4),
  and, for a move into a gated state, until the gate's approvals of the
  proposed version are recorded. `accept-with-edits --from <file>` writes
  the acceptor's content instead. `propose --from <file>` revises the
  proposal against the entity as it is now (a new base). Its author may
  `close` it while it is open (withdrawn); `reject` writes nothing.
- `catalyst approve <case> --gate <gate>` approves the proposed version of
  the case's entity; once it lands those approvals count for the entity,
  and the proposal's author, not the acceptor, is the version's author.
- `catalyst check` reports an open proposal whose entity is gone, whose
  base names no blob, or whose proposed file is missing or changed outside
  catalyst. `catalyst view <case>` gives `proposal`: the entity, its file,
  both blobs, the author and both contents.

### Editing an entity: `edit`

`catalyst edit <ID> [--field NAME=VALUE]… [--section HEADING=TEXT]…
[--section-file HEADING=FILE]… [--as <user>] [--intent <why>] [--json]`
(design 31, `fw-STRUCTURE-000021`) changes an entity's plain fields and
sections, journaled. It never edits `ID` (L7), `Name` or `Filename`
(`rename`), `Signed-off-by` (the verified signer), `Status` (`status set`
and its workflow) or a field catalyst derives; a reference field is
`link`'s, which keeps its back-references. An enum takes only its allowed
values, and an edit that changes nothing is refused.

An admin's edit is made. Anyone else edits only an entity of theirs (they
created it, or a person field names them): directly when it is linked to
nothing; when it cites or is cited by anything, the edit is opened as a
proposal (`propose`, which needs reconciliation rights) that an admin
decides, and the entity's file is untouched until then.

### Trying a change: `try`

`catalyst try [--json] [--keep] <verb> <its arguments…>` (decision T,
design 27) makes one change on a scratch copy of the criterion and says
what it would do; nothing in the criterion or the project changes, and the
journal holds nothing of it. The verb is one of catalyst's writing verbs
(`status`, `new`, `edit`, `link`, `rename`, `restore`, `approve`,
`reconcile`, `propose`), run with its real refusals: a refused change is the answer
(exit `1`, its message said). `catalyst try --proposal <case> --as <user>`
tries accepting a proposal.

The copy is a `git clone --shared` of the criterion under
`$CATALYST_HOME/scratch/` (its objects read in place, its refs its own),
with the criterion's files as they are now copied over it, uncommitted
changes and new files included; it is removed after, or kept with
`--keep`. The report (`spec/try.schema.json`) gives the files the change
writes with their blobs before and after, the `check` findings it adds and
clears (compared as text, with their entity), the `impact` of the entity
it touched, and what it would leave waiting for an approval. The project
side of `check` is not tried; nothing is shared. Making the change for
real is running the same verb without `try`.

**`--preview` and `--forewarned`** (design 31, the admins' forewarning):
every writing verb takes them. `catalyst <verb …> --preview` is `catalyst
try <verb …>` (its `--json`, the try report). `catalyst <verb …>
--forewarned` tries the change first, then makes it anyway: when it adds
`check` findings, its journal entry's intent gains `forewarned: N
finding(s) added: …`, computed by catalyst, and they are said on stderr. A
UI runs an admin's write with `--preview`, then with `--forewarned` once
they confirm.

### Read-only views: `list`, `view`, `backlog`, `journal show`, `graph`, `impact`, `inbox`

Computed from the working copy and the entity type definitions; none of them
writes. `view`, `impact` and `journal show --artifact <id> --content` take an
ID as people write it: in full, short (`REQ-000030`, when one artifact has
that number), or a meta-rule as the handbook writes it (`rr-META-015`); a
short form two artifacts share is refused with both IDs. Each takes `--json`; each payload, and `check --json`'s, is
described by a JSON Schema in the catalyst repository's `spec/` (its
`README.md` maps each schema to its verb and route), which a client can
generate its types from.

- `catalyst list <type> [--filter KEY=VALUE ...] [--type <family>]`:
  artifacts of an entity type (its prefix, name or folder), or `rule`,
  `user` (the signers ledger, with the people of a retired registry),
  `role` (the roles template, for display), `template` (`--type` narrows
  to one family), or `all`.
  A filter keeps items whose field matches, with `*`/`?` wildcards. An
  unknown type exits `1` and names the known ones.
- `catalyst view <ID>`: one artifact or rule, its fields, the IDs it links
  to, the artifacts linking to it and its journal entries; a rule also
  gives its `title`, `status`, `domain` and `text` (its own section, read
  as `graph` reads it).
- `catalyst backlog`: open items per type and status ("open" is any status
  outside the ETD's closed states), open items missing a required link,
  rules no open item targets, and `coverage`: the project's active rules
  (the handbook's meta-rules left out) and how many of them an artifact,
  open or closed, cites in a reference field.
- `catalyst journal show [--since <date>] [--artifact <id>] [--actor <name>]
  [--rule <id>]`: journal entries in time order, filtered.
- `catalyst journal show --artifact <id> --content`: the history of one
  entity (an artifact or a rule; a short ID resolves). Every journal entry
  that changed its file, whatever it is labelled with, in the journal's
  causal order, each with who, when, the command, the intent and the file's
  content before and after, taken from the blobs the journal names. As text
  each change is a unified diff; `--json` gives the payload described by
  `spec/history.schema.json` in the catalyst repository. Content whose blob
  is no longer available is `null`, its hash kept. A rule's history is that
  of the document that holds it. `--content` needs `--artifact`.
- `catalyst graph`: the whole chain in one answer — `rules` (with their
  domain, `title` and `status` line), `domains` (each `{code, file, title}`),
  `artifacts` (each `list` row plus `links`, the IDs each reference field
  cites; an item kept as a table row has `row: true`, the file and line of
  its row and its cells by header in `fields`) and `types`, each entity type's fields, states
  and grounding, so a client needs neither a parser nor the module's type
  list. Every rule and artifact also has `mentions`: the IDs its own text
  cites in backticks (a rule: its section, or its file), resolved like field
  links, itself left out.
- `catalyst impact <id> [--up|--down] [--depth <n>]`: what an entity (an
  artifact, a rule or a domain; a short ID resolves) rests on, `upstream`,
  and what rests on it, `downstream`, followed transitively. A link runs
  from an entity to what one of its reference fields cites, and from a rule
  to its domain; a derived field mirrors its source and adds none. Each
  entry has its `depth` and `via`: the entity one step nearer (`id`), the
  `field`, and the entity that carries it (`on`). `--up` or `--down` gives
  one side, `--depth` stops after that many links. IDs cited in prose only
  are listed apart (`mentions`, `mentioned_by`) and never followed. An
  unknown ID exits `1`. The payload is described by
  `spec/impact.schema.json` in the catalyst repository.
- `catalyst inbox`: what waits for a person, each item with its `evidence`
  and `settle`, the commands that settle it. Seven kinds: a commit made
  outside catalyst whose changes the journal does not record
  (`unrecorded-commit`: adopt it or revert it); a changed or new project
  file not journaled yet (`unrecorded-change`); a reconciliation case that
  is not closed (`reconciliation`: the decisions `catalyst reconcile`
  takes); an analysis in its deciding phase (`analysis`); a gated change
  waiting for its approvals (`approval`: a gated rule whose text lacks
  them, or an open entity one move away from a gated state that lacks them
  for its current version; `catalyst approve` settles it); a proposal
  being decided (`proposal`: its entity, file, base, proposed blob and
  author; the `reconcile` decisions settle it), listed apart from the
  disputes; an open entity past its type's due date (`overdue`: moving it
  on, or a new date, settles it). It lists and
  settles nothing, and exits `0` whether or not anything waits. A bare
  working copy has no project history and lists the last four kinds only.
  The payload is described by `spec/inbox.schema.json`.

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

Prints a new userid: 8 characters drawn uniformly from `[A-Za-z0-9]` with
a cryptographic random source, redrawn if it has no uppercase letter or
collides with a known one (INV-26). An identity's first signature draws its
own the same way.

### `catalyst journal append`

```
catalyst journal append --command <cmd> --action <action> --artifact <id|description>
                        --intent <text> [--intent <text> ...]
                        --file <path> [--file <path> ...]
                        [--target <id> ...] [--tier <tier>]
                        [--as <user>] [--allow-unchanged] [--json]
```

Appends one entry to the signer's shard
(`development/journal/<actor>@<machine>/<YYYY-MM>.jsonl`), under the
criterion's journal lock, with the real UTC time,
the signer as `actor`, and each file's `before`/`after` git blob hashes
(`Rules-of-Rules.md` §12). Write the files first, then append.

- `--command` names the command the change was made for: one of the
  deployed `CODE-OF-CONDUCT.md` §4 or its aliases, a `catalyst <verb>`, or a
  tier's name. Another is written as given, with a warning on stderr.
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
  one of the active module's tiers (`module.yaml` `tiers:`, see
  `MODULE-SPECIFICATION.md`); a module that declares none has `chore` (no
  rule's behaviour changes; needs no artifact), `fix` (restores a documented
  rule's behaviour) and `feature` (new or changed behaviour). Anything else
  is rejected, naming the tiers. What each tier requires beyond the entry is
  the active module's (`CODE-OF-CONDUCT.md` §3, §9); the tier is omitted
  from entries that do not state one.
- A file whose content equals its last journaled state is rejected, since
  it did not change; `--allow-unchanged` accepts it deliberately.
- `--json` prints the written entry.

### `catalyst journal adopt`

```
catalyst journal adopt <commit> [<commit> ...] | <A>..<B>
                       --intent <text> [--intent <text> ...]
                       [--target <id> ...] [--artifact <id|description>]
                       [--tier <tier>] [--as <user>] [--json]
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

### `catalyst journal redact <blob>... --intent <why>`

Redacts content the journal names, such as a secret journaled by mistake
(decision A5): an auditable tombstone, never a rewrite. It appends one entry
(action `redact`, the blobs under `redacted`, who and why; `--intent` is
required) and takes the blobs out of the pins of the criterion and of the
product repository, rewriting the pin ref as one commit without history so
that no older pin commit keeps them. Every entry, hash and commit stays as
it is, so the journal's chain still verifies. A blob the journal does not
name is refused.

From then on the readers treat the content as redacted: `journal verify` and
`check` note the redaction and report no missing blob for it, `journal pin`
and the pin merge of `share`/`criterion` never pin it again, the history
(`journal show --artifact <id> --content`) shows it as `null` with
`redacted: true`, and `journal restore` skips it.

What it does not do: a commit that holds the file still holds the blob,
here and on every clone, until the history is rewritten (`git
filter-repo`), which is the owner's call. Rotate the secret first. The
shared copy's pins change at the next publish.

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

- **`start [<path>...] [--mode bootstrap|incremental] [--passes 1|2] [--name <name>] [--as <user>]`**
  — allocates the record (Status `Extracting`, its `Passes`) and writes
  `inventory.json` (with `passes`: two, four-eyes, unless `--passes 1` or
  `catalyst.toml`'s `analysis_passes = 1` says one; another value of
  `analysis_passes` is refused): every tracked file under the paths (default: the whole
  project, never `.criterion`) with its blob hash, and the product's `HEAD`
  as the code state. `incremental` (the default) also lists the rules,
  domains and rule-grounded artifacts already recorded; `bootstrap`
  refuses when rules exist.
- **`record <ID> --pass A|B <file> [--replace]`** — validates one pass's
  findings (`ANALYSIS-PLAYBOOK.md`, "Findings format": kind, title,
  statement, confidence; a rule's status; in-scope file and line evidence;
  a defect's `breaks`, an existing rule or a rule finding of the same
  pass) and stores it once as `A.json` or `B.json`. Warns when both passes
  are identical. A single-pass analysis refuses `--pass B`.
- **`diff <ID>`** — needs both passes (a single-pass analysis: pass A,
  every finding of which is then `a_only`): pairs findings (same kind; wording
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
- **`status <ID> [--json]`** — the phase, the passes, the diff counts, how
  many findings are decided, and anything keeping the record from its
  phase. `--json`: the full report — what each pass recorded, the diff's
  counts, each reconciled finding with its decision, the problems
  (`spec/analysis.schema.json`; `GET /v1/analyses/<ID>`).
- **`list [--json]`** — every analysis in brief, newest first: phase,
  passes, findings decided, accepted and rejected
  (`spec/analyses.schema.json`; `GET /v1/analyses`).

`catalyst check` applies the same rules to every record: a record in
`Reconciling` or later without its passes and the diff, in `Deciding` or
later without a complete reconciliation, or `Closed` with an undecided
finding or a missing artifact, is an error.

### `catalyst share info|status|pull|push|create|join|login`

The criterion's sharing, whichever driver holds the shared copy (roadmap
R3.2). `catalyst.toml` may name the driver (`share = "git"`, or
`share = "serve"` with `share_url`); without it a criterion with a git
remote, or a project file naming its repository, uses `git`, any other
`local`.

- `info [--json]`: the driver, where the shared copy is, the shared branch,
  and what the driver can do.
- `status [--fetch] [--json]`: unpublished local changes, and how far this
  criterion is ahead of or behind its shared copy.
- `pull`: bring in what the shared copy has; refuses while local work is
  unpublished (git: `criterion sync`).
- `push -m <message> [--as <user>] [--no-pr] [--yes] [--json]`: publish
  this criterion's changes (git: `criterion push`). Without `--yes` it
  prints what it would publish — uncommitted changes, local commits, and
  whether they are added to the open topic branch (its pull request: one
  batch) or start a new one — and exits `3` (INV-4). When the branch is
  pushed but no pull request could be opened, it says so and why.
- `create <url> [--branch <name>] [--protect] [--yes]`: publish a local-only
  criterion for the first time (git: `criterion create <url>`); `--protect`
  also makes pull requests and the `catalyst` check required on the shared
  branch (GitHub, `criterion protect --yes`). Needs `--yes` (INV-4).
  `create <url> --driver serve --as <user> --yes` shares it through a
  `catalyst serve` server instead: `catalyst.toml` gets `share = "serve"`
  and `share_url` (journaled, staged, not committed), then every file is
  pushed.
- `join [<url>]`: bring a shared criterion to this machine, from a project
  whose `catalyst.toml` names it (git: `criterion join`; serve: an empty
  criterion filled by a pull). `catalyst open` does the same.
- `login <url> [--token <t>]`: keep this user's token for a server in
  `$CATALYST_HOME/credentials` (read from stdin without `--token`).

Drivers: `local` (not shared: `pull` and `push` say how to share it), `git`
(below) and `serve` (`catalyst serve`, below). The working form behind every
driver is the criterion's store — read, list, append, lock
(`scripts/catalyst/store.py`).

With `serve`, `push` sends every file that differs from the server's
version this criterion last saw, and the content of every version the new
journal entries name. The server applies the push all or nothing, and
refuses it — nothing applied — when a file moved on the server since, when
a change to a file it already has is not journaled, when a new entry is
signed by anyone but the token's user, when an artifact ID is already
another file's, or when a `RECON-` case changes beyond the signer's
`reconciliation` level. `pull` writes what changed on the server, appends
other people's shards, and stops with nothing written when a file it would
overwrite changed here too: a human settles it (a `RECON-` case).

### `catalyst serve [--db <file>] [--host <addr>] [--port <n>]`

A server several people share criteria through (roadmap R3.9). It keeps
every version of the criterion's files (SQLite, `--db`, default
`$CATALYST_HOME/serve/serve.db`), listens on `127.0.0.1:8765` unless told
otherwise, and leaves TLS to a reverse proxy in front of it. JSON over HTTP
under `/v1`: `GET head`, `GET changes?since=<batch>`, `GET blobs/<sha>`,
`POST have`, `POST push`; every request carries a bearer token.

The read side answers what the read commands answer, with the CLI's own
code over the server's current files, so a client needs no parser of its
own: `GET list?type=<type>&filter=<field=value>` (`catalyst list --json`),
`GET view/<id>` (`catalyst view`), `GET backlog`, and
`GET journal?since=&artifact=&actor=&rule=` (`catalyst journal show`),
`GET graph` (`catalyst graph`),
`GET impact/<id>?direction=up|down|both&depth=<n>` (`catalyst impact`),
`GET commands` and `GET spec/<command>[/<part>]` (`catalyst spec --json`;
a criterion without a `CODE-OF-CONDUCT.md` lists no command), and
`GET history/<id>` (`catalyst journal show --artifact <id> --content`; on a
server the content comes from the blobs it holds), `GET approvals/<id>`
(`catalyst approvals <id> --json`), `GET analyses` and `GET analyses/<id>`
(`catalyst analysis list|status --json`), `GET definitions` (`catalyst
definition list --json`, each deployed definition's slug, version and
description), and `GET inbox`
(`catalyst inbox`; a server has no project history, so its inbox holds the
reconciliation cases, the analyses and the approvals only). Each
answer carries the batch it is for in the `X-Catalyst-Batch` header; an
unknown type or ID is a 404 with the CLI's message. `GET events` is a
server-sent event stream: the current batch on connect, then each new batch
number as it lands. `GET check` answers 501 on a server: its files have no
git history, so the journal checks run where the criterion is. The first
push to an empty server is an import: it brings the history as it is, so
only its signers are not checked.

- `serve token issue <userid>`: a token for a signer of the criterion,
  printed once (the server keeps only its hash); they keep it with `share
  login`.
- `serve token list`, `serve token revoke <n>`.

Tokens are managed on the server's host, by whoever runs the server.

With `--identity-issuer <url>` (and `--identity-api-client <id>`, default
`catalyst-api`; its secret in `CATALYST_IDENTITY_API_SECRET`), the server also
accepts that identity provider's access tokens: only when the provider's
introspection says the token is active, issued by that issuer and meant for the
API client, kept at most 30 seconds. The signer of a push is the line of
`IAM/signers.jsonl` for the token's issuer and subject; a push may add ledger
lines for its own identity only (an import, every signer's) and never change
one. A client sends its provider token when it is logged in, else its
`share login` token.

`--criterion <name>` names the criterion the database serves, its
`project_name`: recorded once (a later start with another name is refused;
one without `--criterion` serves the recorded name) and reported by `GET head`
(`criterion`). A push's signer who administers that criterion in
catalyst-users (`administers`, a `criterion-admin`) holds every grant and the
reconciliation level `full` there (`fw-IDENTITY-000011`). The operator names
it, never a push: a client's `catalyst.toml` is only its word. Without a
name, administering a criterion gives nothing on the server.

**Membership** (design 32, `fw-IDENTITY-000012`, `fw-IDENTITY-000013`). Who
is a member of the served criterion is the identity provider's, asked through
catalyst-users; the server keeps the record, a ledger in its database and
never in the criterion: each entry (who was added or removed, by whom, when,
why) encrypted with the criterion's data key, chained to the one before it by
its hash, and signed by the server. Once the ledger is open the server **fails
closed**: it accepts only the provider's tokens, and admits the Admin and the
criterion's admins, and anyone else only when the provider (asked then, kept
10 seconds) and the ledger both name them. `GET members` lists them and `POST
members` (`{op: add|remove|adopt, member, reason}`) changes them, at the
provider and in the ledger, for admins only. Once a day, whatever changed,
the server writes the ledger's head into the criterion
(`IAM/membership.fingerprints.jsonl`, journaled by its own batch, signed by
whoever opened the ledger), so a rewritten ledger no longer matches what every
clone holds. The cryptography is pycryptodome's, needed on the server's host
only.

- `serve key init [--key-command <cmd>]`: the master key, a new one in this
  host's keychain, or one a key-management service prints (`<cmd>`, or
  `CATALYST_SERVE_KEY_COMMAND`); never in the database.
- `serve key escrow --holder <admin> ... --threshold <k> --out <dir>`: the
  break-glass copy, one share file per holder, any `k` recovering the key.
- `serve key recover --share <file> ... [--reason <text>]`: recovers the key
  from a quorum of shares, records it in the ledger and the journal, and
  replaces the key, every share then void.
- `serve members open [--yes] [--reason <text>]`: the Admin opens the ledger,
  adopting the provider's current members once they agree to the list (exit
  `3` shows it); the first fingerprint follows at once.
- `serve members check [--json]`: the chain, the signatures, the criterion's
  fingerprints, and where the provider's group and the ledger disagree; exit
  `1` on any finding.
- `serve members fingerprint`: writes one now.

### `catalyst members list|add|remove|adopt [<member>] [--reason <text>]`

A served criterion's members, through its server (design 32): `list` them, or
`add`, `remove` or `adopt` (a member already at the provider, recorded) one, with
the reason. The Admin and the criterion's admins only. A criterion not shared
through `catalyst serve` has admins only: the command refuses there.

Embedding (owner decision B8): `--allow-origin <origin>` (repeatable; `--local`
adds `catalyst.toml`'s `embed_origins`) lets pages of that origin read: their GET
requests get `Access-Control-Allow-Origin` and the preflight for a GET is
answered; each read still needs its reader's token, any other method from such
a page is a 403, and no origin is allowed unless named.

`catalyst serve --local [--project <dir>] [--port <n>] [--static <dir>]` serves a project's
own criterion read-only, for a client on this machine that reads every
criterion the same way, served or not. It listens on 127.0.0.1 only, on a
port the system picks unless `--port` names one, and prints one JSON line,
`{"url", "token", "pid"}`; the token is made for the run and never stored.
The read endpoints and `events` answer as on a server, `GET check` returns
`catalyst check --json`, `GET head` adds what the deployment runs (`kernel`,
`modules` with their versions, and `catalyst`, the version serving it) and
its `project` name (catalyst >= 0.86.0),
`GET runs` returns this user's run log for the project (`{runs: [...]}`;
local mode only — a shared server keeps nobody's runs), and `push`, `have`,
`changes` and `blobs` answer 405. Its batch is a change counter: it moves when a criterion file changes
(checked every second), and `events` sends it.

`--static <dir>` (with `--local` only) also serves a directory's files,
for every path outside `/v1`; `/` is its `index.html`. The kernel ships no
page: the directory is the client's. A file needs no token (the page is
what brings the token to the API), a path that leaves the directory or a
missing file is a 404, and the content type follows the extension with
`X-Content-Type-Options: nosniff`. The start line gains `page`, the page's
URL with the token in its fragment (`#token=…`), which a browser never
sends to the server. In this mode an API request whose `Origin` is not the
server's own is refused (403), so another page in the browser cannot read
the criterion even with the token.

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

#### `catalyst criterion push -m <message> [--as <user>] [--no-pr] [--url <url>] [--yes]`

Without `--yes`, it prints what it would publish and exits `3` (INV-4; on a
terminal it asks). `create <url>` and a first `--url` on `sync` publish too,
and take `--yes` the same way.

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
   already open for the branch). Without `gh`, or when `gh` fails, it
   prints the branch to open a pull request from, and the reason.

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
instead. An ID a deployed module lists under `aliases:` counts as kept
when the ID it now has is recorded at `<rev>`. It reads revisions
straight from git, so it needs no checkout
of them. `catalyst check` runs it on its own whenever the criterion's HEAD
is a merge.

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

## Machine-readable output

<!-- generated: cli-json (scripts/gen_docs.py; do not edit by hand) -->

What each command prints with `--json`, and the JSON Schema in `spec/` that describes it, generated from `spec/README.md` and the CLI's parser.

| Command | Schema |
|---|---|
| `catalyst validate` | `spec/validate.schema.json` |
| `catalyst check` | `spec/check.schema.json` |
| `catalyst report` | `spec/report.schema.json` |
| `catalyst audit` | `spec/audit.schema.json` |
| `catalyst unrecorded` | `spec/unrecorded.schema.json` |
| `catalyst spec` | `spec/commands.schema.json`, `spec/command-spec.schema.json` |
| `catalyst journal append` | `spec/journal-entry.schema.json` |
| `catalyst journal adopt` | `spec/journal-entry.schema.json` |
| `catalyst journal verify` | `spec/journal-verify.schema.json` |
| `catalyst journal show` | `spec/history.schema.json`, `spec/journal.schema.json` |
| `catalyst journal redact` | `spec/journal-entry.schema.json` |
| `catalyst list` | `spec/list.schema.json` |
| `catalyst view` | `spec/view.schema.json` |
| `catalyst backlog` | `spec/backlog.schema.json` |
| `catalyst repair derived` | `spec/repair-derived.schema.json` |
| `catalyst graph` | `spec/graph.schema.json` |
| `catalyst new` | `spec/change.schema.json` |
| `catalyst rename` | `spec/change.schema.json` |
| `catalyst edit` | `spec/change.schema.json` |
| `catalyst approve` | `spec/approve.schema.json` |
| `catalyst approvals` | `spec/approvals.schema.json` |
| `catalyst landing init` | `spec/landing-init.schema.json` |
| `catalyst landing show` | `spec/landing-show.schema.json` |
| `catalyst restore` | `spec/change.schema.json` |
| `catalyst status set` | `spec/change.schema.json` |
| `catalyst link` | `spec/change.schema.json` |
| `catalyst user add` | `spec/user.schema.json` |
| `catalyst user remove` | `spec/user.schema.json` |
| `catalyst user modify` | `spec/user.schema.json` |
| `catalyst user assign-role` | `spec/user.schema.json` |
| `catalyst role add` | `spec/role.schema.json` |
| `catalyst role modify` | `spec/role.schema.json` |
| `catalyst freeze` | `spec/freeze.schema.json` |
| `catalyst unfreeze` | `spec/freeze.schema.json` |
| `catalyst definition list` | `spec/definitions.schema.json` |
| `catalyst definition migrate` | `spec/definition-migrate.schema.json` |
| `catalyst sync plan` | `spec/sync-plan.schema.json` |
| `catalyst sync apply` | `spec/sync-apply.schema.json` |
| `catalyst inbox` | `spec/inbox.schema.json` |
| `catalyst impact` | `spec/impact.schema.json` |
| `catalyst module list` | `spec/module-list.schema.json` |
| `catalyst module install` | `spec/module-install.schema.json` |
| `catalyst module available` | `spec/module-releases.schema.json` |
| `catalyst module upgrade` | `spec/sync-plan.schema.json`, `spec/sync-apply.schema.json` |
| `catalyst module verify` | `spec/module-list.schema.json` |
| `catalyst where` | `spec/where.schema.json` |
| `catalyst agent status` | `spec/agent-status.schema.json` |
| `catalyst agent run` | `spec/run-event.schema.json` |
| `catalyst agent runs` | `spec/runs.schema.json` |
| `catalyst runtime status` | `spec/runtime-status.schema.json` |
| `catalyst migrate` | `spec/migrate.schema.json` |
| `catalyst workspace status` | `spec/workspace-status.schema.json` |
| `catalyst analysis status` | `spec/analysis.schema.json` |
| `catalyst analysis list` | `spec/analyses.schema.json` |
| `catalyst try` | `spec/try.schema.json` |
| `catalyst propose` | `spec/propose.schema.json` |
| `catalyst open` | `spec/open.schema.json` |
| `catalyst share info` | `spec/share-info.schema.json` |
| `catalyst share status` | `spec/share-status.schema.json` |
| `catalyst share push` | `spec/share-push.schema.json` |
| `catalyst serve members` | `spec/members-check.schema.json` |
| `catalyst members` | `spec/members.schema.json` |
| `catalyst identity login` | `spec/identity-whoami.schema.json` |
| `catalyst identity whoami` | `spec/identity-whoami.schema.json` |
| `catalyst identity status` | `spec/identity-status.schema.json` |

<!-- end generated: cli-json -->

## Options reference

<!-- generated: cli-options (scripts/gen_docs.py; do not edit by hand) -->

Every command's arguments and options, generated from the CLI's own parser; `catalyst <command> --help` says the same. The sections above describe what each command does and why.

| Command | Argument | What it does |
|---|---|---|
| `catalyst validate` | `--strict` | treat warnings as errors |
|  | `--json` | machine-readable output |
| `catalyst init` | `--name` `NAME` | the project name (the pointer is <name>.catalyst) |
|  | `--module` `MODULE` | the active process module id (no default: without it, init lists the modules it finds) |
|  | `--user` `USER` | the installer's name, as catalyst-users knows them (default: git config user.name) |
|  | `--git-username` `GIT_USERNAME` | the installer's username (default: --user) |
|  | `--rule-doc` `FILE:PREFIX` | a rule document and its ID prefix, e.g. business-rules:br (repeatable) |
|  | `--test-locations` `TEST_LOCATIONS` | where the project's tests live (Rules-of-Rules §2) |
|  | `--at` `AT` | legacy: an agent-owned location reached through a .criterion symlink (default, ADR-010: $HOME/.catalyst/projects/<name>/criterion, nothing in the project) |
|  | `--no-runtime` | do not fill the criterion's .venv now (`catalyst runtime install` later) |
|  | `--agent` `AGENT` | the running agent's id, e.g. claude-code (recorded in catalyst.toml; `catalyst agent install <agent>` wires the agent, at user level) (default `unknown`) |
|  | `--kernel` `KERNEL` | framework/kernel of a catalyst checkout or release (default: this checkout's) |
|  | `--module-dir` `MODULE_DIR` | the module's directory (default: searched) |
|  | `--no-module` | install the kernel only; `catalyst module install` adds a module later |
|  | `--identity-issuer` `IDENTITY_ISSUER` | catalyst-users: the provider's issuer URL people sign through (design 29); log in first with `catalyst identity login --issuer <url>` |
|  | `--identity-client` `IDENTITY_CLIENT` | its public client with the device grant (default: catalyst-cli) |
|  | `--catalyst-client` `CATALYST_CLIENT` | the client whose roles are catalyst grants (default: catalyst) |
| `catalyst check` | `--strict` | treat warnings as errors |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst hook stop` | `--strict` | block on warnings too, not only on errors |
|  | `--format` `FORMAT` | how to block: exit 2 + stderr (Claude Code), decision JSON (Codex, Copilot), Gemini CLI's, Cursor's follow-up message (one of `exit2`, `json`, `gemini`, `cursor`; default `exit2`) |
| `catalyst hook commit-msg` | `<message_file>` | the file git passes the hook, holding the commit message |
|  | `--route` | from the repository top: hand the message to each deployment owning a staged file |
| `catalyst hook install` | — | — |
| `catalyst hook start` | `--format` `FORMAT` | plain text (Claude Code), additionalContext JSON (Codex, Copilot, Gemini), Cursor's (one of `text`, `json`, `cursor`; default `text`) |
|  | `--quiet` | record the session's baseline (from the hook input) and print nothing: for an agent whose session already carries the laws |
| `catalyst report` | `--since` `SINCE` | only history from this date/time on (ISO 8601) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst audit` | `--json` | machine-readable output (JSON on stdout) |
|  | `--html` `FILE` | write a self-contained page, printable to PDF |
| `catalyst badge` | `--metric` `METRIC` | what the badge shows: the deployment's check result, or how many live rules have work resting on them (one of `check`, `chain`; default `check`) |
|  | `--out` `FILE` | write the SVG there (default: stdout) |
| `catalyst unrecorded` | `<range>` | git revision range (default: every commit after the baseline) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst trace` | `<range>` | git revision range (default: HEAD~1..HEAD) |
|  | `--pattern-only` | no working copy (e.g. CI of a local-only deployment): accept any well-formed ID |
| `catalyst recompose` | `--base-kernel` `BASE_KERNEL` | framework/kernel the deployment was composed from (the old version) |
|  | `--base-module` `BASE_MODULE` | the module directory it was composed from |
|  | `--kernel` `KERNEL` | the new framework/kernel |
|  | `--module-dir` `MODULE_DIR` | the new module directory (default: the deployed one) |
|  | `--check` | change nothing; exit 1 if anything would change |
|  | `--force` | also merge documents listed in .frozen |
| `catalyst spec` | `<command>` | e.g. status or /check-rules (none: list commands) |
|  | `<part>` | one part of a command with parts, e.g. `create bug` |
|  | `--general` | the §4 rules that apply to every command |
|  | `--budget` `WORDS` | check every command's spec against a word budget (exit 1 if over) |
|  | `--json` | the commands, or one command's spec, as JSON |
| `catalyst id next` | `<prefix>` | entity type prefix, e.g. RECON or a module's type |
|  | `--count` `COUNT` | that many consecutive IDs, one per line (default `1`) |
|  | `--as` `AS_USER` | signer (name or git_username) |
| `catalyst id next-rule` | `<doc_prefix>` | the rule document's prefix, e.g. br |
|  | `<domain>` | a registered DOMAIN code |
|  | `--as` `AS_USER` | signer (name or git_username) |
| `catalyst journal append` | `--command` `CMD` | the catalyst command, e.g. /status |
|  | `--action` `ACTION` | create\|update\|close\|retire\|status-change\|sync |
|  | `--artifact` `ARTIFACT` | the artifact ID or a short description |
|  | `--target` `TARGET` | a rule/artifact ID this serves (repeatable) |
|  | `--intent` `INTENT` | the goal of the change (repeatable) |
|  | `--file` `FILE` | a touched file (repeatable) |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--allow-unchanged` | journal a file that has not changed since its last entry |
|  | `--tier` `TIER` | the change's ceremony tier, one the active module declares (default: chore, fix, feature; a chore needs no artifact) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst journal adopt` | `<revs>` … | a commit, several, or a range (A..B) |
|  | `--intent` `INTENT` | why the change was made (repeatable, required) |
|  | `--target` `TARGET` | a rule/artifact ID this serves (repeatable) |
|  | `--artifact` `ARTIFACT` | the artifact ID or a short description (default: commit <sha>) |
|  | `--tier` `TIER` | the change's ceremony tier, one the active module declares |
|  | `--as` `AS_USER` | actor (default: the commit's git author) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst journal verify` | `--strict` | treat warnings as errors |
|  | `--legacy` | also list warnings on pre-CLI entries |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst journal restore` | `<timestamp>` | ISO 8601 UTC, e.g. 2026-09-27T18:00:00Z |
|  | `<out>` | side directory, empty or absent (default: journal-restore-<timestamp> in TMPDIR) |
| `catalyst journal show` | `--since` `SINCE` | only entries from this date/time on (ISO 8601) |
|  | `--artifact` `ARTIFACT` | only entries for this artifact |
|  | `--actor` `ACTOR` | only entries by this actor (name or part of it) |
|  | `--rule` `RULE` | only entries targeting this rule or artifact ID |
|  | `--content` | with --artifact: the history of that entity, each change with its content before and after |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst journal redact` | `<blob>` … | a git blob the journal names (40 hex characters) |
|  | `--intent` `INTENT` | why (repeatable; required) |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--tier` `TIER` | the change's ceremony tier (default: the module's tier with no artifact) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst journal pin` | `--share` | also merge with and push the remote's pins (working copy and product repository) |
| `catalyst list` | `<type>` | an entity type (prefix, name or folder), rule, user, role, template, or all |
|  | `--filter` `KEY=VALUE` | keep items whose KEY matches VALUE (* and ? wildcards; repeatable) |
|  | `--type` `TEMPLATE_TYPE` | with `template`: one template family |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst view` | `<id>` | an entity or rule ID |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst backlog` | `--json` | machine-readable output (JSON on stdout) |
| `catalyst repair derived` | `--as` `AS_USER` | signer (name or git_username) |
|  | `--tier` `TIER` | the change's ceremony tier (default: the module's tier with no artifact) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst graph` | `--json` | machine-readable output (JSON on stdout) |
| `catalyst new` | `<type>` | an entity type (prefix, name or folder) |
|  | `--title` `TITLE` | the artifact's title; its file name is made from it |
|  | `--field` `NAME=VALUE` | a field value; references as comma-separated IDs (repeatable) |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--command` `CMD` | the slash command this runs for, journaled |
|  | `--tier` `TIER` | the change's ceremony tier, one the active module declares |
|  | `--json` | machine-readable output (JSON on stdout) |
|  | `--preview` | say what the change would do (its `try`); keep nothing |
|  | `--forewarned` | try it first, then make it anyway, recording in its journal entry what it adds to `check` |
| `catalyst rename` | `<id>` | an entity or rule ID |
|  | `--title` `TITLE` | the new title; the file is renamed to match |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--command` `CMD` | the slash command this runs for, journaled |
|  | `--tier` `TIER` | the change's ceremony tier, one the active module declares |
|  | `--json` | machine-readable output (JSON on stdout) |
|  | `--preview` | say what the change would do (its `try`); keep nothing |
|  | `--forewarned` | try it first, then make it anyway, recording in its journal entry what it adds to `check` |
| `catalyst edit` | `<id>` | an entity or rule ID |
|  | `--field` `FIELD` | NAME=VALUE: a plain field (repeatable; references: `link`) |
|  | `--section` `SECTION` | HEADING=TEXT: a section's new text (repeatable) |
|  | `--section-file` `SECTION_FILE` | HEADING=FILE: a section's new text from a file (repeatable) |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--command` `CMD` | the slash command this runs for, journaled |
|  | `--tier` `TIER` | the change's ceremony tier, one the active module declares |
|  | `--json` | machine-readable output (JSON on stdout) |
|  | `--preview` | say what the change would do (its `try`); keep nothing |
|  | `--forewarned` | try it first, then make it anyway, recording in its journal entry what it adds to `check` |
| `catalyst approve` | `<id>` | an entity or rule ID |
|  | `--gate` `GATE` | the gate's id in IAM/gates.json |
|  | `--as` `AS_USER` | who approves (name or git_username): never the version's author |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--tier` `TIER` | the change's ceremony tier, one the active module declares |
|  | `--json` | machine-readable output (JSON on stdout) |
|  | `--preview` | say what the change would do (its `try`); keep nothing |
|  | `--forewarned` | try it first, then make it anyway, recording in its journal entry what it adds to `check` |
| `catalyst approvals` | `<id>` | an entity or rule ID |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst landing init` | `--policy` `POLICY` | One of `standard`, `open`, `reviewed`, `host`; default `standard` |
|  | `--force` | replace an existing IAM/landing.json |
|  | `--as` `AS_USER` | signer (name or git_username): an admin |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst landing show` | `--json` | machine-readable output (JSON on stdout) |
| `catalyst restore` | `<id>` | an entity or rule ID |
|  | `--to` `TO` | a journal timestamp (ISO; the version after the last entry at or before it), or #N (after its Nth change) |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--command` `CMD` | the slash command this runs for, journaled |
|  | `--tier` `TIER` | the change's ceremony tier, one the active module declares |
|  | `--json` | machine-readable output (JSON on stdout) |
|  | `--preview` | say what the change would do (its `try`); keep nothing |
|  | `--forewarned` | try it first, then make it anyway, recording in its journal entry what it adds to `check` |
| `catalyst status set` | `<id>` | an entity or rule ID |
|  | `<status>` | the state to set, one the type declares |
|  | `--force` | write a status outside the type's statuses, or past a failing guard (journaled) |
|  | `--through` | reach a later status through the states between, each transition and guard checked; one journal entry |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--command` `CMD` | the slash command this runs for, journaled |
|  | `--tier` `TIER` | the change's ceremony tier, one the active module declares |
|  | `--json` | machine-readable output (JSON on stdout) |
|  | `--preview` | say what the change would do (its `try`); keep nothing |
|  | `--forewarned` | try it first, then make it anyway, recording in its journal entry what it adds to `check` |
| `catalyst link` | `<id>` | an entity or rule ID |
|  | `<field>` | the reference field to add to, e.g. Targets |
|  | `<ids>` … | the IDs it cites |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--command` `CMD` | the slash command this runs for, journaled |
|  | `--tier` `TIER` | the change's ceremony tier, one the active module declares |
|  | `--json` | machine-readable output (JSON on stdout) |
|  | `--preview` | say what the change would do (its `try`); keep nothing |
|  | `--forewarned` | try it first, then make it anyway, recording in its journal entry what it adds to `check` |
| `catalyst user add` | `<name>` | the user's name |
|  | `<role>` | the user's first role |
|  | `--git-username` `GIT_USERNAME` | default: the name |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst user remove` | `<name>` | the user's name |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst user modify` | `<name>` | the user's name |
|  | `<field>` | the field to change |
|  | `<value>` | its new value |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst user assign-role` | `<name>` | the user's name |
|  | `<role>` | the role to add |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst role add` | `<name>` | the role's name |
|  | `--action` `ACTION` | an action the role may take (repeatable) |
|  | `--reconciliation` `RECONCILIATION` | what the role may do with a reconciliation case: decide it, propose, or nothing (one of `full`, `propose`, `none`; default `propose`) |
|  | `--provider-role` `PROVIDER_ROLE` | no longer used: roles are catalyst-users' (design 29) |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst role modify` | `<name>` | the role's name |
|  | `--action` `ACTION` | an action the role may take (repeatable) |
|  | `--provider-role` `PROVIDER_ROLE` | no longer used: roles are catalyst-users' (design 29) |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst freeze` | `<item>` | an artifact ID, entity type, template name or working-copy path |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst unfreeze` | `<item>` | an artifact ID, entity type, template name or working-copy path |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst definition list` | `--json` | machine-readable output (JSON on stdout) |
| `catalyst definition migrate` | `<entity>` | the entity type's definitions folder name, e.g. role |
|  | `<version>` | the definition version to migrate the type's artifacts to |
|  | `--kernel` `KERNEL` | framework/kernel of the catalyst release (default: this checkout's) |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst sync plan` | `--kernel` `KERNEL` | the target kernel: framework/kernel of a catalyst checkout, or a kernel-vX.Y.Z.zip |
|  | `--module` `MODULE` | the target module: its directory, release zip, or git URL[@ref] |
|  | `--base-kernel` `BASE_KERNEL` | the kernel the deployment was composed from (default: found next to the zip, or the git tag) |
|  | `--cli` `CLI` | the catalyst.pyz to vendor (default: the release's, or built) |
|  | `--commands-dir` `COMMANDS_DIR` | where an older catalyst wrote the project's command files, to retire them (default: .claude/commands) |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst sync apply` | `--kernel` `KERNEL` | the target kernel: framework/kernel of a catalyst checkout, or a kernel-vX.Y.Z.zip |
|  | `--module` `MODULE` | the target module: its directory, release zip, or git URL[@ref] |
|  | `--base-kernel` `BASE_KERNEL` | the kernel the deployment was composed from (default: found next to the zip, or the git tag) |
|  | `--cli` `CLI` | the catalyst.pyz to vendor (default: the release's, or built) |
|  | `--commands-dir` `COMMANDS_DIR` | where an older catalyst wrote the project's command files, to retire them (default: .claude/commands) |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst inbox` | `--json` | machine-readable output (JSON on stdout) |
| `catalyst impact` | `<id>` | an artifact, a rule or a domain |
|  | `--up` | only what it rests on |
|  | `--down` | only what rests on it |
|  | `--depth` `DEPTH` | stop after this many links (default: all) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst module list` | `--json` | machine-readable output (JSON on stdout) |
| `catalyst module install` | `<source>` | the module: its directory, release zip, or git URL[@ref] |
|  | `--kernel` `KERNEL` | framework/kernel of the release this deployment is at |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst module available` | `<id>` | the installed module |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst module upgrade` | `<id>` | the installed module |
|  | `<source>` | directory, release zip or git URL[@ref] (default: the recorded URL) |
|  | `--kernel` `KERNEL` | framework/kernel of the release this deployment is at |
|  | `--base-kernel` `BASE_KERNEL` | the kernel the deployment was composed from (default: --kernel) |
|  | `--plan` | list what would change, write nothing |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst module verify` | `<id>` | one module (default: all) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst where` | `--json` | machine-readable output (JSON on stdout) |
| `catalyst agent install` | `<agent>` | the agent to wire, at user level (one of `claude-code`, `copilot`, `vscode`, `cursor`, `codex`, `gemini`) |
| `catalyst agent uninstall` | `<agent>` | the agent to unwire (one of `claude-code`, `copilot`, `vscode`, `cursor`, `codex`, `gemini`) |
| `catalyst agent status` | `--json` | machine-readable output (JSON on stdout) |
| `catalyst agent run` | `<command>` | a command of CODE-OF-CONDUCT.md §4, e.g. check-rules |
|  | `<arguments>` … | its arguments, as typed after the slash command |
|  | `--agent` `AGENT` | this run's agent (default: the one `catalyst open --agent` records) |
|  | `--json` | the events as JSON lines (spec/run-event.schema.json) |
| `catalyst agent runs` | `--limit` `LIMIT` | only the last N |
|  | `--json` | the log's lines (spec/runs.schema.json) |
| `catalyst mcp` | — | — |
| `catalyst task` | `<name>` | the task, i.e. the command name (none: list them) |
|  | `<task_args>` … | -- <arguments> for the command |
| `catalyst runtime install` | — | — |
| `catalyst runtime status` | `--json` | machine-readable output (JSON on stdout) |
| `catalyst move` | `--to-home` | symlink, in-project directory or submodule -> $CATALYST_HOME/projects/<name>/criterion |
|  | `--name` `NAME` | rename a home-store project |
|  | `--no-runtime` | do not fill the criterion's .venv now |
|  | `--as` `AS_USER` | actor recorded in the journal |
| `catalyst migrate` | `--kernel` `KERNEL` | framework/kernel of a catalyst checkout, or a kernel release (dir or zip) |
|  | `--apply` | move a legacy layout and add the templates, journaled |
|  | `--template` `TYPE` | with --apply: also add this module type's new template (its prefix or template name, or `all`) (repeatable) |
|  | `--since` `VERSION` | list the judgment steps of every migration after this kernel |
|  | `--no-runtime` | when moving: do not fill the criterion's .venv now |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst workspace init` | `<file>` | the <name>.code-workspace file |
|  | `--user` `USER` | the installer's name, as catalyst-users knows them (default: git config user.name) |
|  | `--git-username` `GIT_USERNAME` | the installer's username (default: their name) |
|  | `--identity-issuer` `IDENTITY_ISSUER` | catalyst-users: the provider's issuer URL (design 29) |
|  | `--identity-client` `IDENTITY_CLIENT` | its public client (default: catalyst-cli) |
|  | `--catalyst-client` `CATALYST_CLIENT` | the client whose roles are catalyst grants (default: catalyst) |
|  | `--kernel` `KERNEL` | framework/kernel (default: this checkout's) |
| `catalyst workspace status` | `<file>` | the <name>.code-workspace file |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst index regen` | `--check` | change nothing; exit 1 if any index is stale |
|  | `--diff` | with --check, show what would change |
| `catalyst analysis start` | `<scope>` … | paths to analyse (default: the whole project) |
|  | `--mode` `MODE` | bootstrap: no rules yet; incremental: find what the rules miss (default) (one of `bootstrap`, `incremental`; default `incremental`) |
|  | `--name` `NAME` | a short name for the record |
|  | `--passes` `PASSES` | independent passes: 2, four-eyes (default), or 1; the deployment's default is catalyst.toml's analysis_passes (one of `1`, `2`) |
|  | `--as` `AS_USER` | signer (name or git_username) |
| `catalyst analysis record` | `<id>` | an entity or rule ID |
|  | `--pass` `WHICH` | the pass it records, A or B (one of `A`, `B`, `a`, `b`) |
|  | `<file>` | the pass's findings file |
|  | `--replace` | replace a pass recorded by mistake |
|  | `--as` `AS_USER` | signer (name or git_username) |
| `catalyst analysis diff` | `<id>` | an entity or rule ID |
|  | `--as` `AS_USER` | signer (name or git_username) |
| `catalyst analysis reconcile` | `<id>` | an entity or rule ID |
|  | `<file>` | the reconciler's list of findings, every one accounted for |
|  | `--as` `AS_USER` | signer (name or git_username) |
| `catalyst analysis decide` | `<id>` | an entity or rule ID |
|  | `<finding>` | the reconciled finding's ID, e.g. F1 |
|  | `<verdict>` | accept the finding, or reject it (one of `accept`, `reject`) |
|  | `--artifact` `ARTIFACT` | the domain code, rule ID or artifact ID an accepted finding became |
|  | `--reason` `REASON` | why |
|  | `--as` `AS_USER` | signer (name or git_username) |
| `catalyst analysis close` | `<id>` | an entity or rule ID |
|  | `--as` `AS_USER` | signer (name or git_username) |
| `catalyst analysis abandon` | `<id>` | an entity or rule ID |
|  | `--reason` `REASON` | why the analysis is abandoned |
|  | `--as` `AS_USER` | signer (name or git_username) |
| `catalyst analysis status` | `<id>` | an entity or rule ID |
|  | `--json` | the full report: passes, diff, findings and decisions |
| `catalyst analysis list` | `--json` | machine-readable output (JSON on stdout) |
| `catalyst reconcile` | `<case>` | the RECON- case ID |
|  | `<verb>` | what to do with the case (one of `accept`, `accept-with-edits`, `reject`, `propose`, `close`) |
|  | `--text` `TEXT` | propose: the proposed resolution (a new Revisions row) |
|  | `--from` `FROM_FILE` | a proposal: the content it now proposes (propose) or accepts (accept-with-edits); - reads stdin |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--preview` | say what the change would do (its `try`); keep nothing |
|  | `--forewarned` | try it first, then make it anyway, recording in its journal entry what it adds to `check` |
| `catalyst try` | `--json` | machine-readable output (JSON on stdout) |
|  | `--keep` | keep the scratch copy, to look inside |
|  | `--proposal` `PROPOSAL` | try accepting this proposal (`reconcile <case> accept`) |
|  | `--as` `AS_USER` | with --proposal: who accepts it (name or git_username) |
|  | `<change>` … | the verb and its arguments, e.g. status set REQ-000004 Done |
| `catalyst propose` | `<id>` | the entity, or a rule (its document is what is proposed) |
|  | `--from` `FROM_FILE` | the proposed content of its file; - reads stdin |
|  | `--title` `TITLE` | the case's title (default: Proposed change to <ID>) |
|  | `--as` `AS_USER` | who proposes (name or git_username) |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
|  | `--tier` `TIER` | the change's ceremony tier, one the active module declares |
|  | `--json` | machine-readable output (JSON on stdout) |
|  | `--preview` | say what the change would do (its `try`); keep nothing |
|  | `--forewarned` | try it first, then make it anyway, recording in its journal entry what it adds to `check` |
| `catalyst why` | `<item>` | L3, INV-17, rr-META-012, a rule or artifact ID |
| `catalyst open` | `--fetch` | fetch the shared copy first |
|  | `--agent` `AGENT` | record the agent this user works with (catalyst task dispatches to it) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst share info` | `--json` | machine-readable output (JSON on stdout) |
| `catalyst share status` | `--fetch` | fetch the shared copy first |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst share pull` | — | — |
| `catalyst share push` | `-m`, `--message` `MESSAGE` | what the change is (commit message, pull request title) |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--no-pr` | git: push the branch without opening a pull request |
|  | `--yes` | the user agreed to publish what the preview shows (INV-4) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst share create` | `<url>` | the criterion repository (empty, or holding this history), or a server's URL |
|  | `--driver` `DRIVER` | git (default) or a catalyst serve server (one of `git`, `serve`; default `git`) |
|  | `--as` `AS_USER` | serve: the signer of the journal entry (name or git_username) |
|  | `--branch` `BRANCH` | the shared branch (default: criterion) (default `criterion`) |
|  | `--protect` | also require pull requests and the check (GitHub) |
|  | `--yes` | the user agreed to publish (INV-4) |
| `catalyst share join` | `<url>` | the criterion repository, when catalyst.toml names none |
| `catalyst share login` | `<url>` | the server's URL, as catalyst.toml's share_url names it |
|  | `--token` `TOKEN` | the token (default: read one line on stdin) |
| `catalyst serve token` | `<action>` | issue a token, list them, or revoke one (one of `issue`, `list`, `revoke`) |
|  | `<who>` | issue: the user's userid; revoke: the token's number |
| `catalyst serve key` | `<action>` | One of `init`, `escrow`, `recover` |
|  | `--key-command` `KEY_COMMAND` | init: a command printing the master key (base64), a key-management service's; default: a new key in this host's keychain |
|  | `--holder` `HOLDER` | escrow: an admin who holds a share (repeatable) |
|  | `--threshold` `THRESHOLD` | escrow: how many shares recover the key |
|  | `--out` `OUT` | escrow: the directory each holder's share file is written to |
|  | `--share` `SHARE` | recover: a share file (repeatable) |
|  | `--reason` `REASON` | recover: why the break-glass copy is used (default ``) |
| `catalyst serve members` | `<action>` | One of `open`, `check`, `fingerprint` |
|  | `--reason` `REASON` | open: why (default ``) |
|  | `--yes` | open: the Admin agreed to the members it adopts (INV-4) |
|  | `--json` | machine-readable output |
| `catalyst members` | `<action>` | One of `list`, `add`, `remove`, `adopt` |
|  | `<member>` | add, remove, adopt: the person's username at the identity provider |
|  | `--reason` `REASON` | why (add, remove, adopt) (default ``) |
|  | `--json` | machine-readable output |
| `catalyst criterion status` | `--fetch` | fetch the shared branch first |
| `catalyst criterion create` | `<url>` | the criterion repository (empty, or already holding this history); without it the working copy is versioned strictly locally, and push/sync/join ask for it |
|  | `--branch` `BRANCH` | the shared branch (default: criterion) (default `criterion`) |
|  | `--yes` | with a URL: the user agreed to publish (INV-4) |
| `catalyst criterion join` | `--url` `URL` | the criterion repository, when the product has no .criterion submodule yet |
| `catalyst criterion push` | `-m`, `--message` `MESSAGE` | commit message / pull request title |
|  | `--as` `AS_USER` | signer (name or git_username) |
|  | `--no-pr` | push the branch without opening a pull request |
|  | `--url` `URL` | the criterion repository, when the deployment is still local only |
|  | `--yes` | the user agreed to publish what the preview shows (INV-4) |
| `catalyst criterion sync` | `--url` `URL` | the criterion repository, when the deployment is still local only |
|  | `--yes` | with --url: the user agreed to publish (INV-4) |
| `catalyst criterion integrity` | `--head` `HEAD` | the merge commit to check (default `HEAD`) |
|  | `--parent` `PARENT` | compare against this revision (repeatable; default: the head's own parents) |
| `catalyst criterion protect` | `--yes` | apply it (without: show what would be set) |
| `catalyst identity configure` | `--provider` `PROVIDER` | the catalyst-users backend (one of `keycloak`, `static`; default `keycloak`) |
|  | `--issuer` `ISSUER` | the provider's issuer URL, e.g. `https://id.example.com/realms/catalyst` |
|  | `--client` `CLIENT` | the public client with the device grant (default: catalyst-cli) |
|  | `--catalyst-client` `CATALYST_CLIENT` | the client whose roles are catalyst grants (default: catalyst) |
|  | `--link` `LINK` | first keep this retired user's userid as yours (`identity link`), then sign |
|  | `--as` `AS_USER` | signer, under the provider in force before the change |
|  | `--intent` `INTENT` | why (repeatable; journaled) |
| `catalyst identity login` | `--issuer` `ISSUER` | a provider's issuer URL, outside any deployment (e.g. before `catalyst init`) |
|  | `--client` `CLIENT` | with --issuer: its public client (default: catalyst-cli) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst identity logout` | `--issuer` `ISSUER` | a provider's issuer URL, outside any deployment (e.g. before `catalyst init`) |
|  | `--client` `CLIENT` | with --issuer: its public client (default: catalyst-cli) |
| `catalyst identity whoami` | `--issuer` `ISSUER` | a provider's issuer URL, outside any deployment (e.g. before `catalyst init`) |
|  | `--client` `CLIENT` | with --issuer: its public client (default: catalyst-cli) |
|  | `--json` | machine-readable output (JSON on stdout) |
|  | `--as` `AS_USER` | the tests' static backend: which declared person |
| `catalyst identity status` | `--issuer` `ISSUER` | a provider's issuer URL, outside any deployment (e.g. before `catalyst init`) |
|  | `--client` `CLIENT` | with --issuer: its public client (default: catalyst-cli) |
|  | `--json` | machine-readable output (JSON on stdout) |
| `catalyst identity link` | `<user>` | the retired user (name, username or userid), who must be you |
|  | `--as` `AS_USER` | the tests' static backend: which declared person |
| `catalyst userid gen` | — | — |

<!-- end generated: cli-options -->

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
