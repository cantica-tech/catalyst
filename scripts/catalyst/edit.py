"""Writing verbs (roadmap R2 W2): `new`, `status set` and `link`.

The mechanical half of the create, status and linking procedures, driven by
the entity type definitions (ETDs) alone: allocate the ID, fill the type's
latest template, sign it, keep back-references both ways, regenerate the
indexes and journal every touched file. What stays with the agent is the
judgment: the content of the artifact's sections, which rules it targets,
whether a change should happen at all.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

from catalyst import indexes, journal
from catalyst.corpus import FIELD_ROW_RE, Artifact, Corpus, load_corpus, norm_field, ref_values
from catalyst.deployment import Deployment
from catalyst.ids import next_entity_id
from module_loader import ETD, FieldDefinition

RECONCILIATION = "RECON"  # its Status changes only through /reconcile (role gate)
REF_KINDS = ("ref", "ref-list")
NONE_YET = "*(none yet)*"
SLUG_RE = re.compile(r"[^a-z0-9]+")


class EditError(Exception):
    pass


@dataclass
class Result:
    id: str
    file: Path
    touched: list[Path] = field(default_factory=list)


# --- helpers --------------------------------------------------------------
def slug(text: str) -> str:
    return SLUG_RE.sub("-", text.lower()).strip("-")[:60].strip("-") or "item"


def etd_named(dep: Deployment, name: str) -> ETD:
    for prefix, etd in dep.etds.items():
        if name.lower() in {prefix.lower(), etd.name.lower(), etd.plural_name.lower(), etd.folder.lower()}:
            return etd
    raise EditError(f"unknown entity type '{name}' (known: {', '.join(sorted(dep.etds))})")


def field_def(etd: ETD, name: str) -> FieldDefinition:
    for f in etd.fields:
        if norm_field(f.name) == norm_field(name):
            return f
    raise EditError(f"{etd.id_prefix} has no field '{name}' (fields: {', '.join(f.name for f in etd.fields)})")


def latest_template(dep: Deployment, etd: ETD) -> Path:
    folder = dep.folder(etd)
    found = []
    for p in (folder / "templates").glob("TEMPLATE-*-v*.md") if folder else []:
        m = re.search(r"-v(\d+)\.md$", p.name)
        if m:
            found.append((int(m.group(1)), p))
    if not found:
        raise EditError(f"no template for {etd.id_prefix} in {folder}/templates")
    return max(found)[1]


def set_field(text: str, name: str, value: str) -> str:
    """Replace the value cell of the `| **name** | … |` row."""
    want = norm_field(name)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        m = FIELD_ROW_RE.match(line)
        if m and norm_field(m.group(1)) == want:
            lines[i] = f"| **{m.group(1)}** | {value} |"
            return "\n".join(lines)
    raise EditError(f"no `{name}` row in the artifact's field table")


def set_or_add_field(text: str, name: str, value: str) -> str:
    """`set_field`, adding the row at the end of the field table when an older
    artifact predates the field."""
    try:
        return set_field(text, name, value)
    except EditError:
        lines = text.split("\n")
        last = max((i for i, line in enumerate(lines) if FIELD_ROW_RE.match(line)), default=None)
        if last is None:
            raise
        lines.insert(last + 1, f"| **{name}** | {value} |")
        return "\n".join(lines)


def _ticked(ids: list[str]) -> str:
    return ", ".join(f"`{i}`" for i in ids) if ids else NONE_YET


def _artifact(corpus: Corpus, item_id: str) -> Artifact:
    arts = corpus.artifacts.get(item_id)
    if not arts:
        raise EditError(f"no artifact '{item_id}' in this deployment")
    return arts[0]


def _check_refs(dep: Deployment, corpus: Corpus, fd: FieldDefinition, ids: list[str]) -> None:
    if fd.target_type in ("rule", "domain"):
        known = set(corpus.rules) if fd.target_type == "rule" else corpus.domains
    else:
        allowed = set((fd.target_type or "").split("|")) - {""}
        known = {i for i, arts in corpus.artifacts.items() if not allowed or arts[0].prefix in allowed}
    missing = [i for i in ids if i not in known]
    if missing:
        raise EditError(f"`{fd.name}` cites what does not exist here: {', '.join(missing)}")


def _add_backrefs(dep: Deployment, corpus: Corpus, fd: FieldDefinition, source_id: str, ids: list[str]) -> list[Path]:
    """Cite `source_id` in each target's back-reference field."""
    if not fd.backref:
        return []
    touched = []
    for target_id in ids:
        target = _artifact(corpus, target_id)
        current = ref_values(target.get(fd.backref) or "")
        if source_id in current:
            continue
        text = target.file.read_text(encoding="utf-8")
        target.file.write_text(set_or_add_field(text, fd.backref, _ticked(current + [source_id])), encoding="utf-8")
        touched.append(target.file)
    return touched


