"""Read-only views of a deployment (roadmap R2 W1): `list`, `journal show`,
`view`, `backlog` and `graph` (every rule, domain and artifact with its
links, and the entity types that give them meaning: what a client draws the
chain from, with no parser or type list of its own).

What `/list`, `/user list`, `/journal` and a module's backlog summary asked
an agent to work out by reading files is computed here, from the working copy
and the entity type definitions (ETDs) alone, so no module entity is named in
this file. Nothing here writes.

Each function returns plain data (lists and dicts, ready for `--json`);
`render_*` turns it into text.
"""

from __future__ import annotations

import fnmatch
import json
import re
from collections.abc import Callable
from pathlib import Path

from catalyst import journal
from catalyst.corpus import DOMAIN_ROW_RE, H1_RE, TABLE_ID_RE, Artifact, Corpus, Rule, norm_field, ref_values
from catalyst.deployment import Deployment

REF_KINDS = ("ref", "ref-list")


class ViewError(Exception):
    pass


# --- filters --------------------------------------------------------------
def parse_filters(specs: list[str] | None) -> list[tuple[str, str]]:
    """`key=value` pairs; the value may use `*` and `?` wildcards."""
    out = []
    for spec in specs or []:
        key, sep, value = spec.partition("=")
        if not sep or not key.strip():
            raise ViewError(f"--filter '{spec}' is not key=value")
        out.append((norm_field(key), value.strip().strip('"').lower()))
    return out


def _matches(row: dict, filters: list[tuple[str, str]]) -> bool:
    fields = {norm_field(k): v for k, v in row.items()}
    for key, pattern in filters:
        value = fields.get(key)
        values = value if isinstance(value, list) else [value]
        if not any(fnmatch.fnmatchcase(str(v).lower(), pattern) for v in values if v is not None):
            return False
    return True


# --- list -----------------------------------------------------------------
def _rel(dep: Deployment, path: Path) -> str:
    try:
        return path.relative_to(dep.root).as_posix()
    except ValueError:
        return path.as_posix()


def _artifact_row(dep: Deployment, art: Artifact) -> dict:
    return {
        "id": art.id,
        "type": art.prefix,
        "title": art.title,
        "file": _rel(dep, art.file),
        **{k: v for k, v in art.fields.items() if k.lower() != "id"},
    }


