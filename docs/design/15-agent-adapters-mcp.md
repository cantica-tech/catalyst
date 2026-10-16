# 15 — Agent adapters at user level: `catalyst mcp` (2026-10-09)

> **Owner decision, 2026-10-09.** "I need catalyst to be agnostic as possible: there should be something comparable
> with copilot or other models. Also, let's make sure that this plugin does not cross over to ui and the software
> engineering module" — then "OK, let's do it". Follows the requirement of `13` §9: catalyst writes no project file
> but `catalyst.toml`. Roadmap item **R3.1c** (`06`).

## 1. The problem

Today an install writes agent wiring into the project: `.claude/commands/*.md` (one per command of the composed §4)
and the `catalyst hook start|stop` hooks in `.claude/settings.json`. Both break `13` §9, and both are Claude
Code-only: another agent gets nothing comparable.

## 2. The design: three layers

| Layer | What | Agent-specific? |
|---|---|---|
| 1. CLI | `catalyst spec`, `check`, `task`, `hook`, views, writing verbs — exists | no |
| 2. `catalyst mcp` | a stdio MCP server inside `catalyst.pyz`, stdlib only. **Prompts** — one per command of the project's composed `CODE-OF-CONDUCT.md` §4, read at connection time, so a module's commands reach the agent without any adapter naming them. **Tools** — the deterministic verbs. **Instructions** — the invariants. The project is found from the client's roots (else the server's cwd), then its `catalyst.toml` | no |
| 3. Adapters | registered once per machine at **user level**: the MCP server, plus session-start / end-of-turn hooks where the agent has them. Kept under `agents/<agent>/` in the kernel | yes, but thin |

An agent without hooks still has the commit-msg hook (opt-in) and CI's `catalyst trace` as enforcement.

## 3. Boundaries (owner: no crossover)

- **Kernel-only.** `catalyst mcp` and every adapter live in the kernel and name no module entity or command:
  module commands exist for an agent only because the deployment's composed §4 lists them. The software-engineering
  module keeps contributing its §4 section and `Taskfile.module.yml`, nothing agent-specific.
- **No UI coupling.** The UI neither ships nor installs an adapter and the adapters do not depend on the UI. The UI
  keeps reading the composed §4 / calling the CLI; it may later be one more MCP client.
- `/dogfood` stays in catalyst's own `.claude/commands/`: it develops catalyst, it is not installed by it.

## 4. Per-agent facts

### Claude Code (verified 2026-10-09: documentation + live sessions, Claude Code 2.1.273)

| Fact | Finding |
|---|---|
| User-level MCP | `claude mcp add --scope user …` (stored in `~/.claude.json`), or a plugin's `mcpServers` |
| Plugin at user scope | `/plugin install <name>@<marketplace> --scope user` → `enabledPlugins` in `~/.claude/settings.json`; nothing in the project. A plugin bundles MCP servers and hooks |
| Where the server starts | not in the project: the project is in `CLAUDE_PROJECT_DIR`; Claude Code also answers `roots/list` (launch directory + added directories) — both used by `catalyst mcp` |
| Protocol | the client asks `2025-11-25` |
| Instructions | reach the model (checked live: it quoted INV-4) — so no SessionStart hook is needed |
| Prompts as commands | plugin server: `/mcp__plugin_catalyst_catalyst__<command>` (checked live); user-scope server: `/catalyst:<command> (MCP)` or `/mcp__catalyst__<command>` |
| Prompt arguments | split on whitespace and given to the declared arguments in order: one declared argument receives only the first word (checked live) |
| Tool | `mcp__plugin_catalyst_catalyst__catalyst`; it ran the project's own pinned catalyst through the launcher (checked live) |
| Stop hook | exit 2 blocks the stop (up to 8 times in a row) |

### Other agents (documentation and source, 2026-10-09; not run live — none installed here)

