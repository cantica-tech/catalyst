"""Writing verbs (roadmap R2 W2): `new`, `status set` and `link`.

The mechanical half of the create, status and linking procedures, driven by
the entity type definitions (ETDs) alone: allocate the ID, fill the type's
latest template, sign it, keep back-references both ways, regenerate the
indexes and journal every touched file. What stays with the agent is the
judgment: the content of the artifact's sections, which rules it targets,
whether a change should happen at all.
"""

from __future__ import annotations

import contextlib
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
    # never ending in "-<digits>", which INV-7 reads as a bare ID ("… r2 adr-020" cut to "…-adr-02")
    return re.sub(r"(?:(?:^|-)\d+)+$", "", SLUG_RE.sub("-", text.lower()).strip("-")[:60].strip("-")) or "item"


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
    missing = [i for i in ids if i not in known and not (fd.target_type == "rule" and corpus.rule_id(i))]
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
    extra: dict | None = None,
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
            extra=extra,
        ),
    )


def recompute_derived(dep: Deployment, item_id: str, path: Path) -> None:
    """An entity's derived fields from their sources now, never from the content written."""
    from catalyst import derived

    for d in derived.drift(dep, load_corpus(dep)):
        if d.art.id == item_id:
            path.write_text(
                set_or_add_field(path.read_text(encoding="utf-8"), d.field, _ticked(d.expected)), encoding="utf-8"
            )


# --- rename ---------------------------------------------------------------
def rename(
    dep: Deployment,
    corpus: Corpus,
    item_id: str,
    title: str,
    signer: dict,
    intent: list[str],
    command: str = "catalyst rename",
    tier: str | None = None,
) -> Result:
    """A new title for an artifact: its heading, `Name`, `Filename` and file
    name follow (L7: the ID never changes). References cite the ID, so none
    is rewritten; the indexes are regenerated and the move journaled."""
    art = _artifact(corpus, item_id)
    old = art.file
    prefix, number = item_id.split("-")[:2]
    name = slug(title)
    path = old.parent / f"{prefix}-{number}-{name}.md"
    if path != old and path.exists():
        raise EditError(f"{path} already exists")
    text = old.read_text(encoding="utf-8")
    text = re.sub(r"^#\s+.*$", f"# `{item_id}` — {title}", text, count=1, flags=re.M)
    for field_name, value in (("Name", f"`{name}`"), ("Filename", f"`{path.name}`")):
        with contextlib.suppress(EditError):  # a type without the field
            text = set_field(text, field_name, value)
    path.write_text(text, encoding="utf-8")
    touched = [path]
    if path != old:
        old.unlink()
        touched.append(old)
    _finish(
        dep,
        command,
        "update",
        item_id,
        [],
        intent or [f"Rename {item_id}: {title}"],
        touched,
        str(signer.get("git_username") or signer.get("name")),
        tier,
    )
    return Result(item_id, path, touched)


