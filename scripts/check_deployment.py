#!/usr/bin/env python3
"""Validate a deployed .criterion/ against catalyst's structural invariants.

This is the enforcement layer of the anti-drift architecture: the invariants an
agent is asked to uphold (INV-5..INV-8, INV-16, INV-17, INV-23, INV-24,
INV-26) are re-checked here deterministically, so they hold every time
regardless of what any agent or human did. Mirrors the existing
scripts/check_plugins.py pattern.

Module-agnostic: entity folders, index names and definition types come from
the kernel's own entity types (framework/kernel/entities/) plus the ETDs of
the project's active module (resolved through module_loader from the
*.catalyst pointer's `module` field). A module's own always-present paths
are declared in its module.yaml `required_paths:`. When no module resolves,
only the kernel checks run.

Exit 0 = clean, exit 1 = violations found (fails CI / Stop hook).

Scope note: only checks the structural invariants that are machine-verifiable
from the tree. Behavioural rules (INV-1..INV-4) are not checkable here and remain
the agent's responsibility, re-grounded via INVARIANTS.md.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from module_loader import (
    ModuleManifest,
    RequiredPath,
    load_kernel_entities,
    load_module,
)

DEPLOY_DIRNAME = ".criterion"
# <app-name>.catalyst — the tracked pointer file at a target project's root.
# Its "agent-source" field names where the actual .criterion/ working
# copy lives (agent-owned space, not necessarily inside the project tree).
POINTER_SUFFIX = ".catalyst"
# <id>-<short-summary>.md ; id like recon-000001, rule prefixes, domains, etc.
NAME_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*-[a-z0-9][a-z0-9-]*\.md$", re.I)
# A trailing all-digit segment (e.g. "br-AUTH-002.md") is a bare ID with no
# descriptive summary — NAME_RE alone can't reject it, since a run of digits
# satisfies the same character class as a real summary word would.
BARE_ID_RE = re.compile(r"-\d+\.md$", re.I)
# TEMPLATE-<TYPE>.md (legacy, pre-INV-20) or TEMPLATE-<TYPE>-vN.md (current).
TEMPLATE_RE = re.compile(r"^TEMPLATE-[A-Z-]+(?:-v\d+)?\.md$")
# An all-uppercase name (README.md, DEPLOYMENT.md, a module's own fixed
# documents) is a fixed document, never an <id>-<summary> artifact.
FIXED_DOC_RE = re.compile(r"^[A-Z][A-Z_-]*\.md$")
# templates-<type>.md — the per-artifact-type templates catalog (INV-20).
TEMPLATES_CATALOG_RE = re.compile(r"^templates-[a-z-]+\.md$")
# git hash-object is a 40-char hex SHA-1.
HASH_RE = re.compile(r"^[0-9a-f]{40}$")
# 8-char case-sensitive alphanumeric — the "contains an uppercase letter"
# half of INV-26's userid shape is checked separately (a character class
# alone can't express "at least one of").
USERID_RE = re.compile(r"^[A-Za-z0-9]{8}$")
# `## N. `id` Title` or `### `id` Title` — a rule heading, id capturing its
# own trailing digits (group 2) and any suffix segments (group 3), the last
# of which (once INV-26 applies) must be a userid.
RULE_HEADING_RE = re.compile(
    r"^#{2,3}\s+(?:\d+\.\s+)?`([a-z]+-[A-Z][A-Z0-9]*-(\d+)((?:-[a-zA-Z0-9]+)*))`"
)
JOURNAL_REQUIRED_FIELDS = (
    "timestamp", "actor", "command", "action", "artifact", "targets",
    "intent", "files",
)
# Kernel index/fixed file names. Each entity type's own `<folder>.md` index
# (kernel and active module alike) is added by DeploymentModel.
INDEX_NAMES = {
    "rules.md", "domains.md", "meta-tags.md", "epics.md", "stories.md",
    "tasks.md", "spikes.md", "sprints.md", "boards.md", "workflows.md",
    "tickets.md", "reconciliations.md",
    "README.md", "CODE-OF-CONDUCT.md", "version.txt",
    "Rules-of-Rules.md", "rules-of-work-items.md", "DEPLOYMENT.md",
}
# Kernel directories walked by the INV-7 naming check. Entity folders (kernel
# and active module) are added by DeploymentModel.
KERNEL_CHECKED_DIRS = ("rules", "reconciliations", "workflows", "IAM",
                       "development", "work-items")
# Kernel entity types that must each have a definitions/<type>.md (INV-23).
KERNEL_ENTITY_TYPES = (
    "rule", "domain", "user", "role", "reconciliation", "meta-tag",
    "journal", "ledger", "slash-command", "templates-catalog", "workflow",
    "entity",
)


@dataclass
class DeploymentModel:
    """What the checks need to know about entity types: the kernel's plus the
    active module's (if any)."""
    checked_dirs: tuple[str, ...] = KERNEL_CHECKED_DIRS
    index_names: set[str] = field(default_factory=lambda: set(INDEX_NAMES))
    entity_types: tuple[str, ...] = KERNEL_ENTITY_TYPES
    # Entity folders whose files are keyed by a free-form name (ETD
    # `naming: free-form`), exempt from the <id>-<summary> naming check.
    free_form_folders: set[str] = field(default_factory=set)
    # Active-module entity folders, each expected to carry <folder>.md.
    module_folders: tuple[str, ...] = ()
    required_paths: list[RequiredPath] = field(default_factory=list)
    module_id: str | None = None


