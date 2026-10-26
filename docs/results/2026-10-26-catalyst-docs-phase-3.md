# Results — 2026-10-26: a better realm search, and catalyst-docs phase 3 (incremental builds)

| What                                                                                                    | Where                                    |
| ------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| [catalyst-kb-engine 0.6.0](https://github.com/cantica-tech/catalyst-kb-engine/releases/tag/0.6.0)       | REQ-000006-7TE7wuaB, REQ-000007-7TE7wuaB; PR 3 |
| [knowledge-base 0.6.1](https://github.com/cantica-tech/catalyst-knowledge-base/releases/tag/0.6.1)      | `GUIDE.md`; distribution repo            |
| The realm build 0.2.1, `KBUILD-000003-erFhHt6m` (0.1.0 and 0.2.0 superseded)                             | the catalyst-docs criterion (shared)     |

1. **Two ways to raise the score, measured** on the same 52 questions and the same sources, top 10 passages:

   | Build | How each chunk is embedded                                  | Vector recall, MRR | Hybrid recall, MRR |
   | ----- | ----------------------------------------------------------- | ------------------ | ------------------ |
   | 0.1.0 | its text alone                                              | 0.635, 0.379       | 0.712, 0.389       |
   | A     | its title and heading before its text                       | 0.712, 0.498       | 0.750, 0.507       |
   | B     | A, with `nomic-embed-text`'s task prefixes                  | 0.731, 0.524       | 0.769, 0.500       |

   B was kept. The manifest records the embedding input and the prefixes, and search embeds each question the same
   way. KBM's `GUIDE.md` names the new fields (knowledge-base 0.6.1). Keyword search is unchanged at 0.673.
2. **Incremental builds** (phase 3):
   - `read-sources --previous` re-views, in each unchanged criterion, only the entities a journal entry since the last
     read names or touched, the new ones, and what they cite. Everything else is carried over.
   - `build-vectors --previous` reuses every vector whose exact embedding input was embedded the same way.
3. **The done-when, on the real fleet.**
   - A full read took 53 seconds (931 documents). Built from experiment B's vectors, it reused 6,721 chunks and
     embedded 204, in 73 seconds instead of about 46 minutes.
   - After one change, the incremental read took 18 seconds. It re-viewed 5 entities in the changed criterion and
     carried 621 over unviewed in the four others.
   - The incremental build embedded 8 chunks of 6,925, in 8 seconds.
4. Checks: ruff, pyright, 66 tests (7 new), CI on 3.11 and 3.13, and `catalyst check` in the engine's, KBM's and
   catalyst-docs' criteria.

## Problems

- **The distribution publish packages the kernel from catalyst's checkout**, which was at 0.116.0, not yet released.
  KBM 0.6.1 was published alone, through the script's own functions; no kernel was published.
- **The release-package commits the script makes in KBM were not journaled**: 0.6.0's was found by `catalyst check`
  hours later. Both were adopted (`catalyst journal adopt`).
- **The first watch on the experiment builds would have killed them** when it expired. They were restarted detached,
  with the watch following their log.
- **I cited a requirement's ID in a rule before allocating it**, the same mistake as phase 0's. I caught it before it
  was journaled.

## What's left

- **Phase 4**: the guide's outline, for the owner to approve before any page is written.
- **Phases 5 and 6**: the public site on Pages, built from GitHub's commits rather than local checkouts, and the search
  behind catalyst-users.
- **The search**: 12 of 52 questions still missed in hybrid mode; better keyword ranking (titles weighted) is next.
- **For the main session**: `list all` and `view` disagree on roadmap rows; and a distribution publish that can skip
  an unreleased kernel.
- **For the owner**: catalyst-docs' uncommitted `KB.md` and `docs/user-generated/project-map.md` (another session's).
