# ADR-018: The handbook, the command catalogue, and the commands they drop

**Date:** 2026-10-10  
**Status:** Accepted  
**Author:** Olivier Steck (owner)  
**Affected scope:** kernel, SE module

## Context

The two governing documents a deployment receives had grown to 184 KB of rule text an agent was expected to obey:
`rules-of-rules.template.md` (66 KB) and `rules-of-development.template.md` (51 KB), plus the module's two
contributions (43 KB). Two read-only audits (roadmap R4.2, `what-is-going-on/18`) found about a quarter of it
obsolete or parked (the symlink, submodule and pointer model, agent-owned space, `/project`, plugins), a tenth
catalyst-development-only, a third restating `FORMAT.md`, `ARTIFACT-LAYOUT.md`, the invariants or the CLI, and ten
contradictions, among them rules described as one file each while every deployment keeps them as headings in rule
documents, and a reconciliation role gate no command enforced.

## Decision

Lift the prose freeze (ADR-017) for this change only, which removes far more prose than it adds:

- **`rules/Rules-of-Rules.md` is the handbook:** every judgment rule, deduplicated, kernel then module (about 13 KB
  composed). Every meta-rule keeps its ID and number (the frozen meta-rule list is unchanged); a parked or moved one
  keeps a one-line placeholder: rr-META-008 and -017 (plugins, R4.7), rr-META-018 (the recreation drift check, now
  catalyst-development only).
- **`CODE-OF-CONDUCT.md` is the command catalogue:** §4 in the shape `catalyst spec`, the MCP prompts and the parity
  check parse; §1–3 and §5–9 point into the handbook, keeping their numbers.
- **The command surface changes:** `/share` replaces `/criterion` (it matches the CLI and any sharing driver);
  `/project create|remove|export|import` and `/switch-agent` are removed (`catalyst init` on request, `catalyst open
  --agent`); `/catalyzer` is parked with the plugins.
- **`catalyst reconcile`** enforces the reconciliation role gate INV-21 describes.

The snapshot `docs/FROZEN-SURFACE.json` is rewritten for these commands; the freeze otherwise stands.

## Consequences

- **Positive:** what an agent must judge fits in about 15 KB (laws and handbook) instead of 184 KB; no stale model
  left in deployed text; the role gate is real.
- **Negative:** agents and people who typed `/criterion …` or `/project …` must use `/share …` and the CLI.
- **Trade-offs:** thin wrappers (`/user-*`, `/role-*`, `/commands`) are kept for now: merging them is roadmap R2's
  slash surface, a separate change.

## Alternatives Considered

1. **A new `HANDBOOK.md`:** a clearer name, but ID allocation, `validate`, `catalyst why` and a layout migration
   would all change; rejected by the owner.
2. **Slim both documents separately:** keeps the duplication between them; rejected.

## Related

- ADR-017 (prose feature freeze)
- `what-is-going-on/17-ten-laws-draft.md`, `what-is-going-on/18-handbook-outline.md`
- Migration: `framework/kernel/migrations/0.52.0/the-handbook.md`
