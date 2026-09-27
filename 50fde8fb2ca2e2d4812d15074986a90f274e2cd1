#!/usr/bin/env python3
"""Module Loader & Registry Engine for Catalyst (Python).

Loads the kernel's own entity types (framework/kernel/entities/) and, for a
project, its active process module: the module declared by the project's
*.catalyst pointer, with its ETDs (Entity Type Definitions), command
registrations, templates and grounding type. Nothing module-specific is
built in: when no module is declared or found, callers get None and run
kernel-only.

Exposes query functions:
- resolve_module_id(project_root) -> str | None
- load_module(project_root, module_id) -> ModuleManifest | None
- load_kernel_entities() -> dict[str, ETD]
- get_active_etds(manifest) -> dict[str, ETD]
- get_grounding_type(manifest) -> str
- resolve_command(manifest, name) -> CommandRegistration | None
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FieldDefinition:
    name: str
    kind: str  # text, enum, ref, ref-list, date, user, user-list
    required: bool = False
    allowed_values: list[str] = field(default_factory=list)
    target_type: str | None = None
    backref: str | None = None
    # must be non-empty once the entity's Status is one of its workflow's
    # closed states (e.g. a feature cannot close without its steps)
    required_when_closed: bool = False


@dataclass
class WorkflowTransition:
    from_state: str
    to_state: str


@dataclass
class WorkflowDefinition:
    initial: str
    states: list[str] = field(default_factory=list)
    closed_states: list[str] = field(default_factory=list)
    transitions: list[WorkflowTransition] = field(default_factory=list)


@dataclass
class ETD:
    id_prefix: str
    name: str
    plural_name: str
    folder: str
    grounding: str  # "required" | "inherited" | "none"
    grounding_field: str | None = None
    # "id-summary" (files named <id>-<short-summary>.md) or "free-form"
    # (files keyed by a free-form name, exempt from that naming check).
    naming: str = "id-summary"
    # The folder's parent inside the working copy ("" = the working copy's
    # root), e.g. "development" for development/<folder>/.
    location: str = ""
    fields: list[FieldDefinition] = field(default_factory=list)
    workflow: WorkflowDefinition = field(
        default_factory=lambda: WorkflowDefinition(initial="Open", states=["Open"], closed_states=[])
    )


@dataclass
class CommandRegistration:
    name: str
    description: str
    argument_hint: str | None = None
    spec_path: str | None = None


@dataclass
class SkillRegistration:
    name: str
    spec_path: str


@dataclass
class TemplateRegistration:
    entity_type: str
    template_path: str


@dataclass
class RequiredPath:
    """A deployment path the module requires to always exist."""
    path: str
    invariant: str | None = None
    seed: str | None = None


@dataclass
class ModuleManifest:
    id: str
    name: str
    version: str
    description: str
    grounding_type: str  # e.g., "rule"
    entity_types: dict[str, ETD] = field(default_factory=dict)
    commands: dict[str, CommandRegistration] = field(default_factory=dict)
    skills: list[SkillRegistration] = field(default_factory=list)
    templates: list[TemplateRegistration] = field(default_factory=list)
    required_paths: list[RequiredPath] = field(default_factory=list)
    path: Path | None = None  # the module directory it was loaded from


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Lightweight YAML parser for simple nested dicts/lists without external dependencies.
    Supports basic key: value, lists (- item), and simple nested maps. Also handles JSON fallback."""
    text = text.strip()
    if not text:
        return {}
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    try:
        import yaml
        res = yaml.safe_load(text)
        if isinstance(res, dict):
            return res
    except Exception:
        pass

    lines = text.splitlines()
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    for line in lines:
        raw_line = line
        # Strip comments
        if "#" in line:
            parts = line.split("#", 1)
            if not (parts[0].count('"') % 2 == 1 or parts[0].count("'") % 2 == 1):
                line = parts[0]
        line_stripped = line.strip()
        if not line_stripped:
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))

        while stack and stack[-1][0] >= indent:
            stack.pop()

        parent = stack[-1][1] if stack else root

        if line_stripped.startswith("- "):
            val = line_stripped[2:].strip()
            # If parent is an empty dict that was created for a key with empty value,
            # convert stack parent or replace in grandparent to list
            if isinstance(parent, dict):
                # find grandparent key that points to this empty dict parent
                if len(stack) >= 2:
                    grandparent = stack[-2][1]
                    if isinstance(grandparent, dict):
                        for gk, gv in list(grandparent.items()):
                            if gv is parent:
                                new_list: list[Any] = []
                                grandparent[gk] = new_list
                                stack[-1] = (stack[-1][0], new_list)
                                parent = new_list
                                break

            if isinstance(parent, list):
                if ":" in val and not (val.startswith('"') or val.startswith("'")):
                    k, v = val.split(":", 1)
                    item_dict = {k.strip(): _parse_scalar(v.strip())}
                    parent.append(item_dict)
                    stack.append((indent, item_dict))
                else:
                    parent.append(_parse_scalar(val))
        elif ":" in line_stripped:
            k, v = line_stripped.split(":", 1)
            k = k.strip()
            v = v.strip()
            if not v:
                nested_container: dict[str, Any] | list[Any] = {}
                if isinstance(parent, dict):
                    parent[k] = nested_container
                elif isinstance(parent, list) and parent and isinstance(parent[-1], dict):
                    parent[-1][k] = nested_container
                stack.append((indent, nested_container))
            else:
                parsed_val = _parse_scalar(v)
                if isinstance(parent, dict):
                    parent[k] = parsed_val
                elif isinstance(parent, list) and parent and isinstance(parent[-1], dict):
                    parent[-1][k] = parsed_val

    return root


