"""`catalyst agent run <command> [<arguments>…]` (roadmap R5.5): one catalyst
command dispatched to the project's agent, non-interactively, its output
streamed as events and closed with what the run cost.

The agent is the one `catalyst open --agent` records for this user. It is
given the command's procedure — the text the `catalyst mcp` prompts give —
and runs from the project's root under the user's own agent settings:
catalyst passes no flag that widens its permissions (laws L3, L4), so a tool
the settings do not allow is refused, and reported as denied.

Each agent's output is normalized by its adapter to the same events
(`spec/run-event.schema.json`):

- `start`: the agent, the command and its arguments;
- `session`: the model and the agent's session;
- `text`: what the agent says;
- `tool`: a tool it calls, with a short summary of the input;
- `tool_result`: whether that call succeeded;
- `end`: `ok`, the turns, token `usage`, `cost_usd`, `duration_ms`, the
  tools the agent was `denied`, and its final `result`. A run the user's
  settings denied a tool is not `ok`: it did not do its work, whatever the
  agent says.

Only Claude Code has an adapter; another agent is said, not guessed at.
No HTTP route starts a run: whether the UI launches agents is an open
owner decision (C2).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

Event = dict[str, object]


class RunError(Exception):
    """The run could not start: no adapter for the agent, or its CLI is missing."""


def _summary(value: object, limit: int = 160) -> str:
    """A tool input in one short line: a command, a path, or compact JSON."""
    if isinstance(value, dict):
        for key in ("command", "file_path", "path", "pattern", "url", "description"):
            if isinstance(value.get(key), str):
                text = str(value[key])
                break
        else:
            text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _usage(raw: dict) -> dict[str, int]:
    """Token usage in catalyst's names: input, output, and the prompt cache's reads and writes."""
    return {
        "input": int(raw.get("input_tokens") or 0),
        "output": int(raw.get("output_tokens") or 0),
        "cache_read": int(raw.get("cache_read_input_tokens") or 0),
        "cache_write": int(raw.get("cache_creation_input_tokens") or 0),
    }


@dataclass
class ClaudeCode:
    """Claude Code in print mode, its output as stream-json."""

    binary: str = "claude"
    _tools: dict[str, str] = field(default_factory=dict)  # tool_use id -> tool name

    def argv(self, prompt: str) -> list[str]:
        return [self.binary, "-p", prompt, "--output-format", "stream-json", "--verbose"]

    def events(self, line: str) -> Iterator[Event]:
        """The catalyst events one line of stream-json carries (none for what catalyst does not show)."""
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            return
        if not isinstance(raw, dict):
            return
        kind = raw.get("type")
        if kind == "system" and raw.get("subtype") == "init":
            yield {"event": "session", "model": raw.get("model"), "session": raw.get("session_id")}
        elif kind == "assistant":
            for part in (raw.get("message") or {}).get("content") or []:
                if part.get("type") == "text" and part.get("text"):
                    yield {"event": "text", "text": part["text"]}
                elif part.get("type") == "tool_use":
                    self._tools[str(part.get("id"))] = str(part.get("name"))
                    yield {"event": "tool", "name": part.get("name"), "input": _summary(part.get("input"))}
        elif kind == "user":
            for part in (raw.get("message") or {}).get("content") or []:
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    name = self._tools.get(str(part.get("tool_use_id")), "")
                    yield {"event": "tool_result", "name": name, "ok": not part.get("is_error")}
        elif kind == "result":
            denied = sorted(
                {str(d.get("tool_name")) for d in raw.get("permission_denials") or [] if d.get("tool_name")}
            )
            yield {
                "event": "end",
                # a run the user's settings stopped did not do its work, whatever the agent says
                "ok": not raw.get("is_error") and raw.get("subtype") == "success" and not denied,
                "turns": int(raw.get("num_turns") or 0),
                "usage": _usage(raw.get("usage") or {}),
                "cost_usd": raw.get("total_cost_usd"),
                "duration_ms": raw.get("duration_ms"),
                "denied": denied,
                "result": raw.get("result") if isinstance(raw.get("result"), str) else "",
            }


ADAPTERS: dict[str, Callable[[], ClaudeCode]] = {"claude-code": ClaudeCode}


def adapter_for(agent: str, which: Callable[[str], str | None] = shutil.which) -> ClaudeCode:
    """The adapter for `agent`, its CLI found on PATH; a RunError says why not."""
    make = ADAPTERS.get(agent)
    if make is None:
        known = ", ".join(sorted(ADAPTERS))
        raise RunError(f"no run adapter for agent '{agent}' yet (catalyst runs: {known})")
    adapter = make()
    found = which(adapter.binary)
    if found is None:
        raise RunError(f"the {agent} CLI (`{adapter.binary}`) is not on PATH")
    adapter.binary = found
    return adapter


def stream(adapter: ClaudeCode, lines: Iterable[str]) -> Iterator[Event]:
    """The events of a run's output lines, in order."""
    for line in lines:
        yield from adapter.events(line)


def run(
    adapter: ClaudeCode,
    agent: str,
    command: str,
    arguments: str,
    prompt: str,
    cwd: Path,
    on_event: Callable[[Event], None],
    popen: Callable[..., subprocess.Popen] = subprocess.Popen,
) -> Event:
    """Dispatch `prompt` to the agent from `cwd`, call `on_event` with each
    event as it arrives, and return the `end` event (one is made up when the
    agent stops without saying how it went)."""
    on_event({"event": "start", "agent": agent, "command": command.lstrip("/"), "arguments": arguments})
    end: Event | None = None
    with popen(
        adapter.argv(prompt),
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    ) as proc:
        assert proc.stdout is not None  # noqa: S101 (PIPE above)
        for event in stream(adapter, proc.stdout):
            if event["event"] == "end":
                end = event
            on_event(event)
        stderr = proc.stderr.read() if proc.stderr else ""
        code = proc.wait()
    if end is None:
        end = {
            "event": "end",
            "ok": False,
            "turns": 0,
            "usage": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0},
            "cost_usd": None,
            "duration_ms": None,
            "denied": [],
            "result": (stderr.strip() or f"the agent exited {code} without a result")[:2000],
        }
        on_event(end)
    return end


def render(event: Event) -> str | None:
    """One event as a line for a person; None for what is not worth a line."""
    kind = event["event"]
    if kind == "start":
        return f"catalyst: /{event['command']} {event['arguments']}".rstrip() + f" → {event['agent']}"
    if kind == "session":
        return f"  model {event.get('model')}, session {event.get('session')}"
    if kind == "text":
        return str(event["text"])
    if kind == "tool":
        return f"  ⚙ {event['name']}: {event['input']}"
    if kind == "tool_result" and not event["ok"]:
        return f"  ✕ {event['name']} failed"
    if kind == "end":
        u = event["usage"]
        assert isinstance(u, dict)  # noqa: S101 (made above)
        cost = event.get("cost_usd")
        lines = [
            f"catalyst: {'done' if event['ok'] else 'FAILED'} in {event['turns']} turn(s); "
            f"tokens {u['input']} in, {u['output']} out, cache {u['cache_read']} read, {u['cache_write']} written"
            + (f"; ${cost:.4f}" if isinstance(cost, (int, float)) else "")
        ]
        if event["denied"]:
            lines.append(
                f"catalyst: denied by your agent settings: {', '.join(map(str, event['denied']))}"  # type: ignore[arg-type]
                " — allow them there for a run to use them; catalyst widens no permission"
            )
        if not event["ok"] and event.get("result"):
            lines.append(f"catalyst: {event['result']}")
        return "\n".join(lines)
    return None
