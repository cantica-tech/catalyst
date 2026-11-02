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
    # what the item template's cell tells its author (module format v3)
    hint: str = ""


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
    # state -> the conditions entering it requires, each (condition, argument):
    # children_closed / nonempty <field>, section_written <heading>, holds <condition>
    guards: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    # when an open entity is due: "<date field>" or "<date field> + <n> days" (W2)
    due: str | None = None


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
    # module format v3: the sections a new artifact carries, each (heading,
    # one-line hint), and the definition text catalyst composes and freezes
    sections: list[tuple[str, str]] = field(default_factory=list)
    definition: str = ""
    generated: bool = False  # declared in a v3 module.yaml: its template and definition are generated
    # whether a person who is not an admin may create it (design 31 §4.1): a module's types by default
    contributors_create: bool = True
    # the one command that creates it (`/open-case`), when its module declares one (`created_by:`): the kernel
    # composes no generic `/create <type>` for it, and `catalyst new` refuses outside that command (REQ-000113)
    created_by: str | None = None


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


@dataclass(frozen=True)
class Tier:
    """A ceremony tier (rr-META-006): `artifact` is the entity type the tier
    opens, `none` when it needs no artifact (only its journal entry), `any`
    when unstated; `commit` the subject prefix a tier with no artifact uses."""

    id: str
    artifact: str = "any"
    commit: str | None = None

    @property
    def needs_artifact(self) -> bool:
        return self.artifact != "none"


# The tiers of a module that declares none.
DEFAULT_TIERS: tuple[Tier, ...] = (
    Tier("chore", "none", "chore:"),
    Tier("fix"),
    Tier("feature"),
)


@dataclass
class ModuleManifest:
    id: str
    name: str
    version: str
    description: str
    grounding_type: str  # e.g., "rule"
    kernel_version: str | None = None  # the kernel versions it works with, e.g. ">=0.42.0"
    entity_types: dict[str, ETD] = field(default_factory=dict)
    commands: dict[str, CommandRegistration] = field(default_factory=dict)
    skills: list[SkillRegistration] = field(default_factory=list)
    templates: list[TemplateRegistration] = field(default_factory=list)
    required_paths: list[RequiredPath] = field(default_factory=list)
    tiers: list[Tier] = field(default_factory=list)  # empty: DEFAULT_TIERS
    # module v3 M4: the module's own meta-rule and invariant namespace
    # (`rr-<NS>-NNN`, `INV-<NS>-n`) and old IDs that now name new ones
    namespace: str | None = None
    aliases: dict[str, str] = field(default_factory=dict)
    path: Path | None = None  # the module directory it was loaded from


def _fold_block_scalars(lines: list[str]) -> list[str]:
    """`key: >` (folded) or `key: |` (literal) and the more-indented lines
    under it, as one `key: "<text>"` line."""
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(\s*)(- )?([^:#]+):\s*([>|])[-+]?\s*$", line)
        if not m:
            out.append(line)
            i += 1
            continue
        indent = len(m.group(1)) + (2 if m.group(2) else 0)
        body: list[str] = []
        i += 1
        while i < len(lines) and (not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip(" ")) > indent):
            body.append(lines[i].rstrip())
            i += 1
        while body and not body[-1]:
            body.pop()
        margin = min((len(b) - len(b.lstrip(" ")) for b in body if b), default=0)
        # folded: one line; literal: the lines as written, less their common indent
        text = " ".join(b.strip() for b in body if b) if m.group(4) == ">" else "\n".join(b[margin:] for b in body)
        out.append(f"{m.group(1)}{m.group(2) or ''}{m.group(3)}: {json.dumps(text)}")
    return out


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """catalyst's YAML reader for module and entity files, with no external
    dependency: maps, lists, flow lists and maps, folded and literal blocks
    (whose final newline it drops). A text starting with `{` is read as JSON."""
    text = text.strip()
    if not text:
        return {}
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # always catalyst's own reader, never an optional library: a module file
    # parses the same on every machine
    lines = _fold_block_scalars(text.splitlines())
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


def _split_flow(body: str) -> list[str]:
    """Top-level comma-separated parts of a flow collection's body."""
    parts, depth, quote, cur = [], 0, "", []
    for ch in body:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur).strip())
    return parts


