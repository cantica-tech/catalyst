"""`catalyst mcp`: catalyst for any agent, over the Model Context Protocol
(roadmap R3.1c, what-is-going-on 15).

A stdio MCP server (newline-delimited JSON-RPC 2.0), standard library only,
registered once per machine at user level — nothing is written into a
project. It serves the project the agent works in, found from the client's
roots (else a project directory the client names in the
environment, else the server's working directory), then its `catalyst.toml`:

- prompts: one per command of the deployment's composed CODE-OF-CONDUCT.md
  §4 (kernel and module alike, read at request time — the server names no
  module command), each carrying that command's `catalyst spec`;
- tools: `catalyst`, the CLI's verbs, run through the launcher in the
  project's root so each project gets its own catalyst version; `command`,
  a command's procedure, for clients without MCP prompts (Copilot CLI,
  Codex). Both take the agent's `cwd` where the client gives no project;
- instructions: the deployment's invariants, as `catalyst hook start`
  prints them.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import project_file
from catalyst import version_string
from catalyst.deployment import DeploymentNotFound, WorkingCopyMissing, load
from catalyst.spec import SpecError, load_section4, spec_text

PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
# where a client names the project when it does not start the server in it
PROJECT_DIR_VARIABLES = ("CLAUDE_PROJECT_DIR",)
REFUSED_VERBS = {"mcp"}  # no server inside the server
# clients that split a prompt's typed arguments on whitespace over the declared
# arguments, in order (Claude Code): they get word slots, joined back
SPLITTING_CLIENTS = {"claude-code"}
WORD_SLOTS = 16
GENERIC_INSTRUCTIONS = (
    "catalyst governs projects that have a catalyst.toml at their root; nothing applies elsewhere. In such a "
    "project, run a catalyst command (a `/name` of the project's CODE-OF-CONDUCT.md §4, e.g. when the user types "
    "`/check-rules`) through this server's prompt of that name or, where prompts are not available, its "
    "`command` tool, which returns the command's procedure; the `catalyst` tool runs the CLI. Pass your working "
    "directory as `cwd` when this server may not know the project."
)
CWD = {
    "type": "string",
    "description": "the directory you work in (the project, or a folder inside it); default: the client's roots",
}
TOOLS = [
    {
        "name": "catalyst",
        "description": (
            'Run the catalyst CLI in the project\'s root, e.g. ["check"], ["spec", "<command>"], ["where"], '
            '["backlog"], ["list", "<type>"], ["view", "<id>"], ["new", ...], ["status", "set", ...], '
            '["journal", "append", ...], ["index", "regen"]. Returns the exit code, stdout and stderr.'
        ),
        "inputSchema": {
            "type": "object",
            "required": ["args"],
            "properties": {
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "the CLI arguments, without the leading `catalyst`",
                },
                "cwd": CWD,
            },
        },
    },
    {
        "name": "command",
        "description": (
            "A catalyst command (a `/name` of the project's CODE-OF-CONDUCT.md §4): returns what to do — the "
            "command's procedure, to carry out with the `catalyst` tool. Without `name`, lists the commands."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "the command, without the slash, e.g. check-rules"},
                "arguments": {"type": "string", "description": "the command's arguments, as the user typed them"},
                "cwd": CWD,
            },
        },
    },
]


def _summary(bullets: list[str]) -> str:
    """A command's one-line description: its §4 bullet, after the dash."""
    first = " ".join(line.strip() for line in bullets[0].splitlines()) if bullets else ""
    text = first.split("—", 1)[1].strip() if "—" in first else first.lstrip("- ")
    return text if len(text) <= 300 else text[:297].rstrip() + "..."


def _path_of(uri: str) -> Path | None:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return None
    path = unquote(parsed.path)
    if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]
    return Path(path)


