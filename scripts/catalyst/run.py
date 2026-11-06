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

Each adapter reads the stream its agent documents (owner decision B2 names
the three): Claude Code's stream-json; Gemini CLI's stream-json (its tools,
a tool its policy refused as denied, its token usage; no cost); Copilot
CLI's JSONL of session events (its tools, a denied permission, token usage
only when it writes `assistant.usage`, else `measured: false`; Copilot bills
premium requests, so no dollar cost). What an agent does not report stays
null or unmeasured, never estimated (L10). The plain-text adapter (`-p`, its
output as text, `ok` from the exit) remains for an agent without a stream.
An agent with no adapter is said, not guessed at (REQ-000120).
No HTTP route starts a run: whether the UI launches agents is an open
owner decision (C2).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from catalyst.journal import VIA_VARIABLE

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
    _ended: bool = False

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
            self._ended = True

    def close(self, code: int, stderr: str) -> Iterator[Event]:
        """What the stream still owes once the agent exits: an `end` when it gave none."""
        if not self._ended:
            yield _unended(code, stderr)


def _unended(code: int, stderr: str, **extra: object) -> Event:
    """The `end` of a run whose agent stopped without saying how it went."""
    return {
        "event": "end",
        "ok": False,
        "turns": 0,
        "usage": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0},
        "cost_usd": None,
        "duration_ms": None,
        "denied": [],
        "result": (stderr.strip() or f"the agent exited {code} without a result")[:2000],
        **extra,
    }


def _json_line(line: str) -> dict | None:
    """One JSONL record, or None for a line that is not one (skipped, never an error)."""
    try:
        raw = json.loads(line)
    except json.JSONDecodeError:
        return None
    return raw if isinstance(raw, dict) else None


def _dict(value: object) -> dict:
    """`value` when it is a JSON object, else an empty one: a field an agent left out reads as nothing."""
    return value if isinstance(value, dict) else {}


def _int(value: object) -> int:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 else 0


@dataclass
class Gemini:
    """Gemini CLI headless, `--output-format stream-json`: events `init`,
    `message`, `tool_use`, `tool_result`, `error` and `result` (its source's
    `packages/core/src/output/types.ts`). Assistant chunks are joined into
    one `text` per reply; a tool its policy refused is denied."""

    binary: str = "gemini"
    _tools: dict[str, str] = field(default_factory=dict)  # tool_id -> tool name
    _reply: list[str] = field(default_factory=list)
    _replies: int = 0
    _denied: set[str] = field(default_factory=set)
    _errors: list[str] = field(default_factory=list)
    _ended: bool = False
    _last: str = ""

    def argv(self, prompt: str) -> list[str]:
        return [self.binary, "-p", prompt, "--output-format", "stream-json"]

    def _flush(self) -> Iterator[Event]:
        text = "".join(self._reply).strip()
        self._reply = []
        if text:
            self._replies += 1
            self._last = text
            yield {"event": "text", "text": text}

    def events(self, line: str) -> Iterator[Event]:
        raw = _json_line(line)
        if raw is None:
            return
        kind = raw.get("type")
        if kind == "message":
            if raw.get("role") == "assistant" and isinstance(raw.get("content"), str):
                self._reply.append(raw["content"])
                if not raw.get("delta"):
                    yield from self._flush()
            return
        yield from self._flush()  # a reply ends where anything else begins
        if kind == "init":
            yield {"event": "session", "model": raw.get("model"), "session": raw.get("session_id")}
        elif kind == "tool_use":
            name = str(raw.get("tool_name") or "")
            self._tools[str(raw.get("tool_id"))] = name
            yield {"event": "tool", "name": name or None, "input": _summary(raw.get("parameters") or {})}
        elif kind == "tool_result":
            name = self._tools.get(str(raw.get("tool_id")), "")
            error = _dict(raw.get("error"))
            if error.get("type") == "policy_violation":
                self._denied.add(name or "?")
            yield {"event": "tool_result", "name": name, "ok": raw.get("status") == "success"}
        elif kind == "error":
            if raw.get("severity") == "error" and raw.get("message"):
                self._errors.append(str(raw["message"]))
        elif kind == "result":
            stats = _dict(raw.get("stats"))
            error = _dict(raw.get("error"))
            ok = raw.get("status") == "success" and not self._denied
            reason = str(error.get("message") or "") or "\n".join(self._errors)
            self._ended = True
            yield {
                "event": "end",
                "ok": ok,
                "turns": self._replies,
                "usage": {
                    "input": _int(stats.get("input")),
                    "output": _int(stats.get("output_tokens")),
                    "cache_read": _int(stats.get("cached")),
                    "cache_write": 0,
                },
                "cost_usd": None,  # Gemini CLI reports no cost
                "duration_ms": _int(stats.get("duration_ms")) or None,
                "denied": sorted(self._denied),
                "result": (reason if not ok and reason else self._last)[:2000],
            }

    def close(self, code: int, stderr: str) -> Iterator[Event]:
        yield from self._flush()
        if not self._ended:
            yield _unended(code, "\n".join(self._errors) or stderr, turns=self._replies, denied=sorted(self._denied))