def _definition_type(name: str) -> str:
    return "-".join(name.lower().split())


def build_model(module: ModuleManifest | None = None) -> DeploymentModel:
    """Derive the DeploymentModel from the kernel's entity types and the
    given active module manifest (None = kernel only)."""
    kernel = load_kernel_entities()
    dirs = list(KERNEL_CHECKED_DIRS)
    index_names = set(INDEX_NAMES)
    types = list(KERNEL_ENTITY_TYPES)
    free_form: set[str] = set()
    for etd in kernel.values():
        if etd.folder not in dirs:
            dirs.append(etd.folder)
        index_names.add(f"{etd.folder}.md")
        if etd.naming == "free-form":
            free_form.add(etd.folder)
    if module is None:
        return DeploymentModel(tuple(dirs), index_names, tuple(types), free_form)

    module_folders: list[str] = []
    for etd in module.entity_types.values():
        module_folders.append(etd.folder)
        if etd.folder not in dirs:
            dirs.append(etd.folder)
        index_names.add(f"{etd.folder}.md")
        if etd.naming == "free-form":
            free_form.add(etd.folder)
    # Definition types: the module's definitions/<type>/ directories when it
    # ships them (they may cover non-entity concepts too), else one per ETD.
    defs_dir = module.path / "definitions" if module.path else None
    if defs_dir is not None and defs_dir.is_dir():
        module_types = sorted(d.name for d in defs_dir.iterdir() if d.is_dir())
    else:
        module_types = [_definition_type(e.name) for e in module.entity_types.values()]
    for t in module_types:
        if t not in types:
            types.append(t)
    for req in module.required_paths:
        index_names.add(Path(req.path).name)
    return DeploymentModel(tuple(dirs), index_names, tuple(types), free_form,
                           tuple(module_folders), list(module.required_paths),
                           module.id)


