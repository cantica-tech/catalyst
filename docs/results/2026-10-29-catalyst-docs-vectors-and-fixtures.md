# catalyst-docs: the public vector database, and test fixtures out of the reference

2026-10-29. Two of the open points of the public documentation site (catalyst-kb-engine's design 01), decided by the
owner: test fixtures leave the reference through `.catalystignore`, and the site serves its documents as a vector
database.

## Done

1. **Test fixtures out of the reference.**
   - Only catalyst-ui had any: the core tests' sample criterion, `packages/catalyst-core/src/test/fixtures` (9
     documents).
   - A root `.catalystignore` names it. That takes it out of catalyst's scope (FORMAT.md §11), and the engine leaves
     out what catalyst ignores (`eng-SOURCE-000004`).
   - Shipped through catalyst-ui PR #186; the journal entry is in its criterion.
2. **The vector database on the site.**
   - Each Pages run also builds the public documents as a `kbm-build/1` vector database. It is embedded in CI with
     Ollama's nomic-embed-text, the public build's model, so no token is needed.
   - It passes the same publication check as the pages.
   - It is served at `vectors/catalyst-vectors.tar.gz`, with its `manifest.json` beside it, and the home page links
     it.
   - Each run reuses the vectors of the archive the site last served.
   - Shipped through catalyst-docs PR #5; the journal entry is in its criterion.

## Checks

- **Locally, with engine 0.12.0, from fresh GitHub clones:**
  - with the ignore file, the reference holds 289 documents instead of 298;
  - the vector build has 2,533 chunks and passes the publication check;
  - the archive is 9 MB;
  - a rebuild from the downloaded archive reused all 2,533 vectors and embedded none;
  - search over it answers.
- **Live:**
  - the Pages run succeeded;
  - the site's manifest counts 289 documents;
  - `vectors/manifest.json` says `Public`, ceiling `Public`, `ollama:nomic-embed-text`, 289 documents and 2,533
    chunks;
  - the archive answers 200 (9.4 MB);
  - the home page links it.

## Problems

- **The first run had nothing to reuse,** so it embedded every chunk; later runs embed only changed ones.
- **The Stop hook flagged the catalyst repository's own kernel 0.118.0 work in progress** (version drift and
  unjournaled kernel files). It was another session's, so it was left untouched.

## What's left

- **Phase 6's live check**: `serve` needs the `catalyst-api` client secret, which the owner supplies; then
  `REQ-000010-7TE7wuaB` completes.
- **The search**: 12 of 52 evaluation questions still missed in hybrid mode.
- **Whether catalyst-kb-container is governed by catalyst.**
- **The public build is not recorded as a `KBUILD-`**: Actions cannot reach the private criterion. Its manifests are
  published with the site.
