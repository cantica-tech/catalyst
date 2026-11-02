"""`catalyst inbox` (roadmap R5.7): what waits for a person, each item with
its evidence and the commands that settle it.

Six sources, each of which already has a verb that settles it:

- commits made outside catalyst whose changes the journal does not record
  (`catalyst journal adopt`, or a revert);
- changed or new project files not journaled yet (`catalyst journal
  append`, or the change discarded);
- reconciliation cases that are not closed (`catalyst reconcile`), a
  proposal apart from a dispute (design 26);
- analyses in their deciding phase (`catalyst analysis decide`);
- gated changes waiting for their approvals, a gated rule's text or an
  entity one move away from a gated state (`catalyst approve`; design 25);
- open entities past their type's due date, with the role a governing
  workflow escalates to (`catalyst status set`, or a new date; W2);
- open bugs and requirements, each awaiting a decision on its status
  (`catalyst status set`), the same "open" as `catalyst backlog`.

The inbox lists; it settles nothing and proposes no decision. A bare working
copy or a served criterion has no project history, so it lists the cases
and the analyses only.
"""

from __future__ import annotations

from catalyst import analysis, gates, proposals, unrecorded
from catalyst.corpus import Corpus
from catalyst.deployment import Deployment

KINDS = (
    "unrecorded-commit",
    "unrecorded-change",
    "reconciliation",
    "analysis",
    "approval",
    "proposal",
    "overdue",
    "review",
)
RECONCILIATION = "RECON"
DECISIONS = ("accept", "accept-with-edits", "reject", "propose")
# the work items a person decides on (review), by type: a bug still open, a requirement not yet completed
REVIEWED = ("BUG", "REQ")


def _item(kind: str, item_id: str, title: str, evidence: dict, settle: list[str]) -> dict:
    return {"kind": kind, "id": item_id, "title": title, "evidence": evidence, "settle": settle}


def inbox(dep: Deployment, corpus: Corpus) -> dict:
    """`{items, counts}`: every item waiting, by kind in `KINDS` order."""
    from catalyst.check import unrecorded_changes

    items = []
    for c in unrecorded.since_baseline(dep):
        evidence = {
            "commit": c.sha,
            "author": c.author,
            "files": [{"path": p, "before": b, "after": a} for p, b, a in c.changes],
        }
        settle = [f"catalyst journal adopt {c.short} --intent <why>", f"git revert {c.short}"]
        items.append(_item(KINDS[0], c.short, c.subject, evidence, settle))
    for path in unrecorded_changes(dep):
        settle = [f"catalyst journal append --file {path} --intent <why> …", "discard the change"]
        items.append(_item(KINDS[1], path, "changed in the project, not in the journal", {"path": path}, settle))
    closed = set(dep.etds[RECONCILIATION].workflow.closed_states) if RECONCILIATION in dep.etds else set()
    for art in corpus.by_prefix.get(RECONCILIATION, []):
        status = (art.get("Status") or "").strip().strip("`")
        if status in closed or status == "Closed":
            continue
        evidence = {"status": status, "entity": (art.get("Entity") or "").strip().strip("`") or None}
        if proposals.is_proposal(art):
            p = proposals.info(dep, corpus, art)
            evidence.update({k: p[k] for k in ("path", "base", "proposed", "author")})
            settle = [
                f"catalyst reconcile {art.id} accept",
                f"catalyst reconcile {art.id} accept-with-edits --from <file>",
                f"catalyst reconcile {art.id} reject",
                f"catalyst reconcile {art.id} propose --from <file>",
            ]
            items.append(_item(KINDS[5], art.id, art.title, evidence, settle))
            continue
        settle = [f"catalyst reconcile {art.id} {d}" for d in DECISIONS]
        items.append(_item(KINDS[2], art.id, art.title, evidence, settle))
    for art in corpus.by_prefix.get(analysis.PREFIX, []):
        if analysis.phase(art) != "Deciding":
            continue
        evidence = {"status": "Deciding", "scope": (art.get("Scope") or "").strip() or None}
        items.append(_item(KINDS[3], art.id, art.title, evidence, [f"catalyst analysis decide {art.id} …"]))
    for w in gates.waiting(dep, corpus):
        what = (
            f"the rules of {w['covers']['rules']['domain']}"
            if "rules" in w["covers"]
            else f"entering {w['covers']['to']}"
        )
        title = f"{w['missing']} of {w['approvals']} approval(s) from {w['role']} missing ({what})"
        evidence = {k: w[k] for k in ("gate", "role", "approvals", "counted", "missing", "version")}
        items.append(_item(KINDS[4], w["id"], title, evidence, [f"catalyst approve {w['id']} --gate {w['gate']}"]))
    from catalyst import workflows

    for o in workflows.overdue(dep, corpus):
        evidence = {k: o[k] for k in ("status", "field", "due", "days", "escalate_to")}
        title = f"{o['title']}: due {o['due']}, {o['days']} day(s) over"
        settle = [f"catalyst status set {o['id']} <state> --intent <why>", f"a new `{o['field']}`, journaled"]
        items.append(_item(KINDS[6], o["id"], title, evidence, settle))
    for prefix in REVIEWED:
        if prefix not in dep.etds:
            continue
        etd = dep.etds[prefix]
        closed = set(etd.workflow.closed_states)
        for art in corpus.by_prefix.get(prefix, []):
            status = (art.get("Status") or "").strip()
            if not status or status in closed:
                continue  # the same "open" as `catalyst backlog`: any status outside the type's closed states
            evidence = {"status": status, "entity": art.id}
            # its own states it can move to next (the type's workflow), each one a decision
            settle = [
                f"catalyst status set {art.id} {state} --intent <why>"
                for state in etd.workflow.states
                if state != status
            ]
            items.append(_item(KINDS[7], art.id, art.title, evidence, settle))
    counts = {kind: sum(1 for i in items if i["kind"] == kind) for kind in KINDS}
    return {"items": items, "counts": counts}


def render(found: dict) -> str:
    if not found["items"]:
        return "nothing waits\n"
    titles = {
        KINDS[0]: "commits made outside catalyst",
        KINDS[1]: "changes not journaled",
        KINDS[2]: "reconciliation cases",
        KINDS[3]: "analyses to decide",
        KINDS[4]: "approvals waiting",
        KINDS[5]: "proposals to decide",
        KINDS[6]: "overdue",
        KINDS[7]: "open work to review",
    }
    lines = []
    for kind in KINDS:
        mine = [i for i in found["items"] if i["kind"] == kind]
        if not mine:
            continue
        lines.append(f"{titles[kind]}: {len(mine)}")
        for i in mine:
            ev = i["evidence"]
            about = ev.get("entity") or ev.get("author") or ev.get("gate") or ev.get("escalate_to") or ""
            lines.append(f"  {i['id']}  {i['title']}" + (f"  ({about})" if about else ""))
            lines.append(f"      {'  |  '.join(i['settle'])}")
    total = len(found["items"])
    return "\n".join(lines) + f"\n{total} item{'' if total == 1 else 's'} waiting\n"