def _resolve_pointer(pointer_path: Path) -> Path | None:
    """Read a <app-name>.catalyst pointer file's "agent-source" field and
    return it as a Path if it names a real directory, else None (malformed
    or stale pointer — callers fall back to legacy in-tree discovery)."""
    try:
        data = json.loads(pointer_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    source = data.get("agent-source")
    if not source:
        return None
    candidate = Path(source).expanduser()
    return candidate if candidate.is_dir() else None


def find_project_root(start: Path) -> Path | None:
    """The directory at or above `start` holding the *.catalyst pointer (or,
    for a legacy deployment, the .criterion/ directory) — where the active
    module is declared."""
    for base in (start, *start.parents):
        if any(_resolve_pointer(p) is not None
               for p in base.glob(f"*{POINTER_SUFFIX}")):
            return base
        if (base / DEPLOY_DIRNAME).is_dir():
            return base
    return None


def find_deploy_root(start: Path) -> Path | None:
    """Prefer the pointer-file model: a *<app-name>.catalyst file at or above
    `start` whose "agent-source" resolves to a real directory. Fall back to
    the legacy model — a `.criterion/` directory itself at or above
    `start` — for deployments not yet migrated (INV-6)."""
    for base in (start, *start.parents):
        for pointer in sorted(base.glob(f"*{POINTER_SUFFIX}")):
            resolved = _resolve_pointer(pointer)
            if resolved is not None:
                return resolved
        candidate = base / DEPLOY_DIRNAME
        if candidate.is_dir():
            return candidate
    return None


def check_naming(root: Path, model: DeploymentModel | None = None) -> list[str]:
    """INV-7: every rule/domain/artifact file is <id>-<short-summary>.md."""
    model = model or build_model()
    errors: list[str] = []
    # "domains" is no longer top-level (INV-20): it nests under rules/, so
    # the "rules" walk below already covers rules/domains/**/*.md.
    for sub in model.checked_dirs:
        d = root / sub
        if not d.is_dir():
            continue
        for f in d.rglob("*.md"):
            name = f.name
            if (name in model.index_names or TEMPLATE_RE.match(name)
                    or FIXED_DOC_RE.match(name)
                    or TEMPLATES_CATALOG_RE.match(name)):
                continue
            # Every templates/ subdirectory (INV-20) accepts files only —
            # already covered by the two exemptions above (README.md via
            # INDEX_NAMES, the catalog, and the TEMPLATE-*-vN.md itself) —
            # nothing else should ever be there, so no separate skip needed.
            # An entity type declaring `naming: free-form` keys its files by
            # a free-form name, not a sequential <id>-<summary> scheme.
            if f.parent.name in model.free_form_folders:
                continue
            if not NAME_RE.match(name) or BARE_ID_RE.search(name):
                errors.append(f"INV-7 naming: {f.relative_to(root)} is not "
                              f"<id>-<short-summary>.md")
    return errors


def _is_under_domains(f: Path, rules: Path) -> bool:
    """True if f sits under rules/domains/ (INV-20) — domain files are not
    rule documents and are exempt from rule-specific checks below."""
    return "domains" in f.relative_to(rules).parts


def check_single_rule_template(root: Path) -> list[str]:
    """INV-8: at least one TEMPLATE-RULE(-vN).md, and every copy of it lives
    in rules/templates/ (never scattered into a rule-type directory).
    Multiple versions coexisting there is normal — INV-20 versions by
    adding files, never editing in place — so this does not require
    exactly one file, only that none strayed from templates/."""
    rules = root / "rules"
    if not rules.is_dir():
        return ["INV-8: rules/ directory is missing"]
    templates_dir = rules / "templates"
    hits = [f for f in rules.rglob("TEMPLATE-RULE*.md")
            if re.match(r"^TEMPLATE-RULE(-v\d+)?\.md$", f.name)]
    errors = []
    if not hits:
        errors.append("INV-8: no TEMPLATE-RULE(-vN).md found")
        return errors
    stray = [f for f in hits if f.parent != templates_dir]
    if stray:
        errors.append(
            "INV-8: TEMPLATE-RULE(-vN).md must live in rules/templates/, "
            f"found at {[str(f.relative_to(root)) for f in stray]}"
        )
    return errors


def check_rule_indexing(root: Path) -> list[str]:
    """INV-8: every rule file appears in the global rules.md index."""
    rules = root / "rules"
    global_index = rules / "rules.md"
    if not global_index.is_file():
        return ["INV-8: rules/rules.md global index is missing"]
    index_text = global_index.read_text(encoding="utf-8", errors="ignore")
    errors = []
    for f in rules.rglob("*.md"):
        if (f.name in INDEX_NAMES or TEMPLATE_RE.match(f.name)
                or TEMPLATES_CATALOG_RE.match(f.name)
                or _is_under_domains(f, rules)):
            continue
        stem = f.stem
        if stem not in index_text and f.name not in index_text:
            errors.append(f"INV-8 orphan: {f.relative_to(root)} not listed in "
                          f"rules/rules.md")
    return errors


def check_required_headings(root: Path) -> list[str]:
    """INV-8: rule docs carry ## Contents and ## Linked Artifacts — Quick Index."""
    rules = root / "rules"
    errors = []
    for f in rules.rglob("*.md"):
        if (f.name in INDEX_NAMES or TEMPLATE_RE.match(f.name)
                or TEMPLATES_CATALOG_RE.match(f.name)
                or _is_under_domains(f, rules)):
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        if "## Contents" not in text:
            errors.append(f"INV-8 heading: {f.relative_to(root)} missing "
                          f"'## Contents'")
        if "Linked Artifacts" not in text:
            errors.append(f"INV-8 heading: {f.relative_to(root)} missing "
                          f"'## Linked Artifacts — Quick Index'")
    return errors


def _known_userids(root: Path) -> set[str]:
    """Every userid currently registered in IAM/users/users.json, or an
    empty set if the file is missing/malformed (already reported by
    check_users_and_roles_exist / check_users_have_userid)."""
    users_path = root / "IAM" / "users" / "users.json"
    if not users_path.is_file():
        return set()
    try:
        data = json.loads(users_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    users = data.get("users", []) if isinstance(data, dict) else []
    return {
        str(u["userid"]) for u in users
        if isinstance(u, dict) and u.get("userid")
    }


def check_rule_id_shape(root: Path) -> list[str]:
    """INV-26: every rule ID's sequence number is 6-digit, and its final
    segment is a userid naming a real registered user. Unlike
    check_rule_indexing/check_required_headings, Rules-of-Rules.md is
    NOT exempt here: `rr-META-*` ids use the exact same id grammar
    (rr-META-003 names `rr` as one of DOC_PREFIX's own examples) and are
    only exempt from *indexing* (never listed in rules.md), not from the
    shape convention itself. Only the pure bullet-list index (rules.md)
    and template/catalog/domain files are skipped — they carry no real
    rule headings to check."""
    rules = root / "rules"
    if not rules.is_dir():
        return []

    known_userids = _known_userids(root)
    errors: list[str] = []
    for f in rules.rglob("*.md"):
        if (f.name == "rules.md" or TEMPLATE_RE.match(f.name)
                or TEMPLATES_CATALOG_RE.match(f.name)
                or _is_under_domains(f, rules)):
            continue
        for lineno, line in enumerate(
            f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
        ):
            m = RULE_HEADING_RE.match(line)
            if not m:
                continue
            full_id, digits, suffixes = m.group(1), m.group(2), m.group(3)
            if len(digits) != 6:
                errors.append(
                    f"INV-26 width: {f.relative_to(root)}:{lineno} `{full_id}` "
                    f"has a {len(digits)}-digit sequence number, expected 6"
                )
            parts = [p for p in suffixes.split("-") if p]
            userid = parts[-1] if parts else None
            if (not userid or not USERID_RE.match(userid)
                    or not any(c.isupper() for c in userid)):
                errors.append(
                    f"INV-26 signer: {f.relative_to(root)}:{lineno} `{full_id}` "
                    f"has no valid trailing userid suffix"
                )
            elif known_userids and userid not in known_userids:
                errors.append(
                    f"INV-26 signer: {f.relative_to(root)}:{lineno} `{full_id}`'s "
                    f"userid '{userid}' does not match any registered user"
                )
    return errors


def check_module_required_paths(root: Path, model: DeploymentModel) -> list[str]:
    """The active module's `required_paths:` (module.yaml) always exist."""
    errors: list[str] = []
    for req in model.required_paths:
        if (root / req.path).exists():
            continue
        label = req.invariant or f"module {model.module_id}"
        msg = f"{label}: {req.path} is missing"
        if req.seed:
            msg += f" — seed it from {req.seed}"
        errors.append(msg)
    return errors


def _locate_folder(root: Path, folder: str) -> Path | None:
    """An entity folder sits at the deployment root or under development/."""
    for cand in (root / folder, root / "development" / folder):
        if cand.is_dir():
            return cand
    return None


def check_module_indexes(root: Path, model: DeploymentModel) -> list[str]:
    """Every active-module entity folder present in the deployment carries
    its own <folder>.md index."""
    errors: list[str] = []
    for folder in model.module_folders:
        d = _locate_folder(root, folder)
        if d is not None and not (d / f"{folder}.md").is_file():
            errors.append(f"module index: {d.relative_to(root)}/{folder}.md "
                          f"is missing (module {model.module_id})")
    return errors


def check_workflows_index_exists(root: Path) -> list[str]:
    """INV-24: workflows/workflows.md index always exists (empty is fine)."""
    index = root / "workflows" / "workflows.md"
    if not index.is_file():
        return ["INV-24: workflows/workflows.md is missing — seed "
                "workflows/ from templates/workflow.template.md"]
    return []


def check_users_and_roles_exist(root: Path) -> list[str]:
    """INV-16: IAM/users/users.json + IAM/roles/roles.json always exist,
    and users.json has at least one active user."""
    errors: list[str] = []
    users_path = root / "IAM" / "users" / "users.json"
    roles_path = root / "IAM" / "roles" / "roles.json"

    if not roles_path.is_file():
        errors.append("INV-16: IAM/roles/roles.json is missing — seed it "
                      "from templates/roles.template.json")

    if not users_path.is_file():
        errors.append("INV-16: IAM/users/users.json is missing — seed it "
                      "from templates/users.template.json")
        return errors

    try:
        data = json.loads(users_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        errors.append(f"INV-16: IAM/users/users.json is not valid JSON: {exc}")
        return errors

    users = data.get("users", []) if isinstance(data, dict) else []
    if not any(isinstance(u, dict) and u.get("active") for u in users):
        errors.append("INV-16: IAM/users/users.json has no active user — "
                      "a project must have at least one (/user-add)")
    return errors


def check_users_have_userid(root: Path) -> list[str]:
    """INV-26: every registered user has a unique, valid 8-char alphanumeric
    userid (containing at least one uppercase letter)."""
    users_path = root / "IAM" / "users" / "users.json"
    if not users_path.is_file():
        return []  # already reported by check_users_and_roles_exist
    try:
        data = json.loads(users_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []  # already reported by check_users_and_roles_exist

    errors: list[str] = []
    seen: set[str] = set()
    users = data.get("users", []) if isinstance(data, dict) else []
    for u in users:
        if not isinstance(u, dict):
            continue
        name = u.get("name", "<unnamed>")
        userid = u.get("userid")
        if (not userid or not USERID_RE.match(str(userid))
                or not any(c.isupper() for c in str(userid))):
            errors.append(
                f"INV-26: user '{name}' has no valid 8-char alphanumeric "
                f"userid (must contain an uppercase letter)"
            )
        elif userid in seen:
            errors.append(
                f"INV-26: userid '{userid}' is assigned to more than one user"
            )
        else:
            seen.add(userid)
    return errors


def check_journal_exists(root: Path) -> list[str]:
    """INV-17: development/journal.jsonl always exists; every non-blank
    line is a well-formed, schema-complete entry."""
    journal = root / "development" / "journal.jsonl"
    if not journal.is_file():
        return ["INV-17: development/journal.jsonl is missing — seed it "
                "(empty) from templates/journal.template.jsonl"]

    errors: list[str] = []
    text = journal.read_text(encoding="utf-8", errors="ignore")
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"INV-17: journal.jsonl:{lineno} is not valid JSON: {exc}")
            continue
        if not isinstance(entry, dict):
            errors.append(f"INV-17: journal.jsonl:{lineno} is not a JSON object")
            continue
        for field in JOURNAL_REQUIRED_FIELDS:
            if field not in entry:
                errors.append(f"INV-17: journal.jsonl:{lineno} missing "
                              f"field '{field}'")
        files = entry.get("files")
        if isinstance(files, list):
            for f in files:
                if not isinstance(f, dict) or "path" not in f:
                    errors.append(f"INV-17: journal.jsonl:{lineno} has a "
                                  f"files[] entry missing 'path'")
                    continue
                for side in ("before", "after"):
                    val = f.get(side)
                    if val is not None and not HASH_RE.match(str(val)):
                        errors.append(
                            f"INV-17: journal.jsonl:{lineno} {f.get('path')} "
                            f"'{side}' is not a 40-hex git hash or null"
                        )
    return errors


def check_definitions_exist(root: Path, model: DeploymentModel | None = None) -> list[str]:
    """INV-23: definitions/<type>.md exists for every real entity type
    (kernel types plus the active module's)."""
    model = model or build_model()
    definitions = root / "definitions"
    if not definitions.is_dir():
        return ["INV-23: definitions/ is missing — seed it from "
                "framework/kernel/definitions/"]

    errors: list[str] = []
    for entity_type in model.entity_types:
        if not (definitions / f"{entity_type}.md").is_file():
            source = ("framework/kernel/definitions" if entity_type in KERNEL_ENTITY_TYPES
                      else f"the {model.module_id} module's definitions")
            errors.append(
                f"INV-23: definitions/{entity_type}.md is missing — seed it "
                f"from {source}/{entity_type}/"
            )
    return errors


def main() -> int:
    root = find_deploy_root(Path.cwd())
    if root is None:
        # No deployment in this repo — nothing to validate, not a failure.
        print(
            f"no *{POINTER_SUFFIX} pointer or {DEPLOY_DIRNAME}/ found; "
            "skipping deployment validation"
        )
        return 0

    project_root = find_project_root(Path.cwd())
    module = load_module(project_root) if project_root else None
    model = build_model(module)

    errors: list[str] = []
    errors += check_naming(root, model)
    errors += check_single_rule_template(root)
    errors += check_rule_indexing(root)
    errors += check_required_headings(root)
    errors += check_rule_id_shape(root)
    errors += check_module_required_paths(root, model)
    errors += check_module_indexes(root, model)
    errors += check_workflows_index_exists(root)
    errors += check_users_and_roles_exist(root)
    errors += check_users_have_userid(root)
    errors += check_journal_exists(root)
    errors += check_definitions_exist(root, model)

    if errors:
        print(f"catalyst deployment validation FAILED ({len(errors)} issue(s)):")
        for e in errors:
            print(f"  - {e}")
        return 1
    scope = f"module {model.module_id}" if model.module_id else "kernel only"
    print(f"catalyst deployment at {root} is valid ({scope})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
