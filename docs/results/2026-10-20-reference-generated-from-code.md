# Results — 2026-10-20: the kernel's reference generated from the code (R4.4 done)

The owner decided (D7) that the kernel's reference documents are generated from the code. All five phases are built.
Kernels 0.97.0 to 0.100.0 are released and published, with 0.100.1, a fix found on the way. Before
that, the owner retired R4.3's 15 KB target (D6), and every release now also goes to the distribution repository
without asking.

| Release | What's in it |
|---|---|
| Kernel [0.97.0](https://github.com/cantica-tech/catalyst/releases/tag/0.97.0) | Every command's arguments with their help; the prose checked against the CLI |
| Kernel [0.98.0](https://github.com/cantica-tech/catalyst/releases/tag/0.98.0) | Each `--json` command's schema; five more schemas; a ratchet on the rest |
| Kernel [0.99.0](https://github.com/cantica-tech/catalyst/releases/tag/0.99.0) | `catalyst.toml`'s and `module.yaml`'s keys from the code and the schemas |
| Kernel [0.100.0](https://github.com/cantica-tech/catalyst/releases/tag/0.100.0) | The migrations from their index; the invariants checked against the CLI |
| Kernel [0.100.1](https://github.com/cantica-tech/catalyst/releases/tag/0.100.1) | `catalyst serve` reads a refused request's body first (BUG-000023) |
| The UI 0.56.1 and 0.56.2 (its own repository) | The desktop app ships kernel 0.96.0, then 0.100.1 |

## What "generated from the code" means here

A reference states facts the code holds: the arguments a command takes, the shape of what it prints, the keys a file
may carry, the migrations a release ships. Those are now generated between markers, and `gen_docs.py --check` fails
CI when a document disagrees with the code. What a command is for and why a rule exists is explanation; it stays
prose, and is checked where it names something the code defines. Plan: `docs/plans/r4-4-generated-reference.md`.

## 1. Commands and their options (0.97.0)

- **The reference:** CLI.md gains an "Options reference" generated from the CLI's parser, with every command's
  arguments, their help, their choices and their defaults.
- **Help on every argument:** 105 of the 338 had none; each has its help now, so `catalyst <command> --help` says it
  too.
- **The prose is checked:** it may name only options the CLI has (other tools' flags aside). It named none that the
  CLI lacked.

## 2. What each command prints (0.98.0)

- **The table:** CLI.md gains a "Machine-readable output" table: each `--json` command and the schema describing it.
- **Five new schemas:** for the writing, user and role verbs, `freeze`/`unfreeze` and `definition migrate`. 36 of the
  56 `--json` commands are now described, against 22 before.
- **A ratchet:** a new `--json` command cannot ship without a schema, and the 20 still without one may only shrink.

## 3. The files' keys (0.99.0)

- **`catalyst.toml`:**
  - its keys come from one registry in the code, which adds the two FORMAT.md lacked, `workspace` and `role_check`;
  - the check fails when the code reads a key the registry does not list.
- **`module.yaml`:**
  - its schema predated module format 3, so every real module failed it, and nothing used it. It now describes format
    3, and the tests hold the sample module and both production modules to it.
  - MODULE-SPECIFICATION.md's four tables are generated from the schemas, so they say what is validated.
- **The test suite's validator:** it stopped checking a schema once an `anyOf` matched. It now checks `anyOf` with the
  other keywords, as JSON Schema does.

## 4. Migrations and invariants (0.100.0)

- **SYNCHRONIZE.md:** its 36 hand-written migration entries stopped at 0.51.x and missed six later migrations. They
  are replaced by a table generated from the migrations index.
- **INVARIANTS.md:** its "enforced by" stays prose, because no code structure records which code enforces which
  invariant, and generating one would only move the table into the code. It is checked instead: every command or
  script it names must exist, and every invariant the code cites must be defined.

## Also done

- Catalyst's own deployment is upgraded to the process module 3.4.1, so its INV-16 says roles are enforced.
- UI 0.56.1 is released, and its `.vsix` is published under the owner's new standing yes; the desktop app ships kernel
  0.96.0.

## 5. A flaky Windows test, fixed (0.100.1)

0.100.0's release failed once on Windows. `catalyst serve` refused a write before reading the request's body; Windows
treated the closed connection as an abort, so the client saw `ConnectionAbortedError` instead of the refusal. The same
test passed in the other run of the same commit. The server now reads a refused request's body first (BUG-000023),
and 0.100.1's Windows runs passed.

## Problems along the way

- **A wrong record:** a DEPLOYMENT.md line named module 3.4.1 before the deployment had it; the line was corrected,
  and the module upgraded.
- **The 0.98.0 sync:** it failed at first because the 0.97.0 tag was not fetched locally. The share then refused to
  publish (`check` saw the version drift), so nothing went out wrong. Tags are now fetched before each sync.
- **A network error:** one interrupted the 0.99.0 chain twice, once before the release and once before the
  distribution push. Both steps were resumed, and the chain now pushes the distribution repository explicitly.
- **A merge without a gate:** one background job would have merged without checking that every check passed. It was
  stopped before it merged anything. Every merge now goes through a script that refuses unless every check passed.
- **My own thin intent:** the thin-intent warning from 0.91.0 caught one of mine ("R4.4 phase 1").

All 741 tests pass.

## What's left

**Your decisions:**

- **The brand:** the colour and type system (item 5), the mark (item 6: a designer, or Claude's drafts), the tagline
  (item 7), and "criterion" or "the Record" (item 12; the recommendation is no).
- **R3.4:** drop the optional `catalyst migrate`, or build it.
- **Declaring format 1.0:** at the 1.0 release.

**Your time:**

- The beta trial (RM-026, RM-028, RM-029).
- Trying the icons, the status line, the Team and Share views, the desktop installers, and Copilot and Gemini CLI
  through `catalyst agent run`.

**Waiting on you:** the Marketplace token, the signing credentials, the update feed, trademark counsel, and a public
address for the Linux package.

**Work Claude can do without you:** schemas for the 20 `--json` commands still undescribed. The ratchet allows it in
any order.

**Blocked on something outside this repository:** module signatures (R4.9 N4) and signed releases (R7) wait on the
signing credentials and the release feed.
