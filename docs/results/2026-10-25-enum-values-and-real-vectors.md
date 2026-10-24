# Results — 2026-10-25: a module's enum values are values, and a real vector build

| What                                                                                         | Where                                                     |
| -------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Kernel [0.110.0](https://github.com/cantica-tech/catalyst/releases/tag/0.110.0) (BUG-000035) | `cantica-tech/catalyst` (PRs 325, 326); distribution repo |
| The engine's vector build, with a real local model                                           | `cantica-tech/catalyst-kb-engine` STEP-000003-7TE7wuaB    |

- **BUG-000035**: catalyst read `none`, `n/a` and `-` (any case) as an empty field, so a module offering one as an
  allowed enum value had it reported missing (the knowledge-base module's `None`, renamed `Local only` in its 0.5.1).
  `corpus.is_unset` now treats an allowed value as set, in `check`'s required fields, `nonempty` guards, `is set`
  conditions and index cells; a schema's allowed values load as text (YAML had read `None` as a null). Tested by
  `tests/test_catalyst_enum_values.py`; the full suite passed (814).
- **A real vector build**: with `nomic-embed-text` pulled into Ollama (owner's assent), `catalyst-kb-engine
build-vectors` wrote 768-dimensional vectors; queried with only pyarrow, the JSON files and Ollama's API, without
  catalyst or the engine, each of three questions retrieved the chunk answering it.
- Checks: every job of both pull requests passed before its merge (one lint rerun: a double blank line in the
  changelog); the distribution repo holds kernel 0.110.0, software-engineering 3.4.1 and knowledge-base 0.5.1.

## What's left

- **Deployments with KBM** (catalyst-users and its knowledge base) still run KBM 0.3.1.
- **The engine's onboarding with a real model** (`onboard --model ollama:…`) is untested; the proposer is tested with
  Pydantic AI's function model.