def _finish(
    dep: Deployment,
    command: str,
    action: str,
    item_id: str,
    targets: list[str],
    intent: list[str],
    files: list[Path],
    actor: str,
    tier: str | None,
) -> None:
    """Common ending: indexes, then one journal entry for every touched file."""
    changes = indexes.regenerate(dep, load_corpus(dep))
    paths = list(dict.fromkeys([*files, *(c.path for c in changes)]))
    journal.append(
        dep,
        journal.AppendRequest(
            command=command,
            action=action,
            artifact=item_id,
            targets=targets,
            intent=intent,
            files=[str(p) for p in paths],
            actor=actor,
            tier=tier,
        ),
    )


# --- new ------------------------------------------------------------------
def new(
    dep: Deployment,
    corpus: Corpus,
    type_name: str,
    title: str,
    values: dict[str, str],
    signer: dict,
    intent: list[str],
    command: str = "catalyst new",
    tier: str | None = None,
    today: datetime.date | None = None,
) -> Result:
    etd = etd_named(dep, type_name)
    if etd.naming == "free-form":
        raise EditError(f"{etd.id_prefix} items are table rows, not files: edit them with their module command")
    given: dict[str, list[str] | str] = {}
    for name, raw in values.items():
        fd = field_def(etd, name)
        if fd.kind in REF_KINDS:
            ids = [v.strip() for v in raw.split(",") if v.strip()]
            if fd.kind == "ref" and len(ids) > 1:
                raise EditError(f"`{fd.name}` takes one ID")
            _check_refs(dep, corpus, fd, ids)
            given[fd.name] = ids
        else:
            if fd.kind == "enum" and fd.allowed_values and raw not in fd.allowed_values:
                raise EditError(f"`{fd.name}` must be one of {', '.join(fd.allowed_values)}")
            given[fd.name] = raw
    status = field_def(etd, "Status") if any(norm_field(f.name) == norm_field("Status") for f in etd.fields) else None
    if status is not None and status.name not in given:
        given[status.name] = etd.workflow.initial
    missing = [
        f.name
        for f in etd.fields
        if f.required
        and f.name not in given
        and norm_field(f.name) not in (norm_field("ID"), norm_field("Status"))
        and f.kind not in ("date", "user")
    ]
    if missing:
        raise EditError(f"{etd.id_prefix} needs {', '.join('--field ' + m + '=…' for m in missing)}")

    item_id = next_entity_id(dep, corpus, etd.id_prefix, signer, reserve=True)
    number = item_id.split("-")[1]
    name = slug(title)
    folder = dep.folder(etd)
    path = folder / f"{etd.id_prefix}-{number}-{name}.md"
    text = latest_template(dep, etd).read_text(encoding="utf-8")
    text = re.sub(r"^#\s+.*$", f"# `{item_id}` — {title}", text, count=1, flags=re.M)
    signer_name = str(signer.get("name"))
    day = (today or datetime.date.today()).isoformat()
    row_values: dict[str, str] = {"ID": f"`{item_id}`", "Name": f"`{name}`", "Filename": f"`{path.name}`"}
    for fd in etd.fields:
        if fd.name in given:
            v = given[fd.name]
            row_values[fd.name] = _ticked(v) if isinstance(v, list) else str(v)
        elif fd.kind == "user":
            row_values[fd.name] = signer_name
        elif fd.kind == "date":
            row_values[fd.name] = day
        elif fd.kind in REF_KINDS:
            row_values[fd.name] = NONE_YET
    for name_, value in row_values.items():
        try:
            text = set_field(text, name_, value)
        except EditError:
            if name_ in {f.name for f in etd.fields}:
                raise
    for line in text.split("\n"):  # fields the template has but the ETD does not declare
        m = FIELD_ROW_RE.match(line)
        if m and m.group(1) in ("Opened", "Created") and m.group(1) not in row_values:
            text = set_field(text, m.group(1), day)
        if m and norm_field(m.group(1)) == norm_field("Signed-off-by") and "Signed-off-by" not in row_values:
            text = set_field(text, m.group(1), signer_name)
    if path.exists():
        raise EditError(f"{path} already exists")
    path.write_text(text, encoding="utf-8")

    touched = [path]
    corpus = load_corpus(dep)
    for fd in etd.fields:
        if fd.kind in REF_KINDS and isinstance(given.get(fd.name), list):
            touched += _add_backrefs(dep, corpus, fd, item_id, given[fd.name])
    targets = given.get(etd.grounding_field, []) if etd.grounding_field else []
    _finish(
        dep,
        command,
        "create",
        item_id,
        list(targets) if isinstance(targets, list) else [],
        intent or [f"Create {item_id}: {title}"],
        touched,
        str(signer.get("git_username") or signer_name),
        tier,
    )
    return Result(item_id, path, touched)


