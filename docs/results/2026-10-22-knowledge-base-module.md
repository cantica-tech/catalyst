# Results — 2026-10-22: the knowledge-base module, and risk management out of scope

The owner asked for a new module, `cantica-knowledge-base`, with one purpose: building and maintaining knowledge
bases. In the same round, risk management left Cantica's scope for now, and the new module took its place as the
second production module.

| Release | What's in it |
|---|---|
| The module [`cantica-knowledge-base` 0.1.0](https://github.com/cantica-tech/catalyst-cantica-knowledge-base/releases/tag/0.1.0) | Its own repository: the types, the commands, the meta-rules and the guide |
| Kernel [0.103.0](https://github.com/cantica-tech/catalyst/releases/tag/0.103.0) | The catalogue, the CI fixture and the second-module test move to the knowledge-base module |

## The owner's choices

- **The name:** `cantica-knowledge-base`, in `cantica-tech/catalyst-cantica-knowledge-base`.
- **A vector database:** portable files. Each version is `manifest.json`, `chunks.jsonl` and `vectors.parquet`, which
  any vector store (FAISS, LanceDB, pgvector, Chroma) and any model can load.
- **Embedding:** by classification. Each knowledge base names the highest classification a hosted embedding service
  may receive; anything above is embedded by a local model and never leaves the machine.
- **A role:** the module proposes a `Knowledge Curator` role, added with the owner's assent; only a curator or an
  Admin imports, classifies and builds.

## What the module is

Three types:

| Type | What it records | Lifecycle |
|---|---|---|
| `KB-` knowledge base | The rules it serves, its kind (project or reflective), classification, policy, embedding allowance, repository, freshness, curator | Proposed → Established → Active → Frozen → Retired |
| `KSOURCE-` source | Where its documents come from, how it is read, the mark its documents get, when it was last checked | Active, Stale, Broken, Retired |
| `KBUILD-` build | A versioned vector database: version, ceiling, classification, embedding model, content commit, location | Planned → Built → Published → Superseded or Withdrawn |

Every type can be retired in place, a lesson from the review of active statuses
(`docs/misc/entities-active-statuses.md`).

- **Classification:** `Public` < `Internal` < `Confidential` < `Restricted`. A document's or a pointer's effective
  classification is the higher of its own mark and its knowledge base's: a public document in an internal knowledge
  base is internal, and a restricted document in a public one stays restricted. Each knowledge base's policy
  (`Default classification`) marks every new, imported or unmarked document when it is written, unless its source
  gives a mark. A build refuses while anything is unmarked, contains nothing above its ceiling, and is classified at
  the highest classification it contains. A mark is lowered only by a person's journaled decision. The module's law,
  KB-L1, is "classification only rises".
- **The two kinds:** a project knowledge base draws on any information outside catalyst; a reflective one only on
  the Cantica ecosystem (the kernel, its modules, its plugins) and is rebuilt at each of their releases.
- **The repository:** each knowledge base is its own repository and its own catalyst project, so every document
  added, changed or reclassified is journaled. It holds `KB.md`, hierarchical `docs/`, `pointers/` mirroring them,
  and `builds/<version>/manifest.json`; the build files themselves are kept where the build says.
- **Commands:** `/kb-setup`, `/kb-import`, `/kb-classify`, `/kb-refresh` (pointers and sources kept fresh, never
  silently dropped), `/kb-build`, `/kb-audit`.
- **Guards:** a knowledge base is `Established` only with its Structure written and `Active` only with its Policy and
  Maintenance; a build is `Published` only with its Verification.
- **The guide:** `GUIDE.md` says how to establish and maintain a knowledge base, with the formats of a document, a
  pointer and a build.

A module is declarative: building a vector database is a procedure the agent follows, recorded and checked by
catalyst, not a new command in the kernel, which names no module.

## Risk management, out of scope

Taken out of the catalogue (so out of the kernel's purity check and its releases), out of CI, and out of the
distribution repository. Its repository and its 0.1.0 release are kept as they are, so it can come back. Decision B1
and the roadmap say so.

## Checks

754 tests pass, the second-module test now driving the knowledge-base module end to end: a knowledge base, a source,
a build, each guard, both back-references, the module's tiers, and a clean check. Installed in a scratch deployment,
the module passes `catalyst check`. Kernel purity, ruff and the generated documents pass.

## Problems along the way

- **A command defined twice:** the module defined `/create kb-source` while catalyst generated `/create
  knowledge-source`; renamed to the generated name, which the module's own text then overrides.
- **Lost release scripts:** the scratch directory was cleared between sessions, taking the release scripts with it,
  the gate included; the first release attempt ran nothing. They were rewritten before the release ran.

## What's left

**Your decisions:**

- **A first knowledge base:** a reflective one of the Cantica ecosystem would exercise the whole module (`/kb-setup
  reflective "Cantica ecosystem"`): its classification, its policy, and where its repository and builds live.
- **The embedding model:** which local model, and which hosted service (if any) a knowledge base may use up to its
  allowance.
- **The active-status gaps** (`docs/misc/entities-active-statuses.md`): roles, domains, gates and a dropped roadmap
  row have no retired state.
- **This deployment's module templates:** `catalyst migrate --apply --template all`, some, or none.
- **The brand**, and **declaring format 1.0** at the 1.0 release.

**Your time:** the beta trial (RM-026, RM-028, RM-029), and trying the new pieces.

**Waiting on you:** the Marketplace token, the signing credentials, the update feed, trademark counsel, and a public
address for the Linux package.

**Work Claude can do without you:** the two notes saved this round (`docs/users-registry.md`,
`docs/misc/entities-active-statuses.md`) are journaled but not committed, waiting on your word.

**Blocked on something outside this repository:** module signatures (R4.9 N4) and signed releases (R7) wait on the
signing credentials and the release feed.
