# Results — 2026-10-25: KBM 0.5.1 in the deployments, module upgrade from an installed CLI, onboarding with a real model

| What                                                                                              | Where                                                     |
| ------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Kernel [0.110.1](https://github.com/cantica-tech/catalyst/releases/tag/0.110.1) (BUG-000036)      | `cantica-tech/catalyst` (PRs 327, 328); distribution repo |
| [catalyst-kb-engine 0.3.1](https://github.com/cantica-tech/catalyst-kb-engine/releases/tag/0.3.1) | BUG-000001-7TE7wuaB                                       |
| catalyst-users and its knowledge base at kernel 0.110.0, knowledge-base 0.5.1                     | their criteria (PRs 23, 24; 8, 9); their `catalyst.toml`  |

- **The two deployments** moved from kernel 0.106.1 and knowledge-base 0.3.1 in two publishes each: the kernel first
  (catalyst refuses a module its shared gate cannot read), then the module from its release zip, with the KB and
  KBUILD templates' new versions (the onboarding fields, the build targets). catalyst-users' `KB-000001` keeps its
  fields as they were: recording its onboarding (`Basis`, `Document base`, `Target`) is its curator's choice.
- **BUG-000036**: `catalyst module upgrade … --kernel <checkout>`, run from a deployment's own CLI, crashed building the
  CLI (`package_release` is not in the zipapp); the checkout now builds it in a subprocess. Found doing the above.
- **The engine with a real model**: onboarding with `ollama:llama3.2:3b` stopped at its first proposal, the model's
  structured output being invalid (engine BUG-000001). Since 0.3.1 the agent retries, then the rules propose, logged;
  the person decides each step. With that model: 1 of 4 proposals from the model, 3 from the rules, in 95 s.
- Checks: the full suite (815) and every job of both catalyst pull requests; the engine's 35 tests and CI; each
  deployment's `catalyst check` (0 errors).

## What's left

- **A larger local model** for onboarding proposals (a 3B model mostly falls back to the rules).
- **catalyst-users' `KB-000001`**: its onboarding fields, if its curator wants them recorded.
- **Kernel 0.110.1 in the other deployments**: KBM's and the engine's own (at 0.107.0), catalyst-users and its
  knowledge base (at 0.110.0).
