# Plugin Activation Checklist

The tickable derivative of the `/catalyzer` activation flow, and the plugin-layer
counterpart to `framework/kernel/INSTANTIATION-CHECKLIST.md`. When activating
a plugin, work *this* list against a deployment ledger
(`framework/kernel/templates/ledger.template.md`), re-reading the plugin's
`working-contract.md` and `INVARIANTS.md` on the usual cadence.

A plugin's contract is exactly the kind of "loaded once at activation, decays over
a long run" artifact the anti-drift architecture protects — hence the re-ground
step and the machine checks below.

## Preconditions
- [ ] `framework/kernel/INVARIANTS.md` read this session (INV-10..INV-13)
- [ ] Activation was explicitly requested via `/catalyzer activate <name>` (INV-10)

## Structure (also enforced by `scripts/check_plugins.py`)
- [ ] Plugin directory carries `README.md` and `working-contract.md` (INV-10)
- [ ] Plugin is sourced from its own repository, not the framework repo (INV-11)

## Contract content (also enforced by `scripts/check_plugin_contracts.py`)
- [ ] All six metadata fields present: Name, Description, UUID, Version, Active, Type
- [ ] No leftover `<placeholder>` values in any metadata field
- [ ] `UUID` is a well-formed UUID and unchanged from any prior activation (INV-12)
- [ ] `Version` == the plugin's own `version.txt` == its `catalog.md` pin (INV-12)
- [ ] `Active` is a boolean; intended load state set/confirmed (INV-12)

## Load into context
- [ ] `working-contract.md` Scope + Responsibilities read into context before use
- [ ] Resolved runtime target = the deployed project's repository root — never the
      catalyst framework repo, never `plugins/<type>/<name>/` (INV-13); target
      recorded in the ledger
- [ ] If `working-contract.md` has a `## Contributes` section (a
      content-contributing plugin, INV-22): materialize the named
      artifact-type folder(s) (full INV-20 `templates/`+catalog
      treatment, templates resolved from the plugin's own repository or
      the named `plugins/_prototyping/` schema) and command file(s)
      (into `.claude/commands/`) — same mechanism first-load
      instantiation uses for core templates. Two content-contributing
      plugins of the same category must not both be active if they'd
      deploy the same artifact-type folder — refuse the second, point
      at deactivating the first.

## Re-ground (anti-drift)
- [ ] Re-read `working-contract.md` + `INVARIANTS.md` after any context compaction
      and every 5 ledger items, before continuing plugin work

## Definition of done
- [ ] Every item above `[x]` in the ledger; blocked items surfaced, not skipped
- [ ] `scripts/check_plugins.py` and `scripts/check_plugin_contracts.py` both pass
- [ ] No commit/push without explicit assent (INV-4)
