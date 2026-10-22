"""Workflow governance (W2, W3): a `WORKFLOW-` that governs a type's moves,
and the due dates its entities are held to.

A workflow governs a type when it names it (`Governs`) and is `Active`. Its
`## Transitions` table lists the moves allowed, one per row:

| From | To | Role | When |
|---|---|---|---|
| Draft | Active | Knowledge Curator | |
| Built | Published | Knowledge Curator | Classification at most Internal |
| * | Withdrawn | Admin | |

`From` may be `*` (any state); `Role` is the role the signer must hold (an
`Admin` holds every one; empty: anyone); `When` a condition on the entity's
fields (`catalyst.conditions`; empty: always). While it is `Active`, a move
of that type must be one of its rows: `status set` refuses any other, and
`--force` does not pass it (it is governance, like a gate). One type has at
most one active governing workflow; `check` reports what is wrong with one.

A type may declare when its open entities are due (`due:`, a date field, or
one plus days: `Checked + 30 days`). One past it is `overdue`: the inbox
lists it with the role its governing workflow `Escalates to`, and `check`
warns.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field

from catalyst import conditions
from catalyst.corpus import Artifact, Corpus, is_empty
from catalyst.deployment import Deployment

WORKFLOW = "WORKFLOW"
ACTIVE = "Active"
ADMIN = "Admin"
DUE = re.compile(r"^\s*(?P<field>[^+]+?)\s*(?:\+\s*(?P<days>\d+)\s*days?)?\s*$")


@dataclass(frozen=True)
class Move:
    from_state: str  # "*": any
    to_state: str
    role: str | None = None
    when: str | None = None


@dataclass
class Governing:
    id: str
    prefix: str
    escalates_to: str | None
    moves: list[Move] = field(default_factory=list)


def _cell(text: str) -> str:
    value = text.strip().strip("`").strip()
    return "" if is_empty(value) or value in ("-", "—") else value


def _transitions(text: str) -> list[Move]:
    """The rows of a workflow's `## Transitions` table."""
    m = re.search(r"^##\s+Transitions\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return []
    moves = []
    for line in m.group(1).splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [_cell(c) for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or set("".join(cells)) <= set("-: ") or cells[0].lower() == "from":
            continue
        cells += [""] * (4 - len(cells))
        if cells[0] and cells[1]:
            moves.append(Move(cells[0], cells[1], cells[2] or None, cells[3] or None))
    return moves


def _status(art: Artifact) -> str:
    return (art.get("Status") or "").strip().strip("`")


def governing_all(dep: Deployment, corpus: Corpus) -> list[Governing]:
    """Every active workflow that governs a type."""
    out = []
    for art in corpus.by_prefix.get(WORKFLOW, []):
        prefix = _cell(art.get("Governs") or "")
        if not prefix or _status(art) != ACTIVE:
            continue
        text = art.file.read_text(encoding="utf-8")
        out.append(Governing(art.id, prefix, _cell(art.get("Escalates to") or "") or None, _transitions(text)))
    return out


def governing(dep: Deployment, corpus: Corpus, prefix: str) -> Governing | None:
    return next((g for g in governing_all(dep, corpus) if g.prefix == prefix), None)


def problems(dep: Deployment, corpus: Corpus) -> list[str]:
    """What is wrong with the active governing workflows (`check` reports each as an error)."""
    from catalyst.corpus import roles as all_roles

    known_roles = {str(r.get("name")) for r in all_roles(dep)}
    out, seen = [], {}
    for g in governing_all(dep, corpus):
        etd = dep.etds.get(g.prefix)
        if etd is None:
            out.append(f"{g.id}: governs `{g.prefix}`, which is not a declared type")
            continue
        if g.prefix in seen:
            out.append(f"{g.id}: {etd.name} is already governed by {seen[g.prefix]}: one active workflow per type")
        seen.setdefault(g.prefix, g.id)
        if not g.moves:
            out.append(f"{g.id}: governs {etd.name} but its `## Transitions` table lists no move")
        if g.escalates_to and g.escalates_to not in known_roles:
            out.append(f"{g.id}: escalates to `{g.escalates_to}`, which is not a role")
        for m in g.moves:
            for state in (m.from_state, m.to_state):
                if state != "*" and state not in etd.workflow.states:
                    out.append(f"{g.id}: `{state}` is not a {etd.name} state ({', '.join(etd.workflow.states)})")
            if m.to_state == "*":
                out.append(f"{g.id}: a move's `To` is a state, never `*`")
            if m.role and m.role not in known_roles:
                out.append(f"{g.id}: `{m.role}` is not a role")
            if m.when:
                try:
                    out += [f"{g.id}: {p}" for p in conditions.problems(conditions.parse(m.when), etd)]
                except conditions.ConditionError as exc:
                    out.append(f"{g.id}: {exc}")
    return out


def definition_problems(dep: Deployment) -> list[str]:
    """What is wrong with a type's `due` or a guard's `holds` (`check` reports each as an error)."""
    out = []
    for prefix, etd in sorted(dep.etds.items()):
        if etd.workflow.due:
            try:
                name, _ = due_spec(etd.workflow.due)
            except ValueError as exc:
                out.append(f"{prefix}: {exc}")
            else:
                fd = next((f for f in etd.fields if conditions.norm_field(f.name) == conditions.norm_field(name)), None)
                if fd is None:
                    out.append(f"{prefix}: `due` names `{name}`, which is not one of its fields")
                elif fd.kind != "date":
                    out.append(f"{prefix}: `due` names `{name}`, a {fd.kind} field, not a date")
        for state, guards in etd.workflow.guards.items():
            for cond, arg in guards:
                if cond != "holds":
                    continue
                try:
                    out += [f"{prefix} entering {state}: {p}" for p in conditions.problems(conditions.parse(arg), etd)]
                except conditions.ConditionError as exc:
                    out.append(f"{prefix} entering {state}: {exc}")
    return out


def refusal(dep: Deployment, corpus: Corpus, art: Artifact, old: str, new: str, signer: dict) -> str | None:
    """Why the active workflow governing `art`'s type refuses its move from `old` to
    `new` by `signer`, or None (no governing workflow, or a row allows it)."""
    g = governing(dep, corpus, art.prefix)
    if g is None:
        return None
    etd = dep.etds.get(art.prefix)
    rows = [m for m in g.moves if m.to_state == new and m.from_state in (old, "*")]
    if not rows:
        return f"{art.id} cannot go from {old or '(none)'} to {new}: {g.id}, which governs it, lists no such move"
    held = {str(r) for r in signer.get("roles") or []}
    why = []
    for m in rows:
        if m.role and ADMIN not in held and m.role not in held:
            why.append(f"it needs the role {m.role}")
            continue
        if m.when and etd is not None and not conditions.holds(conditions.parse(m.when), art, etd):
            why.append(f"`{m.when}` does not hold")
            continue
        return None
    who = signer.get("git_username") or signer.get("name")
    return (
        f"{art.id} cannot go from {old or '(none)'} to {new} as {who}: {g.id}, which governs it, allows it only "
        f"when {' or '.join(dict.fromkeys(why))} (--force does not pass a workflow)"
    )


def next_moves(dep: Deployment, corpus: Corpus, art: Artifact) -> dict[str, list[str]] | None:
    """The states the workflow governing `art`'s type lets it move to from its own,
    each with the conditions that fail now (a role is the signer's, not the
    entity's: not listed); None when no workflow governs its type."""
    g = governing(dep, corpus, art.prefix)
    if g is None:
        return None
    etd = dep.etds.get(art.prefix)
    current = _status(art)
    out: dict[str, list[str]] = {}
    for m in g.moves:
        if m.from_state not in (current, "*") or m.to_state == current:
            continue
        failing = []
        if m.when and etd is not None and not conditions.holds(conditions.parse(m.when), art, etd):
            failing = [f"`{m.when}` does not hold ({g.id})"]
        if m.to_state not in out or not failing:  # one row that passes is enough
            out[m.to_state] = failing if m.to_state not in out else []
    return out


# --- due dates (W2) ---------------------------------------------------------------
def due_spec(text: str) -> tuple[str, int]:
    """`Due` -> ("Due", 0); `Checked + 30 days` -> ("Checked", 30)."""
    m = DUE.match(text or "")
    if not m:
        raise ValueError(f"`{text}` is not a due date (`<date field>` or `<date field> + <n> days`)")
    return m.group("field").strip(), int(m.group("days") or 0)


def due_date(art: Artifact, etd) -> datetime.date | None:
    if not etd.workflow.due:
        return None
    name, days = due_spec(etd.workflow.due)
    raw = conditions.value_of(art, name)
    try:
        return datetime.date.fromisoformat(raw) + datetime.timedelta(days=days)
    except ValueError:
        return None


def overdue(dep: Deployment, corpus: Corpus, today: datetime.date | None = None) -> list[dict]:
    """Every open entity past its type's due date, oldest first."""
    today = today or datetime.date.today()
    out = []
    for prefix, etd in sorted(dep.etds.items()):
        if not etd.workflow.due:
            continue
        g = governing(dep, corpus, prefix)
        name, _ = due_spec(etd.workflow.due)
        for art in corpus.by_prefix.get(prefix, []):
            if _status(art) in etd.workflow.closed_states:
                continue
            due = due_date(art, etd)
            if due is None or due >= today:
                continue
            out.append(
                {
                    "id": art.id,
                    "title": art.title,
                    "type": prefix,
                    "field": name,
                    "due": due.isoformat(),
                    "days": (today - due).days,
                    "status": _status(art),
                    "escalate_to": g.escalates_to if g else None,
                }
            )
    return sorted(out, key=lambda o: (o["due"], o["id"]))
