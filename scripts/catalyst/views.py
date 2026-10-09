"""Read-only views of a deployment (roadmap R2 W1): `list`, `journal show`,
`view` and `backlog`.

What `/list`, `/user-list`, `/journal` and a module's backlog summary asked
an agent to work out by reading files is computed here, from the working copy
and the entity type definitions (ETDs) alone, so no module entity is named in
this file. Nothing here writes.

Each function returns plain data (lists and dicts, ready for `--json`);
`render_*` turns it into text.
"""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path

from catalyst import journal
from catalyst.corpus import Artifact, Corpus, norm_field, ref_values
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


def view(dep: Deployment, corpus: Corpus, item_id: str) -> dict:
    arts = corpus.artifacts.get(item_id)
    if arts:
        art = arts[0]
        out = _artifact_row(dep, art)
        out["links"] = {
            name: ref_values(art.get(name) or "") for name in _ref_fields(dep, art.prefix) if art.get(name) is not None
        }
    elif item_id in corpus.rules:
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
