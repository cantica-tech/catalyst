# 21 — `catalyst module install` (R4.9 design note for the owner, 2026-10-13)

> **Status: decided (owner, 2026-10-13).** All seven decisions as recommended: the record in the criterion
> (`modules/modules.json`); the tree hash recorded and verified; directory, zip and git URL; tiers as a union, one
> grounding type, laws per module, install order; N3 now with `sample-process`; no removal; `init --module` stays.
> **N1 released** (kernel 0.58.0, 2026-10-13, REQ-000027); **N2 released** (kernel 0.59.0, 2026-10-13, REQ-000028): `module install\|upgrade`, `init --no-module`, a git repository as a source; its Windows run found a line-ending defect, fixed before the tag. **N3 released** (kernel 0.60.0, 2026-10-13, REQ-000029): several modules in one deployment, with the collisions refused. R4.9 is done but for N4 (signatures, with R7).
>
> Was: draft for the owner. R4.9 asks for `catalyst module install|list|verify|upgrade` and several modules per
> deployment. A plan exists (`docs/plans/r4-9-module-install.md`, 2026-10-08). It was written before the home store
> (`13`), `catalyst.toml`, module format 3 and namespaces (`20`), and `sync plan|apply`. This note measures where
> kernel 0.57.1 stands against that plan, keeps what still holds, and lists the decisions to take before building.

## 1. Where things stand

| What the plan needs | Kernel 0.57.1 |
|---|---|
| One seeding path | **Missing.** `init` seeds the module inline (`init.py`, about 250 lines: copy into `modules/<id>/`, entity folders, templates, definitions, composed documents). `sync apply --module` replaces the module tree by its own code. Two paths. |
| A record of what is installed | **Partly.** `catalyst.toml` has `module = "<id>"`; `modules/<id>/manifest.json` has id, version and kernel range. No source, no hash, no commit. |
| A module's integrity checked | **Partly, by another route.** `init` and `sync` journal every module file, so `check` reports a module file edited by hand as `unjournaled`. Nothing compares the tree with what the release published. |
| Install into an existing deployment | **Missing.** A module arrives at `init` or through `sync --module`, which only replaces the module already there. |
| Sources | `init`: a directory. `sync`: a directory or a release zip. No git URL. |
| Several modules | **Missing, and wide.** `Deployment.module` is one manifest (16 uses); `compose` takes one module; the working copy's CI loader gives up when `modules/` holds two; tiers, grounding and the module law come from "the" module. |
| What several modules need from R4.3 | **Done.** Format 3, a namespace per module (`rr-<NS>-`, `INV-<NS>-`), generated commands, and `sample-process` as a second module in the tests. |
| Upgrade through `sync` | **Done.** `sync plan\|apply --module`, the kernel range enforced, and since 0.57.1 the shared gate's kernel checked. |

Two lines of the plan no longer hold: its step 6 records into `.catalyst/catalyst.toml` (the file is `catalyst.toml` at
the project root, `13`), and its tests name Python 3.9 (the floor is 3.11).

## 2. What changes, in steps

| Step | Content | Release |
|---|---|---|
| N1 | **One seeding path and a record.** The seeding moves out of `init` into one function that `init` and `sync` both call; no behaviour change. Every install and sync writes the record: id, version, source, commit when known, and the hash of the shipped tree. `catalyst module list` and `module verify`; `check` runs `verify`. | kernel 0.58.0 |
| N2 | **`module install` for the first module, and `module upgrade`.** `install <path\|zip\|git-url>[@ref]` into a deployment that has none; `init --module` becomes `init` then this. `upgrade <id> [<ref>]` plans and applies through `sync`. A git URL is cloned shallow into a temporary directory. | kernel 0.59.0 |
| N3 | **Several modules.** `Deployment.modules` is a list; `compose` takes it; collisions are refused before anything is written (entity types, prefixes, folders, namespaces, command names); `check`, parity and purity run per module; a second module installs beside the first. | kernel 0.60.0 |
| N4 | **Signature** of a release, checked at install, once the release feed exists. | with R7 |

N1 and N2 need nothing new decided beyond §3. N3 is where the cost is: about 16 call sites, `compose`, the standalone
loader the CI gate uses, and four questions of meaning (§3, decision 4).

## 3. Decisions for the owner

1. **Where the record lives.** In the criterion, as `modules/modules.json` (recommended), or in `catalyst.toml` as the
   plan says. The criterion is what is shared and what the gate checks; a second contributor and the CI gate have no
   use for a record in one checkout's project file. `catalyst.toml` keeps `module = "<id>"` for one minor, then a
   list of ids.
2. **What the hash is for.** `check` already catches a hand-edited module file through the journal. The tree hash
   adds one thing: that what was installed is what the release published. Recommended: record it, compare it with the
   release's manifest when the source carries one, and have `verify` recompute it. Or drop the hash and rely on the
   journal until signatures (N4).
3. **Sources.** A directory, a release zip and a git URL with a ref (recommended, in that order of work), or
   directories and zips only until the release feed exists.
4. **What several modules mean**, for the four things one module decides today:
   - *Tiers*: the union of the modules' tiers; two modules declaring the same tier id with different artifacts is a
     collision (recommended).
   - *Grounding*: every module in a deployment grounds on the same type (`rule`) (recommended), or each its own.
   - *Laws*: each module adds its own, at most three each, as today.
   - *Composition order*: install order, after the kernel's (the plan's rule, kept).
5. **When N3 is built.** Now, with `sample-process` as the second module in the tests (recommended if R6's module
   administration, R6.24, is wanted soon), or when a second real module exists (the R7 pilot). N1 and N2 are worth
   having either way: they remove the second seeding path and give `init` and `sync` one record.
6. **Removing a module** stays out of scope (the plan's position): its artifacts would need retiring or migrating.
7. **`init --module` stays** as the one-command install (recommended: it calls `init` then `module install`
   internally), or installing becomes two commands.
