# 0.84.0 — Configurable four-eyes analysis

From `0.83.x` to `0.84.0` (owner decision B5).

## What changes

- `catalyst analysis start --passes 1|2` chooses the number of independent passes of one analysis; `catalyst.toml`'s
  optional `analysis_passes` (`1` or `2`) sets the deployment's default. Without either, two: four-eyes stays the
  default.
- An analysis records its number in its `Passes` field and in `inventory.json` (`passes`). A single-pass analysis
  refuses pass B; `diff` treats each of pass A's findings as found by one pass, so each finding it keeps says how it
  was verified against the code, and the user decides each one.
- An analysis started before 0.84.0 has no `passes`: it is read as two, as it was.
- The analysis template gains the `Passes` row; `/run-analysis` takes `--passes 1|2`.

## Steps

1. `catalyst sync apply --kernel <0.84.0>`: the CLI, the runtime and the recomposed documents.
2. **Judgment:** if the deployment keeps `analyses/templates/`, add the kernel's `templates/analysis.template.md` as
   its next version (`TEMPLATE-ANALYSIS-v<N+1>.md`) with a row in `templates-analysis.md`, journaled; never edit an
   earlier version (L6).
3. **Judgment, only if the owner asks:** set `analysis_passes = 1` in `catalyst.toml` to make single-pass the
   deployment's default. Nothing changes otherwise.
4. `catalyst check`. Existing analyses are untouched.
