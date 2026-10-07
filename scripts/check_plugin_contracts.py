#!/usr/bin/env python3
"""Validate plugin working-contract CONTENT against catalyst invariants INV-12.

Complements scripts/check_plugins.py, which validates plugin *presence* (each
plugin has README.md + working-contract.md, submodules initialized). This script
validates the *content* of each working-contract.md and its coherence with the
plugin's version.txt and the catalog pin:

  - the six metadata fields are present (Name, Description, UUID, Version,
    Active, Type)
  - no leftover <placeholder> values remain in any field
  - UUID is a well-formed UUID
  - Active is a boolean (true|false)
  - Version matches the plugin's own version.txt
  - Version/Tag in framework/kernel/plugins/<type>/catalog.md matches version.txt (catalog pin)

Provenance (INV-11) is only partially covered: check_plugins.py verifies a
plugin is checked out as a submodule at all. origin_url()/normalize_url()
below exist to compare a plugin's declared origin against the framework's
own, but nothing currently wires that comparison into validate_plugin() —
a plugin sourced from the framework's own repo would still pass today.

Exit 0 = clean (including when no plugins are present), exit 1 = violations.
UUID *stability* over time and *activation gating* (INV-13 runtime target) are
behavioural — not checkable from a single tree snapshot — and stay the agent's
responsibility, re-grounded via INVARIANTS.md.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = ROOT / "framework" / "kernel" / "plugins"

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)
REQUIRED_FIELDS = ["Name", "Description", "UUID", "Version", "Active", "Type"]


def parse_metadata(contract: Path) -> dict[str, str]:
    """Extract '- Field: value' pairs under the ## Metadata heading."""
    fields: dict[str, str] = {}
    in_meta = False
    for raw in contract.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            in_meta = line.lower().startswith("## metadata")
            continue
        if in_meta:
            m = re.match(r"-\s*([A-Za-z]+)\s*:\s*(.*)$", line)
            if m:
                fields[m.group(1)] = m.group(2).strip()
    return fields


def read_version_txt(plugin_dir: Path) -> str | None:
    vt = plugin_dir / "version.txt"
    if vt.is_file():
        return vt.read_text(encoding="utf-8", errors="ignore").strip()
    return None


def parse_catalog_pins(type_dir: Path) -> dict[str, dict[str, str]]:
    """Parse framework/kernel/plugins/<type>/catalog.md table → {plugin_name: {release, tag}}."""
    catalog = type_dir / "catalog.md"
    pins: dict[str, dict[str, str]] = {}
    if not catalog.is_file():
        return pins
    for raw in catalog.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        name_cell = cells[0]
        if name_cell.lower().startswith("plugin") or set(name_cell) <= {"-", ":"}:
            continue  # header or separator row
        m = re.search(r"\[([^\]]+)\]", name_cell)
        name = m.group(1) if m else name_cell
        pins[name] = {"release": cells[2], "tag": cells[3]}
    return pins


def normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    url = re.sub(r"\.git$", "", url, flags=re.I)
    url = re.sub(r"^git@([^:]+):", r"\1/", url)     # git@host:owner/repo
    url = re.sub(r"^[a-z]+://", "", url, flags=re.I)  # scheme://
    url = re.sub(r"^[^@/]+@", "", url)               # user@host
    return url.lower()


def origin_url() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], cwd=ROOT, text=True
        )
        return normalize_url(out)
    except Exception:
        return None


def find_plugins() -> list[Path]:
    """plugins/<type>/<name>/ dirs that carry a working-contract.md."""
    found: list[Path] = []
    if not PLUGINS_DIR.is_dir():
        return found
    for type_dir in sorted(PLUGINS_DIR.iterdir()):
        if not type_dir.is_dir() or type_dir.name.startswith("."):
            continue
        for plugin_dir in sorted(type_dir.iterdir()):
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
                continue
            if (plugin_dir / "working-contract.md").is_file():
                found.append(plugin_dir)
    return found


def validate_plugin(plugin_dir: Path, framework_url: str | None) -> list[str]:
    errors: list[str] = []
    try:
        rel = plugin_dir.relative_to(ROOT)
    except ValueError:
        rel = plugin_dir
    contract = plugin_dir / "working-contract.md"
    fields = parse_metadata(contract)

    for field in REQUIRED_FIELDS:
        if field not in fields or not fields[field]:
            errors.append(f"INV-12 {rel}: missing metadata field '{field}'")
    for field, value in fields.items():
        if "<" in value and ">" in value:
            errors.append(f"INV-12 {rel}: placeholder left in '{field}': {value}")

    uuid = fields.get("UUID", "")
    if uuid and "<" not in uuid and not UUID_RE.match(uuid):
        errors.append(f"INV-12 {rel}: UUID is not a well-formed UUID: {uuid}")

    active = fields.get("Active", "").lower()
    if active and active not in {"true", "false"}:
        errors.append(f"INV-12 {rel}: Active must be true|false, got '{active}'")

    version = fields.get("Version", "")
    vtxt = read_version_txt(plugin_dir)
    if vtxt is None:
        errors.append(f"INV-12 {rel}: version.txt is missing")
    elif version and "<" not in version and version != vtxt:
        errors.append(
            f"INV-12 {rel}: Version '{version}' != version.txt '{vtxt}'"
        )

    pins = parse_catalog_pins(plugin_dir.parent).get(plugin_dir.name)
    if pins and vtxt:
        tag = pins["tag"]
        release = pins["release"]
        if tag and tag != vtxt:
            errors.append(f"INV-12 {rel}: catalog Tag '{tag}' != version.txt '{vtxt}'")
        if release and release not in {vtxt, f"v{vtxt}"}:
            errors.append(
                f"INV-12 {rel}: catalog Release '{release}' != '{vtxt}'/'v{vtxt}'"
            )

    return errors


def main(argv: list[str] | None = None) -> int:
    """`--require` (CI, submodules checked out): no plugin to check is a
    failure, so the gate can never pass by checking nothing."""
    argv = list(argv or [])
    if [a for a in argv if a != "--require"]:
        print("usage: check_plugin_contracts.py [--require]")
        return 2
    plugins = find_plugins()
    if not plugins:
        if "--require" in argv:
            print("plugin contract validation FAILED: no plugin with a working-contract.md found "
                  "(are the submodules checked out?) (--require)")
            return 1
        print("no plugins with working-contract.md found; skipping contract checks")
        return 0

    framework_url = origin_url()
    errors: list[str] = []
    for plugin_dir in plugins:
        errors += validate_plugin(plugin_dir, framework_url)

    if errors:
        print(f"plugin contract validation FAILED ({len(errors)} issue(s)):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"plugin contracts valid ({len(plugins)} plugin(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
