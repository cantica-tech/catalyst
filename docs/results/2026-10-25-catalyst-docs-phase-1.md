# Results — 2026-10-25: catalyst-docs phase 1, reading sources (catalyst-kb-engine 0.4.0)

| What                                                                                                  | Where                                       |
| ----------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| [catalyst-kb-engine 0.4.0](https://github.com/cantica-tech/catalyst-kb-engine/releases/tag/0.4.0)     | REQ-000004-7TE7wuaB; PR 1                   |
| `eng-SOURCE-000001`, `eng-SOURCE-000002` ✅; KBM's `kbm-MODEL-000002` ✅                               | the engine's and KBM's criteria             |

1. **`read-sources <KB-id> <out>`** stages a knowledge base's live sources in the `docs/` layout the builds already
   read, so a build of the staging directory is a build of the sources.
2. **A criterion is read only through catalyst's CLI** (`list all --json`, then `view --json`, in parallel), in its
   project, after `catalyst where` confirms the name. Each entity and rule becomes one document whose front matter
   cites its ID, criterion, type and status. The body holds its fields, sections, links and its own history (who,
   when, which command, why), never another entity's content. The composed meta-rules are left out, since they are
   public in the kernel's and modules' repositories.
3. **Visibility, before anything is read.** Each source's `Visibility` is checked against GitHub (for a criterion, its
   criterion repository's). A disagreement, or a `Public` that GitHub cannot confirm, stops the whole read. Every
   document from a private source is at least `Internal`, and `--public-only` never opens a private source.
4. **The real read** of catalyst-docs' knowledge base: 12 live sources (two were retired with catalyst-users-kb).
   - The public read opened the 7 public repositories only, giving 268 documents.
   - The full read gave 906 documents, 636 of them from the five criteria. Each criterion document cites its entity,
     and all are `Internal`.
   - A folders build of the staging directory built all 906. Counts only: the content is private.
5. Checks: ruff, pyright and 47 tests (12 new, against a fake catalyst and a fake GitHub), CI on 3.11 and 3.13, and
   `catalyst check` in the engine's criterion.

## Problems

- **Roadmap rows**: `catalyst list all --json` lists `RM-` rows (59 across catalyst's and the UI's criteria), but
  `catalyst view` refuses them. The engine leaves them out and counts them. Reported to the main session as a kernel
  item.
- **A full read takes about 2.5 minutes**, CPU-bound: each `view` starts a new process. Phase 3's incremental reads
  are the remedy.
- **A build skipped every repository `README.md`**, since in a knowledge base repository it is a folder's
  description. A repository's README is now staged as `readme.md`. Found by comparing staged and built counts.

## What's left

- **Phase 2**: the realm build (vectors with `nomic-embed-text`, local), `search` and its MCP tool (SQLite FTS5 plus
  vectors), and the evaluation set in the catalyst-docs criterion, its score recorded with the build.
- **Phase 3**: incremental builds; re-view only the entities whose journal moved.
- **Phases 4 to 6**: the guide's outline (the owner's to approve), the public site on Pages from GitHub's commit rather
  than local checkouts, and the search behind catalyst-users.
- **For the owner**: catalyst-docs' uncommitted `KB.md` and `docs/user-generated/project-map.md`, and its criterion's
  unshared entries, are another session's, waiting on the owner's commit ask.
- **For the main session**: `list all` and `view` disagree on roadmap rows.