@dataclass
class Copilot:
    """Copilot CLI, `-p … --output-format json`: JSONL of its session events
    (the shapes of the Copilot SDK's `docs/features/streaming-events.md`),
    closed by a `result` record. The run's `end` is made when the CLI exits,
    its `ok` from the exit code, a `session.error` and the denied permissions."""

    binary: str = "copilot"
    _tools: dict[str, str] = field(default_factory=dict)  # toolCallId -> tool name
    _asked: dict[str, str] = field(default_factory=dict)  # permission requestId -> what it asked for
    _denied: set[str] = field(default_factory=set)
    _errors: list[str] = field(default_factory=list)
    _usage: dict[str, int] = field(default_factory=lambda: {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0})
    _measured: bool = False
    _turns: int = 0
    _duration: int | None = None
    _last: str = ""

    def argv(self, prompt: str) -> list[str]:
        return [self.binary, "-p", prompt, "--output-format", "json"]

    def events(self, line: str) -> Iterator[Event]:
        raw = _json_line(line)
        if raw is None:
            return
        kind = raw.get("type")
        data = _dict(raw.get("data"))
        if kind == "session.start":
            yield {"event": "session", "model": data.get("selectedModel"), "session": data.get("sessionId")}
        elif kind == "assistant.message":
            text = data.get("content")
            if isinstance(text, str) and text.strip():
                self._last = text
                yield {"event": "text", "text": text}
        elif kind == "assistant.turn_end":
            self._turns += 1
        elif kind == "assistant.usage":
            self._measured = True
            cache_read, cache_write = _int(data.get("cacheReadTokens")), _int(data.get("cacheWriteTokens"))
            self._usage["input"] += max(_int(data.get("inputTokens")) - cache_read - cache_write, 0)
            self._usage["output"] += _int(data.get("outputTokens"))
            self._usage["cache_read"] += cache_read
            self._usage["cache_write"] += cache_write
        elif kind == "tool.execution_start":
            name = str(data.get("toolName") or "")
            self._tools[str(data.get("toolCallId"))] = name
            yield {"event": "tool", "name": name or None, "input": _summary(data.get("arguments") or {})}
        elif kind == "tool.execution_complete":
            name = self._tools.get(str(data.get("toolCallId")), "")
            yield {"event": "tool_result", "name": name, "ok": bool(data.get("success"))}
        elif kind == "permission.requested":
            asked = _dict(data.get("permissionRequest"))
            self._asked[str(data.get("requestId"))] = str(asked.get("toolName") or asked.get("kind") or "?")
        elif kind == "permission.completed":
            result = _dict(data.get("result"))
            if str(result.get("kind") or "").startswith("denied"):
                self._denied.add(self._asked.get(str(data.get("requestId")), "?"))
        elif kind == "session.error":
            if data.get("message"):
                self._errors.append(str(data["message"]))
        elif kind == "result":
            usage = _dict(raw.get("usage")) or _dict(data.get("usage"))
            if _int(usage.get("sessionDurationMs")):
                self._duration = _int(usage.get("sessionDurationMs"))

    def close(self, code: int, stderr: str) -> Iterator[Event]:
        ok = code == 0 and not self._errors and not self._denied
        reason = "\n".join(self._errors) or stderr.strip() or f"the agent exited {code}"
        yield {
            "event": "end",
            "ok": ok,
            "turns": self._turns,
            "usage": dict(self._usage),
            "cost_usd": None,  # Copilot bills premium requests, not dollars
            "duration_ms": self._duration,
            "denied": sorted(self._denied),
            "result": (self._last if code == 0 and not self._errors else reason)[:2000],
            "measured": self._measured,
        }


