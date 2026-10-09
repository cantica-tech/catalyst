"""The project file: the one file catalyst keeps in a project (ADR-010).

`catalyst.toml` at the project root names the project and pins its versions;
it never holds a path. Deployments made before it carry `<name>.catalyst`
(JSON) instead, read for one minor (ADR-009). Both are read into the same
flat dictionary (the legacy pointer's keys), so callers never care which
file a project has.

Stdlib only. `tomllib` (Python 3.11+) is imported only when a TOML file is
read, so a legacy JSON pointer still works on an older Python.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

NAME = "catalyst.toml"
LEGACY_SUFFIX = ".catalyst"
HEADER = (
    "# catalyst project file: names this project's criterion "
    "($HOME/.catalyst/projects/<project_name>/criterion). Never a path.\n"
)


def find(directory: Path) -> Path | None:
    """The project file in `directory`: `catalyst.toml`, else a legacy
    `<name>.catalyst`."""
    toml = directory / NAME
    if toml.is_file():
        return toml
    legacy = sorted(p for p in directory.glob(f"*{LEGACY_SUFFIX}") if p.is_file())
    return legacy[0] if legacy else None


def is_project(directory: Path) -> bool:
    return find(directory) is not None


def find_up(start: Path) -> Path | None:
    """The nearest directory at or above `start` holding a project file."""
    for d in (start, *start.parents):
        if is_project(d):
            return d
    return None


def read(path: Path) -> dict[str, Any]:
    """The project file's fields; {} when it cannot be parsed."""
    try:
        text = path.read_text(encoding="utf-8")
        if path.name == NAME:
            import tomllib

            data = tomllib.loads(text)
        else:
            data = json.loads(text)
    except (OSError, ValueError, ImportError):
        return {}
    return data if isinstance(data, dict) else {}


def read_dir(directory: Path) -> dict[str, Any]:
    path = find(directory)
    return read(path) if path else {}


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    return json.dumps(str(value), ensure_ascii=False)  # a TOML basic string


def dumps_toml(data: dict[str, Any]) -> str:
    """Flat key = value lines (the project file has no tables)."""
    lines = [HEADER]
    for key, value in data.items():
        if value is None or isinstance(value, dict):
            continue
        lines.append(f"{key} = {_toml_value(value)}\n")
    return "".join(lines)


def write(path: Path, data: dict[str, Any]) -> None:
    """Write `data` in the file's own format."""
    if path.name == NAME:
        path.write_text(dumps_toml(data), encoding="utf-8")
    else:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# --- where the criterion is ------------------------------------------------
LEGACY_DIRNAME = ".criterion"


def home() -> Path:
    """catalyst's own space: `$CATALYST_HOME`, else `$HOME/.catalyst`."""
    import os

    override = os.environ.get("CATALYST_HOME")
    return Path(override).expanduser() if override else Path.home() / ".catalyst"


def project_name(data: dict[str, Any]) -> str | None:
    name = data.get("project_name") or data.get("name")
    return str(name) if name else None


def home_criterion(name: str) -> Path:
    return home() / "projects" / name / "criterion"


def user_agent_file(name: str) -> Path:
    """This user's agent for a project (`catalyst open --agent`): kept in
    catalyst's home, never in the tracked project file, so teammates using
    different agents never rewrite each other's catalyst.toml."""
    return home() / "projects" / name / "agent"


def agent_of(data: dict[str, Any]) -> str:
    """The agent catalyst dispatches to for this user: their own choice
    (`catalyst open --agent`), else the project file's `agent`, else
    claude-code."""
    name = project_name(data)
    if name:
        try:
            chosen = user_agent_file(name).read_text(encoding="utf-8").strip()
        except OSError:
            chosen = ""
        if chosen:
            return chosen
    agent = str(data.get("agent") or "")
    return agent if agent and agent != "unknown" else "claude-code"


def workspace_criterion(name: str) -> Path:
    """A VS Code workspace's meta criterion (ADR-010, roadmap R3.1b)."""
    return home() / "workspaces" / name / "criterion"


def workspace_of(data: dict[str, Any]) -> str | None:
    name = data.get("workspace")
    return str(name) if name else None


def resolve(project_root: Path) -> Path | None:
    """The criterion of the project at `project_root`: its home store
    (`$CATALYST_HOME/projects/<name>/criterion`) when it exists; else, for a
    legacy deployment, `<project>/.criterion` (symlink, directory or
    submodule) or a pre-0.37.0 pointer's "agent-source"."""
    data = read_dir(project_root)
    name = project_name(data)
    if name:
        candidate = home_criterion(name)
        if candidate.is_dir():
            return candidate
    legacy = project_root / LEGACY_DIRNAME
    if legacy.is_dir():
        return legacy
    source = data.get("agent-source")
    if source:
        candidate = Path(str(source)).expanduser()
        if candidate.is_dir():
            return candidate
    return None
