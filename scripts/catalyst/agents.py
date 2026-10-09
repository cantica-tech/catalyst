"""`catalyst agent install|uninstall|status <agent>`: wire catalyst into an
agent at user level (roadmap R3.1c, what-is-going-on 15) — never in a project.

Each agent gets the `catalyst mcp` server (commands, CLI, invariants) and,
where its hooks need it, the end-of-turn check (`catalyst hook stop`) and the
session-start invariants (`catalyst hook start`), in the agent's own format.
Only the agent's user-level files are touched; catalyst's entries are found
again by the launcher path, so uninstall leaves everything else as it was.
A file is backed up once (`<file>.before-catalyst`) before catalyst first
changes it, and a file that is not plain JSON is never rewritten: its
snippet is printed for the user to add.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import project_file

AGENTS = ("claude-code", "copilot", "vscode", "cursor", "codex", "gemini")
SERVER = "catalyst"


class AgentError(Exception):
    pass


def launcher() -> str:
    bin_dir = project_file.home() / "bin"
    return str(bin_dir / ("catalyst.cmd" if os.name == "nt" else "catalyst"))


def _cmd(*args: str) -> str:
    path = launcher()
    return " ".join([f'"{path}"' if " " in path else path, *args])


def vscode_user_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Code" / "User"
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Code" / "User"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "Code" / "User"


@dataclass
class Change:
    file: Path
    path: tuple[str, ...]        # where in the JSON
    value: object                # what catalyst puts there (a dict entry, or list items)


def _hook(command: str, **extra) -> dict:
    return {"hooks": [{"type": "command", "command": command, **extra}]}


def changes(agent: str) -> list[Change]:
    """What `install` writes, per agent (JSON files; Codex's TOML aside)."""
    home = Path.home()
    server = {"command": launcher(), "args": ["mcp"]}
    if agent == "claude-code":      # the MCP server goes through `claude mcp add --scope user`
        return [Change(home / ".claude" / "settings.json", ("hooks", "Stop"), [_hook(_cmd("hook", "stop"))])]
    if agent == "copilot":          # Copilot CLI; its hooks directory is read by VS Code's agent too
        return [Change(home / ".copilot" / "mcp-config.json", ("mcpServers", SERVER),
                       {"type": "local", **server, "tools": ["*"]}),
                Change(home / ".copilot" / "hooks" / "catalyst.json", (), {"version": 1, "hooks": {
                    "sessionStart": [{"type": "command", "bash": _cmd("hook", "start", "--format", "json"),
                                      "powershell": _cmd("hook", "start", "--format", "json"), "timeoutSec": 30}],
                    "agentStop": [{"type": "command", "bash": _cmd("hook", "stop", "--format", "json"),
                                   "powershell": _cmd("hook", "stop", "--format", "json"), "timeoutSec": 120}]}})]
    if agent == "vscode":
        return [Change(vscode_user_dir() / "mcp.json", ("servers", SERVER), {"type": "stdio", **server})]
    if agent == "cursor":
        return [Change(home / ".cursor" / "mcp.json", ("mcpServers", SERVER), {"type": "stdio", **server}),
                Change(home / ".cursor" / "hooks.json", ("hooks", "sessionStart"),
                       [{"command": _cmd("hook", "start", "--format", "cursor")}]),
                Change(home / ".cursor" / "hooks.json", ("hooks", "stop"),
                       [{"command": _cmd("hook", "stop", "--format", "cursor")}])]
    if agent == "codex":            # the MCP server is a TOML table in config.toml (see _codex_toml)
        return [Change(home / ".codex" / "hooks.json", ("hooks", "Stop"),
                       [_hook(_cmd("hook", "stop", "--format", "json"))])]
    if agent == "gemini":
        return [Change(home / ".gemini" / "settings.json", ("mcpServers", SERVER), server),
                Change(home / ".gemini" / "settings.json", ("hooks", "AfterAgent"),
                       [_hook(_cmd("hook", "stop", "--format", "gemini"))])]
    raise AgentError(f"unknown agent '{agent}' (one of: {', '.join(AGENTS)})")


# --- JSON files ---------------------------------------------------------------
def _ours(item) -> bool:
    # the launcher's path as it reads inside JSON text (a Windows path's backslashes are escaped)
    return json.dumps(launcher())[1:-1] in json.dumps(item)


def _load(file: Path) -> dict:
    if not file.is_file():
        return {}
    try:
        data = json.loads(file.read_text(encoding="utf-8") or "{}")
    except ValueError as exc:
        raise AgentError(f"{file} is not plain JSON (comments?): {exc}") from exc
    if not isinstance(data, dict):
        raise AgentError(f"{file} does not hold a JSON object")
    return data


def _save(file: Path, data: dict) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    backup = file.with_name(file.name + ".before-catalyst")
    if file.is_file() and not backup.exists():
        shutil.copy2(file, backup)
    file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _apply(data: dict, change: Change, install: bool) -> dict:
    if not change.path:                                  # a file of catalyst's own
        return change.value if install else {}
    node = data
    for key in change.path[:-1]:
        node = node.setdefault(key, {}) if install else node.get(key, {})
        if not isinstance(node, dict):
            raise AgentError(f"{change.file}: '{key}' is not an object")
    last = change.path[-1]
    if isinstance(change.value, list):                   # hook entries: ours replaced, others kept
        kept = [item for item in node.get(last, []) if not _ours(item)]
        if install:
            node[last] = kept + change.value
        elif kept:
            node[last] = kept
        else:
            node.pop(last, None)
    elif install:
        node[last] = change.value
    elif _ours(node.get(last)):
        node.pop(last, None)
    return data


def _present(change: Change) -> bool:
    try:
        node = _load(change.file)
    except AgentError:
        return False
    for key in change.path:
        node = node.get(key) if isinstance(node, dict) else None
    return node is not None and _ours(node)


# --- Codex: a TOML table in config.toml ------------------------------------------
def _codex_toml() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "config.toml"


CODEX_TABLE = re.compile(r"^\[mcp_servers\.catalyst\]\n(?:(?!\[).*\n?)*", re.M)


def _codex(install: bool) -> str:
    file = _codex_toml()
    text = file.read_text(encoding="utf-8") if file.is_file() else ""
    table = f'[mcp_servers.catalyst]\ncommand = {json.dumps(launcher())}\nargs = ["mcp"]\n'
    stripped = CODEX_TABLE.sub("", text).rstrip("\n")
    new = (stripped + "\n\n" + table if stripped else table) if install else (stripped + "\n" if stripped else "")
    if new != text:
        file.parent.mkdir(parents=True, exist_ok=True)
        backup = file.with_name(file.name + ".before-catalyst")
        if file.is_file() and not backup.exists():
            shutil.copy2(file, backup)
        file.write_text(new, encoding="utf-8")
    return f"{file}: [mcp_servers.catalyst] {'set' if install else 'removed'}"


# --- Claude Code: the MCP server through its own CLI -------------------------------
def _claude_mcp(install: bool) -> str:
    claude = shutil.which("claude")
    if claude is None:
        return ("claude is not on PATH — add the server yourself: claude mcp add --scope user catalyst -- "
                f"{launcher()} mcp")
    subprocess.run([claude, "mcp", "remove", "--scope", "user", SERVER], capture_output=True, check=False)
    if not install:
        return "claude mcp: catalyst removed (user scope)"
    done = subprocess.run([claude, "mcp", "add", "--scope", "user", SERVER, "--", launcher(), "mcp"],
                          capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise AgentError(f"claude mcp add failed: {done.stderr.strip() or done.stdout.strip()}")
    return "claude mcp: catalyst added (user scope, ~/.claude.json)"


def _claude_mcp_present() -> bool | None:
    claude = shutil.which("claude")
    if claude is None:
        return None
    done = subprocess.run([claude, "mcp", "get", SERVER], capture_output=True, text=True, check=False)
    return done.returncode == 0 and launcher() in done.stdout


# --- the verbs ---------------------------------------------------------------------
NOTES = {
    "copilot": "VS Code's agent reads ~/.copilot/hooks too; register its MCP server with `catalyst agent install vscode`.",
    "gemini": "Gemini CLI connects to no MCP server in an untrusted folder: trust the project folder.",
    "codex": "Codex shows no MCP prompts: ask for a command by name, the agent uses the `command` tool.",
}


def run(agent: str, install: bool) -> list[str]:
    if not Path(launcher()).is_file() and install:
        raise AgentError(f"no launcher at {launcher()} — run `catalyst runtime install` first")
    lines = []
    grouped: dict[Path, list[Change]] = {}
    for change in changes(agent):
        grouped.setdefault(change.file, []).append(change)
    for file, group in grouped.items():
        try:
            data = _load(file)
        except AgentError:
            if install:
                snippet = {}
                for change in group:
                    _apply(snippet, change, True)
                raise AgentError(f"{file} cannot be rewritten (not plain JSON); add this yourself:\n"
                                 + json.dumps(snippet, indent=2)) from None
            raise
        for change in group:
            data = _apply(data, change, install)
        if not install and not data and file.is_file() and not group[0].path:
            file.unlink()
            lines.append(f"{file}: removed")
            continue
        if install or file.is_file():
            _save(file, data)
        lines.append(f"{file}: {'set' if install else 'cleared'} " +
                     ", ".join(".".join(c.path) or "(catalyst's own file)" for c in group))
    if agent == "codex":
        lines.append(_codex(install))
    if agent == "claude-code":
        lines.append(_claude_mcp(install))
    if install and agent in NOTES:
        lines.append(f"note: {NOTES[agent]}")
    return lines


def status() -> list[dict]:
    rows = []
    for agent in AGENTS:
        parts = {".".join(c.path) or c.file.name: _present(c) for c in changes(agent)}
        if agent == "codex":
            file = _codex_toml()
            parts["mcp_servers.catalyst"] = file.is_file() and bool(CODEX_TABLE.search(file.read_text(encoding="utf-8")))
        if agent == "claude-code":
            parts["mcp (user scope)"] = _claude_mcp_present()
        rows.append({"agent": agent, "installed": all(v for v in parts.values() if v is not None), "parts": parts})
    return rows
