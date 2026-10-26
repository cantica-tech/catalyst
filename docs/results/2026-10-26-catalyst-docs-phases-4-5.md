# Results — 2026-10-26: catalyst-docs phases 4 and 5, the guide and the public site

| What                                                                                                    | Where                                    |
| ------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| [The public site](https://cantica-tech.github.io/catalyst-docs/), live                                   | catalyst-docs' Pages workflow (PRs 2, 3) |
| The guide: its outline and twelve pages, each approved by the owner                                     | catalyst-docs `docs/guide/`              |
| [catalyst-kb-engine 0.8.0](https://github.com/cantica-tech/catalyst-kb-engine/releases/tag/0.8.0)       | REQ-000009-7TE7wuaB; PR 6                |
| [catalyst-kb-engine 0.6.1](https://github.com/cantica-tech/catalyst-kb-engine/releases/tag/0.6.1), [0.7.0](https://github.com/cantica-tech/catalyst-kb-engine/releases/tag/0.7.0) | BUG-000002, REQ-000008                   |

1. **The guide** (phase 4): the owner approved the outline, decided that designs not yet built are described and marked
   as such, and reviewed every page. Twelve pages of 600 to 1,000 words: what catalyst is, getting started, the ten
   laws, rules and the criterion, working day to day, people and signing, working together, keeping up to date,
   modules, knowledge bases, analysing existing code, and the UI. They are written from public documents only, each
   command checked against the CLI and each claim against the current kernel.
2. **The public site** (phase 5) holds the guide and a reference of the 7 public repositories (one page per document,
   citing its file):
   - it is built in GitHub Actions from GitHub's commits, never from a local checkout, and every source's visibility
     is re-checked on each build;
   - a publication check refuses any document from a source the public sources list does not name, or not `Public`;
   - it is deployed as a Pages artifact, so no branch keeps it, and it rebuilds on every push to `main` and daily.
3. **The engine** gained, along the way:
   - in 0.6.1, roadmap rows read as documents, once kernel 0.116.1 could show them;
   - in 0.7.0, `.catalystignore` honoured, so what catalyst does not govern never enters a knowledge base;
   - in 0.8.0, `export-sources`, `read-sources --sources`, `publish-check` and `site`.
4. Checks:
   - 78 tests, CI on 3.11 and 3.13, and `catalyst check` in the engine's and catalyst-docs' criteria;
   - the live site answers on its home, guide, reference and manifest;
   - its manifest says `Public`, ceiling `Public`, 291 documents, none from a criterion.

## Problems

- **The first deployment failed at its install step**: `mkdocs-material` provides no command, so it is installed with
  MkDocs (`uv tool install mkdocs --with mkdocs-material`). Nothing was published by the failed run.
- **The site lost one document against the local run** (291 against 292): a file in a local checkout was not yet on
  GitHub. That is the point of building from GitHub's commits.
- **Claims were corrected before review**: a reconcile verb that does not exist, a Studio view called
  planned that had shipped, and stale public documents the guide would have followed. The main session has since
  updated catalyst's `README.md` and `GLOSSARY.md`.

## What's left

- **Phase 6**: the realm's search served behind catalyst-users, so a token from outside the realm is refused.
- **The reference includes test fixtures** (a repository's sample criterion under its tests): a source's import should
  name what it draws on, or the repositories opt fixtures out with `.catalystignore`.
- **The public build is not recorded as a `KBUILD-`**: Actions cannot reach the private criterion. Its manifest is
  published with the site.
- **The search**: 12 of 52 questions still missed in hybrid mode.
- **For the UI repository**: its README calls the desktop app experimental, while its `docs/desktop.md` says it ships.