# --- restore --------------------------------------------------------------
def restore(
    dep: Deployment,
    corpus: Corpus,
    item_id: str,
    when: str,
    signer: dict,
    intent: list[str],
    command: str = "catalyst restore",
    tier: str | None = None,
) -> Result:
    """Write an entity's file back as it stood at `when`: the content after
    the last journal entry at or before that time, or after its Nth change
    (`#N`, from 1, exact when timestamps tie); its derived fields are then
    recomputed from their sources. A new journaled change,
    never a rewrite: every entry stays as it was (L1). A rule kept in a
    document with other rules is refused (its document holds them too)."""
    from catalyst import history as entity_history, views

    found = views.resolve(corpus, item_id)
    if found is None:
        raise EditError(f"no artifact or rule '{item_id}' in this deployment")
    if found in corpus.rules and not corpus.rules[found][0].file.name.startswith(found):
        raise EditError(f"{found} shares its rule document with other rules; restoring it would restore them too")
    h = entity_history.history(dep, corpus, found)
    if when.startswith("#"):  # the Nth change of its history: exact even when timestamps tie
        n = int(when[1:]) if when[1:].isdigit() else 0
        if not 1 <= n <= len(h["entries"]):
            raise EditError(f"{found} has {len(h['entries'])} change(s) in its history; {when} is none of them")
        version = h["entries"][n - 1]
    else:
        earlier = [e for e in h["entries"] if (e["timestamp"] or "") <= when]
        if not earlier:
            raise EditError(f"no version of {found} at {when}: its first journal entry is later")
        version = earlier[-1]
    if version["redacted"]:
        raise EditError(f"the version of {found} at {when} was redacted; it cannot be restored")
    if version["after"] is None:
        raise EditError(f"{found}'s file did not exist at {when} (removed by the entry of {version['timestamp']})")
    content = version["content_after"]
    if content is None:
        raise EditError(f"catalyst no longer holds the version of {found} at {when}")
    if found in corpus.artifacts:
        from catalyst import gates

        art = corpus.artifacts[found][0]
        then = ""
        for line in content.splitlines():
            m = FIELD_ROW_RE.match(line)
            if m and norm_field(m.group(1)) == norm_field("Status"):
                cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
                then = (cells[1] if len(cells) > 1 else "").strip("`")
                break
        now = (art.get("Status") or "").strip().strip("`")
        try:
            refused = gates.refusal(dep, corpus, found, then) if then and then != now else None
        except gates.GateError as exc:
            raise EditError(str(exc)) from None
        if refused:
            raise EditError(f"restoring {found} moves it to {then}, a gated state: {refused}")
    path = dep.root / h["file"]
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        raise EditError(f"{found} is already as it stood at {when}")
    path.write_text(content, encoding="utf-8")
    recompute_derived(dep, found, path)  # derived fields come from their sources now, never from the old version
    _finish(
        dep,
        command,
        "update",
        found,
        [],
        intent or [f"Restore {found} to its version of {version['timestamp']}"],
        [path],
        str(signer.get("git_username") or signer.get("name")),
        tier,
    )
    return Result(found, path, [path])


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
    if status is not None:
        from catalyst import gates

        try:
            entered = gates.entering(dep, corpus, etd.id_prefix, str(given[status.name]))
        except gates.GateError as exc:
            raise EditError(str(exc)) from None
        if entered:  # a version nobody approved yet: create it, approve it, then `status set`
            raise EditError(
                f"{etd.name} enters {given[status.name]} through gate {entered[0].id}: create it in another "
                "state, have it approved, then `catalyst status set`"
            )
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
        # a required user or date field defaults to the signer and today; an
        # optional one (an assignee, a due date) stays empty until it is given
        elif fd.kind == "user" and fd.required:
            row_values[fd.name] = signer_name
        elif fd.kind == "date" and fd.required:
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
    from catalyst import gates

    try:
        refused = gates.refusal(dep, corpus, item_id, status)  # before the guards: --force never passes a gate
    except gates.GateError as exc:
        raise EditError(str(exc)) from None
    if refused:
        raise EditError(refused)
    from catalyst.guards import failures

    blocked = failures(dep, corpus, art, status)
    if blocked and not force:
        raise EditError(
            f"{item_id} cannot become {status}: {'; '.join(blocked)} (the module's guards; --force overrides, journaled)"
        )
    if blocked:
        intent = [
            *(intent or [f"{item_id}: {old or '(none)'} -> {status}"]),
            f"guards overridden with --force: {'; '.join(blocked)}",
        ]
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


# --- reconcile ------------------------------------------------------------
RESOLVING = {
    "accept": "Resolved-Accepted",
    "accept-with-edits": "Resolved-Accepted-with-Edits",
    "reject": "Resolved-Rejected",
}
RECON_VERBS = (*RESOLVING, "propose", "close")
LEVELS = {"none": 0, "propose": 1, "full": 2}


def reconciliation_level(dep: Deployment, signer: dict) -> tuple[str, str]:
    """The signer's reconciliation level — the highest among their roles'
    `reconciliation` (a role without one counts as `none`) — and the role
    that grants it."""
    import json

    try:
        roles = json.loads((dep.root / "IAM" / "roles" / "roles.json").read_text(encoding="utf-8")).get("roles", [])
    except (OSError, ValueError):
        roles = []
    by_name = {str(r.get("name")): str(r.get("reconciliation") or "none") for r in roles if isinstance(r, dict)}
    best = ("none", "")
    for role in signer.get("roles") or []:
        level = by_name.get(str(role), "none")
        if LEVELS.get(level, 0) > LEVELS[best[0]]:
            best = (level, str(role))
    return best


def _append_revision(text: str, author: str, note: str, blob: str | None = None) -> str:
    """A new row at the end of the `## Revisions` table."""
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.strip() == "## Revisions"), None)
    if start is None:
        raise EditError("no `## Revisions` section in the case")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    rows = [i for i in range(start + 1, end) if lines[i].startswith("|")]
    if not rows:
        raise EditError("no revisions table in the case's `## Revisions` section")
    numbers = [int(m.group(1)) for i in rows if (m := re.match(r"^\|\s*(\d+)\s*\|", lines[i]))]
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    cell = note.replace("|", "\\|").replace("\n", " ")
    hashed = f"`{blob}`" if blob else "—"
    lines.insert(rows[-1] + 1, f"| {max(numbers, default=0) + 1} | {author} | {stamp} | {hashed} | {cell} |")
    return "\n".join(lines)


