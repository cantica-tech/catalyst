# Results: `view` shows table rows (kernel 0.116.1), 2026-10-26

The catalyst-docs lead, reading the fleet's criteria for its knowledge base, reported that `catalyst list all --json`
named items kept as table rows (roadmap rows: 34 in catalyst's criterion, 25 in catalyst-ui's), but
`catalyst view` refused each one as "no artifact or rule". Fixed as BUG-000037-yCNjAMXO, with a second fix from the
same report (BUG-000038-yCNjAMXO).

## What shipped

- **`catalyst view <row ID>`** shows the row:
  - its table's file and its line;
  - the row as written (`text`);
  - its cells by column (`fields`);
  - its title (the Title, Name, Feature or Item column) and its status;
  - its journal;
  - `"row": true`, the same mark `graph` uses.

  A short ID (`RM-000001`) finds the row as it finds an artifact.
- **`catalyst list`** gives each row its file and line.
- **The schemas:** `spec/view.schema.json` gains a `tableRow`, and `spec/list.schema.json` gains `file` and `line`.
  Both changes only add fields, so existing readers keep working.
- **Publishing only a release** (BUG-000038, also reported by the catalyst-docs lead): `package_release.py
  --publish-dir` (`task release:publish`) refuses a kernel whose version has no release tag, or a checkout not at
  it, unless `--unreleased` says so. A development checkout ahead of its last tag can no longer publish an unreleased
  kernel.

## Tested

- A new test lists and views a table row by its full and short ID. `tests/test_spec.py` validates `view <row>`
  against the schema.
- The whole suite: 876 passed.
- `tests/test_package_release.py`: the publish guard refuses without a tag and past it, and allows with
  `--unreleased`.
- ruff, pyright and the standards lint pass on a clean copy.
- In catalyst's own criterion, `view RM-000001` shows the row and its three journal entries, and all 34 rows carry
  their file and line.

## What's left

- **Links from rows:** a row's links are not read. A roadmap row's `Linked` column is shown among its cells, but not
  as `links`.
- **Writing rows:** `edit` and `history` still know only artifacts with a file of their own.
- **The engine:** catalyst-kb-engine still skips table rows. It can read them once a deployment syncs to 0.116.1.
