"""Approval gates, opt-in (owner decision G; design `docs/design/25`):
`IAM/gates.json` declares them, `catalyst approve` records an approval of
one version of an entity, `catalyst approvals` says what each gate covering
an entity has and lacks.

A gate covers the rules of one domain, or an entity type entering one
state, and asks for a number of approvals from one role; a type's gate may
apply only `when` a condition on the entity's fields holds
(`catalyst.conditions`, workflow governance W1). An approval is of
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
    when: str | None = None  # a type's gate: only while this condition holds

    def applies_to(self, art, etd) -> bool:
        """Whether the gate asks anything of `art` (an entity of its type): always,
        unless its `when` does not hold for the entity's fields."""
        if not self.when or etd is None:
            return True
        from catalyst import conditions

        return conditions.holds(conditions.parse(self.when), art, etd)

    def covers_rule(self, rule_id: str) -> bool:
        parts = rule_id.split("-")
        return self.domain is not None and len(parts) > 2 and parts[1] == self.domain

    def covers_move(self, prefix: str, state: str) -> bool:
        return self.type == prefix and self.to == state

    def describe(self) -> str:
        what = f"rules of domain {self.domain}" if self.domain else f"{self.type} entering {self.to}"
        when = f" when {self.when}" if self.when else ""
        return f"{self.id}: {self.approvals} approval(s) from {self.role} for {what}{when}"


def _raw(dep: Deployment) -> list | None:
    path = dep.root / GATES
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GateError(f"{GATES.as_posix()}: not JSON ({exc})") from None
    gates = data.get("gates") if isinstance(data, dict) else None
    if not isinstance(gates, list):
        raise GateError(f'{GATES.as_posix()}: a "gates" list is expected')
    return gates


def _roles(dep: Deployment) -> set[str]:
    from catalyst.corpus import roles

    return {str(r.get("name")) for r in roles(dep)}


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
        where = f"{GATES.as_posix()} gate {i + 1}"
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
            where = f"{GATES.as_posix()} gate {gid}"
        n = g.get("approvals")
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            out.append(f"{where}: `approvals` is a whole number, at least 1")
        if g.get("role") not in roles:
            out.append(f"{where}: `role` {g.get('role')!r} is not a role of {ROLES.as_posix()}")
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
            elif g.get("when") is not None:
                from catalyst import conditions

                try:
                    out += [f"{where}: {p}" for p in conditions.problems(conditions.parse(str(g["when"])), etd)]
                except conditions.ConditionError as exc:
                    out.append(f"{where}: {exc}")
        if "rules" in covers and g.get("when") is not None:
            out.append(f"{where}: `when` applies to a type's gate, not to a domain's rules")
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
                when=g.get("when"),
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


def _ledger(dep: Deployment) -> list[dict]:
    return [entry for _, entry, _ in journal.read(dep) if entry]


def author(dep: Deployment, path: str, blob: str, entries: list[dict] | None = None) -> str | None:
    """Who wrote this version: the actor of the last entry whose content after it is
    — or, for an accepted proposal, the proposed version's author (`proposed_by`)."""
    who = None
    for entry in _ledger(dep) if entries is None else entries:
        if entry.get("action") == APPROVE:
            continue
        for f in entry.get("files") or []:
            if isinstance(f, dict) and f.get("path") == path and f.get("after") == blob:
                who = entry.get("proposed_by") or entry.get("actor")
    return who


def recorded(dep: Deployment, item_id: str, gate_id: str, blob: str, entries: list[dict] | None = None) -> list[str]:
    """The actors of the approvals of this gate for this version, in order, each once."""
    out: list[str] = []
    for entry in _ledger(dep) if entries is None else entries:
        if (
            entry.get("action") == APPROVE
            and entry.get("artifact") == item_id
            and entry.get("gate") == gate_id
            and (entry.get("approved") or {}).get("blob") == blob
            and entry.get("actor") not in out
        ):
            out.append(str(entry.get("actor")))
    return out


def _roles_recorded(item_id: str, gate_id: str, blob: str, entries: list[dict]) -> dict[str, list[str]]:
    """The roles each approval of this version recorded (its first one), by actor."""
    out: dict[str, list[str]] = {}
    for entry in entries:
        if (
            entry.get("action") == APPROVE
            and entry.get("artifact") == item_id
            and entry.get("gate") == gate_id
            and (entry.get("approved") or {}).get("blob") == blob
        ):
            out.setdefault(str(entry.get("actor")), [str(r) for r in entry.get("roles") or []])
    return out


