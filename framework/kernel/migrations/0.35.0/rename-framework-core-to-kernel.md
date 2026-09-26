# Migration 0.35.0: the kernel

> Apply this migration when synchronizing a deployment whose `version.txt`
> is being advanced to `0.35.0` or later. See `SYNCHRONIZE.md` for the full
> synchronization procedure.

The module-independent part of the catalyst framework is now called **the
kernel**. The framework is the kernel plus its process modules
(`INVARIANTS.md` INV-3, `MODULE-SPECIFICATION.md`).

## What changed

1. **Kernel folder.** In the catalyst repository, every kernel file moved from
   `framework/` to `framework/kernel/` (guides, templates, definitions,
   schemas, migrations, plugins). `framework/modules/` stays a sibling. Paths
   such as `framework/INVARIANTS.md` are now `framework/kernel/INVARIANTS.md`.
2. **Kernel version.** The root `version.txt` is the kernel version. The
   `<app-name>.catalyst` pointer field `framework_version` is renamed
   `kernel_version`.
3. **`/sync-kernel`.** `/sync-framework` is renamed `/sync-kernel`.
   `/sync-framework` stays as an alias, the same way any command alias in
   `CODE-OF-CONDUCT.md` §4 works.
4. **Module manifests.** A module release's `manifest.json` declares its
   compatible kernel as `kernelVersion` (was `frameworkVersion`). Readers
   accept both names.
5. **Kernel release.** The kernel ships as
   `catalyst/kernel/v<version>/kernel-v<version>.zip` (manifest id
   `catalyst-kernel`) instead of `catalyst/framework/v<version>/framework-v<version>.zip`.
6. **Modules are full repositories.** A production module is no longer a
   catalyst submodule. Each lives in its own repository, checked out next
   to catalyst as `catalyst-<module-id>/`, which the release task
   (`scripts/package_release.py`) and module loader read from.

## Steps for deployed projects

1. **Pointer.** In `<app-name>.catalyst`, rename `framework_version` to
   `kernel_version`, keeping its value until step 5.
2. **Command spec.** Refresh `.criterion/CODE-OF-CONDUCT.md` §4 from
   `framework/kernel/rules-of-development.template.md`: the `/sync-kernel`
   bullet (with its `/sync-framework` alias) and its behavior paragraph.
3. **Command files.** Add `.claude/commands/sync-kernel.md` from
   `framework/kernel/templates/slash-command.template.md`, and turn the
   existing `sync-framework.md` into its alias.
4. **Taskfile.** Refresh `.criterion/Taskfile.common.yml` from
   `framework/kernel/templates/Taskfile.common.template.yml`: add the
   `sync-kernel` task and keep `sync-framework` as its alias.
5. **Version.** Set `.criterion/version.txt` and the pointer's
   `kernel_version` to `0.35.0`.