def _parse_scalar(val: str) -> Any:
    if val in ("true", "True", "TRUE"):
        return True
    if val in ("false", "False", "FALSE"):
        return False
    if val in ("null", "None", "~", ""):
        return None
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    if val.isdigit():
        return int(val)
    return val


POINTER_SUFFIX = ".catalyst"
DEPLOY_DIRNAME = ".criterion"
REPO_ROOT = Path(__file__).resolve().parent.parent
KERNEL_ENTITIES_DIR = REPO_ROOT / "framework" / "kernel" / "entities"


def _read_pointer(project_root: Path) -> dict[str, Any]:
    """The first parseable *.catalyst pointer at `project_root`, or {}."""
    for pointer in sorted(project_root.glob(f"*{POINTER_SUFFIX}")):
        try:
            data = json.loads(pointer.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return {}


def resolve_deploy_root(project_root: Path | str | None) -> Path | None:
    """The deployment root for `project_root` (same rule as
    check_deployment.find_deploy_root): <project root>/.criterion — symlink
    followed, or the in-project directory — else a pre-0.37.0 pointer's
    legacy "agent-source" when it names a real directory."""
    if not project_root:
        return None
    root = Path(project_root).resolve()
    local = root / DEPLOY_DIRNAME
    if local.is_dir():
        return local
    source = _read_pointer(root).get("agent-source")
    if source:
        candidate = Path(str(source)).expanduser()
        if candidate.is_dir():
            return candidate
    return None


def resolve_module_id(project_root: Path | str | None) -> str | None:
    """The active module id declared for `project_root`: the `module` field
    of its *.catalyst pointer, then `.criterion/config.yaml` `module:`, then
    `.criterion/module.yaml` `id:`. None when no module is declared."""
    if not project_root:
        return None
    root = Path(project_root).resolve()

    declared = _read_pointer(root).get("module")
    if declared:
        return str(declared)

    cfg_yaml = root / DEPLOY_DIRNAME / "config.yaml"
    if cfg_yaml.is_file():
        parsed = parse_simple_yaml(cfg_yaml.read_text())
        if isinstance(parsed, dict) and parsed.get("module"):
            return str(parsed["module"])

    mod_yaml = root / DEPLOY_DIRNAME / "module.yaml"
    if mod_yaml.is_file():
        parsed = parse_simple_yaml(mod_yaml.read_text())
        if isinstance(parsed, dict) and parsed.get("id"):
            return str(parsed["id"])

    return None

def parse_etd_dict(d: dict[str, Any]) -> ETD:
    id_prefix = d.get("id_prefix", "")
    name = d.get("name", id_prefix)
    plural_name = d.get("plural_name", f"{name}s")
    folder = d.get("folder", id_prefix.lower())
    grounding = d.get("grounding", "none")
    grounding_field = d.get("grounding_field")
    naming = str(d.get("naming") or "id-summary")
    location = str(d.get("location") or "").strip("/")

    fields: list[FieldDefinition] = []
    for f in d.get("fields", []):
        if isinstance(f, dict):
            fields.append(
                FieldDefinition(
                    name=f.get("name", ""),
                    kind=f.get("kind", "text"),
                    required=bool(f.get("required", False)),
                    allowed_values=f.get("allowed_values", []) or [],
                    target_type=f.get("target_type"),
                    backref=f.get("backref"),
                    required_when_closed=bool(f.get("required_when_closed", False)),
                )
            )

    wf_raw = d.get("workflow", {})
    if isinstance(wf_raw, dict):
        wf = WorkflowDefinition(
            initial=wf_raw.get("initial", "Open"),
            states=wf_raw.get("states", []),
            closed_states=wf_raw.get("closed_states", []),
        )
    else:
        wf = WorkflowDefinition(initial="Open", states=["Open"], closed_states=[])

    return ETD(
        id_prefix=id_prefix,
        name=name,
        plural_name=plural_name,
        folder=folder,
        grounding=grounding,
        grounding_field=grounding_field,
        naming=naming,
        location=location,
        fields=fields,
        workflow=wf,
    )


def load_etd_file(path: Path) -> ETD | None:
    """Parse one ETD YAML file, or None if it is missing or malformed."""
    if not path.is_file():
        return None
    data = parse_simple_yaml(path.read_text())
    if not isinstance(data, dict) or not data.get("id_prefix"):
        return None
    return parse_etd_dict(data)


def load_kernel_entities(entities_dir: Path | None = None) -> dict[str, ETD]:
    """The kernel's own entity types (framework/kernel/entities/*.yaml),
    keyed by id prefix. These are present whatever module is active."""
    base = entities_dir or KERNEL_ENTITIES_DIR
    etds: dict[str, ETD] = {}
    if not base.is_dir():
        if entities_dir is None:
            return _embedded_kernel_entities()
        return etds
    for path in sorted(base.glob("*.yaml")):
        etd = load_etd_file(path)
        if etd is not None:
            etds[etd.id_prefix] = etd
    return etds


def _embedded_kernel_entities() -> dict[str, ETD]:
    """The kernel's entity types as embedded in the `catalyst.pyz` zipapp by
    scripts/package_release.py (no repository to read them from there)."""
    try:
        from kernel_entities_embedded import ENTITIES  # type: ignore
    except ImportError:
        return {}
    etds: dict[str, ETD] = {}
    for text in ENTITIES.values():
        data = parse_simple_yaml(text)
        if isinstance(data, dict) and data.get("id_prefix"):
            etd = parse_etd_dict(data)
            etds[etd.id_prefix] = etd
    return etds


def module_search_dirs(project_root: Path | str | None, module_id: str) -> list[Path]:
    """Candidate directories for module `module_id`, in search order."""
    dirs: list[Path] = []
    if project_root:
        pr = Path(project_root).resolve()
        deploy = resolve_deploy_root(pr)
        if deploy is not None:
            dirs.append(deploy / "modules" / module_id)
        dirs.extend([
            pr / DEPLOY_DIRNAME / "modules" / module_id,
            pr / "framework" / "modules" / module_id,
            # A module's own repository, checked out next to the project.
            pr.parent / f"catalyst-{module_id}",
        ])
    dirs.extend([
        REPO_ROOT / "framework" / "modules" / module_id,
        REPO_ROOT.parent / f"catalyst-{module_id}",
    ])
    unique: list[Path] = []
    for d in dirs:
        if d not in unique:
            unique.append(d)
    return unique


def find_module_dir(project_root: Path | str | None, module_id: str) -> Path | None:
    """The first search directory holding a module.yaml, or None."""
    for mdir in module_search_dirs(project_root, module_id):
        if (mdir / "module.yaml").is_file():
            return mdir
    return None


def load_module(project_root: Path | str | None = None,
                module_id: str | None = None,
                module_dir: Path | None = None) -> ModuleManifest | None:
    """Load the manifest of module `module_id` (or of the module declared for
    `project_root`, or the one at `module_dir`). None when no module is
    declared or it cannot be found."""
    if module_dir is not None:
        mdir = module_dir if (module_dir / "module.yaml").is_file() else None
        target_id = module_dir.name
    else:
        target_id = module_id or resolve_module_id(project_root)
        if not target_id:
            return None
        mdir = find_module_dir(project_root, target_id)
    if mdir is None:
        return None
    data = parse_simple_yaml((mdir / "module.yaml").read_text())
    if not isinstance(data, dict):
        return None

    etds: dict[str, ETD] = {}
    for item in data.get("entity_types") or []:
        if not isinstance(item, dict):
            continue
        eid, rel_schema = item.get("id"), item.get("schema")
        if eid and rel_schema:
            etd = load_etd_file(mdir / str(rel_schema))
            if etd is not None:
                etds[str(eid)] = etd

    cmds: dict[str, CommandRegistration] = {}
    for c in data.get("commands") or []:
        if isinstance(c, dict) and c.get("name"):
            cname = str(c["name"])
            cmds[cname] = CommandRegistration(
                name=cname,
                description=c.get("description", "") or "",
                argument_hint=c.get("argument_hint"),
                spec_path=c.get("spec_path"),
            )

    templates: list[TemplateRegistration] = []
    for t in data.get("templates") or []:
        if isinstance(t, dict) and t.get("entity_type") and t.get("template_path"):
            templates.append(TemplateRegistration(str(t["entity_type"]), str(t["template_path"])))

    required_paths: list[RequiredPath] = []
    for r in data.get("required_paths") or []:
        if isinstance(r, dict) and r.get("path"):
            required_paths.append(RequiredPath(
                path=str(r["path"]),
                invariant=r.get("invariant"),
                seed=r.get("seed"),
            ))

    mid = str(data.get("id", target_id))
    return ModuleManifest(
        id=mid,
        name=str(data.get("name", mid)),
        version=str(data.get("version", "1.0.0")),
        description=data.get("description", "") or "",
        grounding_type=data.get("grounding_type", "rule") or "rule",
        entity_types=etds,
        commands=cmds,
        templates=templates,
        required_paths=required_paths,
        path=mdir,
    )

def get_active_etds(manifest: ModuleManifest) -> dict[str, ETD]:
    """Return dictionary of active ETDs keyed by ID prefix."""
    return manifest.entity_types


def get_grounding_type(manifest: ModuleManifest) -> str:
    """Return the module's grounding artifact type (a kernel type, e.g. 'rule')."""
    return manifest.grounding_type


def resolve_command(manifest: ModuleManifest, name: str) -> CommandRegistration | None:
    """Resolve command registration by name."""
    clean_name = name.lstrip("/")
    return manifest.commands.get(clean_name)