def _parse_scalar(val: str) -> Any:
    if val.startswith("[") and val.endswith("]"):  # a flow list: [a, b]
        return [_parse_scalar(p) for p in _split_flow(val[1:-1])]
    if val.startswith("{") and val.endswith("}"):  # a flow map: { k: v, ... }
        out: dict[str, Any] = {}
        for part in _split_flow(val[1:-1]):
            key, _, value = part.partition(":")
            out[key.strip().strip("\"'")] = _parse_scalar(value.strip())
        return out
    if val in ("true", "True", "TRUE"):
        return True
    if val in ("false", "False", "FALSE"):
        return False
    if val in ("null", "None", "~", ""):
        return None
    if val.startswith('"') and val.endswith('"') and len(val) >= 2:
        try:
            return json.loads(val)  # a double-quoted string's escapes (`\n` from a folded `|` block)
        except json.JSONDecodeError:
            return val[1:-1]
    if val.startswith("'") and val.endswith("'") and len(val) >= 2:
        return val[1:-1]
    if val.isdigit():
        return int(val)
    return val


POINTER_SUFFIX = ".catalyst"
DEPLOY_DIRNAME = ".criterion"
REPO_ROOT = Path(__file__).resolve().parent.parent
KERNEL_ENTITIES_DIR = REPO_ROOT / "framework" / "kernel" / "entities"


def _read_pointer(project_root: Path) -> dict[str, Any]:
    """The project file at `project_root` (catalyst.toml, else a legacy
    *.catalyst pointer), or {}."""
    import project_file

    return project_file.read_dir(project_root)


def resolve_deploy_root(project_root: Path | str | None) -> Path | None:
    """The deployment root for `project_root` (same rule as
    check_deployment.find_deploy_root): <project root>/.criterion — symlink
    followed, or the in-project directory — else a pre-0.37.0 pointer's
    legacy "agent-source" when it names a real directory."""
    if not project_root:
        return None
    import project_file

    return project_file.resolve(Path(project_root).resolve())


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
        parsed = parse_simple_yaml(cfg_yaml.read_text(encoding="utf-8"))
        if isinstance(parsed, dict) and parsed.get("module"):
            return str(parsed["module"])

    mod_yaml = root / DEPLOY_DIRNAME / "module.yaml"
    if mod_yaml.is_file():
        parsed = parse_simple_yaml(mod_yaml.read_text(encoding="utf-8"))
        if isinstance(parsed, dict) and parsed.get("id"):
            return str(parsed["id"])

    return None


def v3_entity(prefix: str, spec: dict[str, Any]) -> ETD:
    """A type declared inline in a v3 `module.yaml` (`entities:`), as the
    same ETD its v2 schema file would give: fields as a map, `to` for a
    reference's target (a list for several), `values` for an enum, the
    `Status` field from `states` (`status_hint:` for its cell), `hint:` for
    what a field's cell tells the author, `storage: rows` for a type kept as table
    rows; plus its sections and definition."""
    name = str(spec.get("name") or prefix)
    states = [str(x) for x in spec.get("states") or ["Open"]]
    fields: list[dict[str, Any]] = [{"name": "ID", "kind": "text", "required": True}]
    fields.append(
        {"name": "Status", "kind": "enum", "required": True, "allowed_values": states, "hint": spec.get("status_hint")}
    )
    for fname, fspec in (spec.get("fields") or {}).items():
        f = fspec if isinstance(fspec, dict) else {"kind": str(fspec)}
        to = f.get("to")
        fields.append(
            {
                "name": str(fname),
                "kind": str(f.get("kind") or "text"),
                "required": bool(f.get("required", False)),
                "allowed_values": [str(v) for v in f.get("values") or []],
                "target_type": "|".join(str(t) for t in to) if isinstance(to, list) else (str(to) if to else None),
                "backref": f.get("backref"),
                "required_when_closed": bool(f.get("required_when_closed", False)),
                "hint": f.get("hint"),
            }
        )
    grounding = spec.get("grounding") or "none"
    grounding_field = spec.get("grounding_field")
    if isinstance(grounding, dict):  # { inherited_from: Parent } or { required: Targets }
        (kind, field_name), *_ = grounding.items()
        grounding = "inherited" if kind == "inherited_from" else str(kind)
        grounding_field = str(field_name)
    etd = parse_etd_dict(
        {
            "id_prefix": prefix,
            "name": name,
            "plural_name": spec.get("plural") or f"{name}s",
            "folder": spec.get("folder") or prefix.lower(),
            "location": spec.get("location") or "",
            "grounding": grounding,
            "grounding_field": grounding_field,
            "naming": "free-form" if spec.get("storage") == "rows" else "id-summary",
            "fields": fields,
            "workflow": {
                "initial": spec.get("initial") or states[0],
                "states": states,
                "closed_states": [str(x) for x in spec.get("closed") or []],
                "guards": spec.get("guards") or {},
                "due": spec.get("due"),
            },
        }
    )
    for section in spec.get("sections") or []:
        if isinstance(section, dict):
            (heading, hint), *_ = section.items()
            etd.sections.append((str(heading), str(hint or "")))
        else:
            etd.sections.append((str(section), ""))
    etd.definition = str(spec.get("definition") or "").strip()
    etd.generated = True
    etd.contributors_create = spec.get("contributors_create", True) is not False
    etd.created_by = creating_command(spec.get("created_by"))
    return etd