def counted(
    dep: Deployment,
    corpus: Corpus,
    gate: Gate,
    item_id: str,
    entries: list[dict] | None = None,
    current: tuple[str, str] | None = None,
    wrote: str | None = None,
) -> tuple[list[str], int]:
    """(the approvals that count for the entity's current version — or the
    `current` (path, blob) given, by its author `wrote` — how many are missing)."""
    entries = _ledger(dep) if entries is None else entries
    path, blob = current or version(dep, corpus, item_id)
    wrote = wrote if current and wrote is not None else author(dep, path, blob, entries)
    counts = []
    held = _roles_recorded(item_id, gate.id, blob, entries)
    for actor in recorded(dep, item_id, gate.id, blob, entries):
        user = corpus.user(actor)
        # an identity provider's signer holds the roles its approval recorded (fw-IDENTITY-000004)
        roles = held.get(actor, []) if user and user.get("iss") else (user or {}).get("roles") or []
        if user and user.get("active", True) and gate.role in roles and not _same(user, wrote):
            counts.append(actor)
    return counts, max(0, gate.approvals - len(counts))


def covering(dep: Deployment, corpus: Corpus, item_id: str) -> list[Gate]:
    """The gates that cover an entity: its rule domain's, or its type's (whatever state it enters)."""
    gates = load(dep, corpus)
    if item_id in corpus.rules:
        return [g for g in gates if g.covers_rule(item_id)]
    art = corpus.artifacts[item_id][0] if item_id in corpus.artifacts else None
    return [g for g in gates if art and g.type == art.prefix and g.applies_to(art, dep.etds.get(art.prefix))]


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
    one `approve` entry, its gate and version named; nothing else changes.
    Named by an open proposal's case (design 26), it approves the proposed
    version of the case's entity, which counts once the proposal lands."""
    from catalyst import proposals, views

    found = views.resolve(corpus, item_id)
    if found is None:
        raise GateError(f"no artifact or rule '{item_id}' in this deployment")
    case, p = None, {}
    if found in corpus.artifacts and proposals.is_proposal(corpus.artifacts[found][0]):
        case = corpus.artifacts[found][0]
        if not proposals.is_open(case):
            raise GateError(f"{found} is decided: approve its entity's version instead")
        p = proposals.info(dep, corpus, case)
        if p["path"] is None or not p["proposed"]:
            raise GateError(f"{found} names no entity or no proposed version (`catalyst check`)")
        found = p["entity"]
    gate = next((g for g in load(dep, corpus) if g.id == gate_id), None)
    if gate is None:
        raise GateError(f"no gate '{gate_id}' in {GATES.as_posix()}")
    if gate not in covering(dep, corpus, found):
        raise GateError(f"gate {gate_id} does not cover {found} ({gate.describe()})")
    if not signer.get("active", True):
        raise GateError(f"{signer.get('name')} is not an active user")
    if gate.role not in (signer.get("roles") or []):
        raise GateError(f"{signer.get('name')} does not hold the role {gate.role} that gate {gate_id} asks for")
    if case is not None:
        path, blob, wrote = journal.WC + p["path"], p["proposed"], p["author"]
    else:
        path, blob = version(dep, corpus, found)
        wrote = author(dep, path, blob)
    if _same(signer, wrote):
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
    if case is not None:
        entry["proposal"] = case.id
    if signer.get("iss"):  # verified by the identity provider: its roles now are the approval's (fw-IDENTITY-000004)
        entry["roles"] = list(signer.get("roles") or [])
    if tier:
        entry["tier"] = tier
    with journal.journal_lock(dep):
        journal.write(dep, entry)
    return entry


def left_after(dep: Deployment, corpus: Corpus, entry: dict) -> dict:
    """After an approval: its gate's count for the version it approved — the
    entity's current one, or a proposal's proposed one (`missing`)."""
    gate = next(g for g in load(dep, corpus) if g.id == entry["gate"])
    if entry.get("proposal"):
        from catalyst import proposals

        p = proposals.info(dep, corpus, corpus.artifacts[entry["proposal"]][0])
        current = (entry["approved"]["path"], entry["approved"]["blob"])
        counts, missing = counted(dep, corpus, gate, entry["artifact"], current=current, wrote=p["author"] or "")
    else:
        counts, missing = counted(dep, corpus, gate, entry["artifact"])
    return {"gate": gate.id, "counted": counts, "missing": missing}


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


