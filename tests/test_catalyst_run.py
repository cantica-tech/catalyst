"""`catalyst agent run` (roadmap R5.5; REQ-000048): a command dispatched to
the project's agent, its output normalized to events. The agent here is a
recorded Claude Code stream replayed by a script: no network, no agent."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import schema_check
from catalyst import run as runs
from catalyst.__main__ import main
from catalyst_fixtures import make_project, write

SECTION4 = """# Rules of Development

## 4. Slash-command entry points

- `/alpha <x>` — do alpha.

When the user enters `/alpha <x>`, run `catalyst check`.

## 5. Next
"""

STREAM = [
    {"type": "system", "subtype": "hook_started", "hook_id": "h"},
    {"type": "system", "subtype": "init", "model": "claude-opus-5-5", "session_id": "s-1", "tools": []},
    {"type": "rate_limit_event", "rate_limit_info": {}},
    {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "text", "text": "Checking the rules."},
                {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "catalyst  check\n --json"}},
                {"type": "tool_use", "id": "t2", "name": "Write", "input": {"file_path": "/x/y.md", "content": "…"}},
            ]
        },
    },
    {
        "type": "user",
        "message": {
            "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "ok"},
                {"type": "tool_result", "tool_use_id": "t2", "is_error": True, "content": "denied"},
            ]
        },
    },
    {"type": "assistant", "message": {"content": [{"type": "text", "text": "No errors."}]}},
    {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": "No errors.",
        "num_turns": 2,
        "duration_ms": 4200,
        "total_cost_usd": 0.0123,
        "usage": {
            "input_tokens": 12,
            "output_tokens": 34,
            "cache_read_input_tokens": 5000,
            "cache_creation_input_tokens": 600,
        },
        "permission_denials": [{"tool_name": "Write", "tool_use_id": "t2", "tool_input": {}}],
    },
]

AGENT = """import json, sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]), encoding="utf-8")
for line in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines():
    print(line, flush=True)
print(sys.argv[3], file=sys.stderr)
sys.exit(int(sys.argv[4]))
"""


def lines(stream: list[dict]) -> list[str]:
    return [json.dumps(item) for item in stream] + ["not json", "[]"]


def test_a_claude_code_stream_becomes_catalyst_events_each_as_its_schema_says():
    events = list(runs.stream(runs.ClaudeCode(), lines(STREAM)))
    assert [e["event"] for e in events] == [
        "session",
        "text",
        "tool",
        "tool",
        "tool_result",
        "tool_result",
        "text",
        "end",
    ]
    assert events[0] == {"event": "session", "model": "claude-opus-5-5", "session": "s-1"}
    assert events[2] == {"event": "tool", "name": "Bash", "input": "catalyst check --json"}  # one line
    assert events[3]["input"] == "/x/y.md"
    assert events[4:6] == [
        {"event": "tool_result", "name": "Bash", "ok": True},
        {"event": "tool_result", "name": "Write", "ok": False},
    ]
    end = events[-1]
    assert end["ok"] is False and end["turns"] == 2 and end["denied"] == ["Write"]  # stopped by the settings
    assert end["usage"] == {"input": 12, "output": 34, "cache_read": 5000, "cache_write": 600}
    assert end["cost_usd"] == 0.0123 and end["result"] == "No errors."
    schema = schema_check.load("run-event")
    start = {"event": "start", "agent": "claude-code", "command": "alpha", "arguments": "x"}
    for event in [start, *events]:
        assert schema_check.problems(event, schema) == [], event


def test_an_agent_without_an_adapter_or_without_its_cli_is_said():
    with pytest.raises(runs.RunError, match="no run adapter for agent 'codex'"):
        runs.adapter_for("codex")
    with pytest.raises(runs.RunError, match="`claude`\\) is not on PATH"):
        runs.adapter_for("claude-code", which=lambda _name: None)
    assert runs.adapter_for("claude-code", which=lambda name: f"/bin/{name}").binary == "/bin/claude"


class Replay(runs.ClaudeCode):
    """Claude Code's parsing, the process a script that replays a stream."""

    def __init__(self, tmp: Path, stream: list[dict], code: int = 0, stderr: str = ""):
        super().__init__()
        self.seen = tmp / "argv.json"
        self.recording = tmp / "stream.jsonl"
        self.recording.write_text("\n".join(lines(stream)), encoding="utf-8")
        self.script = tmp / "agent.py"
        self.script.write_text(AGENT, encoding="utf-8")
        self.code, self.stderr = code, stderr

    def argv(self, prompt: str) -> list[str]:
        real = super().argv(prompt)
        return [
            sys.executable,
            str(self.script),
            str(self.seen),
            str(self.recording),
            self.stderr,
            str(self.code),
            *real,
        ]


@pytest.fixture
def project(tmp_path, monkeypatch):
    p = make_project(tmp_path / "app")
    write(p / ".criterion" / "CODE-OF-CONDUCT.md", SECTION4)
    monkeypatch.chdir(p)
    return p


