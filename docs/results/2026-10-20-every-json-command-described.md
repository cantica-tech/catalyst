# Results — 2026-10-20: every `--json` command described

R4.4 phase 2 left 20 `--json` commands on a ratchet: they had no schema, and the list could only shrink. Each of them
now has one, checked against the command's real output. Kernel
[0.101.0](https://github.com/cantica-tech/catalyst/releases/tag/0.101.0) ships them, with one fix found on the way. It
is published in the distribution repository, and the desktop app ships it from UI 0.56.3.

| Before | After |
|---|---|
| 36 of 56 `--json` commands described | all 56 |
| a ratchet listing 20 gaps | an empty list, and a test that keeps it empty |

## The schemas

Commands that print the same shape share a schema, so 16 files in `spec/` cover the 20 commands:

| Schema | Commands |
|---|---|
| `journal-entry` | `journal append`, `journal adopt`, `journal redact` |
| `sync-plan` | `sync plan`, `module upgrade --plan` |
| `sync-apply` | `sync apply`, `module upgrade` |
| `module-list` | `module list`, `module verify` |
| one each | `approve`, `repair derived`, `unrecorded`, `module install`, `where`, `agent status`, `runtime status`, `workspace status`, `propose`, `open`, `share info`, `share push` |

- **How they were written:** each schema was written from the command's code, then checked against the output the
  command printed in a scratch deployment. The deployment had a gate to approve, a proposal, a sync, a redaction and an
  adopted commit.
- **How they are held:** each command's own test now checks its real `--json` output against its schema; 15 test
  files gained a check. CLI.md's "Machine-readable output" table names a schema for every command, and `spec/README.md`
  says it covers every command, not only the read verbs.
- **The ratchet:** `UNDESCRIBED` in `scripts/gen_docs.py` is empty, and a test holds it so. A new `--json` command
  cannot ship without its schema.

## A fix found on the way (BUG-000024)

`catalyst share push --yes --json` printed a plain sentence when there was nothing to publish, so a client parsing it
failed on the simplest case. It now prints the push result with `commits` 0. This release's own criterion push was
the first to use it.

## Checks

745 tests pass (741 before). ruff, pyright (0 errors), kernel purity, frozen surface and the generated documents pass.
`catalyst check` on catalyst's own deployment passes. The release's pull requests merged only after every check passed.

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

**Work Claude can do without you:** the schemas describe the CLI's output; a client still writes its own types for
it. Generating the UI's types from `spec/` would make the schemas the single source there too. That belongs to the
UI's roadmap and is not yet an item.

**Blocked on something outside this repository:** module signatures (R4.9 N4) and signed releases (R7) wait on the
signing credentials and the release feed.