# --- enforcing them (design 25 A3, A4) ------------------------------------------
def entering(dep: Deployment, corpus: Corpus, prefix: str, state: str, art=None) -> list[Gate]:
    """The gates an entity of this type passes to enter this state — those whose
    `when` holds for `art`, when given (without it, every one: a gate fails
    closed). A malformed `IAM/gates.json` refuses every move it could cover."""
    try:
        gates = load(dep, corpus)
    except GateError as exc:
        if (dep.root / GATES).is_file():
            raise GateError(f"{exc} — fix {GATES.as_posix()} before moving an entity") from None
        raise
    etd = dep.etds.get(prefix)
    return [g for g in gates if g.covers_move(prefix, state) and (art is None or g.applies_to(art, etd))]


def refusal(dep: Deployment, corpus: Corpus, item_id: str, state: str) -> str | None:
    """Why the entity may not enter `state` yet — the gates whose approvals for
    its current version are missing, how many and from which role — or None."""
    art = corpus.artifacts[item_id][0] if item_id in corpus.artifacts else None
    short = []
    for g in entering(dep, corpus, art.prefix if art else "", state, art):
        _, missing = counted(dep, corpus, g, item_id)
        if missing:
            short.append(f"gate {g.id} lacks {missing} of {g.approvals} approval(s) from {g.role}")
    if not short:
        return None
    return (
        f"{item_id} cannot become {state}: {'; '.join(short)} for its current version "
        f"(`catalyst approve {item_id} --gate <gate>`; --force does not pass a gate)"
    )


def _waiting_entry(g: Gate, item_id: str, blob: str, counts: list[str], missing: int) -> dict:
    return {
        "id": item_id,
        "gate": g.id,
        "role": g.role,
        "approvals": g.approvals,
        "covers": {"rules": {"domain": g.domain}} if g.domain else {"type": g.type, "to": g.to},
        "version": blob,
        "counted": counts,
        "missing": missing,
    }


def unapproved_rules(dep: Deployment, corpus: Corpus) -> list[dict]:
    """Each rule a gate covers whose current text lacks its approvals (`check` errors
    on each); a malformed or absent `IAM/gates.json` gives none (`check` reports it)."""
    try:
        gates = [g for g in load(dep, corpus) if g.domain]
    except GateError:
        return []
    if not gates:
        return []
    entries, blobs, out = _ledger(dep), {}, []
    for rid in sorted(corpus.rules):
        rule = corpus.rules[rid][0]
        if rule.retired:
            continue
        for g in (g for g in gates if g.covers_rule(rid)):
            if rule.file not in blobs:
                blobs[rule.file] = version(dep, corpus, rid)
            counts, missing = counted(dep, corpus, g, rid, entries, blobs[rule.file])
            if missing:
                out.append(_waiting_entry(g, rid, blobs[rule.file][1], counts, missing))
    return out


def waiting(dep: Deployment, corpus: Corpus) -> list[dict]:
    """What waits for an approval (`catalyst inbox` kind `approval`): every gated
    rule whose text lacks its approvals, and every open entity one move away from
    a gated state — a state a transition leads into from its own, or any when its
    type declares no transitions — that lacks them for its current version."""
    out = unapproved_rules(dep, corpus)
    try:
        gates = [g for g in load(dep, corpus) if g.type]
    except GateError:
        return out
    entries = _ledger(dep) if gates else []
    for g in gates:
        etd = dep.etds.get(g.type) if g.type else None
        if etd is None or g.type is None or g.to is None:
            continue
        moves = {(t.from_state, t.to_state) for t in etd.workflow.transitions}
        for art in corpus.by_prefix.get(g.type, []):
            state = (art.get("Status") or "").strip().strip("`")
            if state == g.to or state in etd.workflow.closed_states:
                continue
            if moves and (state, g.to) not in moves:
                continue
            if not g.applies_to(art, etd):
                continue
            current = version(dep, corpus, art.id)
            counts, missing = counted(dep, corpus, g, art.id, entries, current)
            if missing:
                out.append(_waiting_entry(g, art.id, current[1], counts, missing))
    return out
