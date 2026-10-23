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

# Every key a project file may carry: (key, type, meaning, what checks it). `FORMAT.md` §1's table is generated
# from this (R4.4 phase 3), and `gen_docs.py --check` fails when the code reads a key this does not list.
KEYS: tuple[tuple[str, str, str, str], ...] = (
    (
        "project_name",
        "string",
        "The project's name: its criterion is `$CATALYST_HOME/projects/<project_name>/criterion`.",
        "—",
    ),
    (
        "format",
        "string",
        "The format version this deployment is written in: `1.0-rc` today, `1.0` read ahead of the release.",
        "`check`: warning if absent, error if not supported.",
    ),
    (
        "kernel_version",
        "string",
        "The kernel version the deployment is at.",
        "Structure: must equal the criterion's `version.txt` (`version drift`).",
    ),
    (
        "module",
        "string",
        "The first installed module's id; `modules/modules.json` records every one.",
        "A module that cannot be found leaves the checks kernel-only (the check's scope line says so).",
    ),
    (
        "agent",
        "string",
        "The project's default agent, e.g. `claude-code` (`unknown` if none was given). Each user's own choice wins: `catalyst open --agent <id>` records it in `$CATALYST_HOME/projects/<name>/agent`, never here.",
        "—",
    ),
    (
        "workspace",
        "string",
        "Optional: the VS Code workspace this project is a member of; it inherits that workspace criterion's rules, domains, roles template and, when it has none, its pointer to catalyst-users (R3.1b, design 29).",
        "—",
    ),
    (
        "role_check",
        "string",
        "Optional: `enforce` (the default) or `warn`. A writing verb refuses a signer whose grants from catalyst-users do not allow its command, or warns with `warn` (decision D5, design 29).",
        "—",
    ),
    (
        "embed_origins",
        "string",
        "Optional: the origins, comma-separated (`https://wiki.example.com, http://localhost:3000`), whose pages may read this criterion through `catalyst serve --local` (decision B8): their reads get CORS headers, each with its reader's token; nothing is written. Absent: no other origin.",
        "`serve` refuses an origin that is not `scheme://host[:port]`.",
    ),
    (
        "analysis_passes",
        "integer",
        "Optional: the default number of independent passes of an analysis, `2` (four-eyes, the default) or `1`; `catalyst analysis start --passes` overrides it for one analysis.",
        "`catalyst analysis start` refuses another value.",
    ),
    (
        "governance",
        "string",
        "Optional. `suspended`: the owner suspended enforcement — `catalyst hook stop` reports it and never blocks; `catalyst check` still reports everything.",
        "—",
    ),
    (
        "share",
        "string",
        "Optional: the criterion's sharing driver, `git`, `serve` or `local` (`catalyst share`). Absent: `git` when the criterion has a remote or `catalyst_repo_url` is set, else `local`.",
        "An unknown driver is refused by `catalyst share`.",
    ),
    (
        "share_url",
        "string",
        "With `share = \"serve\"`: the server's URL (`catalyst serve`). Each user's token for it is in `$CATALYST_HOME/credentials` (`catalyst share login`), never here.",
        "`catalyst share` refuses `serve` without it.",
    ),
    ("repoed", "boolean", "`true` once the deployment is shared (INV-18).", "—"),
    ("catalyst_repo", "string or null", "Informational name of the criterion repository.", "—"),
    ("catalyst_repo_url", "string or null", "The criterion repository's URL, when shared.", "—"),
    ("criterion_branch", "string or null", "The shared branch; `null` means `criterion`.", "—"),
    ("created_by", "string or null", "The installing user's name (`ACCESS-CONTROL.md`). Informational.", "—"),
    ("created", "date", "When the project file was written.", "—"),
    ("updated", "date", "When it last changed.", "—"),
    (
        "journal_since",
        "string",
        'The baseline for changes made outside catalyst: the product commit after which every commit\'s changes must be in the journal (`catalyst init` writes `HEAD`); `""` checks the whole history.',
        "`check`: warning if absent (history not checked); unrecorded changes after it reported (§7).",
    ),
    (
        "strict_journal",
        "boolean",
        "Optional, default `false`: `true` makes unrecorded changes errors before format `1.0`.",
        "—",
    ),
)
# Keys only an older project file carries: read, never written.
LEGACY_KEYS: tuple[tuple[str, str], ...] = (
    ("name", "`project_name` before it had that name."),
    ("framework_version", "`kernel_version` before 0.35.0."),
    ("agent-source", "A path to the criterion, written by kernels before 0.37.0; honoured when present."),
    (
        "identity",
        "`local` or `oidc` (0.105.x, design 28); migration 0.106.0 moves the pointer into `IAM/identity.json`.",
    ),
    ("identity_issuer", "The provider's issuer (0.105.x); migration 0.106.0 moves it into `IAM/identity.json`."),
    ("identity_client", "The provider's login client (0.105.x); migration 0.106.0 moves it into `IAM/identity.json`."),
)
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


def legacy_parts(project_root: Path, criterion: Path) -> list[str]:
    """What of a deployment is still a 0.x model (R3.4): a `<name>.catalyst`
    pointer instead of `catalyst.toml`, a criterion inside the project instead
    of catalyst's home. Empty for a current deployment."""
    parts = []
    found = find(project_root)
    if found is not None and found.suffix == LEGACY_SUFFIX:
        parts.append(f"the legacy pointer {found.name}")
    try:
        homed = criterion.resolve().is_relative_to(home().resolve())
    except OSError:
        homed = False
    if not homed:
        parts.append(f"a criterion outside catalyst's home ({LEGACY_DIRNAME} in the project, or a path)")
    return parts


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
