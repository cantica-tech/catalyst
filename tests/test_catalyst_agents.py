"""`catalyst agent`: catalyst in an agent's user-level configuration, never in
a project (roadmap R3.1c)."""
import json
from pathlib import Path

import pytest

from catalyst import agents
from catalyst.__main__ import main

PLUGIN = Path(__file__).resolve().parent.parent / "agents" / "claude-code" / "plugin" / ".claude-plugin" / "plugin.json"


@pytest.fixture
def home(tmp_path, monkeypatch):
    user = tmp_path / "user"
    user.mkdir()
    monkeypatch.setenv("HOME", str(user))
    monkeypatch.setenv("USERPROFILE", str(user))          # Path.home() on Windows
    monkeypatch.setenv("APPDATA", str(user / "AppData"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(user / ".config"))
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setenv("PATH", "")                    # never the real `claude`
    launcher = Path(agents.launcher())
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    return user


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_install_and_uninstall_keep_everything_else(home):
    settings = home / ".gemini" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"theme": "dark", "mcpServers": {"other": {"command": "x"}},
                                    "hooks": {"AfterAgent": [{"hooks": [{"type": "command", "command": "mine"}]}]}}),
                        encoding="utf-8")
    agents.run("gemini", install=True)
    agents.run("gemini", install=True)                # idempotent
    data = _json(settings)
    assert data["mcpServers"]["catalyst"] == {"command": agents.launcher(), "args": ["mcp"]}
    assert [h["hooks"][0]["command"] for h in data["hooks"]["AfterAgent"]] == [
        "mine", f"{agents.launcher()} hook stop --format gemini"]
    assert (home / ".gemini" / "settings.json.before-catalyst").is_file()
    assert [r for r in agents.status() if r["agent"] == "gemini"][0]["installed"]
    agents.run("gemini", install=False)
    assert _json(settings) == {"theme": "dark", "mcpServers": {"other": {"command": "x"}},
                               "hooks": {"AfterAgent": [{"hooks": [{"type": "command", "command": "mine"}]}]}}


def test_every_agent_installs_at_user_level(home):
    for agent in agents.AGENTS:
        agents.run(agent, install=True)
    rows = {r["agent"]: r for r in agents.status()}
    assert all(r["installed"] for r in rows.values()), rows
    assert rows["claude-code"]["parts"]["mcp (user scope)"] is None        # no `claude` on PATH
    hooks = _json(home / ".copilot" / "hooks" / "catalyst.json")["hooks"]
    assert "--format json" in hooks["agentStop"][0]["bash"]
    toml = (home / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert toml.count("[mcp_servers.catalyst]") == 1 and '"mcp"' in toml
    for agent in agents.AGENTS:
        agents.run(agent, install=False)
    assert not (home / ".copilot" / "hooks" / "catalyst.json").exists()
    assert "catalyst" not in (home / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert not any(r["installed"] for r in agents.status() if r["agent"] != "claude-code")


def test_a_file_that_is_not_plain_json_is_never_rewritten(home, capsys):
    mcp = home / ".cursor" / "mcp.json"
    mcp.parent.mkdir()
    mcp.write_text('{\n  // mine\n  "mcpServers": {}\n}\n', encoding="utf-8")
    assert main(["agent", "install", "cursor"]) == 1
    assert "add this yourself" in capsys.readouterr().err
    assert "// mine" in mcp.read_text(encoding="utf-8")


def test_the_claude_code_plugin_runs_what_the_installer_writes(home):
    plugin = _json(PLUGIN)
    assert plugin["mcpServers"]["catalyst"]["args"] == ["mcp"]
    stop = plugin["hooks"]["Stop"][0]["hooks"][0]["command"]
    assert stop.endswith("/.catalyst/bin/catalyst\" hook stop")
    assert agents.changes("claude-code")[0].value[0]["hooks"][0]["command"].endswith("hook stop")
