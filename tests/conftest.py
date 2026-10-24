import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import pytest


@pytest.fixture(autouse=True)
def _isolated_catalyst_home(tmp_path_factory, monkeypatch):
    """No test reads or writes the real $HOME/.catalyst, nor this machine's catalyst-users settings (its system
    account, design 29 §3.4a)."""
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path_factory.mktemp("catalyst-home")))
    monkeypatch.setenv("CATALYST_USERS_HOME", str(tmp_path_factory.mktemp("catalyst-users-home")))


# --- people through catalyst-users (design 29) -------------------------------------------
# A criterion no longer holds people: it points at catalyst-users (IAM/identity.json). The suite's fixtures still
# declare people the old way (IAM/users/users.json, IAM/roles/roles.json); for a deployment that has no pointer,
# this bridge presents them through catalyst-users' static backend (accepted only with the flag set here): each
# person a declared identity, each role its grants as `catalyst-users roles provision` writes them, each person an
# existing ledger line with the userid the fixture gave them. Every signature still goes through the facade.
def _legacy(root: Path, name: str, key: str) -> list[dict]:
    import json

    try:
        data = json.loads((root / "IAM" / name / f"{name}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = data.get(key) if isinstance(data, dict) else None
    return [i for i in items if isinstance(i, dict)] if isinstance(items, list) else []


def _slug(name: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")


def _grants(role: dict) -> list[str]:
    out = set()
    for action in role.get("actions") or ():
        text = str(action).strip()
        if text == "*":
            out.add("cmd:*")
        elif text.startswith("/") and text[1:].split():
            out.add("cmd:" + text[1:].split()[0])
    if str(role.get("name")) == "Admin":
        out.add("cmd:*")
    if str(role.get("reconciliation") or "none") in ("full", "propose"):
        out.add("reconcile:" + str(role["reconciliation"]))
    return sorted(out)


def legacy_pointer(root: Path) -> dict | None:
    users = _legacy(root, "users", "users")
    if not users:
        return None
    roles = _legacy(root, "roles", "roles")
    defs = [{"id": _slug(r["name"]), "name": r["name"], "grants": _grants(r)} for r in roles if r.get("name")]
    if not any(d["name"] == "Admin" for d in defs):
        defs.append({"id": "admin", "name": "Admin", "grants": ["cmd:*"]})
    people = [
        {
            "username": str(u.get("git_username") or u.get("name")),
            "name": str(u.get("name") or u.get("git_username")),
            "subject": str(u.get("userid") or u.get("git_username") or u.get("name")),
            "roles": [_slug(r) for r in u.get("roles") or []],
            "active": u.get("active", True) is not False,
        }
        for u in users
    ]
    return {"provider": "static", "people": people, "roles": defs}


def legacy_signers(root: Path) -> list[dict]:
    return [
        {
            "userid": str(u["userid"]),
            "iss": "static:",
            "sub": str(u["userid"]),
            "username": str(u.get("git_username") or u.get("name")),
            "name": str(u.get("name") or u.get("git_username")),
        }
        for u in _legacy(root, "users", "users")
        if u.get("userid")
    ]


def persist_bridge(root: Path) -> None:
    """Write the bridge's pointer and signers ledger to disk, for a test that runs catalyst in a subprocess (which
    does not see this conftest's in-process bridge)."""
    import json

    (root / "IAM" / "identity.json").write_text(json.dumps(legacy_pointer(root)), encoding="utf-8")
    (root / "IAM" / "signers.jsonl").write_text("".join(json.dumps(e) + "\n" for e in legacy_signers(root)))


@pytest.fixture(autouse=True)
def _people_through_catalyst_users(monkeypatch):
    monkeypatch.setenv("CATALYST_ALLOW_STATIC_IDENTITY", "1")
    from catalyst import corpus, provider

    real_read, real_ledger, real_problems, real_roles = (
        provider.read_pointer,
        provider.ledger,
        provider.problems,
        corpus._roles_at,
    )

    def read_pointer(root):
        doc = real_read(root)
        return doc if doc is not None or (root / provider.POINTER).exists() else legacy_pointer(root)

    def ledger(root):
        own = real_ledger(root)
        if (root / provider.POINTER).exists():
            return own
        seen = {(e["iss"], e["sub"]) for e in own}
        return own + [e for e in legacy_signers(root) if (e["iss"], e["sub"]) not in seen]

    def problems(dep):
        if not (dep.root / provider.POINTER).is_file() and legacy_pointer(dep.root) is not None:
            return [], []
        return real_problems(dep)

    def roles_at(root):
        legacy = [{**r, "id": _slug(r["name"])} for r in _legacy(root, "roles", "roles") if r.get("name")]
        names = {r["name"] for r in legacy}
        return legacy + [r for r in real_roles(root) if r.get("name") not in names]

    monkeypatch.setattr(provider, "read_pointer", read_pointer)
    monkeypatch.setattr(provider, "ledger", ledger)
    monkeypatch.setattr(provider, "problems", problems)
    monkeypatch.setattr(corpus, "_roles_at", roles_at)
