# Results — 2026-10-27: the UI 0.66.0, one Instance(s) view and a quiet start

The owner asked for three changes to the VS Code extension's sidebar: each instance listed by its name alone, no
"(Chain Inspector)" appended; one panel, **Instance(s)**, grouping every instance; and catalyst's settings opened
from one place, not from each instance. Then, asked what the extension shows when it starts, they found it too many
notifications and asked for that to be a second requirement, built after the first.

| What | Where |
|---|---|
| The UI 0.66.0: REQ-000068 (`vscode-INSPECTOR-000001` amended), STEP-000084 | the UI's repository, #184, #185 |
| The UI 0.66.0: REQ-000069 (`vscode-ONBOARDING-000001`, `vscode-ONBOARDING-000002`, `vscode-INSPECTOR-000001` amended), STEP-000085 | the UI's repository, #184, #185 |
| The two requirements, steps and amended rules | the UI's criterion, PR #115 (waits on the owner's approval) |

## 1. One Instance(s) view

VS Code nests no view inside another, and a button on the sidebar container itself is proposed API, closed to a
Marketplace extension. The owner chose one tree: the eight view slots became one view, **Instance(s)**, whose
top-level entries are the instances, each named exactly as the instance is and expanding into its sections. Open
Settings, Refresh, Switch UI Module, Send to Agent and Configure Criterion appear once, in its title bar. The cap of
eight instances is gone. Revealing the entity a detail panel shows (REQ-000017) still selects it under its instance.

## 2. A quiet start

What could appear unasked before: one notification per folder without catalyst, one per instance behind the
verified kernel, one for the restored UI module, one per instance catalyst cannot serve (again on every failed
refresh), and all of these again whenever trust was granted or `catalyst.ignoredFolders` changed. Now at most one
remains, the sync offer, when there is one:

- A folder with no catalyst is an Instance(s) entry, "no catalyst — set up…"; selecting it offers Set up catalyst…,
  Never offer here, Not in this workspace and Hide here.
- Every instance that can sync is named in one notification, offered once per session.
- The restored UI module is written to the Catalyst output channel.
- "catalyst cannot serve …" is notified once per instance per session, then only logged.

## Checks

- From a clean build: lint, format, typecheck, every package's tests (2 new for the sync offer's wording), the
  Studio's build; `catalyst check` on the UI's deployment, 0 errors.
- CI green on #184 and #185; tagged `0.66.0` on release; the `.vsix` published to the distribution repository.
- Not tried: the extension in a running VS Code. The tree, the set-up entry and the batched notification were not
  seen on screen.

## What's left

- The owner: approve criterion PR #115 (the landing policy needs a Criterion Admin's approval); look at 0.66.0 in VS
  Code; decide whether it goes to the Marketplace (never published without asking).
- Signed as the system account: nobody was logged in to the local Keycloak this session.
- catalyst-kb-engine and catalyst-knowledge-base are still on kernel 0.110.1, which reads `~/.catalyst-users`: keep
  the link until they are synced.
