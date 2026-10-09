"""Parse a deployment's working copy into plain data: rules, domains, users,
artifacts and index registrations.

Artifacts are the active module's (and the kernel's) per-file entities:
Markdown files named `<PREFIX>-NNNNNN-<summary>.md` whose fields live in a
`| **Field** | value |` table. Free-form entity types (ETD
`naming: free-form`, e.g. a roadmap whose items are table rows) are read as
row tables instead.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from check_deployment import (
    RULE_HEADING_RE, TEMPLATE_RE, TEMPLATES_CATALOG_RE,
)
from module_loader import ETD

from catalyst.deployment import Deployment

FIELD_ROW_RE = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|")
TICKED_RE = re.compile(r"`([^`]+)`")
H1_RE = re.compile(r"^#\s+(.*)$")
DOMAIN_ROW_RE = re.compile(r"^\|\s*\[?`([A-Z][A-Z0-9_.]*)`")
LINK_ID_RE = re.compile(r"^\|\s*\[`?([A-Za-z]+-[0-9]{3,6}(?:-[A-Za-z0-9]+)?)`?\]\(([^)]+)\)")
TABLE_ID_RE = re.compile(r"^\|\s*`?([A-Z]+-[0-9]{6}(?:-[A-Za-z0-9]{8})?)`?\s*\|")
PLACEHOLDER_MARK = "owned by the active module"
EMPTY_VALUES = {"", "-", "—", "n/a", "none"}


def norm_field(name: str) -> str:
    """Field names compared loosely: case, punctuation and a trailing plural
    `(s)` or `s` are ignored ("Requirement(s)" == "Requirements")."""
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    return key[:-1] if key.endswith("s") else key


def is_empty(raw: str) -> bool:
    text = raw.strip()
    return text.lower() in EMPTY_VALUES or text.startswith("*(none")


def ref_values(raw: str) -> list[str]:
    """The IDs a field value cites: backticked tokens, else comma-separated
    bare tokens."""
    if is_empty(raw):
        return []
    ticked = TICKED_RE.findall(raw)
    if ticked:
        return [t.strip() for t in ticked if t.strip()]
    return [t.strip() for t in raw.split(",") if t.strip()]


@dataclass
class Rule:
    id: str
    file: Path
    line: int
    retired: bool = False
    inherited: bool = False         # from the project's workspace criterion (R3.1b), read-only


@dataclass
class Artifact:
    id: str
    prefix: str
    file: Path
    title: str
    fields: dict[str, str] = field(default_factory=dict)   # raw name -> raw value

    def get(self, name: str) -> str | None:
        want = norm_field(name)
        for key, value in self.fields.items():
            if norm_field(key) == want:
                return value
        return None


@dataclass
class Corpus:
    rules: dict[str, list[Rule]] = field(default_factory=dict)
    indexed_rules: set[str] = field(default_factory=set)
    domains: set[str] = field(default_factory=set)
    users: list[dict] = field(default_factory=list)
    artifacts: dict[str, list[Artifact]] = field(default_factory=dict)   # id -> defs
    by_prefix: dict[str, list[Artifact]] = field(default_factory=dict)
    index_rows: dict[str, dict[str, str]] = field(default_factory=dict)  # prefix -> id -> file
    row_items: dict[str, set[str]] = field(default_factory=dict)         # prefix -> ids

    def all_ids(self) -> set[str]:
        ids = set(self.rules) | set(self.artifacts)
        for items in self.row_items.values():
            ids |= items
        return ids

    def user(self, name: str) -> dict | None:
        wanted = name.strip().lower()
        for u in self.users:
            if wanted in {str(u.get(k, "")).lower() for k in ("name", "git_username", "userid")}:
                return u
        return None


def _rules(root: Path) -> tuple[dict[str, list[Rule]], set[str]]:
    rules_dir = root / "rules"
    found: dict[str, list[Rule]] = {}
    indexed: set[str] = set()
    if not rules_dir.is_dir():
        return found, indexed
    index = rules_dir / "rules.md"
    if index.is_file():
        indexed = set(re.findall(r"`([a-z]+-[A-Z][A-Z0-9]*-\d+(?:-[A-Za-z0-9]+)*)`",
                                 index.read_text(encoding="utf-8")))
    for f in sorted(rules_dir.rglob("*.md")):
        if (f.name == "rules.md" or TEMPLATE_RE.match(f.name)
                or TEMPLATES_CATALOG_RE.match(f.name) or "domains" in f.relative_to(rules_dir).parts
                or "templates" in f.relative_to(rules_dir).parts):
            continue
        lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        current: Rule | None = None
        for lineno, line in enumerate(lines, 1):
            m = RULE_HEADING_RE.match(line)
            if m and PLACEHOLDER_MARK in line:
                # a kernel placeholder for a module-owned meta-rule
                # (MODULE-SPECIFICATION.md §6.1), not a definition
                current = None
            elif m:
                current = Rule(m.group(1), f, lineno)
                found.setdefault(current.id, []).append(current)
                current.retired = "🗑" in line
            elif current is not None and line.startswith("#"):
                current = None
            elif current is not None and "🗑" in line and "status" in line.lower():
                current.retired = True
    return found, indexed


def _domains(root: Path) -> set[str]:
    index = root / "rules" / "domains" / "domains.md"
    if not index.is_file():
        return set()
    codes = set()
    for line in index.read_text(encoding="utf-8").splitlines():
        m = DOMAIN_ROW_RE.match(line)
        if m:
            codes.add(m.group(1))
    return codes


def _users(root: Path) -> list[dict]:
    path = root / "IAM" / "users" / "users.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    users = data.get("users", []) if isinstance(data, dict) else []
    return [u for u in users if isinstance(u, dict)]


def parse_artifact(path: Path, prefix: str) -> Artifact | None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    fields: dict[str, str] = {}
    title = ""
    for line in text.splitlines():
        if not title:
            h1 = H1_RE.match(line)
            if h1:
                heading = h1.group(1)
                title = heading.split("—", 1)[1].strip() if "—" in heading else heading.strip()
                continue
        m = FIELD_ROW_RE.match(line)
        if m and m.group(1).strip() not in fields:
            # cell 2 only: a third "notes" cell is not part of the value
            row = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
            fields[m.group(1).strip()] = row[1] if len(row) > 1 else ""
    raw_id = fields.get("ID", "")
    ids = ref_values(raw_id)
    art_id = ids[0] if ids else ""
    if not art_id:
        m = re.match(rf"^({re.escape(prefix)}-\d{{6}})", path.name)
        art_id = m.group(1) if m else ""
    if not art_id:
        return None
    return Artifact(art_id, prefix, path, title, fields)


def _index_rows(index: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    if not index.is_file():
        return rows
    for line in index.read_text(encoding="utf-8").splitlines():
        m = LINK_ID_RE.match(line)
        if m:
            rows[m.group(1)] = m.group(2)
    return rows


def _row_items(folder: Path, prefix: str) -> set[str]:
    ids: set[str] = set()
    for f in folder.glob("*.md"):
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = TABLE_ID_RE.match(line)
            if m and m.group(1).startswith(prefix + "-"):
                ids.add(m.group(1))
    return ids


def _inherit_workspace(dep: Deployment, corpus: Corpus) -> None:
    """A member of a VS Code workspace (`workspace = "<name>"` in its
    catalyst.toml) also sees the workspace criterion's rules, domains, users
    and roles, read-only; its own entries win on a clash (R3.1b)."""
    import project_file
    name = project_file.workspace_of(dep.pointer or {})
    root = project_file.workspace_criterion(name) if name else None
    if root is None or not root.is_dir() or root == dep.root:
        return
    rules, indexed = _rules(root)
    for rid, defs in rules.items():
        if rid not in corpus.rules:
            for rule in defs:
                rule.inherited = True
            corpus.rules[rid] = defs
            corpus.indexed_rules.add(rid)
    corpus.domains |= _domains(root)
    known = {str(u.get(k, "")).lower() for u in corpus.users for k in ("name", "git_username", "userid")}
    corpus.users += [u for u in _users(root)
                     if not {str(u.get(k, "")).lower() for k in ("name", "git_username", "userid")} & known]


def load_corpus(dep: Deployment) -> Corpus:
    corpus = Corpus()
    corpus.rules, corpus.indexed_rules = _rules(dep.root)
    corpus.domains = _domains(dep.root)
    corpus.users = _users(dep.root)
    _inherit_workspace(dep, corpus)
    file_re_cache: dict[str, re.Pattern] = {}
    for prefix, etd in dep.etds.items():
        folder = dep.folder(etd)
        if folder is None:
            continue
        if etd.naming == "free-form":
            corpus.row_items[prefix] = _row_items(folder, prefix)
            continue
        pattern = file_re_cache.setdefault(prefix, re.compile(rf"^{re.escape(prefix)}-\d{{6}}-.+\.md$"))
        arts = []
        for f in sorted(folder.glob("*.md")):
            if not pattern.match(f.name):
                continue
            art = parse_artifact(f, prefix)
            if art is not None:
                arts.append(art)
                corpus.artifacts.setdefault(art.id, []).append(art)
        corpus.by_prefix[prefix] = arts
        corpus.index_rows[prefix] = _index_rows(folder / f"{folder.name}.md")
    return corpus


def etd_for(dep: Deployment, prefix: str) -> ETD | None:
    return dep.etds.get(prefix)
