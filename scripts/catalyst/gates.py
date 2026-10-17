"""Approval gates, opt-in (owner decision G; design `docs/design/25`):
`IAM/gates.json` declares them, `catalyst approve` records an approval of
one version of an entity, `catalyst approvals` says what each gate covering
an entity has and lacks.

A gate covers the rules of one domain, or an entity type entering one
state, and asks for a number of approvals from one role. An approval is of
a version: the entity file's blob, as the journal already keeps it. It
counts when its signer is active, holds the role, did not write that
version (law L4: the author never approves their own change) and has not
approved it already. No file, no gate.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from catalyst import journal
from catalyst.corpus import Corpus
from catalyst.deployment import Deployment

GATES = Path("IAM") / "gates.json"
ROLES = Path("IAM") / "roles" / "roles.json"
GATE_ID = re.compile(r"^[a-z][a-z0-9-]{0,40}$")
APPROVE = "approve"


class GateError(Exception):
    pass


@dataclass(frozen=True)
class Gate:
    id: str
    approvals: int
    role: str
    domain: str | None = None  # covers the rules of this domain
    type: str | None = None  # or this entity type entering `to`
    to: str | None = None

    def covers_rule(self, rule_id: str) -> bool:
        parts = rule_id.split("-")
        return self.domain is not None and len(parts) > 2 and parts[1] == self.domain

    def covers_move(self, prefix: str, state: str) -> bool:
        return self.type == prefix and self.to == state

    def describe(self) -> str:
        what = f"rules of domain {self.domain}" if self.domain else f"{self.type} entering {self.to}"
        return f"{self.id}: {self.approvals} approval(s) from {self.role} for {what}"


def _raw(dep: Deployment) -> list | None:
    path = dep.root / GATES
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GateError(f"{GATES}: not JSON ({exc})") from None
    gates = data.get("gates") if isinstance(data, dict) else None
    if not isinstance(gates, list):
        raise GateError(f'{GATES}: a "gates" list is expected')
    return gates


def _roles(dep: Deployment) -> set[str]:
    try:
        data = json.loads((dep.root / ROLES).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {str(r.get("name")) for r in data.get("roles", []) if isinstance(r, dict)}


def problems(dep: Deployment, corpus: Corpus) -> list[str]:
    """What is wrong with the declared gates, one line each (`check` reports them as errors)."""
    try:
        raw = _raw(dep)
    except GateError as exc:
        return [str(exc)]
    if raw is None:
        return []
    out, seen, roles = [], set(), _roles(dep)
    for i, g in enumerate(raw):
        where = f"{GATES} gate {i + 1}"
        if not isinstance(g, dict):
            out.append(f"{where}: not an object")
            continue
        gid = g.get("id")
        if not isinstance(gid, str) or not GATE_ID.match(gid):
            out.append(f"{where}: `id` is a lowercase name (letters, digits, dashes)")
        elif gid in seen:
            out.append(f"{where}: `id` {gid} is declared twice")
        else:
            seen.add(gid)
            where = f"{GATES} gate {gid}"
        n = g.get("approvals")
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            out.append(f"{where}: `approvals` is a whole number, at least 1")
        if g.get("role") not in roles:
            out.append(f"{where}: `role` {g.get('role')!r} is not a role of {ROLES}")
        covers = g.get("covers")
        if not isinstance(covers, dict) or len(covers) != (2 if "type" in (covers or {}) else 1):
            out.append(f'{where}: `covers` is {{"rules": {{"domain": …}}}} or {{"type": …, "to": …}}')
            continue
        if "rules" in covers:
            domain = (covers.get("rules") or {}).get("domain") if isinstance(covers.get("rules"), dict) else None
            if domain not in corpus.domains:
                out.append(f"{where}: domain {domain!r} is not registered (rules/domains/domains.md)")
        else:
            prefix, to = covers.get("type"), covers.get("to")
            etd = dep.etds.get(str(prefix))
            if etd is None:
                out.append(f"{where}: type {prefix!r} is not declared")
            elif to not in etd.workflow.states:
                out.append(f"{where}: {to!r} is not a {etd.name} state ({', '.join(etd.workflow.states)})")
    return out


def load(dep: Deployment, corpus: Corpus) -> list[Gate]:
    """The declared gates; a GateError when any is malformed (`check` says which)."""
    found = problems(dep, corpus)
    if found:
        raise GateError("; ".join(found))
    gates = []
    for g in _raw(dep) or []:
        covers = g["covers"]
        rules = covers.get("rules")
        gates.append(
            Gate(
                id=g["id"],
                approvals=g["approvals"],
                role=g["role"],
                domain=rules["domain"] if rules else None,
                type=covers.get("type"),
                to=covers.get("to"),
            )
        )
    return gates


# --- versions, authors, approvals ----------------------------------------------
def _file_of(corpus: Corpus, item_id: str) -> Path:
    if item_id in corpus.artifacts:
        return corpus.artifacts[item_id][0].file
    if item_id in corpus.rules:
        return corpus.rules[item_id][0].file
    raise GateError(f"no artifact or rule '{item_id}' in this deployment")


def version(dep: Deployment, corpus: Corpus, item_id: str) -> tuple[str, str]:
    """(journal path, blob) of the entity's file as it is now."""
    path = _file_of(corpus, item_id)
    rel = path.relative_to(dep.root).as_posix()
    return journal.WC + rel, journal.git(dep.root, "hash-object", "--", rel)


