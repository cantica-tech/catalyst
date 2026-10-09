"""VS Code workspace criterion (roadmap R3.1b, ADR-010).

A workspace is a `<name>.code-workspace` file; its members are its folders
holding a `catalyst.toml`. Its meta criterion,
`$CATALYST_HOME/workspaces/<name>/criterion`, holds what the members share —
rules and domains, users and roles — with its own journal and no process
module. Each member's `catalyst.toml` names it (`workspace = "<name>"`), and
loading a member also loads the workspace's rules, domains and users,
read-only (`corpus._inherit_workspace`).
"""
from __future__ import annotations

import datetime
import json
import re
import shutil
import subprocess
from pathlib import Path

import project_file

from catalyst import journal
from catalyst.deployment import load_working_copy
from catalyst.ids import generate_userid


class WorkspaceError(Exception):
    pass


def _strip_jsonc(text: str) -> str:
    """VS Code's workspace files are JSON with comments and trailing commas."""
    out, i, in_str = [], 0, False
    while i < len(text):
        ch = text[i]
        if in_str:
            out.append(ch)
            if ch == "\\":
                out.append(text[i + 1:i + 2])
                i += 2
                continue
            if ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
            out.append(ch)
        elif text.startswith("//", i):
            i = text.find("\n", i)
            i = len(text) if i == -1 else i
            continue
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end == -1 else end + 2
            continue
        else:
            out.append(ch)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def read(workspace_file: Path) -> tuple[str, list[Path]]:
    """The workspace's name (the file's stem) and its folders, absolute."""
    if not workspace_file.name.endswith(".code-workspace"):
        raise WorkspaceError(f"{workspace_file} is not a .code-workspace file")
    try:
        data = json.loads(_strip_jsonc(workspace_file.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        raise WorkspaceError(f"cannot read {workspace_file}: {exc}") from exc
    name = workspace_file.name[:-len(".code-workspace")]
    base = workspace_file.resolve().parent
    folders = []
    for entry in data.get("folders", []) if isinstance(data, dict) else []:
        path = entry.get("path") if isinstance(entry, dict) else None
        if path:
            folders.append((base / path).resolve() if not Path(path).is_absolute() else Path(path))
    return name, folders


def members(workspace_file: Path) -> list[Path]:
    """The workspace's folders that are catalyst projects (`catalyst.toml`)."""
    return [f for f in read(workspace_file)[1] if (f / project_file.NAME).is_file()]


def _skeleton(root: Path, kernel: Path, user: dict) -> list[Path]:
    """A kernel-only criterion: rules and domains, users and roles, journal."""
    written = []

    def write(rel: str, text: str) -> None:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)

    write("rules/rules.md", "# Rules index\n\nRules every member of this workspace shares.\n")
    write("rules/domains/domains.md", "# Domains index\n\n| Code | Document | Defined |\n|---|---|---|\n")
    write("IAM/users/users.json", json.dumps({"users": [user]}, indent=2) + "\n")
    roles = kernel / "templates" / "roles.template.json"
    write("IAM/roles/roles.json", roles.read_text(encoding="utf-8") if roles.is_file() else '{"roles": []}\n')
    write("development/journal.jsonl", "")
    write("version.txt", (kernel.parent.parent / "version.txt").read_text(encoding="utf-8")
          if (kernel.parent.parent / "version.txt").is_file() else "0.0.0\n")
    write("README.md", "# Workspace criterion\n\nShared by the workspace's member projects (their "
          "`catalyst.toml` names it): rules and domains, users and roles. Read-only from a member.\n")
    write(".gitignore", "/.venv\n")
    return written


def init(workspace_file: Path, kernel: Path, user_name: str, git_username: str | None = None) -> tuple[Path, list[str]]:
    name, _ = read(workspace_file)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
        raise WorkspaceError(f"workspace name '{name}' must be letters, digits, '.', '_' or '-'")
    root = project_file.workspace_criterion(name)
    if root.exists() and any(root.iterdir()):
        raise WorkspaceError(f"a workspace criterion named '{name}' already exists ({root})")
    projects = members(workspace_file)
    root.mkdir(parents=True, exist_ok=True)
    user = {"name": user_name, "git_username": git_username or user_name, "roles": ["Admin"],
            "registered": datetime.date.today().isoformat(), "active": True, "notes": "",
            "userid": generate_userid(set())}
    written = _skeleton(root, kernel, user)
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True, capture_output=True)
    steps = [f"created the workspace criterion {root}"]
    for project in projects:
        toml = project / project_file.NAME
        data = project_file.read(toml)
        if project_file.workspace_of(data) not in (None, name):
            steps.append(f"left {project.name}: it belongs to workspace '{data['workspace']}'")
            continue
        data["workspace"] = name
        data["updated"] = datetime.date.today().isoformat()
        project_file.write(toml, data)
        steps.append(f"{project.name}: catalyst.toml names workspace '{name}' (not committed)")
    dep = load_working_copy(root)
    journal.append(dep, journal.AppendRequest(
        command="catalyst workspace init", action="create", artifact=f"workspace {name}", targets=[],
        intent=[f"Create the meta criterion of the VS Code workspace {workspace_file.name}: the rules, domains, "
                f"users and roles its {len(projects)} member project(s) share."],
        files=[str(p) for p in written if p.name != "journal.jsonl"], actor=git_username or user_name,
        allow_unchanged=True, tier="chore"))
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "-c", f"user.name={user_name}", "-c",
                    f"user.email={(git_username or 'catalyst')}@catalyst.invalid", "commit", "-q", "-m",
                    f"catalyst workspace init: {name}"], check=True, capture_output=True)
    return root, steps


def status(workspace_file: Path) -> dict:
    name, folders = read(workspace_file)
    root = project_file.workspace_criterion(name)
    rows = []
    for folder in folders:
        data = project_file.read_dir(folder)
        rows.append({"folder": str(folder), "project": project_file.project_name(data),
                     "member": project_file.workspace_of(data) == name})
    return {"workspace": name, "criterion": str(root) if root.is_dir() else None, "folders": rows}
