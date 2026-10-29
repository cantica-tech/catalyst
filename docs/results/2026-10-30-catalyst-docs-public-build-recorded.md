# catalyst-docs: the public build recorded, and the fixtures confirmed gone

2026-10-30. The owner decided two catalyst-docs points:

- test fixtures leave the public reference;
- the public build gets a build record (`KBUILD-`).

## Done

1. **Test fixtures.** Of the seven public sources, only catalyst-ui commits fixture markdown. A root
   `.catalystignore` there names `packages/catalyst-core/src/test/fixtures` (done 2026-10-28, catalyst-ui PR #186).
2. **The public build recorded**, with catalyst-kb-engine 0.16.0 (`REQ-000017-7TE7wuaB`, rule
   `eng-PUBLISH-000003-7TE7wuaB`).
   - `record-site <site>` reads the manifests a site serves (`manifest.json`, `vectors/manifest.json`), on the
     curator's machine: Actions cannot reach the private criterion.
   - It records each new manifest as a `KBUILD-`, writing its Verification before setting it `Published`.
   - A manifest already recorded is skipped, identified by its SHA-256. A new one supersedes the build the site
     served before at the same place.
   - A manifest that is not `Public` in both classification and ceiling is refused.
   - catalyst-docs' README gives the command to run after a deployment.
3. **catalyst-docs' builds**: `KBUILD-000007-erFhHt6m` (the pages) and `KBUILD-000008-erFhHt6m` (the vectors) are
   `Published`. They supersede `-000005` and `-000006`, recorded from the previous deployment. The local public
   vectors, `-000004`, never published, are `Superseded`.

## Checks

- **The live manifests hold no fixture file**: none of the 294 files the pages' manifest lists, nor of the 296 the
  vectors' lists. The site holds 292 documents.
- **The engine**: ruff, pyright and 138 tests pass, 7 of them for `record-site`; CI passed on 3.11 and 3.13.
- **Live, three runs**:
  - the first recorded `-000005` and `-000006`;
  - the second recorded nothing;
  - after the README's deployment, the released 0.16.0 recorded `-000007` and `-000008` and superseded the first
    two.
- **catalyst check**: passes in the engine's and catalyst-docs' criteria.

## Problems

- **The first live run titled the records with the knowledge base's ID and left Related as the template's text.**
  Both are fixed in 0.16.0. The two first records keep their titles, since file names are permanent; their Related
  sections were written by hand and journaled.

## What's left

- **`record-site` is run by hand after a deployment.** A scheduled local job could run it daily after the Pages
  run.
- **The search's 7 misses** in hybrid mode (0.865 at k 10): mostly vocabulary.
