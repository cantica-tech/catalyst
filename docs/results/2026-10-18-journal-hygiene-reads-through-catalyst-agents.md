# Results — 2026-10-18: journal hygiene, the UI reads through catalyst, three agents run commands

Work that needed nothing from the owner while the signing keys wait. All of it is released on GitHub except kernel
0.89.0, whose release PR was in CI when this was written.

| Release | What's in it |
|---|---|
| Kernel [0.88.0](https://github.com/cantica-tech/catalyst/releases/tag/0.88.0) | A warning for journal commands the deployment doesn't have; the deployed definitions served |
| Kernel 0.89.0 | `catalyst agent run` runs GitHub Copilot and Gemini CLI; changes record their tier |
| The UI 0.53.0 (its own repository) | The desktop app for macOS, Windows and Linux, attached to the release; the UI reads through catalyst |

## 1. Journal hygiene (R4.8)

- `catalyst journal append` warns when `--command` is none of the deployment's commands, a `catalyst <verb>` or a
  tier's name; the entry is still written. The audit had found 66 entries naming commands no deployment has.
- A writing verb (`new`, `status set`, `link`, `rename`, `restore`) run without `--tier` records the tier its
  artifact's type opens, when exactly one tier names that type. 27% of catalyst's entries had no tier.
- Still open: short placeholder intents and repeated `/status` entries.

## 2. The UI reads through catalyst (R5.3)

- The VS Code command picker takes the commands from `catalyst spec --json`.
- Users, roles and definitions come from `catalyst serve` (`GET /v1/definitions` is new in 0.88.0); an older
  catalyst that doesn't serve definitions gives none rather than failing the read.
- Deleted from the UI: the module loader, the IAM and definition file readers, `parseFieldTable`, three unused
  markdown helpers and the 450-line test fixture writer.

## 3. Three agents run commands (decision B2)

`catalyst agent run` now runs GitHub Copilot (`copilot -p`) and Gemini CLI (`gemini -p`) beside Claude Code. What
they print is passed on as text, and the run is `ok` when the agent exits 0. They report no tool calls, usage or
cost, so their end event says `measured: false` instead of claiming zeros. Neither CLI is installed on this
machine: the adapters were tested with a stand-in process.

## 4. The desktop app's first release

Publishing UI 0.53.0 ran the `Desktop` workflow's release path for the first time: all three builds passed and 11
files are attached to the release (macOS DMG and ZIP for both chips; Windows installers for x64, arm64 and both;
Linux AppImage and `.deb` for both architectures). They are unsigned until the keys exist.

## Problems along the way

- The purity check caught a docstring naming a module's command in the kernel; reworded.
- A criterion PR was merged before its check had started; the check then failed only because the PR's merge ref
  was gone, and its content passes `catalyst check` locally. Merges now wait for that check to start.

All tests pass: 693 in the kernel, every UI package. Not tried by a person: the desktop installers, the two new
agent adapters with the real CLIs.

## Waiting on the owner

- The Windows (Azure) and macOS (Apple) signing credentials, a public address for the Linux package's maintainer,
  and the auto-update feed's choice (see the UI repository's `docs/desktop.md`).
- R6.29 (sandboxed module UI) and R6.21 (brand) need decisions.