def _roles(dep: Deployment) -> list[dict]:
    try:
        data = json.loads((dep.root / "IAM" / "roles" / "roles.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [r for r in (data.get("roles", []) if isinstance(data, dict) else []) if isinstance(r, dict)]


def _templates(dep: Deployment) -> list[dict]:
    rows = []
    for path in sorted(dep.root.glob("**/templates/TEMPLATE-*.md")):
        if "modules" in path.relative_to(dep.root).parts:
            continue
        stem = path.stem[len("TEMPLATE-") :]
        family, _, version = stem.rpartition("-v")
        rows.append({"family": family or stem, "version": version, "file": _rel(dep, path)})
    return rows


def kinds(dep: Deployment) -> dict[str, str]:
    """Every name `list` accepts -> its canonical kind (an ETD prefix, or
    rule/user/role/template)."""
    names = {k: k for k in ("rule", "user", "role", "template")}
    names.update({"rules": "rule", "users": "user", "roles": "role", "templates": "template"})
    for prefix, etd in dep.etds.items():
        for alias in (prefix, etd.name, etd.plural_name, etd.folder):
            names[alias.lower()] = prefix
    return names


def list_items(
    dep: Deployment, corpus: Corpus, kind: str, filters: list[tuple[str, str]], template_family: str | None = None
) -> list[dict]:
    if kind.lower() == "all":
        return [row for k in ["rule", *sorted(dep.etds)] for row in list_items(dep, corpus, k, filters)]
    canon = kinds(dep).get(kind.lower())
    if canon is None:
        known = sorted({*dep.etds, "rule", "user", "role", "template"})
        raise ViewError(f"unknown type '{kind}' — one of: all, {', '.join(known)}")
    if canon == "rule":
        rows = [
            {
                "id": rid,
                "type": "rule",
                "file": _rel(dep, defs[0].file),
                "line": defs[0].line,
                "retired": defs[0].retired,
            }
            for rid, defs in sorted(corpus.rules.items())
        ]
    elif canon == "user":
        rows = [dict(u) for u in corpus.users]
    elif canon == "role":
        rows = _roles(dep)
    elif canon == "template":
        rows = [r for r in _templates(dep) if template_family is None or r["family"].lower() == template_family.lower()]
    else:
        rows = [_artifact_row(dep, a) for a in corpus.by_prefix.get(canon, [])]
        rows += [{"id": i, "type": canon} for i in sorted(corpus.row_items.get(canon, ()))]
    return [r for r in rows if _matches(r, filters)]


# --- journal show ---------------------------------------------------------
def journal_entries(
    dep: Deployment,
    since: str | None = None,
    artifact: str | None = None,
    actor: str | None = None,
    rule: str | None = None,
) -> list[dict]:
    after = journal.parse_time(since) if since else None
    out = []
    for at, entry, _ in journal.read(dep):
        if entry is None:
            continue
        when = journal._entry_time(entry)
        if after and (when is None or when < after):
            continue
        if artifact and str(entry.get("artifact", "")) != artifact:
            continue
        if actor and actor.lower() not in str(entry.get("actor", "")).lower():
            continue
        if rule and rule not in (entry.get("targets") or []):
            continue
        out.append({"at": at, **entry})
    return sorted(out, key=lambda e: (journal._entry_time(e) is None, str(e.get("timestamp", ""))))


# --- view -----------------------------------------------------------------
def _ref_fields(dep: Deployment, prefix: str) -> list[str]:
    etd = dep.etds.get(prefix)
    return [f.name for f in (etd.fields if etd else []) if f.kind in REF_KINDS]


def resolve(corpus: Corpus, item_id: str) -> str | None:
    """The artifact or rule an ID names, however it is written: in full,
    short (`REQ-000030`, when one artifact has it), a rule as its document
    cites it, or a meta-rule as the handbook writes it (`rr-META-015`).
    None when nothing has it; ViewError when a short form names several."""
    from catalyst.corpus import meta_key

    if item_id in corpus.artifacts:
        return item_id
    rule = corpus.rule_id(item_id)
    if rule:
        return rule
    key = meta_key(item_id)
    found = sorted(
        {i for i in corpus.artifacts if i.startswith(item_id + "-")}
        | {r for r in corpus.rules if r.startswith(item_id + "-") or (key and meta_key(r) == key)}
    )
    if len(found) > 1:
        raise ViewError(f"'{item_id}' names several: {', '.join(found)}")
    return found[0] if found else None


def view(dep: Deployment, corpus: Corpus, item_id: str) -> dict:
    item_id = resolve(corpus, item_id) or item_id
    arts = corpus.artifacts.get(item_id)
    if arts:
        art = arts[0]
        out = _artifact_row(dep, art)
        out["links"] = {
            name: ref_values(art.get(name) or "") for name in _ref_fields(dep, art.prefix) if art.get(name) is not None
        }
    elif corpus.rule_id(item_id):
        item_id = corpus.rule_id(item_id) or item_id
        rule = corpus.rules[item_id][0]
        out = {
            "id": item_id,
            "type": "rule",
            "file": _rel(dep, rule.file),
            "line": rule.line,
            "retired": rule.retired,
            "links": {},
        }
    else:
        raise ViewError(f"no artifact or rule '{item_id}' in this deployment")
    out["linked_from"] = sorted(
        {
            (other.id, name)
            for defs in corpus.artifacts.values()
            for other in defs
            if other.id != item_id
            for name in _ref_fields(dep, other.prefix)
            if item_id in ref_values(other.get(name) or "")
        }
    )
    out["linked_from"] = [{"id": i, "field": f} for i, f in out["linked_from"]]
    out["journal"] = [
        {
            "timestamp": e.get("timestamp"),
            "actor": e.get("actor"),
            "command": e.get("command"),
            "action": e.get("action"),
            "intent": e.get("intent"),
        }
        for e in journal_entries(dep)
        if e.get("artifact") == item_id or item_id in (e.get("targets") or [])
    ]
    return out


# --- backlog --------------------------------------------------------------
def backlog(dep: Deployment, corpus: Corpus) -> dict:
    """Open work by type and status, open items missing a required link, and
    rules no open item targets. "Open" is any status outside the ETD's
    closed states."""
    open_by_type: dict[str, dict[str, list[str]]] = {}
    missing: list[dict] = []
    targeted: set[str] = set()
    for prefix in sorted(dep.etds):
        etd = dep.etds[prefix]
        closed = set(etd.workflow.closed_states)
        for art in corpus.by_prefix.get(prefix, []):
            status = (art.get("Status") or "").strip() or "(no status)"
            if status in closed:
                continue
            open_by_type.setdefault(prefix, {}).setdefault(status, []).append(art.id)
            for f in etd.fields:
                if f.kind in REF_KINDS and f.required and not ref_values(art.get(f.name) or ""):
                    missing.append({"id": art.id, "field": f.name})
            if etd.grounding_field:
                targeted |= set(ref_values(art.get(etd.grounding_field) or ""))
    idle = sorted(rid for rid, defs in corpus.rules.items() if not defs[0].retired and rid not in targeted)
    return {"open": open_by_type, "missing_links": missing, "rules_without_open_work": idle}


# --- graph ----------------------------------------------------------------
def _rule_domain(rule_id: str) -> str | None:
    parts = rule_id.split("-")
    return parts[1] if len(parts) > 2 else None


BACKTICKED = re.compile(r"(?<=`)([^`\s]+)(?=`)")  # every segment between two backticks, so a token wrapped
# across lines (`PREFIX-000010-\nAb12Cd34`) never throws the pairing off
SHORT_FORM = re.compile(r"^[A-Z][A-Z0-9]*-\d{6}$")


def _resolver(corpus: Corpus, ids: set[str]) -> Callable[[str], str | None]:
    """A cited token's node: the ID itself, a rule's `<ID>-<slug>`, or a
    short form (`PREFIX-NNNNNN`) naming exactly one ID."""
    shorts: dict[str, str | None] = {}
    for i in ids:
        m = re.match(r"^([A-Z][A-Z0-9]*-\d{6})-", i)
        if m:
            shorts[m.group(1)] = None if m.group(1) in shorts else i

    def resolve(token: str) -> str | None:
        if token in ids:
            return token
        if (rule := corpus.rule_id(token)) is not None:
            return rule
        return shorts.get(token) if SHORT_FORM.match(token) else None

    return resolve


def _mentions(text: str, resolve: Callable[[str], str | None], itself: str) -> list[str]:
    """The IDs `text` cites in backticks, resolved, itself left out, in the
    order first met."""
    out: dict[str, None] = {}
    for token in BACKTICKED.findall(text):
        found = resolve(token)
        if found and found != itself:
            out[found] = None
    return list(out)


def _rule_text(rule: Rule) -> str:
    """A rule's own text: its file, for a one-file rule; else its heading to
    the next heading of the same or a higher level."""
    try:
        lines = rule.file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    if rule.file.name.startswith(rule.id):
        return "\n".join(lines)
    start = max(rule.line - 1, 0)
    level = len(lines[start]) - len(lines[start].lstrip("#")) if start < len(lines) else 0
    end = len(lines)
    for i in range(start + 1, len(lines)):
        depth = len(lines[i]) - len(lines[i].lstrip("#"))
        if 0 < depth <= level and lines[i][depth : depth + 1] == " ":
            end = i
            break
    return "\n".join(lines[start:end])


def _cells(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def _rows(dep: Deployment, corpus: Corpus) -> list[tuple[str, str, Path, int, str, dict[str, str]]]:
    """(id, type, file, line, row text, cells by header) for each item kept
    as a table row; the cells are raw, as an artifact's fields are."""
    out = []
    for prefix, ids in sorted(corpus.row_items.items()):
        etd = dep.etds.get(prefix)
        folder = dep.folder(etd) if etd else None
        if folder is None:
            continue
        seen: set[str] = set()
        for f in sorted(folder.glob("*.md")):
            lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
            header: list[str] = []
            for n, line in enumerate(lines, 1):
                if n < len(lines) and line.startswith("|") and re.match(r"^\|[\s:|-]+\|$", lines[n].strip()):
                    header = _cells(line)  # the row above a |---| separator
                m = TABLE_ID_RE.match(line)
                if m and m.group(1) in ids and m.group(1) not in seen:
                    seen.add(m.group(1))
                    fields = {h: c for h, c in zip(header, _cells(line), strict=False) if h}
                    out.append((m.group(1), prefix, f, n, line, fields))
    return out


STATUS_MARKS = ("✅", "❌", "🗑", "⚠️")


def _rule_title(rule: Rule, text: str, index: list[str]) -> str:
    """A rule's heading after its ID; a one-file rule (which opens with its
    metadata, not a title): its `rules.md` bullet after the dash
    (`` - `<ID>-<slug>` — Title ``), else its file's slug."""
    if rule.file.name.startswith(rule.id):
        entry = re.compile(rf"^\s*[-*]\s+`{re.escape(rule.id)}(?:-[a-z0-9-]+)?`\s+—\s+(.+)$")
        for line in index:
            if m := entry.match(line):
                return m.group(1).strip()
        return rule.file.stem[len(rule.id) :].strip("-").replace("-", " ")
    first = text.splitlines()[0] if text else ""
    heading = re.sub(r"^\d+\.\s+", "", first.lstrip("#").strip())
    return heading.replace(f"`{rule.id}`", "").replace(rule.id, "").strip(" —-")


def _rule_status(text: str) -> str:
    """The first line of a rule's text carrying a status mark, without its
    `Status` label."""
    for line in text.splitlines()[1:]:
        if any(mark in line for mark in STATUS_MARKS):
            return re.sub(r"^[-*\s]*(\*\*Status\*\*:?|\*\*Status:\*\*)\s*:?\s*", "", line.strip()).strip()
    return ""


def _domain_docs(dep: Deployment, corpus: Corpus) -> list[dict]:
    """Each registered domain: its code, the file its registry row links to
    (criterion-relative, None when absent) and that file's first heading."""
    registry = dep.root / "rules" / "domains" / "domains.md"
    links: dict[str, str] = {}
    if registry.is_file():
        for line in registry.read_text(encoding="utf-8").splitlines():
            m = DOMAIN_ROW_RE.match(line)
            link = re.search(r"\]\(([^)]+)\)", line)
            if m and link:
                links.setdefault(m.group(1), link.group(1))
    out = []
    for code in sorted(corpus.domains):
        path = (registry.parent / links[code]) if code in links else None
        title = ""
        if path is not None and path.is_file():
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if h1 := H1_RE.match(line):
                    title = h1.group(1).strip()
                    break
        else:
            path = None
        out.append({"code": code, "file": _rel(dep, path) if path else None, "title": title})
    return out


def graph(dep: Deployment, corpus: Corpus) -> dict:
    """The whole chain in one answer: rules (with their domain), domains,
    artifacts (each `list` row plus `links`, the IDs each reference field
    cites; an item kept as a table row has `row: true` and its cells by
    header in `fields`), `types`, each
    entity type's definition. Every rule and artifact also carries
    `mentions`: the IDs its own text cites in backticks, apart from its
    field links."""
    rows = _rows(dep, corpus)
    resolve = _resolver(corpus, corpus.all_ids() | set(corpus.domains))
    artifacts = []
    for prefix in sorted(corpus.by_prefix):
        refs = _ref_fields(dep, prefix)
        for art in corpus.by_prefix[prefix]:
            row = _artifact_row(dep, art)
            row["links"] = {name: ref_values(art.get(name) or "") for name in refs if art.get(name) is not None}
            try:
                text = art.file.read_text(encoding="utf-8")
            except OSError:
                text = ""
            row["mentions"] = _mentions(text, resolve, art.id)
            artifacts.append(row)
    for item, prefix, f, n, line, cells in rows:
        artifacts.append(
            {
                "id": item,
                "type": prefix,
                "file": _rel(dep, f),
                "line": n,
                "row": True,
                "fields": cells,
                "links": {},
                "mentions": _mentions(line, resolve, item),
            }
        )
    types = {
        prefix: {
            "name": etd.name,
            "plural_name": etd.plural_name,
            "folder": etd.folder,
            "location": etd.location,
            "grounding": etd.grounding,
            "grounding_field": etd.grounding_field,
            "fields": [
                {"name": f.name, "kind": f.kind, "required": f.required, "target_type": f.target_type}
                for f in etd.fields
            ],
            "states": list(etd.workflow.states),
            "initial": etd.workflow.initial,
            "closed_states": list(etd.workflow.closed_states),
        }
        for prefix, etd in sorted(dep.etds.items())
    }
    rules = []
    rules_index = dep.root / "rules" / "rules.md"
    index = rules_index.read_text(encoding="utf-8").splitlines() if rules_index.is_file() else []
    for rid, defs in sorted(corpus.rules.items()):
        text = _rule_text(defs[0])
        rules.append(
            {
                "id": rid,
                "title": _rule_title(defs[0], text, index),
                "status": _rule_status(text),
                "file": _rel(dep, defs[0].file),
                "line": defs[0].line,
                "retired": defs[0].retired,
                "domain": _rule_domain(rid),
                "mentions": _mentions(text, resolve, rid),
            }
        )
    return {"rules": rules, "domains": _domain_docs(dep, corpus), "artifacts": artifacts, "types": types}


def render_graph(g: dict) -> str:
    open_count = sum(
        1
        for a in g["artifacts"]
        if not a.get("row") and (a.get("Status") or "") not in g["types"].get(a["type"], {}).get("closed_states", [])
    )
    links = sum(len(v) for a in g["artifacts"] for v in a["links"].values())
    return (
        f"{len(g['rules'])} rule(s) in {len(g['domains'])} domain(s); {len(g['artifacts'])} artifact(s), "
        f"{open_count} open, {links} link(s); {len(g['types'])} entity type(s) (`--json` for the graph)\n"
    )


# --- text -----------------------------------------------------------------
def render_list(rows: list[dict]) -> str:
    if not rows:
        return "(none)\n"
    lines = []
    for r in rows:
        head = r.get("id") or r.get("name") or r.get("family") or "?"
        extra = [
            f"{k}: {v}"
            for k, v in r.items()
            if k in ("Status", "status", "title", "roles", "active", "version", "retired") and v not in ("", None)
        ]
        lines.append(f"{head}  {r.get('file', '')}".rstrip() + (f"  ({'; '.join(map(str, extra))})" if extra else ""))
    return "\n".join(lines) + f"\n{len(rows)} item(s)\n"


def render_journal(entries: list[dict]) -> str:
    if not entries:
        return "(no journal entries)\n"
    out = []
    for e in entries:
        targets = ", ".join(e.get("targets") or []) or "-"
        intent = " / ".join(e.get("intent") or []) if isinstance(e.get("intent"), list) else str(e.get("intent", ""))
        out.append(
            f"{e.get('timestamp')}  {e.get('actor')}  {e.get('command')} {e.get('action')}  "
            f"{e.get('artifact')}  [{targets}]\n    {intent}"
        )
    return "\n".join(out) + f"\n{len(entries)} entr{'y' if len(entries) == 1 else 'ies'}\n"


def render_view(v: dict) -> str:
    skip = {"links", "linked_from", "journal"}
    lines = [f"{v['id']}  ({v['type']})  {v.get('file', '')}"]
    lines += [f"  {k}: {val}" for k, val in v.items() if k not in skip | {"id", "type", "file"}]
    lines.append("links:" if v["links"] else "links: (none)")
    lines += [f"  {name}: {', '.join(ids) or '-'}" for name, ids in v["links"].items()]
    lines.append("linked from:" if v["linked_from"] else "linked from: (none)")
    lines += [f"  {x['id']} ({x['field']})" for x in v["linked_from"]]
    lines.append(f"journal: {len(v['journal'])} entr{'y' if len(v['journal']) == 1 else 'ies'}")
    lines += [f"  {e['timestamp']}  {e['actor']}  {e['command']} {e['action']}" for e in v["journal"]]
    return "\n".join(lines) + "\n"


def render_backlog(b: dict) -> str:
    lines = ["Open work:"] if b["open"] else ["Open work: (none)"]
    for prefix, by_status in b["open"].items():
        total = sum(len(v) for v in by_status.values())
        lines.append(f"  {prefix}: {total}")
        lines += [f"    {status}: {', '.join(ids)}" for status, ids in sorted(by_status.items())]
    lines.append(f"Open items missing a required link: {len(b['missing_links'])}")
    lines += [f"  {m['id']}: {m['field']}" for m in b["missing_links"]]
    lines.append(f"Rules no open item targets: {len(b['rules_without_open_work'])}")
    lines += [f"  {r}" for r in b["rules_without_open_work"]]
    return "\n".join(lines) + "\n"
