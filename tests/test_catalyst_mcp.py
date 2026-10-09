"""`catalyst mcp`: catalyst served to any agent over MCP (roadmap R3.1c)."""
import io
import json
import subprocess
import sys
from pathlib import Path

from catalyst.mcp import Server
from catalyst_fixtures import make_project, write
from test_catalyst_spec import COC

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _project(tmp_path):
    p = make_project(tmp_path)
    write(p / ".criterion" / "CODE-OF-CONDUCT.md", COC)
    write(p / ".criterion" / "INVARIANTS.md", "# Catalyst Invariants\n\n- INV-1 — be good.\n")
    return p


def _session(messages, cwd, launcher=None):
    reader = io.StringIO("".join(json.dumps(m) + "\n" for m in messages))
    writer = io.StringIO()
    Server(reader, writer, cwd, launcher=launcher).serve()
    return [json.loads(line) for line in writer.getvalue().splitlines()]


def _init(capabilities=None, client="test"):
    return {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": capabilities or {},
                       "clientInfo": {"name": client, "version": "0"}}}


def test_the_commands_of_the_composed_section_4_are_prompts(tmp_path):
    project = _project(tmp_path)
    out = _session([_init(), {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    {"jsonrpc": "2.0", "id": 2, "method": "prompts/list"},
                    {"jsonrpc": "2.0", "id": 3, "method": "prompts/get",
                     "params": {"name": "alpha", "arguments": {"arguments": "x1"}}},
                    {"jsonrpc": "2.0", "id": 4, "method": "prompts/get", "params": {"name": "nope"}}], project)
    init, listed, got, missing = out
    assert init["result"]["serverInfo"]["name"] == "catalyst"
    assert "INV-1" in init["result"]["instructions"]
    assert [(p["name"], p["description"]) for p in listed["result"]["prompts"]] == [
        ("alpha", "do alpha. More about alpha."), ("beta", "do beta.")]
    text = got["result"]["messages"][0]["content"]["text"]
    assert "/alpha with the arguments: x1" in text and "do the alpha thing" in text
    assert missing["error"]["code"] == -32602


def test_the_project_comes_from_the_clients_roots(tmp_path):
    project = _project(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    out = _session([_init({"roots": {}}), {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    {"jsonrpc": "2.0", "id": 2, "method": "prompts/list"},
                    {"jsonrpc": "2.0", "id": "catalyst-1",
                     "result": {"roots": [{"uri": (project / "src").as_uri()}]}}],
                   elsewhere)
    init, asked, listed = out
    assert "INV-1" not in init["result"]["instructions"]        # roots are not known yet
    assert asked["method"] == "roots/list"
    assert [p["name"] for p in listed["result"]["prompts"]] == ["alpha", "beta"]


def test_outside_a_project_there_is_nothing_to_serve(tmp_path):
    out = _session([_init(), {"jsonrpc": "2.0", "id": 2, "method": "prompts/list"},
                    {"jsonrpc": "2.0", "id": 3, "method": "nope"}], tmp_path)
    assert out[1]["result"] == {"prompts": []} and out[2]["error"]["code"] == -32601


def test_the_tool_runs_the_cli_in_the_project(tmp_path):
    project = _project(tmp_path)
    cli = [sys.executable, "-c", "import os, sys; print(os.getcwd(), *sys.argv[1:]); sys.exit(3)"]
    out = _session([_init(), {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                    {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                     "params": {"name": "catalyst", "arguments": {"args": ["spec", "alpha"]}}},
                    {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                     "params": {"name": "catalyst", "arguments": {"args": ["mcp"]}}}], project, launcher=cli)
    assert [t["name"] for t in out[1]["result"]["tools"]] == ["catalyst", "command"]
    called = out[2]["result"]
    assert called["isError"] and called["content"][0]["text"].startswith("exit 3\n")
    assert f"{project.resolve()} spec alpha" in called["content"][0]["text"].replace(str(project), str(project.resolve()))
    assert out[3]["result"]["isError"]


def test_the_server_speaks_on_stdout_only(tmp_path):
    project = _project(tmp_path)
    messages = [_init(), {"jsonrpc": "2.0", "id": 2, "method": "prompts/list"}]
    done = subprocess.run([sys.executable, "-m", "catalyst", "--project", str(project), "mcp"],
                          input="".join(json.dumps(m) + "\n" for m in messages), capture_output=True, text=True,
                          env={"PYTHONPATH": str(SCRIPTS), "PATH": ""}, timeout=60, check=True)
    replies = [json.loads(line) for line in done.stdout.splitlines()]
    assert [r["id"] for r in replies] == [1, 2] and len(replies[1]["result"]["prompts"]) == 2


def test_a_project_directory_named_by_the_client_is_used(tmp_path, monkeypatch):
    project = _project(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))
    out = _session([_init(), {"jsonrpc": "2.0", "id": 2, "method": "prompts/list"}], elsewhere)
    assert "INV-1" in out[0]["result"]["instructions"]
    assert [p["name"] for p in out[1]["result"]["prompts"]] == ["alpha", "beta"]


def test_without_prompts_a_command_comes_from_the_command_tool_and_the_agents_cwd(tmp_path):
    project = _project(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    call = lambda i, args: {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                            "params": {"name": "command", "arguments": args}}
    out = _session([_init(), call(2, {"cwd": str(project / ".criterion")}),
                    call(3, {"name": "beta", "arguments": "now please", "cwd": str(project)}),
                    call(4, {"name": "beta"})], elsewhere)
    assert out[1]["result"]["content"][0]["text"] == "/alpha — do alpha. More about alpha.\n/beta — do beta."
    assert "/beta with the arguments: now please" in out[2]["result"]["content"][0]["text"]
    assert out[3]["result"]["isError"]                         # no project known


def test_a_client_that_splits_arguments_gets_word_slots(tmp_path):
    project = _project(tmp_path)
    out = _session([_init(client="claude-code"), {"jsonrpc": "2.0", "id": 2, "method": "prompts/list"},
                    {"jsonrpc": "2.0", "id": 3, "method": "prompts/get",
                     "params": {"name": "alpha", "arguments": {"word1": "flaky", "word2": "checkout", "word3": "test"}}}],
                   project)
    assert len(out[1]["result"]["prompts"][0]["arguments"]) == 16
    assert "with the arguments: flaky checkout test," in out[2]["result"]["messages"][0]["content"]["text"]