@dataclass
class PlainText:
    """An agent run in its non-interactive mode (`<binary> -p <prompt>`), what
    it prints passed on as text; it says nothing of tools, usage or cost."""

    binary: str
    _last: list[str] = field(default_factory=list)

    def argv(self, prompt: str) -> list[str]:
        return [self.binary, "-p", prompt]

    def events(self, line: str) -> Iterator[Event]:
        text = line.rstrip("\n")
        if text.strip():
            self._last = [*self._last[-40:], text]
            yield {"event": "text", "text": text}

    def close(self, code: int, stderr: str) -> Iterator[Event]:
        yield self.finish(code, stderr)

    def finish(self, code: int, stderr: str) -> Event:
        """The run's end, from the agent's exit: `ok` on 0; nothing measured."""
        result = "\n".join(self._last[-20:]) if code == 0 else (stderr.strip() or f"the agent exited {code}")
        return {
            "event": "end",
            "ok": code == 0,
            "turns": 0,
            "usage": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0},
            "cost_usd": None,
            "duration_ms": None,
            "denied": [],
            "result": result[:2000],
            "measured": False,
        }


Adapter = ClaudeCode | Gemini | Copilot | PlainText

ADAPTERS: dict[str, Callable[[], Adapter]] = {
    "claude-code": ClaudeCode,
    "copilot": Copilot,
    "gemini": Gemini,
}


def adapter_for(agent: str, which: Callable[[str], str | None] = shutil.which) -> Adapter:
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


def stream(adapter: Adapter, lines: Iterable[str]) -> Iterator[Event]:
    """The events of a run's output lines, in order."""
    for line in lines:
        yield from adapter.events(line)


def run(
    adapter: Adapter,
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
        env={**os.environ, VIA_VARIABLE: "agent"},  # its catalyst calls are an agent's (fw-STRUCTURE-000022)
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
    for event in adapter.close(code, stderr):  # what the stream still owes: a held reply, the end
        if event["event"] == "end":
            if end is not None:
                continue
            end = event
        on_event(event)
    assert end is not None  # noqa: S101 (every adapter's close ends the run)
    return end


# --- the run log -------------------------------------------------------------
def log_path(project: Path) -> Path | None:
    """This user's run log for a project: in catalyst's home beside their
    agent choice, never in the criterion or the project (it is telemetry,
    not governed content). None outside a catalyst project."""
    import project_file

    name = project_file.project_name(project_file.read_dir(project))
    return project_file.home() / "projects" / name / "runs.jsonl" if name else None


def record(project: Path, actor: str, agent: str, command: str, arguments: str, end: Event) -> None:
    """One line per run: when, who, which agent and command, how it ended
    and what it cost. A log that cannot be written never fails the run."""
    import datetime

    path = log_path(project)
    if path is None:
        return
    line = {
        "timestamp": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actor": actor,
        "agent": agent,
        "command": command.lstrip("/"),
        "arguments": arguments,
        **{k: end.get(k) for k in ("ok", "turns", "usage", "cost_usd", "duration_ms", "denied")},
        **({"measured": False} if end.get("measured") is False else {}),  # zeros that are unknown, not none
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError:
        pass


def runs(project: Path, limit: int | None = None) -> list[dict]:
    """The logged runs, oldest first (the last `limit` when given); a damaged line is skipped."""
    path = log_path(project)
    if path is None or not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            out.append(item)
    return out[-limit:] if limit else out


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
        tokens = (
            "tokens not reported by the agent"
            if event.get("measured") is False
            else f"tokens {u['input']} in, {u['output']} out, cache {u['cache_read']} read, {u['cache_write']} written"
        )
        lines = [
            f"catalyst: {'done' if event['ok'] else 'FAILED'} in {event['turns']} turn(s); {tokens}"
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
