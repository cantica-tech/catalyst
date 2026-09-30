# Migration 0.44.0: four-eyes analysis of existing code

> Apply this migration when synchronizing a deployment whose `version.txt`
> is being advanced past `0.43.0` to `0.44.0` or later. See `SYNCHRONIZE.md`
> for the full synchronization procedure. Never re-run on a later sync once
> applied.

Until `0.43.0`, `/run-analysis` pointed at an `ANALYSIS-PLAYBOOK.md` "in
the project root" that no deployment had: the playbook shipped in the
kernel release but was never deployed. From `0.44.0` the analysis of
existing code is a process the CLI enforces.

## What changed

1. **The `ANALYSIS-` kernel entity** (`analyses/`): one record per
   analysis — scope, mode (`bootstrap` / `incremental`), the product commit
   analysed, and its reports in `analyses/reports/<ID>/`: the inventory,
   two independent passes, their diff, the reconciliation, the decisions.
2. **`catalyst analysis`** (`CLI.md`): `start`, `record --pass A|B`, `diff`,
   `reconcile`, `decide`, `close`, `abandon`, `status`. Each phase refuses
   to skip the one before; `catalyst check` rejects a record whose reports
   do not support its phase.
3. **`/run-analysis [<path>...] [--bootstrap|--incremental]`** runs it:
   two blind passes, a reconciliation accounting for every finding, and the
   user's decision on each domain, rule and defect before any artifact is
   written.
4. **`.criterion/ANALYSIS-PLAYBOOK.md`**: the phases, the prompts and the
   findings format, deployed and refreshed with the kernel.

## Steps for every deployment

1. **Add the entity folder.** Create `analyses/` with a `README.md`, the
   index `analyses.md` (`# Analyses index` and an empty
   `| ID | Title | Status |` table), and `templates/` holding
   `TEMPLATE-ANALYSIS-v1.md` (the kernel's `templates/analysis.template.md`),
   its `README.md` and the catalog `templates-analysis.md` — the shape of
   every entity folder (INV-20).
2. **Add the definition.** Copy the kernel's
   `definitions/analysis/DEFINITION-ANALYSIS-v1.md` to
   `definitions/analysis.md` (INV-23).
3. **Deploy the playbook.** Copy the kernel's `ANALYSIS-PLAYBOOK.md` to
   `.criterion/ANALYSIS-PLAYBOOK.md`. Every later `/sync-framework`
   replaces it with the release's.
4. **Refresh the kernel files.** Recompose `CODE-OF-CONDUCT.md` and
   `Taskfile.common.yml` with `catalyst recompose` from the previous
   kernel (leave anything listed in `.frozen` alone): §4 gains the
   `/run-analysis` arguments and procedure. Replace the `/run-analysis`
   command file with the release's.
5. **Re-vendor the CLI.** Replace `.criterion/bin/catalyst.pyz` with the
   release's; check that `python3 .criterion/bin/catalyst.pyz analysis
   --help` works.
6. **Version.** Set `.criterion/version.txt` and the pointer's
   `kernel_version`.
7. **Journal and check.** One `catalyst journal append --command
   /sync-framework --action sync --artifact "kernel <version>" --file …`
   entry for every touched file, then `catalyst check`.

A shared deployment lands the working-copy changes as one pull request
(`catalyst criterion push`); the command file is a product-repository
change.

## Rollback

Remove `analyses/`, `definitions/analysis.md` and
`.criterion/ANALYSIS-PLAYBOOK.md`; restore the previous kernel files,
command file, CLI and `version.txt`. No other artifact refers to an
`ANALYSIS-` record unless the deployment ran one.
