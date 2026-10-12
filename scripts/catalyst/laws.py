"""The laws (roadmap R4.1): what a session loads, and `catalyst why`.

`INVARIANTS.md` (and the module's `INVARIANTS.module.md`) open with the
laws, then a marker, then the invariants they come from. A session loads
only what precedes the marker (the brief); `why` looks up a law, an
invariant or a meta-rule in the full texts. A file without the marker (a
deployment from before the laws) is its own brief.
"""

from __future__ import annotations

import re
from pathlib import Path

MARKER = "<!-- catalyst: end of the session brief -->"
FILES = ("INVARIANTS.md", "INVARIANTS.module.md")
LAW_RE = re.compile(r"^- \*\*((?:[A-Z]+-)?L\d+) — ")
INV_RE = re.compile(r"^- \*\*(INV-(?:[A-Z]+-)?\d+)\b")
# a meta-rule heading, its ID short (`rr-META-012`) or widened and signed
# (`rr-META-000012-<userid>`), the kernel's namespace or a module's (`rr-SE-001`)
META_RE = re.compile(r"^## \d+\. `rr-([A-Z]+)-(\d+)(?:-[A-Za-z0-9]{8})?`")
META_KEY_RE = re.compile(r"^rr-([A-Z]+)-(\d+)(?:-[A-Za-z0-9]{8})?$")


def brief(text: str) -> str:
    """The part of a laws file a session loads."""
    return text.split(MARKER, 1)[0].rstrip() + "\n"


def session_brief(root: Path) -> str:
    """The kernel's and the module's briefs, as a session start shows them."""
    parts = [brief(p.read_text(encoding="utf-8", errors="replace")) for p in (root / f for f in FILES) if p.is_file()]
    return "\n".join(parts)


def _bullets(text: str, pattern: re.Pattern) -> dict[str, str]:
    """`- **ID …` bullets, each with its continuation lines."""
    found: dict[str, str] = {}
    current, lines = None, []
    for line in text.splitlines():
        m = pattern.match(line)
        if m or line.startswith(("- **", "#", "<!--")) or (current and not line.strip()):
            if current:
                found.setdefault(current, "\n".join(lines).rstrip())
            current, lines = (m.group(1), [line]) if m else (None, [])
        elif current:
            lines.append(line)
    if current:
        found.setdefault(current, "\n".join(lines).rstrip())
    return found


def _row(text: str, inv: str) -> str | None:
    """The invariants table's row for `inv` (a range row, INV-10 to INV-13, included;
    a module's `INV-<NS>-n` by its exact ID)."""
    if not inv[4:].isdigit():
        return next((line for line in text.splitlines() if line.startswith(f"| {inv} ")), None)
    n = int(inv[4:])
    for line in text.splitlines():
        m = re.match(r"^\| INV-(\d+)(?:[\u2013-](\d+))? ", line)  # an en dash or a hyphen
        if m and int(m.group(1)) <= n <= int(m.group(2) or m.group(1)):
            return line
    return None


def _aliases(root: Path) -> dict[str, str]:
    """The deployed module's `aliases:` (an old ID -> the ID it is now)."""
    from module_loader import load_module

    out: dict[str, str] = {}
    for mod in sorted((root / "modules").glob("*/module.yaml")) if (root / "modules").is_dir() else []:
        manifest = load_module(module_dir=mod.parent)
        if manifest is not None:
            out.update(manifest.aliases)
    return out


def why(root: Path, item: str) -> str | None:
    """What `catalyst why <item>` prints, or None when it is not a law,
    an invariant or a meta-rule of this criterion. An old ID the module
    lists under `aliases:` is explained as the ID it now is."""
    from catalyst.corpus import meta_key

    key = meta_key(item)
    alias = next(
        (new for old, new in _aliases(root).items() if old == item.strip() or (key and meta_key(old) == key)), None
    )
    if alias:
        found = _why(root, alias)
        return f"{item.strip()} is now {alias}.\n\n{found}" if found else None
    return _why(root, item)


def _why(root: Path, item: str) -> str | None:
    texts = [(f, (root / f).read_text(encoding="utf-8", errors="replace")) for f in FILES if (root / f).is_file()]
    key = item.strip()
    if re.fullmatch(r"(?:[A-Za-z]+-)?[Ll]\d+", key):
        key = key.upper()
        for name, text in texts:
            law = _bullets(text, LAW_RE).get(key)
            if law:
                rows = [line for line in text.splitlines() if line.startswith("| INV-") and f" {key}" in line]
                rows = [r for r in rows if re.search(rf"\b{re.escape(key)}\b", r.split("|")[2])]
                cited = "\n".join(rows)
                return f"{law}\n\n({name})" + (f"\n\nFrom the invariants:\n{cited}" if cited else "")
        return None
    if re.fullmatch(r"(?i)inv-(?:[a-z]+-)?\d+", key):
        key = key.upper()
        rows, details = [], []
        for name, text in texts:
            row = _row(text, key)
            if row:
                cells = [c.strip() for c in row.strip("|").split("|")]
                rows.append(f"{cells[0]} — law: {cells[1]}; enforced by: {cells[2]} ({name})")
            detail = _bullets(text, INV_RE).get(key)
            if detail:
                details.append(detail)
        moved = [d for d in details if "owned by the active module" not in d]
        return "\n\n".join(rows + (moved or details)) or None
    wanted = META_KEY_RE.match(key)
    if wanted:
        doc = root / "rules" / "Rules-of-Rules.md"
        if doc.is_file():
            text = doc.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            for i, line in enumerate(lines):
                m = META_RE.match(line)
                if m and m.group(1) == wanted.group(1) and int(m.group(2)) == int(wanted.group(2)):
                    end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
                    return "\n".join(lines[i:end]).rstrip()
    return None
