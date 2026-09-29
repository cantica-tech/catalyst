"""Regenerate each per-file entity type's `<folder>/<folder>.md` index from
the artifact files themselves, so an index can never drift from what is on
disk (or conflict in a merge — regenerate instead of merging).

Each index keeps its own prose, any other tables, and its ID table's
header columns; that table's rows are rebuilt in ID order: `ID` links the
file, `Title` is the artifact's H1 title, any other column is the artifact
field of the same name (loosely matched, refs rendered bare). A cell with no
matching field keeps what the old row held, and a row whose file is gone is
kept as it was — regenerating never drops information, and never frees an
ID for reuse (`validate` reports such rows as index-orphan errors).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from catalyst.corpus import Artifact, Corpus, is_empty, norm_field, ref_values
from catalyst.deployment import Deployment

DEFAULT_COLUMNS = ["ID", "Title", "Status"]
PLACEHOLDER_RE = re.compile(r"^\*\(none yet.*\)\*\s*$")


@dataclass
class IndexChange:
    path: Path
    old: str
    new: str


def cells(line: str) -> list[str]:
    """A Markdown table row's cells, splitting on unescaped pipes."""
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") and not inner.endswith("\\|") else inner
    return [c.strip() for c in re.split(r"(?<!\\)\|", inner)]


def _split(text: str) -> tuple[list[str], list[str] | None, list[str], list[str]]:
    """(lines before the ID table, its header or None, its data rows, lines
    after it). The ID table is the first whose header has an `ID` column."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if (line.startswith("|") and i + 1 < len(lines)
                and re.match(r"^\|\s*:?-{3,}", lines[i + 1])):
            header = cells(line)
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            if any(norm_field(h) == "id" for h in header):
                return lines[:i], header, lines[i + 2:j], lines[j:]
    return lines, None, [], []


def _cell(art: Artifact, column: str, old: str | None) -> str:
    key = norm_field(column)
    if key == "id":
        return f"[{art.id}]({art.file.name})"
    if key == "title":
        return art.title
    raw = art.get(column)
    if raw is None:
        return old or ""          # no such field: keep what the index held
    if is_empty(raw):
        return ""
    values = ref_values(raw) if "`" in raw else [raw.strip()]
    return ", ".join(v.replace("|", "\\|") for v in values)


def _number(art_id: str) -> int:
    m = re.match(r"^[A-Za-z]+-(\d+)", art_id)
    return int(m.group(1)) if m else 0


def _row_id(row: list[str], id_col: int) -> str | None:
    if id_col >= len(row):
        return None
    m = re.match(r"^\[?`?([A-Za-z]+-\d+(?:-[A-Za-z0-9]+)?)`?\]?", row[id_col])
    return m.group(1) if m else None


def render(existing: str, title: str, arts: list[Artifact]) -> str:
    if existing:
        before, header, old_rows, after = _split(existing)
    else:
        before, header, old_rows, after = [f"# {title} index", ""], None, [], []
    if existing and header is None and not arts:
        return existing        # an empty index without a table stays as written
    columns = header or DEFAULT_COLUMNS
    id_col = next(i for i, c in enumerate(columns) if norm_field(c) == "id")
    old: dict[str, list[str]] = {}
    for line in old_rows:
        row = cells(line)
        rid = _row_id(row, id_col)
        if rid:
            old[rid] = row
    current = {a.id for a in arts}
    entries = [(a.id, "| " + " | ".join(
        _cell(a, c, old.get(a.id, [None] * len(columns))[i] if i < len(old.get(a.id, [])) else None)
        for i, c in enumerate(columns)) + " |") for a in arts]
    entries += [(rid, line) for line in old_rows
                if (rid := _row_id(cells(line), id_col)) and rid not in current]
    rows = [f"| {' | '.join(columns)} |", f"|{'|'.join('---' for _ in columns)}|"]
    rows += [line for _, line in sorted(entries, key=lambda e: _number(e[0]))]
    if arts:
        after = [line for line in after if not PLACEHOLDER_RE.match(line.strip())]
    while before and not before[-1].strip():
        before.pop()
    out = [*before, "", *rows]
    tail = list(after)
    while tail and not tail[0].strip():
        tail.pop(0)
    if tail:
        out += ["", *tail]
    return "\n".join(out).rstrip() + "\n"


def regenerate(dep: Deployment, corpus: Corpus, write: bool = True) -> list[IndexChange]:
    changes = []
    for prefix, arts in sorted(corpus.by_prefix.items()):
        etd = dep.etds[prefix]
        folder = dep.folder(etd)
        if folder is None:
            continue
        index = folder / f"{folder.name}.md"
        old = index.read_text(encoding="utf-8") if index.is_file() else ""
        new = render(old, etd.plural_name, arts)
        if new != old:
            changes.append(IndexChange(index, old, new))
            if write:
                index.write_text(new, encoding="utf-8")
    return changes
