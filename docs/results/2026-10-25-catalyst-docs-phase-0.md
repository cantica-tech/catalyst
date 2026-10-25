# Results — 2026-10-25: KBM 0.6.0 (a source's kind and visibility), catalyst-docs phase 0

| What                                                                                                         | Where                                                                    |
| ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| [knowledge-base 0.6.0](https://github.com/cantica-tech/catalyst-knowledge-base/releases/tag/0.6.0)           | REQ-000002-I3JORbi9, `kbm-MODEL-000002`; its criterion (PR 5); distribution repo |
| [`cantica-tech/catalyst-docs`](https://github.com/cantica-tech/catalyst-docs) (public), created              | PR 1: `catalyst.toml`, `KB.md`                                           |
| `cantica-tech/catalyst-docs-criterion` (private), created and shared                                         | PR 1: the `DOCS` domain, `kn-DOCS-000001`, `KB-000002`, 14 sources       |

1. **KBM 0.6.0.** `KSOURCE` gains two optional fields. `Kind` is `Repository`, `Folder`, `Site` or `Criterion` (a
   catalyst project's criterion, read only through catalyst's CLI). `Visibility` is `Public` or `Private`. Every
   document read from a private source is at least `Internal` (`rr-KB-002`), and a build refuses to run when the record
   and the host disagree. `/kb-setup`, `/create knowledge-source` and `/kb-import` set, check and apply them; migration
   `0.107.0/source-kind-and-visibility`. The rule is 🟡 specified: the build's visibility check is the engine's (phase 1).
   The owner's embedding-model decision (`nomic-embed-text`, local) shipped with it, in `docs/engine-and-onboarding.md`.
2. **Phase 0: catalyst-docs.** The project runs KBM alone. Its knowledge base `KB-000002-erFhHt6m` "catalyst" is
   `Active`, serving `kn-DOCS-000001-erFhHt6m`, with the owner's onboarding choices:
   - classification `Public`, default `Internal`, so only what a public source brings is public;
   - embedding `Local only`, sources checked every 7 days, `Reflective`, `Documents`, `Dynamic`, target
     `Vector database` (the public build records `Folders`).

   It has 14 sources, each visibility checked against GitHub: the 7 public repositories (`Public`, both builds), the
   private knowledge-base repository and the fleet's 6 criteria (`Private`, the realm build only).
3. **The evaluation set** (the realm search's questions) goes in the catalyst-docs criterion (owner, 2026-10-25).
4. Checks:
   - a throwaway deployment seeded with KBM 0.6.0, with a `Criterion` source: `catalyst check` passed, and a bad `Kind`
     was refused;
   - `catalyst check` passes in KBM's criterion and in catalyst-docs' (0 errors, 0 warnings), and both criterion PRs'
     CI passed;
   - `catalyst unrecorded` reports 0 in both projects, and markdownlint is clean on the new files.

## Problems

- **The knowledge base is `KB-000002`, not `KB-000001`.** A journal entry named `KB-000001` before it existed, and the
  allocator treats every ID the journal mentions as used, so that no number is ever reused. IDs are permanent (L7), so
  number 1 stays unused. Lesson: never cite an ID in an intent before it is allocated.
- **The distribution publish re-packaged kernel 0.114.0.** Its `catalyst.pyz` differs from the one already published
  only by its build ID (the catalyst commit it was packaged from). The contents are identical.
- `GUIDE.md` in KBM has 3 markdownlint `MD040` findings. They predate this work, and KBM has no CI to catch them.

## What's left

- **Phase 1** (catalyst-kb-engine): the `Criterion` reader and the visibility floors, which make `kbm-MODEL-000002` ✅.
- **Phases 2 and 3**: the realm build and its search, with the evaluation set; then incremental builds.
- **Phases 4 to 6**: the guide (its outline is the owner's to approve), the public site on Pages, and the search behind
  catalyst-users.
- **catalyst-users has no group for catalyst-docs** (`/criteria/catalyst-docs/admins`). The owner signs as a realm
  Admin; per-criterion membership waits on designs 30 and 32.
