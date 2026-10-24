# Results — 2026-10-24: the engine records in the criterion, and builds vector databases

| What                                                                                              | Where                                           |
| ------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| [catalyst-kb-engine 0.2.0](https://github.com/cantica-tech/catalyst-kb-engine/releases/tag/0.2.0) | REQ-000002-7TE7wuaB: recording in the criterion |
| [catalyst-kb-engine 0.3.0](https://github.com/cantica-tech/catalyst-kb-engine/releases/tag/0.3.0) | REQ-000003-7TE7wuaB: the vector database build  |
| [KBM 0.5.1](https://github.com/cantica-tech/catalyst-knowledge-base/releases/tag/0.5.1)           | BUG-000001-I3JORbi9: `Local only`, not `None`   |

- **Recording** (`eng-WORKFLOW-000003`): onboarding becomes a `KB-` (with `Basis`, `Document base`, `Target`), one
  `KSOURCE-` per source (the criterion first) and the folder plan in its Structure; a build becomes a `KBUILD-`, its
  Contents written, `Built`. All through catalyst's CLI, so journaled and signed; `plan <KB-id>` reads a knowledge
  base back into its onboarding plan, to resume. CLI: `onboard --record`, `build-folders --record`, `plan`.
- **The vector build** (`eng-OUTPUT-000002`): chunks by heading, one embedding model per build (hosted only when every
  chunk is within the knowledge base's `Hosted embedding up to`, else local, else nothing built), unit-length vectors
  in `vectors.parquet`, `chunks.jsonl`, the documents beside them, a manifest naming the model: readable by any
  model or vector store without catalyst. A failed embedding writes nothing. CLI `build-vectors`; extras `vectors`
  (pyarrow), `openai` (Ollama, OpenAI-compatible).
- **Found on the way** (KBM `BUG-000001`): `Hosted embedding up to=None` failed `catalyst check`, because catalyst reads
  `none` as an empty field; KBM 0.5.1 offers `Local only` instead, with a migration. No real deployment held `None`.
- Checks: the engine's 34 offline tests, ruff and pyright, and CI on 3.11 and 3.13; an integration test against a real
  deployment (catalyst's checkout, KBM 0.5.1): the plan recorded and read back identical, a build `Built`,
  `catalyst check` 0 errors.

## What's left

- **A real local embedding model**: the vector build ran only with Pydantic AI's test model. This machine's Ollama has
  no embedding model (`ollama pull nomic-embed-text` would add one).
- **The kernel's empty values**: catalyst reads `none`, `n/a` and `-` as empty in any field, so a module enum value
  among them breaks `check`; a kernel rule (an allowed enum value is never empty) would close the hazard for every
  module.
- **KBM 0.5.1 in the distribution repository**: it ships with the next kernel publish.
- **Deployments with KBM** (catalyst-users and its knowledge base) still run 0.3.1.