def creating_command(value: Any) -> str | None:
    """A declared `created_by:` as `/<command>` (`open-case`, `/open-case` and `/create case` read as `/open-case`,
    `/open-case` and `/create-case`), or None when there is none."""
    words = str(value or "").strip().lstrip("/").split()
    return "/" + "-".join(words) if words else None


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
                    allowed_values=[str(v) for v in f.get("allowed_values") or []],
                    target_type=f.get("target_type"),
                    backref=f.get("backref"),
                    required_when_closed=bool(f.get("required_when_closed", False)),
                    hint=str(f.get("hint") or ""),
                )
            )

    wf_raw = d.get("workflow", {})
    if isinstance(wf_raw, dict):
        guards: dict[str, list[tuple[str, str]]] = {}
        for state, conditions in (wf_raw.get("guards") or {}).items():
            for cond in conditions if isinstance(conditions, list) else [conditions]:
                if isinstance(cond, dict):
                    guards.setdefault(str(state), []).extend((str(k), str(v)) for k, v in cond.items())
        transitions = [
            WorkflowTransition(from_state=str(t["from"]), to_state=str(t["to"]))
            for t in wf_raw.get("transitions") or []
            if isinstance(t, dict) and "from" in t and "to" in t
        ]  # BUG: declared since the ETD schema's first version, never read until now
        wf = WorkflowDefinition(
            initial=wf_raw.get("initial", "Open"),
            states=wf_raw.get("states", []),
            closed_states=wf_raw.get("closed_states", []),
            transitions=transitions,
            guards=guards,
            due=str(wf_raw["due"]) if wf_raw.get("due") else None,
        )
    else:
        wf = WorkflowDefinition(initial="Open", states=["Open"], closed_states=[])

    etd = ETD(
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
    etd.created_by = creating_command(d.get("created_by"))
    return etd


def load_etd_file(path: Path) -> ETD | None:
    """Parse one ETD YAML file, or None if it is missing or malformed."""
    if not path.is_file():
        return None
    data = parse_simple_yaml(path.read_text(encoding="utf-8"))
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
        dirs.extend(
            [
                pr / DEPLOY_DIRNAME / "modules" / module_id,
                pr / "framework" / "modules" / module_id,
                # A module's own repository, checked out next to the project.
                pr.parent / f"catalyst-{module_id}",
            ]
        )
    dirs.extend(
        [
            REPO_ROOT / "framework" / "modules" / module_id,
            REPO_ROOT.parent / f"catalyst-{module_id}",
        ]
    )
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


def load_module(
    project_root: Path | str | None = None, module_id: str | None = None, module_dir: Path | None = None
) -> ModuleManifest | None:
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
    data = parse_simple_yaml((mdir / "module.yaml").read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None

    etds: dict[str, ETD] = {}
    if str(data.get("format", "")) == "3":
        for prefix, spec in (data.get("entities") or {}).items():
            if isinstance(spec, dict):
                etds[str(prefix)] = v3_entity(str(prefix), spec)
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
            required_paths.append(
                RequiredPath(
                    path=str(r["path"]),
                    invariant=r.get("invariant"),
                    seed=r.get("seed"),
                )
            )

    tiers: list[Tier] = []
    for t in data.get("tiers") or []:
        if isinstance(t, dict) and t.get("id"):
            tiers.append(
                Tier(
                    id=str(t["id"]),
                    artifact=str(t.get("artifact") or "any"),
                    commit=str(t["commit"]) if t.get("commit") else None,
                )
            )

    mid = str(data.get("id", target_id))
    return ModuleManifest(
        id=mid,
        name=str(data.get("name", mid)),
        version=str(data.get("version", "1.0.0")),
        description=data.get("description", "") or "",
        grounding_type=data.get("grounding_type", "rule") or "rule",
        kernel_version=str(data["kernel_version"]) if data.get("kernel_version") else None,
        entity_types=etds,
        commands=cmds,
        templates=templates,
        required_paths=required_paths,
        tiers=tiers,
        namespace=str(data["namespace"]).upper() if data.get("namespace") else None,
        aliases={str(k): str(v) for k, v in (data.get("aliases") or {}).items()},
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
