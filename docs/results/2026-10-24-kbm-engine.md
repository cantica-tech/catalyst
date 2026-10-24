# Results — 2026-10-24: KBM onboarding, builds any model can read, and its engine

The owner's decisions: the engine in its own repository under catalyst (and KBM's repository under catalyst too), a
new field on the KB record, KBM's output consumable outside catalyst by any model, and Pydantic AI.

| What                                                                                                     | Where                                                                                                   |
| -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Kernel [0.107.0](https://github.com/cantica-tech/catalyst/releases/tag/0.107.0) (REQ-000088, BUG-000034) | `cantica-tech/catalyst` (PRs 319, 320); distribution repo                                               |
| [KBM 0.5.0](https://github.com/cantica-tech/catalyst-knowledge-base/releases/tag/0.5.0)                  | `cantica-tech/catalyst-knowledge-base`; distribution repo                                               |
| [catalyst-kb-engine 0.1.0](https://github.com/cantica-tech/catalyst-kb-engine/releases/tag/0.1.0)        | `cantica-tech/catalyst-kb-engine` (new, public, Apache-2.0)                                             |
| Two shared criteria                                                                                      | `cantica-tech/catalyst-knowledge-base-criterion`, `cantica-tech/catalyst-kb-engine-criterion` (private) |

- **Kernel 0.107.0**: modules compose (INV-30, L9, `fw-STRUCTURE-000018`), and a module whose repository is a
  catalyst project ships no `catalyst.toml` and seeds none into a criterion (BUG-000034), which putting KBM's
  repository under catalyst needed.
- **KBM under catalyst** (its owner signs as `I3JORbi9`): domains `COMPOSE`, `MODEL`, `ONBOARDING`, `OUTPUT`, four
  rules, `REQ-000001`. **KBM 0.5.0**: the KB record gains `Basis` (Criterion / Documents), `Document base`
  (Static / Dynamic) and `Target` (Folders / Vector database); `/kb-setup` is the onboarding (the criterion enriched
  by sources, or gathered documents; location and storage; target; document base), its curator role from
  catalyst-users; `rr-KB-009` and INV-KB-9: a build of either target is readable by any model without catalyst
  (format `kbm-build/1`); migration `0.107.0`; it needs kernel 0.107.0.
- **The engine** (`7TE7wuaB`): domains `ARCH`, `WORKFLOW`, `OUTPUT`, `QUALITY`, six rules, `REQ-000001`. 0.1.0: the
  onboarding plan as typed data and its workflow as a `pydantic-graph` graph (each decision proposed by rules or a
  Pydantic AI agent, any model, and decided by a person); the folders build in `kbm-build/1`; a CLI; 21 offline
  tests; CI (ruff, pyright, pytest on 3.11 and 3.13) passes.
- Checks: every catalyst pull request's jobs passed before its merge (797 tests locally); catalyst's KBM tests against
  0.5.0; the KBM zip ships no `catalyst.toml`; every deployment's `catalyst check` passes.

## What's left

- **The engine's next slices**: the vector database target (embedding within each knowledge base's allowance, local
  models above it), and recording onboarding and builds in the criterion through catalyst's CLI (`eng-WORKFLOW-000003`).
- **Deployments with KBM** (catalyst-users and its knowledge base) still run KBM 0.3.1; `catalyst module upgrade
knowledge-base` to 0.5.0 needs their kernel at 0.107.0 first.
- **The engine and KBM repositories** have no `catalyst trace` CI job yet (it needs a deploy key on each criterion).
