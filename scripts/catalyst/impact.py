"""`catalyst impact <id>` (roadmap R5.6): what an entity rests on, and what
rests on it.

A link runs from an entity to what one of its reference fields cites (as its
type declares the field), and from a rule to its domain. A derived field is
the mirror of the field it is derived from and adds no link. Upstream is
what the entity rests on, downstream what rests on it, both followed
transitively; each entry carries its depth and the entity and field that
brought it in. IDs an entity only cites in its prose are reported apart
(`mentions`, `mentioned_by`) and never followed. Nothing is stored and
nothing is written: the answer is computed from `graph`.
"""

from __future__ import annotations

from collections import deque

from catalyst import derived, views
from catalyst.corpus import Corpus
from catalyst.deployment import Deployment

DIRECTIONS = ("both", "up", "down")


def _nodes(g: dict) -> dict[str, dict]:
    nodes: dict[str, dict] = {}
    for d in g["domains"]:
        nodes[d["code"]] = {"id": d["code"], "type": "domain", "title": d.get("title") or "", "status": None}
    for r in g["rules"]:
        nodes[r["id"]] = {"id": r["id"], "type": "rule", "title": r.get("title") or "", "status": r.get("status")}
    for a in g["artifacts"]:
        status = a.get("Status") or (a.get("fields") or {}).get("Status")
        nodes[a["id"]] = {"id": a["id"], "type": a["type"], "title": a.get("title") or "", "status": status}
    return nodes


def links(dep: Deployment, g: dict, nodes: dict[str, dict]) -> list[tuple[str, str, str]]:
    """(entity, field, what it rests on), for every link between known
    entities; derived fields are left out."""
    mirrors = set(derived.sources(dep))
    found = []
    for r in g["rules"]:
        if r.get("domain") in nodes:
            found.append((r["id"], "domain", r["domain"]))
    for a in g["artifacts"]:
        for field, targets in (a.get("links") or {}).items():
            if (a["type"], field) in mirrors:
                continue
            found += [(a["id"], field, t) for t in targets if t in nodes and t != a["id"]]
    return found


def _closure(
    start: str, step: dict[str, list[tuple[str, str]]], nodes: dict, depth: int | None, carried_by_reached: bool
) -> list[dict]:
    """Breadth-first from `start`: each entity once, at its shortest depth.
    `via` names the entity one step nearer, the reference field, and `on`,
    the entity that carries the field (the nearer one going up, the reached
    one going down)."""
    seen, out, queue = {start}, [], deque([(start, 0)])
    while queue:
        current, d = queue.popleft()
        if depth is not None and d >= depth:
            continue
        for field, other in sorted(step.get(current, []), key=lambda e: (e[1], e[0])):
            if other in seen:
                continue
            seen.add(other)
            via = {"id": current, "field": field, "on": other if carried_by_reached else current}
            out.append({**nodes[other], "depth": d + 1, "via": via})
            queue.append((other, d + 1))
    return out


def impact(dep: Deployment, corpus: Corpus, item_id: str, direction: str = "both", depth: int | None = None) -> dict:
    """The impact of `item_id` (an artifact, a rule or a domain code)."""
    if direction not in DIRECTIONS:
        raise views.ViewError(f"direction '{direction}' is not one of {', '.join(DIRECTIONS)}")
    if depth is not None and depth < 1:
        raise views.ViewError("depth is a number of links, 1 or more")
    g = views.graph(dep, corpus)
    nodes = _nodes(g)
    subject = item_id if item_id in nodes else views.resolve(corpus, item_id)  # a domain is its code
    if subject not in nodes:
        raise views.ViewError(f"no artifact, rule or domain '{item_id}' in this deployment")
    rests_on: dict[str, list[tuple[str, str]]] = {}
    rested_on: dict[str, list[tuple[str, str]]] = {}
    linked: set[tuple[str, str]] = set()
    for source, field, target in links(dep, g, nodes):
        rests_on.setdefault(source, []).append((field, target))
        rested_on.setdefault(target, []).append((field, source))
        linked.add((source, target))
    cites = {e["id"]: e.get("mentions") or [] for e in [*g["rules"], *g["artifacts"]]}
    weak = lambda a, b: (a, b) not in linked and (b, a) not in linked  # noqa: E731
    out = dict(nodes[subject])
    if direction in ("both", "up"):
        out["upstream"] = _closure(subject, rests_on, nodes, depth, carried_by_reached=False)
    if direction in ("both", "down"):
        out["downstream"] = _closure(subject, rested_on, nodes, depth, carried_by_reached=True)
    out["mentions"] = sorted(m for m in cites.get(subject, []) if m in nodes and m != subject and weak(subject, m))
    out["mentioned_by"] = sorted(i for i, ms in cites.items() if subject in ms and i != subject and weak(i, subject))
    return out


def render(d: dict) -> str:
    def state(e: dict) -> str:
        text = str(e.get("status") or "")
        return f" [{text if len(text) <= 24 else text[:23] + '…'}]" if text else ""

    def line(e: dict) -> str:
        return f"{'  ' * e['depth']}{e['id']} ({e['type']}){state(e)}  via {e['via']['on']}.{e['via']['field']}"

    status = state(d)
    lines = [f"{d['id']} ({d['type']}){status} {d.get('title') or ''}".rstrip()]
    for key, title in (("upstream", "rests on"), ("downstream", "rested on by")):
        if key in d:
            lines.append(f"{title}: {len(d[key])}")
            lines += [line(e) for e in d[key]]
    for key, title in (("mentions", "mentions, not followed"), ("mentioned_by", "mentioned by, not followed")):
        if d.get(key):
            lines.append(f"{title}: {', '.join(d[key])}")
    return "\n".join(lines) + "\n"
