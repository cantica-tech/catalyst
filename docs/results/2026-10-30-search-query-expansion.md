# The search's misses: query expansion tried and dropped

2026-10-30. catalyst-docs' realm search misses 7 of 52 evaluation questions in hybrid mode (recall 0.865 at k 10,
catalyst-kb-engine 0.15.0). The misses are mostly vocabulary: a question's words are not its rule's. This round
tried query expansion against them: a local model writes a hypothetical answer, which is searched beside the
question.

## Done

- **Stemming** was already on (FTS5 `porter`), so no gain there.
- **Query expansion** was built as `search` and `evaluate --expand MODEL [--expand-context TEXT]`, measured, and
  reverted, so nothing shipped. `REQ-000018-7TE7wuaB` is Abandoned; its step holds the measurements.

## Checks

Measured on the realm build 0.2.1, 52 questions, k 10, hybrid recall / MRR, with `llama3.2:3b`:

| Setup | Recall | MRR |
| --- | --- | --- |
| Without expansion | 0.865 | 0.569 |
| Generic prompt | 0.865 | 0.564 |
| With a sentence saying what the knowledge base documents | 0.865 | 0.558 |
| First prototype (other wording, Ollama's own API) | 0.904 | 0.567 |

The prototype's lead is two questions, within what the prompt's wording alone swings. Each question costs about 10 s.
The engine's tests passed while the feature was in (141); `catalyst check` passes in the engine's criterion.

## Problems

- **The first prototype's 0.904 did not hold up** in the real `evaluate`. Its gain came from the prompt's wording,
  not from expansion as such.

## What's left

- **The 7 misses.** They need the documents' own words to change, for example rule titles that use the words people
  ask with, or a glossary of synonyms. Neither is engine work. A larger expansion model is untried.
- **`record-site`** still runs by hand after each deployment.
