"""Proposals (owner decision P; design `docs/design/26`): a change offered
for review before it lands. A proposal is a reconciliation case
(`Trigger: proposal`) naming its entity, the entity's file as it was when
the proposal was made (its base, a blob) and the proposed content, kept
beside the case as `reconciliations/<RECON-id>.proposed`. `catalyst
propose` opens it; `catalyst reconcile … accept` writes the proposed
content to the entity, refused when the base has moved and for the
proposed version's own author (law L4).
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path

from catalyst import journal
from catalyst.corpus import Artifact, Corpus
from catalyst.deployment import Deployment

TRIGGER = "proposal"
SUFFIX = ".proposed"
RECONCILIATION = "RECON"
OPEN = ("Open", "Under Review")
BLOB = re.compile(r"\b[0-9a-f]{40}\b")


class ProposalError(Exception):
    pass


def _clean(value: str | None) -> str:
    return (value or "").strip().strip("`").strip()


def is_proposal(art: Artifact) -> bool:
    return art.prefix == RECONCILIATION and _clean(art.get("Trigger")) == TRIGGER


def is_open(art: Artifact) -> bool:
    return _clean(art.get("Status")) in OPEN


def proposed_path(dep: Deployment, case_id: str) -> Path:
    folder = dep.folder(dep.etds[RECONCILIATION])
    if folder is None:
        raise ProposalError("this deployment has no reconciliations folder")
    return folder / f"{case_id}{SUFFIX}"


def _blob_in(value: str | None) -> str | None:
    m = BLOB.search(value or "")
    return m.group(0) if m else None


def info(dep: Deployment, corpus: Corpus, art: Artifact) -> dict:
    """What a proposal case records: its entity, the entity's file, the base and
    the proposed blob, the proposed file, and who wrote the proposed version."""
    entity = _clean(art.get("Entity"))
    target = _target_file(corpus, entity)
    proposed = proposed_path(dep, art.id)
    rel = proposed.relative_to(dep.root).as_posix()
    blob = _blob_in(art.get("Proposed"))
    from catalyst import gates

    return {
        "case": art.id,
        "entity": entity,
        "path": target.relative_to(dep.root).as_posix() if target else None,
        "base": _blob_in(art.get("Baseline")),
        "proposed": blob,
        "file": rel,
        "author": gates.author(dep, journal.WC + rel, blob) if blob else None,
        "status": _clean(art.get("Status")),
    }


def _target_file(corpus: Corpus, entity: str) -> Path | None:
    if entity in corpus.artifacts:
        return corpus.artifacts[entity][0].file
    if entity in corpus.rules:
        return corpus.rules[entity][0].file
    return None


def _hash(dep: Deployment, path: Path) -> str:
    return journal.git(dep.root, "hash-object", "--", path.relative_to(dep.root).as_posix())


def _signer_label(dep: Deployment, signer: dict) -> tuple[str, str]:
    from catalyst.edit import reconciliation_level

    level, role = reconciliation_level(dep, signer)
    return f"{signer.get('name')} ({role or 'no role'})", level


def propose(
    dep: Deployment,
    corpus: Corpus,
    item_id: str,
    content: str,
    signer: dict,
    title: str | None = None,
    intent: list[str] | None = None,
    tier: str | None = None,
):
    """Open a proposal: a case naming the entity and the base, the proposed
    content beside it; one journal entry, the entity's own file untouched."""
    from catalyst import views
    from catalyst.edit import Result, _finish, latest_template, set_field, set_or_add_field, slug
    from catalyst.ids import next_entity_id

    found = views.resolve(corpus, item_id)
    if found is None:
        raise ProposalError(f"no artifact or rule '{item_id}' in this deployment")
    if found in corpus.artifacts and corpus.artifacts[found][0].prefix == RECONCILIATION:
        raise ProposalError(f"{found} is a reconciliation case: a case is decided, never proposed")
    target = _target_file(corpus, found)
    if target is None:
        raise ProposalError(f"no file holds {found} in this deployment")
    if not target.is_relative_to(dep.root):
        raise ProposalError(
            f"{found} is inherited from the workspace criterion, read-only here: propose the change there "
            "(`catalyst --project <its root> propose …`)"
        )
    if target.read_text(encoding="utf-8") == content:
        raise ProposalError(f"{found} already has this content: nothing to propose")
    label, level = _signer_label(dep, signer)
    if level == "none":
        raise ProposalError(
            f"{signer.get('name')} has no reconciliation rights (no role grants `propose` or `full`): "
            "a proposal is a reconciliation case"
        )
    rel = target.relative_to(dep.root).as_posix()
    base = _hash(dep, target)
    etd = dep.etds[RECONCILIATION]
    case_id = next_entity_id(dep, corpus, RECONCILIATION, signer, reserve=True)
    what = title or f"Proposed change to {found}"
    name = slug(what)
    folder = dep.folder(etd)
    if folder is None:
        raise ProposalError("this deployment has no reconciliations folder")
    path = folder / f"{RECONCILIATION}-{case_id.split('-')[1]}-{name}.md"
    proposed = proposed_path(dep, case_id)
    proposed.write_text(content, encoding="utf-8")
    blob = _hash(dep, proposed)
    stamp = journal.now()
    text = latest_template(dep, etd).read_text(encoding="utf-8")
    text = re.sub(r"^#\s+.*$", f"# `{case_id}` — {what}", text, count=1, flags=re.M)
    who = str(signer.get("name"))
    for field_name, value in {
        "ID": f"`{case_id}`",
        "Name": f"`{name}`",
        "Filename": f"`{path.name}`",
        "Entity": f"`{found}`",
        "Workflow": "",
        "Trigger": f"`{TRIGGER}`",
        "Status": "Open",
        "Proposer": label,
        "Baseline": f"`{base}` — `{rel}` when the proposal was made",
        "Proposed": f"`{blob}` — `{proposed.relative_to(dep.root).as_posix()}`",
        "Opened": datetime.date.today().isoformat(),
        "Resolved": "",
        "Resolver": "",
        "Signed-off-by": who,
    }.items():
        text = set_or_add_field(text, field_name, value) if field_name != "ID" else set_field(text, field_name, value)
    why = "; ".join(intent or []) or what
    text = _section(
        text, "Description", f"{why}\n\nThe proposed content of `{rel}` is `{proposed.name}`, beside this case."
    )
    text = re.sub(
        r"^\|\s*1\s*\|\s*\{\{proposer\}\}.*$",
        f"| 1 | {who} | {stamp} | `{blob}` | Initial proposal |",
        text,
        count=1,
        flags=re.M,
    )
    path.write_text(text, encoding="utf-8")
    _finish(
        dep,
        "catalyst propose",
        "create",
        case_id,
        [found],
        intent or [f"Propose a change to {found}"],
        [path, proposed],
        str(signer.get("git_username") or who),
        tier,
    )
    return Result(case_id, path, [path, proposed])


