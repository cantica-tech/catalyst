"""Administration verbs (roadmap R2 W3): freeze/unfreeze and definition
migration.

The mechanical half of `/freeze` and `/migrate-definition`: the refusals
those procedures list, the write, and one journal entry. A deployed
definition moves only to a version that exists (INV-23). People and roles
are catalyst-users' (design 29): `catalyst user` and `catalyst role` only
say so.
"""

from __future__ import annotations

import re
from pathlib import Path

from catalyst import journal
from catalyst.corpus import Corpus, load_corpus
from catalyst.deployment import Deployment


class AdminError(Exception):
    pass


def _journal(
    dep: Deployment, command: str, action: str, artifact: str, intent: list[str], files: list[Path], actor: dict
) -> None:
    journal.append(
        dep,
        journal.AppendRequest(
            command=command,
            action=action,
            artifact=artifact,
            targets=[],
            intent=intent,
            files=[str(p) for p in dict.fromkeys(files)],
            actor=str(actor.get("git_username") or actor.get("name")),
            tier="chore",
        ),
    )


# --- freeze ---------------------------------------------------------------
def resolve_item(dep: Deployment, corpus: Corpus, item: str) -> str:
    """An item ID, a path, an entity type or a template file name, as a
    working-copy-relative path."""
    if item in corpus.artifacts:
        return corpus.artifacts[item][0].file.relative_to(dep.root).as_posix()
    for prefix, etd in dep.etds.items():
        if item.lower() in {prefix.lower(), etd.name.lower(), etd.plural_name.lower(), etd.folder.lower()}:
            folder = dep.folder(etd)
            if folder is not None:
                return folder.relative_to(dep.root).as_posix()
    candidate = Path(item.removeprefix(".criterion/"))
    if (dep.root / candidate).exists():
        return candidate.as_posix()
    hits = sorted(dep.root.glob(f"**/templates/{item}")) + sorted(dep.root.glob(f"**/templates/{item}.md"))
    if hits:
        return hits[0].relative_to(dep.root).as_posix()
    raise AdminError(f"'{item}' is not an artifact ID, entity type, template or path in this working copy")


def _frozen(dep: Deployment) -> tuple[Path, list[str]]:
    path = dep.root / ".frozen"
    return path, (path.read_text(encoding="utf-8").splitlines() if path.is_file() else [])


def freeze(dep: Deployment, item: str, signer: dict, intent: list[str], unfreeze: bool = False) -> str:
    rel = resolve_item(dep, load_corpus(dep), item)
    path, lines = _frozen(dep)
    listed = [line.strip().removeprefix(".criterion/") for line in lines]
    if unfreeze:
        if rel not in listed:
            raise AdminError(f"{rel} is not frozen")
        lines = [line for line in lines if line.strip().removeprefix(".criterion/") != rel]
    else:
        if rel in listed:
            raise AdminError(f"{rel} is already frozen")
        lines.append(rel)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    _journal(
        dep,
        "/unfreeze" if unfreeze else "/freeze",
        "update",
        rel,
        intent or [f"{'Unfreeze' if unfreeze else 'Freeze'} {rel} for /sync-framework"],
        [path],
        signer,
    )
    return rel


# --- definitions ----------------------------------------------------------
def definition_versions(sources: list[Path], entity: str) -> dict[int, Path]:
    found: dict[int, Path] = {}
    for src in sources:
        folder = src / "definitions" / entity
        for p in folder.glob(f"DEFINITION-{entity.upper()}-v*.md") if folder.is_dir() else []:
            if m := re.search(r"-v(\d+)\.md$", p.name):
                found.setdefault(int(m.group(1)), p)
    return found


def migrate_definition(
    dep: Deployment, entity: str, version: int, kernel: Path, signer: dict, intent: list[str]
) -> tuple[str, int]:
    """Overwrite `definitions/<entity>.md` with that exact version, from the
    kernel's or the deployed module's `definitions/<entity>/`."""
    sources = [kernel, *dep.module_dirs()]
    versions = definition_versions(sources, entity)
    if not versions:
        known = sorted(
            {
                p.name
                for s in sources
                if (s / "definitions").is_dir()
                for p in (s / "definitions").iterdir()
                if p.is_dir()
            }
        )
        raise AdminError(f"'{entity}' is not an entity type with definitions (types: {', '.join(known)})")
    if version not in versions:
        raise AdminError(f"{entity} has no v{version}; the highest is v{max(versions)}")
    target = dep.root / "definitions" / f"{entity}.md"
    old = re.search(r"\*\*Version\*\*\s*\|\s*(\d+)", target.read_text(encoding="utf-8")) if target.is_file() else None
    old_version = int(old.group(1)) if old else 0
    if old_version == version:
        raise AdminError(f"definitions/{entity}.md is already v{version}")
    target.write_text(versions[version].read_text(encoding="utf-8"), encoding="utf-8")
    _journal(
        dep,
        "/migrate-definition",
        "update",
        f"definition {entity} v{old_version} -> v{version}",
        intent or [f"Move the {entity} definition to v{version}"],
        [target],
        signer,
    )
    return entity, old_version
