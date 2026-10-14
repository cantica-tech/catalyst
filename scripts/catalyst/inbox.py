"""`catalyst inbox` (roadmap R5.7): what waits for a person, each item with
its evidence and the commands that settle it.

Four sources, each of which already has a verb that settles it:

- commits made outside catalyst whose changes the journal does not record
  (`catalyst journal adopt`, or a revert);
- changed or new project files not journaled yet (`catalyst journal
  append`, or the change discarded);
- reconciliation cases that are not closed (`catalyst reconcile`);
- analyses in their deciding phase (`catalyst analysis decide`).

The inbox lists; it settles nothing and proposes no decision. A bare working
copy or a served criterion has no project history, so it lists the cases
and the analyses only.
"""

from __future__ import annotations

from catalyst import analysis, unrecorded
from catalyst.corpus import Corpus
from catalyst.deployment import Deployment

KINDS = ("unrecorded-commit", "unrecorded-change", "reconciliation", "analysis")
RECONCILIATION = "RECON"
DECISIONS = ("accept", "accept-with-edits", "reject", "propose")


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
        settle = [f"catalyst reconcile {art.id} {d}" for d in DECISIONS]
        items.append(_item(KINDS[2], art.id, art.title, evidence, settle))
    for art in corpus.by_prefix.get(analysis.PREFIX, []):
        if analysis.phase(art) != "Deciding":
            continue
        evidence = {"status": "Deciding", "scope": (art.get("Scope") or "").strip() or None}
        items.append(_item(KINDS[3], art.id, art.title, evidence, [f"catalyst analysis decide {art.id} …"]))
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
    }
    lines = []
    for kind in KINDS:
        mine = [i for i in found["items"] if i["kind"] == kind]
        if not mine:
            continue
        lines.append(f"{titles[kind]}: {len(mine)}")
        for i in mine:
            about = i["evidence"].get("entity") or i["evidence"].get("author") or ""
            lines.append(f"  {i['id']}  {i['title']}" + (f"  ({about})" if about else ""))
            lines.append(f"      {'  |  '.join(i['settle'])}")
    total = len(found["items"])
    return "\n".join(lines) + f"\n{total} item{'' if total == 1 else 's'} waiting\n"