def reconcile(
    dep: Deployment,
    corpus: Corpus,
    case_id: str,
    verb: str,
    signer: dict,
    text: str = "",
    intent: list[str] | None = None,
    content: str | None = None,
) -> Result:
    """`/reconcile <case> <verb>` (Rules-of-Rules.md rr-META-016, INV-21): the
    one role check catalyst enforces. `full` may use every verb, `propose`
    only `propose`, `none` nothing. On a dispute it records the decision;
    applying an accepted version stays the human's (or the agent's, on the
    human's word) ordinary, journaled work. On a proposal (design 26)
    `accept` writes the proposed content to the entity (`accept-with-edits`
    writes `content`), `propose` with `content` revises it, and its author
    may `close` it while it is open (withdrawn)."""
    from catalyst import proposals

    if verb not in RECON_VERBS:
        raise EditError(f"'{verb}' is not a reconcile verb ({', '.join(RECON_VERBS)})")
    art = _artifact(corpus, case_id)
    if art.prefix != RECONCILIATION:
        raise EditError(f"{case_id} is not a reconciliation case")
    who = str(signer.get("name") or signer.get("git_username"))
    level, role = reconciliation_level(dep, signer)
    proposal = proposals.is_proposal(art)
    withdrawing = (
        proposal
        and verb == "close"
        and proposals.is_open(art)
        and _same_user(signer, (art.get("Signed-off-by") or "").strip())
    )
    if level == "none" and not withdrawing:
        raise EditError(
            f"{who} has no reconciliation rights (no role grants `propose` or `full`): ask a `full` or "
            "`propose` user to act"
        )
    if verb != "propose" and level != "full" and not withdrawing:
        raise EditError(f"`{verb}` needs a `full` reconciliation role; {who} ({role}) may only `propose`")
    status = (art.get("Status") or "").strip()
    if status == "Closed":
        raise EditError(f"{case_id} is Closed: a closed case is final")
    resolved = status.startswith("Resolved-")
    body = art.file.read_text(encoding="utf-8")
    files, targets, extra = [art.file], [], None
    if content is not None and not (proposal and verb in ("propose", "accept-with-edits")):
        raise EditError("--from is for a proposal's `propose` or `accept-with-edits`")
    try:
        if verb == "propose":
            if resolved:
                raise EditError(f"{case_id} is already {status}: close it, or open a new case")
            if content is not None:
                blob, proposed, base = proposals.revise(dep, corpus, art, content)
                body = set_or_add_field(body, "Proposed", f"`{blob}` — `{proposed.relative_to(dep.root).as_posix()}`")
                entity_file = proposals.info(dep, corpus, art)["path"]
                body = set_or_add_field(body, "Baseline", f"`{base}` — `{entity_file}` when this revision was made")
                note = text.strip() or "Revised proposal"
                body, files = _append_revision(body, who, note, blob), [art.file, proposed]
            elif not text.strip():
                raise EditError(
                    "`propose` needs the proposal's text (--text)" + (" or content (--from)" if proposal else "")
                )
            else:
                body = _append_revision(body, who, text.strip())
            new = "Under Review"
        elif verb == "close":
            if not resolved and not withdrawing:
                raise EditError(f"{case_id} is {status or 'not resolved'}: resolve it (accept/reject) before closing")
            new = "Closed"
        else:
            if resolved:
                raise EditError(f"{case_id} is already {status}")
            if proposal and verb in ("accept", "accept-with-edits"):
                if verb == "accept-with-edits" and content is None:
                    raise EditError("`accept-with-edits` on a proposal needs the content it accepts (--from)")
                target, extra = proposals.apply(dep, corpus, art, signer, content)
                files, targets = [art.file, target], [_clean_ref(art.get("Entity"))]
                if content is not None:
                    blob = journal.git(dep.root, "hash-object", "--", target.relative_to(dep.root).as_posix())
                    body = _append_revision(body, who, "Accepted with edits", blob)
            new = RESOLVING[verb]
            today = datetime.date.today().isoformat()
            body = set_or_add_field(set_or_add_field(body, "Resolved", today), "Resolver", f"{who} ({role})")
    except proposals.ProposalError as exc:
        raise EditError(str(exc)) from None
    body = set_field(body, "Status", new)
    art.file.write_text(body, encoding="utf-8")
    _finish(
        dep,
        "/reconcile",
        "status-change" if new != status else "update",
        case_id,
        targets,
        list(intent or [])
        or [f"{case_id}: {verb} ({status or '?'} -> {new})" + (f" — {text.strip()}" if text else "")],
        files,
        str(signer.get("git_username") or signer.get("name")),
        None,
        extra,
    )
    return Result(case_id, art.file, files)


def _clean_ref(value: str | None) -> str:
    return (value or "").strip().strip("`").strip()


def _same_user(signer: dict, name: str) -> bool:
    from catalyst.gates import _same

    return _same(signer, name)