# --- status set -----------------------------------------------------------
def set_status(
    dep: Deployment,
    corpus: Corpus,
    item_id: str,
    status: str,
    signer: dict,
    intent: list[str],
    force: bool = False,
    command: str = "/status",
    tier: str | None = None,
) -> Result:
    art = _artifact(corpus, item_id)
    if art.prefix == RECONCILIATION:
        raise EditError(f"{item_id} is a reconciliation case: only /reconcile changes its Status")
    etd = dep.etds[art.prefix]
    fd = field_def(etd, "Status")
    old = (art.get(fd.name) or "").strip()
    if status == old:
        raise EditError(f"{item_id} is already {status}")
    if fd.allowed_values and status not in fd.allowed_values and not force:
        raise EditError(
            f"'{status}' is not a {etd.name} status ({', '.join(fd.allowed_values)}); force writes it anyway"
        )
    allowed = {(t.from_state, t.to_state) for t in etd.workflow.transitions}
    if allowed and (old, status) not in allowed and not force:
        nexts = sorted(t for f, t in allowed if f == old)
        raise EditError(f"{etd.name} cannot go from {old} to {status} (from {old}: {', '.join(nexts) or 'nothing'})")
    art.file.write_text(set_field(art.file.read_text(encoding="utf-8"), fd.name, status), encoding="utf-8")
    grounding = ref_values(art.get(etd.grounding_field) or "") if etd.grounding_field else []
    _finish(
        dep,
        command,
        "status-change",
        item_id,
        grounding,
        intent or [f"{item_id}: {old or '(none)'} -> {status}"],
        [art.file],
        str(signer.get("git_username") or signer.get("name")),
        tier,
    )
    return Result(item_id, art.file, [art.file])


# --- link -----------------------------------------------------------------
def link(
    dep: Deployment,
    corpus: Corpus,
    item_id: str,
    field_name: str,
    ids: list[str],
    signer: dict,
    intent: list[str],
    command: str = "catalyst link",
    tier: str | None = None,
) -> Result:
    art = _artifact(corpus, item_id)
    etd = dep.etds[art.prefix]
    fd = field_def(etd, field_name)
    if fd.kind not in REF_KINDS:
        raise EditError(f"`{fd.name}` is not a reference field")
    _check_refs(dep, corpus, fd, ids)
    current = ref_values(art.get(fd.name) or "")
    added = [i for i in ids if i not in current]
    if not added:
        raise EditError(f"{item_id} `{fd.name}` already cites {', '.join(ids)}")
    if fd.kind == "ref" and len(current + added) > 1:
        raise EditError(f"`{fd.name}` takes one ID and already cites {', '.join(current)}")
    art.file.write_text(
        set_field(art.file.read_text(encoding="utf-8"), fd.name, _ticked(current + added)), encoding="utf-8"
    )
    touched = [art.file] + _add_backrefs(dep, load_corpus(dep), fd, item_id, added)
    grounding = ref_values(art.get(etd.grounding_field) or "") if etd.grounding_field else []
    _finish(
        dep,
        command,
        "update",
        item_id,
        grounding,
        intent or [f"{item_id} `{fd.name}` cites {', '.join(added)}"],
        touched,
        str(signer.get("git_username") or signer.get("name")),
        tier,
    )
    return Result(item_id, art.file, touched)
