# Design 01 done; the search's misses; catalyst-kb-container governed

2026-10-29. This round:

- phase 6's live check, which closes catalyst-kb-engine's design 01;
- the bug that check found;
- the two points left open after it: the search's misses, and whether catalyst governs catalyst-kb-container.

## Done

1. **Phase 6's live check passed** (run by the kernel session, accepted by the owner).
   - A realm token gets 200 on `/me` and `/search`.
   - These are refused with 401 on both routes: no token, a non-token, another issuer's token, a realm token with
     altered claims, and an expired token.
   - `REQ-000010-7TE7wuaB` is Completed, and design 01's six phases are delivered.
2. **`BUG-000044-7TE7wuaB`, fixed in catalyst-kb-engine 0.14.1.**
   - An `ollama:` model needed `OLLAMA_BASE_URL`: `serve`'s `/search` answered 500, and `search`, `mcp` and
     `build-vectors` failed too.
   - It now defaults to Ollama's own address.
3. **One passage per document, `REQ-000016-7TE7wuaB`, catalyst-kb-engine 0.15.0.**
   - A search keeps each document's best passage, so k passages are k documents; `--per-document N` keeps up to N.
   - On catalyst-docs' realm (52 questions, k 10), hybrid recall goes from 0.788 to 0.865 and MRR from 0.536 to 0.569,
     so 7 questions miss instead of 11. Keyword recall goes from 0.692 to 0.75, vector from 0.731 to 0.846.
   - The score is recorded in `KBUILD-000003-erFhHt6m`.
4. **catalyst-kb-container is governed by catalyst** (the owner's decision).
   - Kernel 0.118.0, software-engineering module; the criterion is in the private
     `cantica-tech/catalyst-kb-container-criterion`.
   - It was installed after the other session committed its edits, so nothing started out unrecorded.
   - Its first rules, gathered from the code:
     - an offline install of a released engine;
     - generated files never committed;
     - the container run as its user;
     - a sign-in never stored;
     - private text sent to Copilot only with `-I`.

## Checks

- **Engine**: ruff, pyright and 131 tests pass, and CI passed on 3.11 and 3.13 for both releases.
- **The Ollama default**: the failure was reproduced without the fix; with it, a live query embeds (768 dimensions).
- **Search variants measured and dropped**:
  - 2 passages per document: 0.827;
  - capping each ranking before fusion: 0.635;
  - fusing by document: 0.846 to 0.865;
  - 200 candidates: the same recall.
- **catalyst check**: passes in the engine's, catalyst-docs' and catalyst-kb-container's criteria.

## Problems

- **`evaluate --record` failed** because `catalyst` was not on the shell's PATH. The score was added to the build's
  record by hand and journaled, as the previous one had been.
- **The installed `catalyst` CLI was still 0.117.3**, so the container was installed from catalyst's source, at 0.118.0.
- **`rules/rules.md` is not one of the generated indexes**: `index regen` leaves it alone, so the new rules were
  listed there by hand.

## What's left

- **The search's 7 misses**: mostly vocabulary, where the question's words are not its rule's. That needs better
  rule text or query expansion, measured the same way.
- **catalyst-kb-container's commit-msg hook** (`catalyst hook install`): offered, not installed.
- **The public build is not recorded as a `KBUILD-`**: Actions cannot reach the private criterion.