def _section(text: str, heading: str, body: str) -> str:
    """Replace a `## heading` section's body (the template's guidance) with `body`."""
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.strip() == f"## {heading}"), None)
    if start is None:
        return text + f"\n## {heading}\n\n{body}\n"
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join([*lines[: start + 1], "", body, "", *lines[end:]])


def revise(dep: Deployment, corpus: Corpus, art: Artifact, content: str) -> tuple[str, Path, str]:
    """A new proposed content (`reconcile <case> propose --from <file>`),
    against the entity as it is now: the proposed file rewritten; returns its
    blob, its path and the new base (the entity's file now). The caller sets
    `Proposed` and `Baseline`, adds the revision row and journals both files."""
    if not is_open(art):
        raise ProposalError(f"{art.id} is {_clean(art.get('Status'))}: a decided proposal is not revised")
    target = _target_file(corpus, _clean(art.get("Entity")))
    if target is None:
        raise ProposalError(
            f"{art.id} proposes a change to {_clean(art.get('Entity'))}, which is not in this deployment"
        )
    proposed = proposed_path(dep, art.id)
    if proposed.is_file() and proposed.read_text(encoding="utf-8") == content:
        raise ProposalError(f"{art.id} already proposes this content")
    proposed.write_text(content, encoding="utf-8")
    return _hash(dep, proposed), proposed, _hash(dep, target)


