# Instantiation Guide

How to stand catalyst up in a project, new or existing. Only on the user's
explicit request (law L8). `catalyst init` does everything mechanical
(`CLI.md` lists what it writes, `ARTIFACT-LAYOUT.md` shows the tree); this
guide is the judgment it leaves to the agent. Work it from
`INSTANTIATION-CHECKLIST.md`, its tickable form.

## 1. New project

1. **Rule documents.** One per natural seam of the project (UI and backend,
   or one per service), each with a short lowercase prefix:
   `--rule-doc <file>:<prefix>` (e.g. `business-rules:br`). With none,
   `init` creates `<name>-rules.md` with prefix `br`.
2. **Project name.** A project-local `dev-instructions.yaml`'s `name`
   (`name: "project-name"`, a plain identifier) if present, deleted after a
   successful install; else ask, defaulting to the repository's name. An
   old `layout` key in it is not applied: say so.
3. **The other inputs.**
   - The active module (`--module <id>`): no default. `init` without it
     lists the modules checked out next to the project or catalyst as
     `catalyst-<id>` (`framework/modules/catalog.md`); propose one and ask.
     Elsewhere: `--module-dir <dir>`, a checkout at the release matching
     this kernel.
   - The catalyst-users provider people sign with: `--identity-issuer
     <url>` (default: this machine's catalyst-users), asked. The installer
     logs in first (`catalyst identity login --issuer <url>`).
   - The agent (`--agent <id>`), and optionally where tests live
     (`--test-locations`; on the greenfield path, from the testing
     decision, §3).
4. **Run `catalyst init`** from the project root. It refuses where catalyst
   is already installed, commits nothing in the project, and adds only
   `catalyst.toml` to it.
5. **Wire the agent**, once per machine: `catalyst agent install <agent>`
   (user level only). Never write command files, hooks or a `Taskfile.yml`
   into the project; `catalyst task <command>` runs the criterion's tasks.
   Offer `catalyst hook install` (the commit-msg check) and, with CI, a
   `catalyst trace` step (`CLI.md`); run either only on the user's yes, and
   leave an existing `commit-msg` hook for the user to merge.
6. **What the module requires.** A document the module requires at
   instantiation that still holds `{{PLACEHOLDER}}` text is filled by the
   command the module names.
   **People, roles and landing**, together: roles and groups in
   catalyst-users (`roles provision`, `criteria add`), then the landing
   policy (design 33): recommend `standard`, run `catalyst landing init
   --policy <chosen>`; its entry is the Admin's assent.
7. **Landing page.** Extend the root `README.md` stub with the project's
   rule and workflow structure, linking each folder's `README.md`.
8. **First content**, on the path that fits: greenfield (§3) or retrofit
   (§4). The active module's meta-rules say which starter artifacts to
   create; tie each to concrete screens, flows or components. Allocate
   rule IDs with `catalyst id next-rule <prefix> <DOMAIN>`; journal every
   change (`catalyst journal append`).
9. **Finish with `catalyst check`**: no errors (report the warnings).
   Present the deployed tree; nothing is committed or pushed without the
   user's yes (law L3).

## 2. Choosing your agile flavor

Work items are a module's types (ADR-022); without them the chain starts at
the active module's artifacts. The kernel requires only that no work starts
without a targeted rule (`CODE-OF-CONDUCT.md` §1).

## 3. Greenfield path — no existing code or practices

The toolchain is decided as rules before the first line of application
code, so the codebase is born governed.

1. Add a dev-environment rule document to step 1 (e.g.
   `--rule-doc dev-environment-rules:env`), and install first.
2. With the user, one domain per decision area, the domain file before its
   rules (`Rules-of-Rules.md` §7): runtime and language, dependency policy,
   code style, testing (which gives `{{TEST_LOCATIONS}}` in
   `Rules-of-Rules.md` §2), CI/CD, local dev environment, repository
   layout. Skip what does not apply; add what the project needs.
3. Implement each rule in the same pass (the real config files); its
   "tested" bar is that the tool runs clean on the scaffold.
4. This document stands in for the starter artifacts of §1 step 8. Real
   application code is then ordinary work against a business or UI rule
   document.

## 4. Retrofitting an existing project

1. Do not write every rule up front: gather them per functional area as you
   touch it, or bootstrap a first pass with `/run-analysis --bootstrap`
   (`ANALYSIS-PLAYBOOK.md`). A rule counts only once it passes the conflict
   check and is gathered, implemented, tested and documented
   (`Rules-of-Rules.md` §1–§2).
2. Keep what the project already practises; on a conflict, ask the user
   rather than choose.
3. Create each domain's file before its rules (§7); give existing prose
   bullets IDs in document order (`catalyst id next-rule`), sub-cases of
   one bullet as `-1`, `-2` suffixes.
4. Then open active-module artifacts for known issues and pending work,
   citing the rule IDs.

## 5. Keeping the two in sync

A process rule a project adds that would help every project is proposed
back to catalyst's templates, not kept as a local fork.

## 6. Remember the deployment target across sessions

With a persistent memory store, keep a short note: catalyst, the project,
`catalyst where`'s answer, the date. It is a convenience: `catalyst.toml`
and the criterion's `DEPLOYMENT.md` are the record, and `catalyst open`
reads them each session. Update the note rather than duplicating it.
