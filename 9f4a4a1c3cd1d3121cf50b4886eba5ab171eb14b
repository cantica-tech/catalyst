# Audit: catalyst-git submodule pointer bump + stray `.vscode/`

Cycle timestamp: 2026-08-04T20:15:03Z

## Change set

```json
{"entered": {"plugins/repository/catalyst-git": " M|None", ".vscode/": "??|None"}, "updated": {}, "cleared": []}
```

## Findings

- **`plugins/repository/catalyst-git` (gitlink, ` M`)** — `git diff` shows the
  submodule pointer moved `eb18b14 → 4bc76a6`. `git log eb18b14..4bc76a6`
  shows exactly one new commit: *"Add per-cycle change-diff stdout output to
  git status monitor"*, which adds `service.py` (the polling/diff monitor
  implementation itself). `version.txt` is unchanged at `0.1.1` in both
  commits — no version bump accompanies this commit. The catalog at
  `plugins/repository/catalog.md` pins `catalyst-git` at `Release v0.1.1` /
  `Tag 0.1.1`, which resolves to commit `acc6e0f` on the submodule's
  `release` branch; `eb18b14` (the previously-committed gitlink) is an
  ancestor of that release commit, and `4bc76a6` is one commit further
  ahead on `development`, past the last release. This is normal interim
  development state: the catalog correctly tracks the last released
  version, and the working submodule checkout is simply ahead of it with
  unreleased work-in-progress — not a mismatch needing a catalog update.
  One caveat: `git status` inside the submodule shows `development` is
  ahead of `origin/development` by 1 commit — `4bc76a6` has not been pushed
  to the submodule's origin yet. If the superproject's pending gitlink bump
  (currently just an uncommitted working-tree change) were committed before
  that push happens, a fresh clone + `git submodule update --init` elsewhere
  would fail to resolve `4bc76a6`. No action is needed yet since nothing has
  been committed on either side, but the push should happen before the
  gitlink bump is committed.

- **`.vscode/` (untracked directory)** — Contains a single file,
  `.vscode/settings.json`, holding only a Python-environment/interpreter
  association (`python-envs.pythonProjects` pointing `envManager`/
  `packageManager` at the local venv). No repo-root `.gitignore` exists (the
  only `.gitignore` in the tree is under `.venv/`), so the directory is
  genuinely untracked rather than intentionally excluded — but it is pure
  editor configuration with no framework or code content. Confirmed against
  `~/.claude/commands/cut-release.md` line 37, which explicitly instructs
  ignoring "stray editor dirs like `.vscode/`" when checking for uncommitted
  changes before a release — so the existing tooling's treatment of this
  directory as noise still holds.

- **Break check** — `python3 scripts/check_plugins.py` from the catalyst
  root **fails**:
  ```
  Plugin rule validation failed:
  - plugin submodule is not initialized or checked out
  ```
  This is a **false positive caused by a real bug** in
  `scripts/check_plugins.py`'s `validate_plugin_sources()` (lines 62–71): it
  greps for the literal substring `plugins/repository/catalyst-git` anywhere
  in `git status --short` output and, if found, unconditionally reports
  "not initialized or checked out" — without inspecting the actual porcelain
  status code. The submodule *is* initialized and checked out (files
  present, `HEAD` resolvable, `git log` works); it merely shows ` M` because
  its pointer has moved ahead of the superproject's committed gitlink,
  which is the exact benign interim-development scenario described above.
  Before this cycle's submodule bump, `git status --short` had no entry for
  the submodule path and the check passed; the bump is what surfaced the
  bug, but the bug itself pre-dates this diff and will misfire on *any*
  modified (not just uninitialized) submodule state.

## Impact

**Low.**
- The submodule pointer divergence itself is benign, expected
  interim-development state; the catalog pin is still correct for the last
  actual release and needs no change.
- The `.vscode/` directory has no bearing on framework items or code
  correctness and is already treated as ignorable noise by existing release
  tooling.
- The `check_plugins.py` failure does not reflect an actual break in the
  repository or the submodule — it's a pre-existing false-positive bug in
  the validation script's logic, incidentally triggered by this cycle's
  submodule bump. It is not "severe/high-impact" in the sense of the
  working contract (nothing is actually broken), but it is a genuine code
  defect worth fixing since it will produce misleading failures on every
  future normal submodule pointer bump until corrected.

## Action needed

- Fix `validate_plugin_sources()` in
  `/Users/oliviersteck/sources/catalyst/scripts/check_plugins.py` to
  distinguish a genuinely uninitialized/missing submodule (e.g. an empty
  working tree or a porcelain code indicating deletion) from a merely
  modified/advanced submodule pointer (porcelain code ` M`), so the check
  doesn't false-positive on normal interim development.
- Push the submodule's local `development` commit (`4bc76a6`) to
  `origin/development` before the superproject's pending gitlink change for
  `plugins/repository/catalyst-git` is committed, so the pinned commit
  remains resolvable from a fresh clone.
- No action needed for `.vscode/`.