def apply(dep: Deployment, corpus: Corpus, art: Artifact, signer: dict, edited: str | None) -> tuple[Path, dict]:
    """Write an accepted proposal to its entity (or the acceptor's edited
    content): refused when the entity's file is no longer the base, for the
    proposed version's own author, and for a move into a gated state the
    proposed version lacks the approvals of. Returns the entity's file and
    the fields its journal entry adds."""
    from catalyst import gates
    from catalyst.edit import recompute_derived

    p = info(dep, corpus, art)
    if p["path"] is None:
        raise ProposalError(f"{art.id} proposes a change to {p['entity']}, which is not in this deployment")
    target = dep.root / p["path"]
    proposed = dep.root / p["file"]
    if not proposed.is_file():
        raise ProposalError(f"{art.id}: its proposed content {p['file']} is missing")
    if _hash(dep, target) != p["base"]:
        raise ProposalError(
            f"{p['entity']} changed since {art.id} was proposed (its file is no longer the base): revise the "
            f"proposal against the current text (`reconcile {art.id} propose --from <file>`), or accept it "
            "with edits"
        )
    content = proposed.read_text(encoding="utf-8") if edited is None else edited
    if edited is None:
        if gates._same(signer, p["author"]):
            raise ProposalError(
                f"{signer.get('name')} wrote this proposal's version of {p['entity']}: an author never accepts "
                "their own proposal"
            )
        _check_gated_move(dep, corpus, p, content)
    target.write_text(content, encoding="utf-8")
    recompute_derived(dep, p["entity"], target)
    extra = {"proposal": art.id}
    if edited is None and p["author"] and _hash(dep, target) == p["proposed"]:
        extra["proposed_by"] = p["author"]  # the version's author, for the gates: not the acceptor
    return target, extra


def _status_of(content: str) -> str:
    from catalyst.corpus import FIELD_ROW_RE, norm_field

    for line in content.splitlines():
        m = FIELD_ROW_RE.match(line)
        if m and norm_field(m.group(1)) == norm_field("Status"):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
            return (cells[1] if len(cells) > 1 else "").strip("`")
    return ""


def _check_gated_move(dep: Deployment, corpus: Corpus, p: dict, content: str) -> None:
    """A proposal that moves its entity into a gated state needs that gate's
    approvals of the proposed version, its author not counting."""
    from catalyst import gates

    if p["entity"] not in corpus.artifacts:
        return
    art = corpus.artifacts[p["entity"]][0]
    then, now = _status_of(content), _clean(art.get("Status"))
    if not then or then == now:
        return
    try:
        entering = gates.entering(dep, corpus, art.prefix, then, art)
    except gates.GateError as exc:
        raise ProposalError(str(exc)) from None
    short = []
    for g in entering:
        _, missing = gates.counted(
            dep, corpus, g, p["entity"], current=(journal.WC + p["path"], p["proposed"]), wrote=p["author"]
        )
        if missing:
            short.append(f"gate {g.id} lacks {missing} of {g.approvals} approval(s) from {g.role}")
    if short:
        raise ProposalError(
            f"{p['case']} moves {p['entity']} to {then}: {'; '.join(short)} for the proposed version "
            f"(`catalyst approve {p['case']} --gate <gate>`)"
        )


def problems(dep: Deployment, corpus: Corpus) -> list[str]:
    """What is wrong with the open proposals (`check` reports each as an error)."""
    out = []
    for art in corpus.by_prefix.get(RECONCILIATION, []):
        if not is_proposal(art) or not is_open(art):
            continue
        p = info(dep, corpus, art)
        if p["path"] is None:
            out.append(
                f"{art.id}: proposes a change to {p['entity'] or '(no Entity)'}, which is not in this deployment"
            )
        if not p["base"]:
            out.append(f"{art.id}: its `Baseline` names no blob")
        proposed = dep.root / p["file"]
        if not proposed.is_file():
            out.append(f"{art.id}: its proposed content {p['file']} is missing")
        elif _hash(dep, proposed) != p["proposed"]:
            out.append(f"{art.id}: {p['file']} is not the version its `Proposed` names (changed outside catalyst)")
    return out
