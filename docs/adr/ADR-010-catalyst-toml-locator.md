# ADR-010: `catalyst.toml` locates the criterion in `$HOME/.catalyst`

**Date:** 2026-10-07 (revised 2026-10-08)  
**Status:** Accepted (owner, 2026-10-08)  
**Author:** Olivier Steck (owner)  
**Affected scope:** kernel

## Context

A deployment is located today through three mechanisms: the `<name>.catalyst` pointer at the project root, a
`.criterion` symlink (gitignored) into agent-owned space, and, for a shared deployment, a `.criterion` git submodule.
The working copy therefore appears inside the project tree, where any version control system can pick it up as part of
the code base, and its place depends on the agent (`~/.claude/projects/<slug>/.criterion` under Claude Code).

A first version of this ADR (2026-10-08 morning) chose `.catalyst/catalyst.toml` in the product repository with the
governance data beside it. The owner's requirement of the same day (`what-is-going-on/13-criterion-home-requirement.md`)
replaces it: **nothing of the criterion sits in the project.**

## Decision

1. **The criterion lives in catalyst's own space:**
   - a project's: `$HOME/.catalyst/projects/<project name>/criterion`;
   - a workspace's meta criterion: `$HOME/.catalyst/workspaces/<workspace name>/criterion`, where a workspace is a
     VS Code workspace (`<name>.code-workspace`) whose member folders carry a `catalyst.toml`.
2. **The only tracked file is `catalyst.toml`** at the project root (renamed from today's `<name>.catalyst`
   pointer). It names the project (and its workspace, when it has one) and pins the catalyst and module versions; it
   never holds a path. One fixed name: no `*.catalyst` globbing, and the project name lives in the content only.
3. **One resolver**, `catalyst where`: `catalyst.toml` → `$HOME/.catalyst/projects/<name>/criterion`. No symlink,
   no submodule, no agent-owned directory.
4. **Python floor 3.11** from R3.1, so the stdlib `tomllib` reads the file (3.9 is past end of life; the uv-built
   runtime brings its own Python, and only the `python -m venv` fallback needs a system 3.11+). Existing
   `<name>.catalyst` files are read for one minor (ADR-009); `catalyst migrate` renames them.
5. **The name "criterion" stays**: the root of the work, the single truth the work is based on.
6. **Each criterion carries its runtime** in `…/criterion/.venv`: a runtime per catalyst version is built once per
   machine (`uv venv --relocatable`, else `python -m venv`) and copied into the criterion's `.venv` whenever the
   criterion is created or loaded. The launcher runs that venv's Python directly; nothing is activated. `.venv` is never
   shared (ignored in the criterion's own repository). Several catalyst versions run side by side.

## Consequences

- **Positive:**
  - Nothing governance-related in the project tree beyond one small `catalyst.toml`; works with any VCS, or none.
  - Agent-neutral: every agent, the UI, hooks and CI resolve the same place.
  - No symlinks: Windows needs nothing special.
  - A fresh clone finds its criterion by name on any machine.
  - Per-criterion runtime: no guessing which `python3` runs catalyst; versions coexist.
- **Negative:**
  - The criterion is not backed up by the product repository: it is its own git repository, pushed to a remote to be
    shared or kept.
  - Project names must be unique per machine (`init` refuses a clash).
  - catalyst must ship as a wheel as well as a zipapp.
- **Trade-offs:** TOML (comments, the familiar `*.toml` convention) costs the Python 3.9/3.10 support; a small
  subset parser or `catalyst.json` would have kept 3.9, at the price of maintained code or a file without comments.

## Alternatives Considered

1. **`.catalyst/catalyst.toml` with the governance data in the product repository** (Proposal A, this ADR's first
   version): rejected by the owner; governance would enter the code base.
2. **A machine-local registry, nothing tracked** (`$HOME/.catalyst/registry.toml`): every machine would have to
   register each project; one tracked file is simpler.
3. **Keep `<name>.catalyst` (JSON)**: no Python floor change, but a variable file name to search for and no comments.
4. **Keep the agent-owned working copy and the `.criterion` symlink** (kernel 0.37–0.46): agent-dependent and visible
   in the project tree.

## Related

- `what-is-going-on/13-criterion-home-requirement.md` (the requirement and the owner's answers)
- ADR-009 (legacy deployments), ADR-011 (store abstraction: the `home` driver comes first)
- Replaces INV-6's agent-owned working copy; scheduled as roadmap R3.1, R3.1a (runtime), R3.1b (workspace)
