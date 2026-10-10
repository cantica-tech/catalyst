# Migration 0.52.0: the laws and the handbook

> Apply this migration when synchronizing a deployment whose `version.txt`
> is being advanced past `0.51.x` to `0.52.0` or later. See `SYNCHRONIZE.md`
> for the full synchronization procedure. Never re-run on a later sync once
> applied.

Until `0.51.x` a deployment's agent was expected to obey about 184 KB of rule
text: 25 invariants restated in several places, a 66 KB `Rules-of-Rules.md`
and a 51 KB `CODE-OF-CONDUCT.md`, much of it describing the model before the
home store (symlinks, submodules, pointers, `/project`), plugins, or what the
CLI already enforces. From `0.52.0` (roadmap R4.1, R4.2; ADR-018):

## What changed

1. **The ten laws.** `INVARIANTS.md` opens with ten laws an agent must judge,
   then a marker, an index (each invariant, its law, what enforces it) and
   every invariant in full. A session loads only the laws (`catalyst hook
   start`, the MCP server's instructions); `catalyst why <L3|INV-17|rr-META-012|ID>`
   explains the rest. The active module adds at most three laws of its own
   (software engineering: SE-L1, the tier decides the artifact). INV-19 is
   retired; INV-10 to INV-13 and INV-22 are parked with the plugins.
2. **The handbook.** `rules/Rules-of-Rules.md` holds every judgment rule,
   deduplicated (about 13 KB with the module's part). Every meta-rule keeps
   its ID; rr-META-008 and -017 (plugins) are parked placeholders, rr-META-018
   (the recreation drift check) is catalyst-development only.
3. **The command catalogue.** `CODE-OF-CONDUCT.md` is §4 — the commands, read
   one at a time by `catalyst spec` and the MCP prompts — with §1–3 and §5–9
   pointing into the handbook.
4. **Commands.** `/share info|status|pull|push|create|join` replaces
   `/criterion`; `/project create|remove|export|import` and `/switch-agent`
   are gone (`catalyst init` on request; `catalyst open --agent`);
   `/catalyzer` is parked. The `Taskfile.common.yml` tasks follow.
5. **`catalyst reconcile <RECON-id> <verb>`** enforces the reconciliation role
   gate (INV-21); the reconciliation type gains `Resolved-Accepted-with-Edits`.

## Steps for every deployment

1. **Synchronize** with `catalyst sync plan|apply --kernel <0.52.0 release>
   --module <the active module's matching release>`: it recomposes
   `Rules-of-Rules.md`, `CODE-OF-CONDUCT.md` and `Taskfile.common.yml` and
   copies the new `INVARIANTS.md`. A local edit to those documents is
   reported as a conflict: most local edits were to text this release
   removes — keep what still applies by moving it into a rule document.
2. **Tell the users** of the deployment: `/criterion …` is now `/share …`,
   and `/project …` and `/switch-agent` are gone.
3. **Scripts or tools** that run `/criterion` (an editor extension, a CI job)
   switch to `/share`, and those that read `INVARIANTS.md` for the session
   read its brief (up to the marker) or call `catalyst why`.
