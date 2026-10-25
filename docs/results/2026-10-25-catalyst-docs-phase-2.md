# Results — 2026-10-25: catalyst-docs phase 2, the realm's search (catalyst-kb-engine 0.5.0)

| What                                                                                              | Where                                                    |
| ------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| [catalyst-kb-engine 0.5.0](https://github.com/cantica-tech/catalyst-kb-engine/releases/tag/0.5.0) | REQ-000005-7TE7wuaB; PR 2                                |
| The realm build 0.1.0, `KBUILD-000001-erFhHt6m` (`Built`)                                          | the catalyst-docs criterion; private storage, not shared |
| The evaluation set, 52 questions                                                                   | the catalyst-docs criterion (private)                    |

1. **`search`** reads a vector build and writes nothing. Keywords (an in-memory SQLite FTS5 index) and vectors (the
   question embedded with the build's own model, compared by cosine) are merged by reciprocal rank. Each passage
   cites its source, document, heading and classification, and for a criterion document its entity's ID.
2. **`mcp`** serves the same search as an MCP tool over stdio, for an agent on the machine that keeps the build.
3. **`evaluate`** runs every question in every mode and reports recall at k and mean reciprocal rank. It names only
   the IDs of missed questions, since the questions are drawn from private criteria. `--record` keeps the score in
   the build's `KBUILD-` `Verification`, KBM's section for "a sample of queries and what they returned".
4. **The realm build**: 913 documents from the knowledge base's 12 live sources, in 6,791 chunks. It was embedded
   locally with `nomic-embed-text` (768 dimensions) in about 25 minutes, and is kept on the curator's machine, never
   in a repository.
5. **The first score**, 52 questions across the five criteria and the public repositories, top 10 passages:

   | Mode    | Recall at 10 | MRR   | Missed |
   | ------- | ------------ | ----- | ------ |
   | keyword | 0.673        | 0.370 | 17     |
   | vector  | 0.635        | 0.379 | 19     |
   | hybrid  | 0.712        | 0.389 | 15     |

6. Checks: ruff, pyright, 59 tests (12 new, one of them the MCP tool in-process), CI on 3.11 and 3.13, and
   `catalyst check` in the engine's and catalyst-docs' criteria.

## Problems

- **The mcp package is now 2.x**, and `FastMCP` was renamed `MCPServer`. The engine requires `mcp>=2.3`.
- **The catalyst-docs criterion is not shared.** It holds another session's entries waiting on the owner's commit
  ask, and a `share push` would publish everything together. The build's record and the evaluation set wait with
  them.

## What's left

- **Phase 3**: incremental builds. A full vector build takes about 25 minutes and a full read about 2.5; reuse what is
  unchanged.
- **Raising the score**, each candidate measured against the evaluation set before it is kept:
  - embed each chunk with its title and heading;
  - use `nomic-embed-text`'s task prefixes.
- **Phases 4 to 6**: the guide's outline (the owner's to approve), the public site on Pages, and the search behind
  catalyst-users.
- **For the owner**: the catalyst-docs commit and share (see Problems).
- **For the main session**: `list all` and `view` disagree on roadmap rows.
