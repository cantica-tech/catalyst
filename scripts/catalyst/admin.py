"""Administration verbs (roadmap R2 W3): users, roles, freeze/unfreeze and
definition migration.

The mechanical half of `/user-*`, `/role-*`, `/freeze` and
`/migrate-definition`: the refusals those procedures list, the write, and
one journal entry. Users are never deleted (signatures must stay
resolvable), a userid is always drawn (INV-26), the last active user is never
removed, and a deployed definition moves only to a version that exists
(INV-23).
"""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path

from catalyst import journal
from catalyst.corpus import Corpus, load_corpus
from catalyst.deployment import Deployment
from catalyst.ids import generate_userid

RECONCILIATION_LEVELS = ("full", "propose", "none")
USERS = Path("IAM") / "users" / "users.json"
ROLES = Path("IAM") / "roles" / "roles.json"
IDENTITY_FIELDS = {"name", "registered", "userid"}


class AdminError(Exception):
    pass


# --- json files -----------------------------------------------------------
def _latest_template(folder: Path, stem: str) -> Path | None:
    found = [
        (int(m.group(1)), p)
        for p in folder.glob(f"TEMPLATE-{stem}-v*.json")
        if (m := re.search(r"-v(\d+)\.json$", p.name))
    ]
    return max(found)[1] if found else None


def _load(dep: Deployment, rel: Path, key: str, created: list[Path]) -> dict:
    path = dep.root / rel
    if not path.is_file():
        template = _latest_template(path.parent / "templates", key.upper())
        data = json.loads(template.read_text(encoding="utf-8")) if template else {}
        data.setdefault(key, [])
        _save(path, data)
        created.append(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get(key), list):
        raise AdminError(f"{rel.as_posix()} has no `{key}` list")
    return data


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _find(items: list[dict], name: str, keys=("name",)) -> dict | None:
    wanted = name.strip().lower()
    return next((i for i in items if any(str(i.get(k, "")).lower() == wanted for k in keys)), None)


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


def _role_names(dep: Deployment, created: list[Path]) -> list[str]:
    return [str(r.get("name")) for r in _load(dep, ROLES, "roles", created)["roles"]]


# --- users ----------------------------------------------------------------
def user_add(
    dep: Deployment,
    name: str,
    role: str,
    signer: dict,
    intent: list[str],
    git_username: str | None = None,
    today: datetime.date | None = None,
) -> dict:
    created: list[Path] = []
    data = _load(dep, USERS, "users", created)
    if _find(data["users"], name, ("name", "git_username")):
        raise AdminError(f"'{name}' is already registered — use `user modify` or `user assign-role`")
    roles = _role_names(dep, created)
    if role not in roles:
        raise AdminError(f"no role '{role}' (roles: {', '.join(roles)}) — `role add` it first")
    user = {
        "name": name,
        "git_username": git_username or name,
        "roles": [role],
        "registered": (today or datetime.date.today()).isoformat(),
        "active": True,
        "notes": "",
        "userid": generate_userid({str(u.get("userid")) for u in data["users"]}),
    }
    data["users"].append(user)
    _save(dep.root / USERS, data)
    _journal(
        dep,
        "/user-add",
        "create",
        f"user {name}",
        intent or [f"Register {name} as {role}"],
        [*created, dep.root / USERS],
        signer,
    )
    return user


def _existing_user(dep: Deployment, name: str) -> tuple[dict, dict]:
    data = _load(dep, USERS, "users", [])
    user = _find(data["users"], name, ("name", "git_username", "userid"))
    if user is None:
        raise AdminError(f"'{name}' is not registered — `user add` first")
    return data, user


def user_remove(dep: Deployment, name: str, signer: dict, intent: list[str]) -> dict:
    data, user = _existing_user(dep, name)
    if not user.get("active", True):
        raise AdminError(f"'{user['name']}' is already inactive")
    if sum(1 for u in data["users"] if u.get("active", True)) == 1:
        raise AdminError(f"'{user['name']}' is the only active user — `user add` a replacement first (INV-16)")
    user["active"] = False  # never deleted: signatures stay resolvable
    _save(dep.root / USERS, data)
    _journal(
        dep,
        "/user-remove",
        "update",
        f"user {user['name']}",
        intent or [f"Deactivate {user['name']}"],
        [dep.root / USERS],
        signer,
    )
    return user


def user_modify(dep: Deployment, name: str, field: str, value: str, signer: dict, intent: list[str]) -> dict:
    data, user = _existing_user(dep, name)
    if field == "roles":
        raise AdminError("roles change through `user assign-role`")
    if field in IDENTITY_FIELDS:
        raise AdminError(f"`{field}` is an identity field, never edited in place")
    if field == "active":
        if value.lower() in ("false", "no", "0"):
            raise AdminError("deactivate with `user remove` (it keeps one active user)")
        new: object = True
    else:
        new = value
    user[field] = new
    _save(dep.root / USERS, data)
    _journal(
        dep,
        "/user-modify",
        "update",
        f"user {user['name']}",
        intent or [f"{user['name']}: {field} = {value}"],
        [dep.root / USERS],
        signer,
    )
    return user


def user_assign_role(dep: Deployment, name: str, role: str, signer: dict, intent: list[str]) -> dict:
    data, user = _existing_user(dep, name)
    roles = _role_names(dep, [])
    if role not in roles:
        raise AdminError(f"no role '{role}' (roles: {', '.join(roles)}) — `role add` it first")
    if role in user.get("roles", []):
        raise AdminError(f"'{user['name']}' already has role '{role}'")
    user.setdefault("roles", []).append(role)
    _save(dep.root / USERS, data)
    _journal(
        dep,
        "/user-assign-role",
        "update",
        f"user {user['name']}",
        intent or [f"{user['name']} gains role {role}"],
        [dep.root / USERS],
        signer,
    )
    return user


# --- roles ----------------------------------------------------------------
def role_add(
    dep: Deployment, role: str, actions: list[str], signer: dict, intent: list[str], reconciliation: str = "propose"
) -> dict:
    if reconciliation not in RECONCILIATION_LEVELS:
        raise AdminError(f"reconciliation is one of {', '.join(RECONCILIATION_LEVELS)}")
    created: list[Path] = []
    data = _load(dep, ROLES, "roles", created)
    if _find(data["roles"], role):
        raise AdminError(f"role '{role}' exists — use `role modify`")
    entry = {"name": role, "actions": actions, "reconciliation": reconciliation}
    data["roles"].append(entry)
    _save(dep.root / ROLES, data)
    _journal(
        dep, "/role-add", "create", f"role {role}", intent or [f"Add role {role}"], [*created, dep.root / ROLES], signer
    )
    return entry


def role_modify(dep: Deployment, role: str, actions: list[str], signer: dict, intent: list[str]) -> dict:
    data = _load(dep, ROLES, "roles", [])
    entry = _find(data["roles"], role)
    if entry is None:
        raise AdminError(f"no role '{role}' — use `role add`")
    entry["actions"] = actions  # signatures already recorded are not touched
    _save(dep.root / ROLES, data)
    _journal(
        dep,
        "/role-modify",
        "update",
        f"role {role}",
        intent or [f"Role {role}: actions replaced"],
        [dep.root / ROLES],
        signer,
    )
    return entry


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
    sources = [kernel] + ([dep.root / "modules" / dep.module.id] if dep.module else [])
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
