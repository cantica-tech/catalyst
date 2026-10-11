"""Derived fields (rr-META-015, L6): a field another type names as its
`backref` (`CHILD.Parent` → `PARENT.Children`) is derived from its sources.
catalyst writes it (`new`, `link`); `check` reports one that disagrees with
its sources; `catalyst repair derived` rewrites it from them. Read from the
module's types: the kernel names none."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field

from catalyst.corpus import Artifact, Corpus, ref_values
from catalyst.deployment import Deployment


@dataclass
class Drift:
    art: Artifact
    field: str
    missing: list[str] = dc_field(default_factory=list)  # sources citing it that it does not cite
    extra: list[str] = dc_field(default_factory=list)  # what it cites that does not cite it back
    expected: list[str] = dc_field(default_factory=list)


def sources(dep: Deployment) -> dict[tuple[str, str], list[tuple[str, str]]]:
    """(type, derived field) -> the (type, field) pairs it is derived from."""
    out: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for prefix, etd in dep.etds.items():
        for fd in etd.fields:
            if not fd.backref:
                continue
            for target in (fd.target_type or "").split("|"):
                if target and target in dep.etds:
                    out.setdefault((target, fd.backref), []).append((prefix, fd.name))
    return out


def _resolver(corpus: Corpus):
    ids = set(corpus.artifacts)

    def resolve(token: str) -> str | None:
        if token in ids:
            return token
        hits = [i for i in ids if i.startswith(token + "-")]
        return hits[0] if len(hits) == 1 else None

    return resolve


def drift(dep: Deployment, corpus: Corpus) -> list[Drift]:
    """Every derived field that disagrees with its sources."""
    resolve = _resolver(corpus)
    out = []
    for (target, name), froms in sorted(sources(dep).items()):
        cited_by: dict[str, list[str]] = {}
        for prefix, source_field in froms:
            for src in corpus.by_prefix.get(prefix, []):
                for token in ref_values(src.get(source_field) or ""):
                    hit = resolve(token)
                    if hit is not None:
                        cited_by.setdefault(hit, []).append(src.id)
        for art in corpus.by_prefix.get(target, []):
            have = [resolve(t) or t for t in ref_values(art.get(name) or "")]
            want = sorted(set(cited_by.get(art.id, [])))
            missing = [w for w in want if w not in have]
            extra = [h for h in have if h not in want]
            if missing or extra:
                kept = [h for h in have if h in want]
                out.append(Drift(art, name, missing, extra, kept + missing))
    return out


def repair(dep: Deployment, corpus: Corpus, signer: dict, tier: str | None = None) -> list[Drift]:
    """Rewrite every drifting derived field from its sources, journaled in
    one entry; returns what changed (nothing when run again)."""
    from catalyst import journal
    from catalyst.edit import _ticked, set_or_add_field

    found = drift(dep, corpus)
    if not found:
        return []
    files = []
    for d in found:
        text = d.art.file.read_text(encoding="utf-8")
        d.art.file.write_text(set_or_add_field(text, d.field, _ticked(d.expected)), encoding="utf-8")
        if d.art.file not in files:
            files.append(d.art.file)
    journal.append(
        dep,
        journal.AppendRequest(
            command="catalyst repair derived",
            action="update",
            artifact="derived fields",
            targets=[],
            intent=[
                "derived fields rewritten from their sources: " + "; ".join(f"{d.art.id}.{d.field}" for d in found)
            ],
            files=[str(f) for f in files],
            actor=str(signer.get("git_username") or signer.get("name")),
            tier=tier,
            allow_unchanged=True,  # a repair may restore a file's last journaled state (an unjournaled hand edit undone)
        ),
    )
    return found
