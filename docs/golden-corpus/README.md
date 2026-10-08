# Golden corpus (roadmap R1.4)

Read-only snapshots of real deployments, for R3's migration tests (old layout →
locator) and R5's UI parity tests. Each corpus is a deployment's `*.catalyst`
pointer plus its `.criterion` working copy, packed by
`scripts/capture_golden_corpus.py`.

**Corpora are private and local only.** They hold governance data (users,
journal, rules), so `tests/fixtures/*-golden-corpus.*` is gitignored. The
working copy's own `.git` (its history), `.ledger/` and `.journal-restore/`
are never captured.

## Capture

From the catalyst repository root, one command per deployment:

```
python3 scripts/capture_golden_corpus.py --project <project root> --name <name>
```

| Name | Deployment | Working copy |
|---|---|---|
| `catalyst` | this repository (dogfood) | symlink to agent-owned space |
| `ui` | the UI repository | git submodule |
| `example` | the published example's `snapshot/` | plain directory, no history |

It writes `tests/fixtures/<name>-golden-corpus.tar.gz` (deterministic: same
working copy, same bytes) and `<name>-golden-corpus.json`:

| Field | Meaning |
|---|---|
| `project`, `module`, `format` | from the pointer |
| `kernel_version` | the working copy's `version.txt` |
| `working_copy_head` | the working copy's own git HEAD; `null` when it has no repository of its own |
| `files` | files in the archive |
| `journal_entries`, `users`, `roles` | counted from the journal and `IAM/` |
| `markdown_per_folder` | `.md` files per top-level working-copy folder |

## Tests

`tests/test_golden_corpus.py` checks the capture on a synthetic deployment
(always runs, in CI too), and checks every corpus found in `tests/fixtures/`
(skipped when none is captured): no private history, the core files present,
the summary matching the archive.
