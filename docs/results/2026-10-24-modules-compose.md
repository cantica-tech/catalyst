# Results — 2026-10-24: modules compose (kernel 0.107.0, KBM 0.4.1)

The owner's fact, made foundation: the knowledge base module (KBM) exists alone in any criterion, and also beside any
other module, so knowledge bases are built off any project.

| What                                                                                    | Where                                      |
| --------------------------------------------------------------------------------------- | ------------------------------------------ |
| Kernel 0.107.0 (REQ-000088, `fw-STRUCTURE-000018`)                                      | `cantica-tech/catalyst`; distribution repo |
| [KBM 0.4.0](https://github.com/cantica-tech/catalyst-knowledge-base/releases/tag/0.4.0) | `cantica-tech/catalyst-knowledge-base`     |

- **The kernel** names no module, so it states the general law: **INV-30 now reads "The kernel is module-agnostic, and
  modules compose"**, and its law L9 reads "The kernel knows no module; no module knows another module or an agent." Every module works alone
  and beside any other the composition rules admit, in either install order, and never requires, names or assumes
  another. `MODULE-SPECIFICATION.md` §1 says what a module owes; the catalogue names KBM's two setups.
- **CI enforces it on the real KBM**: `tests/test_second_module.py` installs it alone (as before), with another module
  installed beside it, and beside another module installed first; both deployments pass `catalyst check` with both
  modules in scope. CI now checks KBM out at 0.4.1.
- **Not a new invariant**: the kernel's prose surface is frozen (ADR-017), and a new invariant needs an owner-reviewed
  ADR, so the guarantee extends INV-30 rather than adding INV-31. KBM 0.4.0 cited INV-31; 0.4.1 corrects it.
- **KBM** adds law **KB-L2 — Alone or beside any module**, invariant INV-KB-8 and meta-rule `rr-KB-008`; `GUIDE.md`
  and the README describe both setups.
- Checked: neither production module names the other.

## What's left

- **Deployments with KBM** (catalyst-users and its knowledge base) still run KBM 0.3.1: `catalyst module upgrade
knowledge-base` brings KB-L2 into their session brief.
- **`/kb-setup` on kernel 0.106 or later**: it still adds the Knowledge Curator role with `catalyst role add`, which
  refuses since people and roles are catalyst-users'. A KBM fix is pending.
