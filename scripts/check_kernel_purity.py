#!/usr/bin/env python3
"""Validate that the kernel never names a process module or its entities (INV-30).

The kernel (framework/kernel/) and catalyst's own tooling and root docs must
stay module-agnostic: they may speak of "a module", "the active module's
entity types" or `<entity-type>`, but never of a specific module, its entity
id prefixes, entity folders, commands, templates or definitions.

The denylist is never hardcoded here. It is derived from the manifests of the
modules listed in framework/modules/catalog.md, found as sibling checkouts
(`../catalyst-<id>/`), under framework/modules/<id>/, or under
$CATALYST_MODULES_DIR/<id>/ (or $CATALYST_MODULES_DIR/catalyst-<id>/).

Two tiers:
  - errors (exit 1): the module id, entity id prefixes (`PREFIX-...` or the
    bare uppercase prefix), entity folder paths (`folder/`, `folder.md`),
    module command names, and template/definition file names;
  - warnings (exit 0): entity names and plural names as words, which also
    occur as ordinary English and need a human look.

Exit 0 = clean (warnings allowed), exit 1 = violations found.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from module_loader import parse_simple_yaml

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "framework" / "modules" / "catalog.md"

# What must stay module-agnostic, relative to ROOT.
SCAN_DIRS = ("framework/kernel", "scripts")
SCAN_ROOT_GLOBS = ("*.md", "*.txt")
SCAN_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".jsonl", ".txt"}

CATALOG_ROW_RE = re.compile(r"^\|\s*`([a-z0-9-]+)`\s*\|")


@dataclass
class Pattern:
    regex: re.Pattern[str]
    label: str


@dataclass
class Denylist:
    errors: list[Pattern] = field(default_factory=list)
    warnings: list[Pattern] = field(default_factory=list)


def catalog_module_ids(catalog: Path = CATALOG) -> list[str]:
    if not catalog.is_file():
        return []
    ids: list[str] = []
    for line in catalog.read_text(encoding="utf-8").splitlines():
        m = CATALOG_ROW_RE.match(line)
        if m:
            ids.append(m.group(1))
    return ids


def find_module_dir(module_id: str, root: Path = ROOT) -> Path | None:
    candidates = [
        root.parent / f"catalyst-{module_id}",
        root / "framework" / "modules" / module_id,
    ]
    env = os.environ.get("CATALYST_MODULES_DIR")
    if env:
        base = Path(env).expanduser()
        candidates[:0] = [base / module_id, base / f"catalyst-{module_id}"]
    for cand in candidates:
        if (cand / "module.yaml").is_file():
            return cand
    return None


def _word(text: str) -> str:
    """Whole-word regex for a (possibly hyphenated, multi-word) term."""
    return r"(?<![\w-])" + re.escape(text) + r"(?![\w-])"


def build_denylist(module_dir: Path) -> Denylist:
    deny = Denylist()
    manifest = parse_simple_yaml((module_dir / "module.yaml").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        return deny
    module_id = str(manifest.get("id", module_dir.name))
    deny.errors.append(Pattern(re.compile(_word(module_id)), f"module id '{module_id}'"))

    for entry in manifest.get("entity_types") or []:
        if not isinstance(entry, dict):
            continue
        prefix = str(entry.get("id", ""))
        if prefix:
            deny.errors.append(
                Pattern(re.compile(r"(?<![\w-])" + re.escape(prefix) + r"(?:-|(?![\w-]))"), f"entity prefix '{prefix}'")
            )
            deny.errors.append(
                Pattern(re.compile(re.escape(f"DEFINITION-{prefix}"), re.I), f"definition of '{prefix}'")
            )
        schema = entry.get("schema")
        etd = {}
        if schema and (module_dir / schema).is_file():
            etd = parse_simple_yaml((module_dir / schema).read_text(encoding="utf-8")) or {}
        folder = str(etd.get("folder", "")) if isinstance(etd, dict) else ""
        if folder:
            deny.errors.append(
                Pattern(re.compile(r"(?<![\w-])" + re.escape(folder) + r"(?:/|\.md\b)"), f"entity folder '{folder}'")
            )
        for key in ("name", "plural_name"):
            term = str(etd.get(key, "")) if isinstance(etd, dict) else ""
            if term:
                deny.warnings.append(Pattern(re.compile(_word(term), re.I), f"entity {key} '{term}'"))

    for cmd in manifest.get("commands") or []:
        name = str(cmd.get("name", "")) if isinstance(cmd, dict) else ""
        if name:
            deny.errors.append(Pattern(re.compile(_word(name)), f"module command '{name}'"))

    for tpl in manifest.get("templates") or []:
        path = str(tpl.get("template_path", "")) if isinstance(tpl, dict) else ""
        if path:
            base = Path(path).name
            deny.errors.append(Pattern(re.compile(re.escape(base)), f"module template '{base}'"))
    return deny


def scan_files(root: Path = ROOT) -> list[Path]:
    files: set[Path] = set()
    for d in SCAN_DIRS:
        base = root / d
        if base.is_dir():
            for f in base.rglob("*"):
                if f.is_file() and f.suffix in SCAN_SUFFIXES and "__pycache__" not in f.parts:
                    files.add(f)
    for pattern in SCAN_ROOT_GLOBS:
        files.update(f for f in root.glob(pattern) if f.is_file())
    # Submodule checkouts (plugins) carry their own repositories' content.
    return sorted(f for f in files if not _inside_submodule(f, root))


def _inside_submodule(path: Path, root: Path) -> bool:
    for parent in path.relative_to(root).parents:
        if parent != Path() and (root / parent / ".git").exists():
            return True
    return False


def check(files: list[Path], denylists: list[Denylist], root: Path = ROOT) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for f in files:
        rel = f.relative_to(root)
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for n, line in enumerate(lines, 1):
            for deny in denylists:
                for p in deny.errors:
                    if p.regex.search(line):
                        errors.append(f"{rel}:{n}: names {p.label}")
                for p in deny.warnings:
                    if p.regex.search(line):
                        warnings.append(f"{rel}:{n}: mentions {p.label}")
    return errors, warnings


def main() -> int:
    ids = catalog_module_ids()
    denylists: list[Denylist] = []
    for module_id in ids:
        module_dir = find_module_dir(module_id)
        if module_dir is None:
            print(
                f"kernel purity: warning: module '{module_id}' is not checked out; its names cannot be checked",
                file=sys.stderr,
            )
            continue
        denylists.append(build_denylist(module_dir))
    if not denylists:
        print("kernel purity: no catalogued module found; nothing to check")
        return 0

    errors, warnings = check(scan_files(), denylists)
    verbose = "-v" in sys.argv or "--warnings" in sys.argv
    if warnings and verbose:
        for w in warnings:
            print(f"  warning: {w}")
    if errors:
        print(f"kernel purity validation FAILED ({len(errors)} issue(s), {len(warnings)} warning(s)):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"kernel purity validation PASSED ({len(warnings)} warning(s); -v to list)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
