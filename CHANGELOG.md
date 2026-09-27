# Changelog

catalyst is pre-1.0: minor versions may change the deployed layout. Every
such change ships a migration (`framework/kernel/migrations/migrations.md`)
that `/sync-framework` applies to an existing deployment. Versions before
0.37.0 are described by that migrations index and by the tagged commit
messages.

## 0.37.0 — unreleased

Beta-readiness Phase 0.

- Licensed under Apache-2.0; added `CONTRIBUTING.md`, `SECURITY.md` and this
  changelog.
- `scripts/package_release.py` no longer commits or pushes anything unless
  given `--push`; the distribution target is a `--publish-dir` argument
  instead of a hardcoded sibling checkout, and the kernel zip now carries
  `LICENSE`. `task release` packages only; `task release:publish
  PUBLISH_DIR=<checkout>` packages, publishes, commits and pushes.
- Removed stale files: `SUBMODULE-NOTE.txt`, `PROPOSAL-generic-framework.md`
  (shipped as the kernel/module split) and the 2026-08-04 audit report.
- **Working copy location is computed, never committed** (migration
  `0.37.0/computed-working-copy-location.md`, INV-6 revised). The
  `<app-name>.catalyst` pointer no longer stores `agent-source`; each
  machine computes its agent-owned location, and a gitignored `.criterion`
  symlink at the project root is the single access path. The root
  `Taskfile.yml` includes `.criterion/Taskfile.common.yml` as optional, so
  fresh clones and CI work. Tools resolve `.criterion` first and honor a
  legacy `agent-source` until migrated.
- The Claude Code Stop hook now actually enforces: `scripts/stop_hook.py`
  runs every checker and, on failure, writes the output to stderr and exits
  2, so the agent sees the failures and keeps working (a second consecutive
  block lets the stop through, to avoid loops).
- `check_deployment.py` reports version drift between the working copy's
  `version.txt`, the pointer's `kernel_version` (or legacy
  `framework_version`) and, in catalyst's own repository, the kernel's
  `version.txt`.
- Feature freeze recorded in `CONTRIBUTING.md`: no new invariants,
  meta-rules or entity types until criterion is rebuilt on git.