| Agent | User-level MCP | Prompts as `/commands` | Project known to the server | Instructions reach the model | Hooks (user level) |
|---|---|---|---|---|---|
| Copilot in VS Code | profile `mcp.json` (`servers`) | yes (`/mcp.<server>.<prompt>` or `/<server>.<prompt>`) | roots + cwd = workspace | yes (1.104+) | preview: `~/.copilot/hooks/*.json` |
| Copilot CLI | `~/.copilot/mcp-config.json` | **no** (issues #505, #1518 open) | unreliable | partly (filtered by default) | GA: `~/.copilot/hooks/*.json`, `sessionStart`, `agentStop` (`decision: block`) |
| Cursor | `~/.cursor/mcp.json` | yes, likely `/<prompt>` | roots "supported", content unknown; cwd not the project | unknown | `~/.cursor/hooks.json`; input has `workspace_roots`; stop → `followup_message` |
| Codex CLI | `[mcp_servers.<name>]` in `~/.codex/config.toml` | **no** (never calls prompts) | no roots; cwd = the project | as the tools' namespace description | `~/.codex/hooks.json` (Claude-style), Stop → `decision: block` |
| Gemini CLI | `~/.gemini/settings.json` | yes, `/<prompt>` | roots (all workspace dirs) | yes | `hooks` in settings.json; `AfterAgent` → `decision: deny`. **No MCP server at all in an untrusted folder** |

## 5. Decisions taken from the facts (2026-10-09)

- **Commands without prompts.** Copilot CLI and Codex show no MCP prompts, so the server also has a `command` tool
  (a command's procedure, or the list); its instructions tell the agent to use it when the user names a command.
- **Finding the project.** Roots first, then `CLAUDE_PROJECT_DIR`, then the server's cwd; every tool also takes the
  agent's `cwd`. Hooks take the project from their input (`cwd`, Cursor's `workspace_roots`).
- **Arguments.** Claude Code splits typed arguments on whitespace over the declared ones: it gets 16 word slots,
  joined back; other clients get one `arguments` field.
- **Hooks speak each agent's format:** `catalyst hook stop --format exit2|json|gemini|cursor`,
  `hook start --format text|json|cursor`. Session-start invariants are installed only where the server's
  instructions may not reach the model (Copilot, Cursor).
- **One installer:** `catalyst agent install|uninstall|status <agent>` writes only the agent's user-level files,
  backs each up once, never rewrites a file with comments (prints the snippet), and finds its entries again by the
  launcher path. For Claude Code it uses `claude mcp add --scope user` (commands read `/catalyst:<command>`) — the
  plugin in `agents/claude-code/plugin` is the same wiring for a marketplace, with longer command names
  (`/mcp__plugin_catalyst_catalyst__<command>`).
- **Version per project.** The server runs the newest runtime; its `catalyst` tool runs each project's pinned
  version through the launcher (checked live on a second deployment).

## 6. Plan

1. ✅ `catalyst mcp` (prompts, `catalyst` and `command` tools, instructions; roots) with tests; live in Claude Code.
2. ✅ Claude Code adapter: `catalyst agent install claude-code`, and the plugin.
3. ✅ Copilot (CLI, VS Code), Cursor, Codex, Gemini: `catalyst agent install <agent>`; hook formats. Not yet run in
   those agents.
4. ✅ `catalyst init` writes no command files or hooks; `catalyst sync apply` retires the ones an older catalyst
   wrote (unedited command files removed, edited ones reported, catalyst's hooks taken out of
   `.claude/settings.json`); `check_command_parity.py` checks only the Taskfile and the module's commands against §4;
   kernel releases ship no `commands/`; the software-engineering module drops its `commands/` and `spec_path`;
   migration `0.49.0/agents-at-user-level.md`. The UI reads the commands from the composed §4 and asks the agent to
   run them through the MCP server.
5. ✅ Installed on the owner's machine (`catalyst agent install claude-code`, 2026-10-09). Open: release 0.49.0 (and
   the module), then sync the UI and catalyst's own deployment to retire their `.claude/commands/` and hooks.

Open questions: content-contributing **plugins** still deploy command files into `.claude/commands/` (INV-22,
Rules-of-Rules §17) — no plugin is activatable today; their commands should reach agents the same way (§4 or the
MCP server) before one is. A `DEFINITION-SLASH-COMMAND-v2` should describe a command served by `catalyst mcp`.