def _run(monkeypatch, capsys, adapter: Replay, *argv: str) -> tuple[int, str]:
    monkeypatch.setattr(runs, "adapter_for", lambda agent, which=None: adapter)
    capsys.readouterr()
    code = main(["agent", "run", *argv])
    return code, capsys.readouterr().out


CLEAN = [*STREAM[:-1], {**STREAM[-1], "permission_denials": []}]


def test_the_cli_sends_the_procedure_from_the_project_root_and_streams_json(project, tmp_path, monkeypatch, capsys):
    adapter = Replay(tmp_path, CLEAN)
    code, out = _run(monkeypatch, capsys, adapter, "alpha", "x", "y", "--json")
    assert code == 0
    events = [json.loads(line) for line in out.splitlines()]
    assert events[0] == {"event": "start", "agent": "claude-code", "command": "alpha", "arguments": "x y"}
    assert events[-1]["event"] == "end" and events[-1]["ok"] is True
    sent = json.loads(adapter.seen.read_text(encoding="utf-8"))
    claude = sent[sent.index("-p") - 1 :]
    assert claude[1:2] == ["-p"] and claude[3:] == ["--output-format", "stream-json", "--verbose"]
    prompt = claude[2]
    assert "Run the catalyst command /alpha with the arguments: x y" in prompt and "run `catalyst check`" in prompt
    assert not any("dangerously" in a or "permission" in a for a in sent)  # nothing widens the agent's permissions


def test_the_cli_reads_for_a_person_and_says_what_was_denied(project, tmp_path, monkeypatch, capsys):
    code, out = _run(monkeypatch, capsys, Replay(tmp_path, CLEAN), "alpha", "x")
    assert code == 0
    assert "catalyst: /alpha x → claude-code" in out and "⚙ Bash: catalyst check --json" in out
    assert "✕ Write failed" in out and "No errors." in out
    assert "done in 2 turn(s); tokens 12 in, 34 out, cache 5000 read, 600 written; $0.0123" in out
    # a tool the user's settings refused: the run did not do its work
    code, out = _run(monkeypatch, capsys, Replay(tmp_path, STREAM), "alpha", "x")
    assert code == 1 and "FAILED in 2 turn(s)" in out
    assert "denied by your agent settings: Write — allow them there" in out


def test_a_failed_run_exits_1_and_one_without_a_result_says_why(project, tmp_path, monkeypatch, capsys):
    failed = [*STREAM[:-1], {**STREAM[-1], "subtype": "error_max_turns", "is_error": True, "result": "too many turns"}]
    code, out = _run(monkeypatch, capsys, Replay(tmp_path, failed), "alpha", "x")
    assert code == 1 and "FAILED" in out and "too many turns" in out
    code, out = _run(
        monkeypatch, capsys, Replay(tmp_path, STREAM[:3], code=3, stderr="auth expired"), "alpha", "--json"
    )
    end = json.loads(out.splitlines()[-1])
    assert code == 1 and end["event"] == "end" and end["ok"] is False and end["result"] == "auth expired"


def test_an_unknown_command_or_agent_exits_2(project, capsys):
    assert main(["agent", "run", "nope"]) == 2
    assert "/nope is not in CODE-OF-CONDUCT.md" in capsys.readouterr().err
    assert main(["agent", "run", "--agent", "codex", "alpha"]) == 2
    assert "no run adapter for agent 'codex'" in capsys.readouterr().err


def test_each_run_is_logged_for_this_user_and_listed_with_its_cost(project, tmp_path, monkeypatch, capsys):
    """REQ-000050: the run log in catalyst's home, never in the criterion or the project."""
    home = tmp_path / "home"
    monkeypatch.setenv("CATALYST_HOME", str(home))
    assert _run(monkeypatch, capsys, Replay(tmp_path, CLEAN), "alpha", "x")[0] == 0
    assert _run(monkeypatch, capsys, Replay(tmp_path, STREAM), "alpha", "y")[0] == 1
    logged = list(home.glob("projects/*/runs.jsonl"))
    assert len(logged) == 1 and not list(project.rglob("runs.jsonl"))
    capsys.readouterr()
    assert main(["agent", "runs", "--json"]) == 0
    items = json.loads(capsys.readouterr().out)
    assert [(r["command"], r["arguments"], r["ok"]) for r in items] == [("alpha", "x", True), ("alpha", "y", False)]
    assert items[0]["usage"] == {"input": 12, "output": 34, "cache_read": 5000, "cache_write": 600}
    assert items[1]["denied"] == ["Write"]
    assert schema_check.problems(items, schema_check.load("runs")) == []
    assert main(["agent", "runs"]) == 0
    assert "2 run(s), $0.0246 in all" in capsys.readouterr().out
    assert main(["agent", "runs", "--limit", "1", "--json"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 1