def _same(user: dict, actor: str | None) -> bool:
    a = (actor or "").strip().lower()
    return bool(a) and a in {str(user.get(k, "")).strip().lower() for k in ("name", "git_username", "userid")}


def author(dep: Deployment, path: str, blob: str) -> str | None:
    """Who wrote this version: the actor of the last entry whose content after it is."""
    who = None
    for _, entry, _ in journal.read(dep):
        if not entry or entry.get("action") == APPROVE:
            continue
        for f in entry.get("files") or []:
            if isinstance(f, dict) and f.get("path") == path and f.get("after") == blob:
                who = entry.get("actor")
    return who


def recorded(dep: Deployment, item_id: str, gate_id: str, blob: str) -> list[str]:
    """The actors of the approvals of this gate for this version, in order, each once."""
    out: list[str] = []
    for _, entry, _ in journal.read(dep):
        if (
            entry
            and entry.get("action") == APPROVE
            and entry.get("artifact") == item_id
            and entry.get("gate") == gate_id
            and (entry.get("approved") or {}).get("blob") == blob
            and entry.get("actor") not in out
        ):
            out.append(str(entry.get("actor")))
    return out


def counted(dep: Deployment, corpus: Corpus, gate: Gate, item_id: str) -> tuple[list[str], int]:
    """(the approvals that count for the entity's current version, how many are missing)."""
    path, blob = version(dep, corpus, item_id)
    wrote = author(dep, path, blob)
    counts = []
    for actor in recorded(dep, item_id, gate.id, blob):
        user = corpus.user(actor)
        if user and user.get("active", True) and gate.role in (user.get("roles") or []) and not _same(user, wrote):
            counts.append(actor)
    return counts, max(0, gate.approvals - len(counts))


def covering(dep: Deployment, corpus: Corpus, item_id: str) -> list[Gate]:
    """The gates that cover an entity: its rule domain's, or its type's (whatever state it enters)."""
    gates = load(dep, corpus)
    if item_id in corpus.rules:
        return [g for g in gates if g.covers_rule(item_id)]
    prefix = corpus.artifacts[item_id][0].prefix if item_id in corpus.artifacts else None
    return [g for g in gates if prefix and g.type == prefix]


def approve(
    dep: Deployment,
    corpus: Corpus,
    item_id: str,
    gate_id: str,
    signer: dict,
    intent: list[str],
    tier: str | None = None,
) -> dict:
    """Record one approval of the entity's current version under a gate:
    one `approve` entry, its gate and version named; nothing else changes."""
    from catalyst import views

    found = views.resolve(corpus, item_id)
    if found is None:
        raise GateError(f"no artifact or rule '{item_id}' in this deployment")
    gate = next((g for g in load(dep, corpus) if g.id == gate_id), None)
    if gate is None:
        raise GateError(f"no gate '{gate_id}' in {GATES}")
    if gate not in covering(dep, corpus, found):
        raise GateError(f"gate {gate_id} does not cover {found} ({gate.describe()})")
    if not signer.get("active", True):
        raise GateError(f"{signer.get('name')} is not an active user")
    if gate.role not in (signer.get("roles") or []):
        raise GateError(f"{signer.get('name')} does not hold the role {gate.role} that gate {gate_id} asks for")
    path, blob = version(dep, corpus, found)
    if _same(signer, author(dep, path, blob)):
        raise GateError(
            f"{signer.get('name')} wrote this version of {found}: an author never approves their own change"
        )
    if any(_same(signer, a) for a in recorded(dep, found, gate_id, blob)):
        raise GateError(f"{signer.get('name')} already approved this version of {found} under gate {gate_id}")
    journal.check_tier(dep, tier)
    entry = {
        "timestamp": journal.now(),
        "actor": str(signer.get("git_username") or signer.get("name")),
        "command": "catalyst approve",
        "action": APPROVE,
        "artifact": found,
        "targets": [found],
        "intent": intent or [f"Approve {found} under gate {gate_id}"],
        "files": [],
        "gate": gate_id,
        "approved": {"path": path, "blob": blob},
        "writer": f"catalyst/{journal.__version__}",
    }
    if tier:
        entry["tier"] = tier
    with journal.journal_lock(dep):
        journal.write(dep, entry)
    return entry


def report(dep: Deployment, corpus: Corpus, item_id: str) -> dict:
    """`catalyst approvals <ID>`: each gate covering the entity, what counts for its current version, what is missing."""
    from catalyst import views

    found = views.resolve(corpus, item_id)
    if found is None:
        raise GateError(f"no artifact or rule '{item_id}' in this deployment")
    _, blob = version(dep, corpus, found)
    out = []
    for g in covering(dep, corpus, found):
        counts, missing = counted(dep, corpus, g, found)
        out.append(
            {
                "gate": g.id,
                "role": g.role,
                "approvals": g.approvals,
                "covers": {"rules": {"domain": g.domain}} if g.domain else {"type": g.type, "to": g.to},
                "counted": counts,
                "missing": missing,
            }
        )
    return {"id": found, "version": blob, "gates": out}