class Server:
    def __init__(self, reader, writer, cwd: Path, launcher: list[str] | None = None) -> None:
        self.reader, self.writer, self.cwd = reader, writer, cwd
        self.launcher = launcher
        self.client_roots = False
        self.client = ""
        self.roots: list[Path] | None = None  # None: not asked yet
        self.queue: list[dict] = []
        self.next_id = 0

    # --- transport ---------------------------------------------------------
    def send(self, message: dict) -> None:
        self.writer.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.writer.flush()

    def receive(self) -> dict | None:
        if self.queue:
            return self.queue.pop(0)
        while True:
            line = self.reader.readline()
            if not line:
                return None
            if line.strip():
                try:
                    return json.loads(line)
                except ValueError:
                    self.send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})

    def ask(self, method: str, params: dict | None = None) -> dict | None:
        """A request to the client; other messages arriving meanwhile are queued."""
        self.next_id += 1
        rid = f"catalyst-{self.next_id}"
        self.send({"jsonrpc": "2.0", "id": rid, "method": method, **({"params": params} if params else {})})
        while True:
            line = self.reader.readline()
            if not line:
                return None
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if message.get("id") == rid and "method" not in message:
                return message
            self.queue.append(message)

    # --- the project -------------------------------------------------------
    def project(self, ask_roots: bool = True, hint: str | None = None) -> Path | None:
        if hint:
            found = project_file.find_up(Path(hint).expanduser())
            if found is not None:
                return found
        if ask_roots and self.client_roots and self.roots is None:
            reply = self.ask("roots/list") or {}
            self.roots = [
                p for r in (reply.get("result") or {}).get("roots", []) if (p := _path_of(r.get("uri", ""))) is not None
            ]
        hinted = [Path(os.environ[v]) for v in PROJECT_DIR_VARIABLES if os.environ.get(v)]
        for start in [*(self.roots or []), *hinted, self.cwd]:
            found = project_file.find_up(start)
            if found is not None:
                return found
        return None

    def deployment(self, ask_roots: bool = True, hint: str | None = None):
        project = self.project(ask_roots, hint)
        if project is None:
            return None
        try:
            return load(project)
        except (DeploymentNotFound, WorkingCopyMissing):
            return None

    def instructions(self) -> str:
        dep = self.deployment(ask_roots=False)  # roots can only be asked after initialize
        parts = [GENERIC_INSTRUCTIONS]
        for name in ("INVARIANTS.md", "INVARIANTS.module.md"):
            path = dep.root / name if dep else None
            if path is not None and path.is_file():
                parts.append(path.read_text(encoding="utf-8", errors="replace"))
        return "\n\n".join(parts)

    # --- methods -------------------------------------------------------------
    def initialize(self, params: dict) -> dict:
        self.client_roots = "roots" in (params.get("capabilities") or {})
        self.client = str((params.get("clientInfo") or {}).get("name", ""))
        asked = params.get("protocolVersion")
        return {
            "protocolVersion": asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
            "capabilities": {"prompts": {"listChanged": False}, "tools": {"listChanged": False}},
            "serverInfo": {"name": "catalyst", "version": version_string()},
            "instructions": self.instructions(),
        }

    def arguments(self) -> list[dict]:
        if self.client in SPLITTING_CLIENTS:
            return [
                {
                    "name": f"word{i}",
                    "description": "the command's arguments" if i == 1 else f"word {i}",
                    "required": False,
                }
                for i in range(1, WORD_SLOTS + 1)
            ]
        return [
            {
                "name": "arguments",
                "description": "the command's arguments, as you would type them after the slash command",
                "required": False,
            }
        ]

    def section4(self, hint: str | None = None):
        dep = self.deployment(hint=hint)
        if dep is None:
            raise RpcError(-32602, "no catalyst project here (no catalyst.toml in the client's roots or `cwd`)")
        try:
            return dep, load_section4(dep)
        except (OSError, SpecError) as exc:
            raise RpcError(-32602, str(exc)) from exc

    def prompts_list(self, _params: dict) -> dict:
        try:
            _, s = self.section4()
        except RpcError:
            return {"prompts": []}
        return {
            "prompts": [
                {"name": name, "description": _summary(s.bullets[name]), "arguments": self.arguments()}
                for name in sorted(s.bullets)
            ]
        }

    def procedure(self, name: str, arguments: str, hint: str | None = None) -> str:
        dep, s = self.section4(hint)
        try:
            text = spec_text(s, name)
        except SpecError as exc:
            raise RpcError(-32602, str(exc)) from exc
        return (
            f"Run the catalyst command /{name.lstrip('/')}"
            + (f" with the arguments: {arguments}" if arguments else "")
            + f", in the project at {dep.project_root}. Use the `catalyst` tool (or the `catalyst` CLI) for "
            "every step the specification below gives to the CLI.\n\n" + text
        )

    def prompts_get(self, params: dict) -> dict:
        name = str(params.get("name", ""))
        given = params.get("arguments") or {}
        if "arguments" in given:
            arguments = str(given["arguments"])
        else:
            arguments = " ".join(str(given[f"word{i}"]) for i in range(1, WORD_SLOTS + 1) if given.get(f"word{i}"))
        return {
            "description": f"catalyst /{name}",
            "messages": [
                {"role": "user", "content": {"type": "text", "text": self.procedure(name, arguments.strip())}}
            ],
        }

    def tools_list(self, _params: dict) -> dict:
        return {"tools": TOOLS}

    def tools_call(self, params: dict) -> dict:
        name, given = params.get("name"), params.get("arguments") or {}
        hint = given.get("cwd") if isinstance(given.get("cwd"), str) else None
        if name == "command":
            try:
                if not given.get("name"):
                    _, s = self.section4(hint)
                    return _result("\n".join(f"/{c} — {_summary(s.bullets[c])}" for c in sorted(s.bullets)))
                return _result(self.procedure(str(given["name"]), str(given.get("arguments") or "").strip(), hint))
            except RpcError as exc:
                return _result(str(exc), error=True)
        if name != "catalyst":
            raise RpcError(-32602, f"unknown tool {name!r}")
        args = given.get("args")
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise RpcError(-32602, "`args` must be a list of strings")
        if args and args[0] in REFUSED_VERBS:
            return _result(f"catalyst {args[0]} cannot run through this tool", error=True)
        project = self.project(hint=hint)
        try:
            done = subprocess.run(
                [*self.cli(), *args],
                cwd=project or self.cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdin=subprocess.DEVNULL,
                check=False,
                timeout=600,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return _result(f"catalyst: {exc}", error=True)
        out = f"exit {done.returncode}\n{done.stdout}" + (f"\n[stderr]\n{done.stderr}" if done.stderr else "")
        return _result(out, error=done.returncode != 0)

    def cli(self) -> list[str]:
        """The launcher, which runs the project's own catalyst; else this one."""
        if self.launcher is not None:
            return self.launcher
        launcher = project_file.home() / "bin" / "catalyst"
        if launcher.is_file():
            return [sys.executable, str(launcher)]
        if sys.argv and sys.argv[0].endswith(".pyz"):
            return [sys.executable, sys.argv[0]]
        return [sys.executable, "-m", "catalyst"]

    METHODS = {
        "initialize": initialize,
        "prompts/list": prompts_list,
        "prompts/get": prompts_get,
        "tools/list": tools_list,
        "tools/call": tools_call,
        "ping": lambda self, p: {},
    }

    def serve(self) -> int:
        while (message := self.receive()) is not None:
            method, mid = message.get("method"), message.get("id")
            if method is None:
                continue  # a stray response
            if method == "notifications/roots/list_changed":
                self.roots = None
                continue
            if mid is None:
                continue  # other notifications
            handler = self.METHODS.get(method)
            if handler is None:
                self.send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"no method {method}"}})
                continue
            try:
                self.send({"jsonrpc": "2.0", "id": mid, "result": handler(self, message.get("params") or {})})
            except RpcError as exc:
                self.send({"jsonrpc": "2.0", "id": mid, "error": {"code": exc.code, "message": str(exc)}})
            except Exception as exc:  # never let one request end the session
                self.send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": f"catalyst: {exc}"}})
        return 0


class RpcError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


def _result(text: str, error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": error}


def run(cwd: Path) -> int:
    """Serve on stdio. Anything else written to file descriptor 1 (a stray
    print, a child process) would corrupt the protocol: the protocol keeps a
    private copy of stdout, and fd 1 is pointed at stderr."""
    protocol = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8", newline="\n")
    sys.stdout.flush()
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    reader = sys.stdin
    if hasattr(reader, "reconfigure"):
        reader.reconfigure(encoding="utf-8", errors="replace")
    return Server(reader, protocol, cwd).serve()
