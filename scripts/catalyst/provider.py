"""Who signs: catalyst-users is the facade (design 29, ADR-000049; fw-IDENTITY-000002, 000003, 000007..000010).

A criterion holds no user or role registry. `IAM/identity.json` points at the deployment's catalyst-users
configuration, and catalyst reaches people only through catalyst-users' facade (`catalyst.identity.provider`,
vendored):

- the signer is the identity the facade says is logged in, verified at each signature; none, nothing is signed;
- its roles, groups, grants (`cmd:<command>`, `reconcile:<level>`) and reconciliation level come from the provider,
  read-only; a role's display name comes from the deployment's roles template, which grants nothing;
- each identity that signs gets one line in the append-only ledger `IAM/signers.jsonl`, journaled the first time;
  the journal's actor is the ledger's username;
- the logged-in identity is kept per machine as a read-only snapshot with a hash of its content, rewritten at each
  signature; an edited one is discarded and the person authenticated anew.

The `static` backend, which verifies nobody, is accepted only with `CATALYST_ALLOW_STATIC_IDENTITY=1`.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from catalyst.deployment import Deployment

POINTER = Path("IAM") / "identity.json"
SIGNERS = Path("IAM") / "signers.jsonl"
STATIC_FLAG = "CATALYST_ALLOW_STATIC_IDENTITY"
DEFAULT_CLIENT = "catalyst-cli"
LEDGER_KEYS = ("userid", "iss", "sub", "username", "name", "first_signed")


class ProviderError(Exception):
    pass


@dataclass(frozen=True)
class ProviderSettings:
    """What the vendored OIDC client reads (`catalyst.identity.config.Settings`), for any issuer."""

    issuer: str
    client_id: str = DEFAULT_CLIENT
    api_client_id: str = "catalyst-api"
    api_client_secret: str | None = field(default=None, repr=False)
    timeout: float = 10.0


# --- the pointer (fw-IDENTITY-000007) ----------------------------------------------------
def read_pointer(root: Path) -> dict[str, Any] | None:
    try:
        doc = json.loads((root / POINTER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def pointer(dep: Deployment) -> dict[str, Any] | None:
    """The deployment's pointer, else its workspace's (a member inherits it, R3.1b)."""
    own = read_pointer(dep.root)
    if own is not None:
        return own
    from catalyst.corpus import _workspace_root

    root = _workspace_root(dep)
    return read_pointer(root) if root is not None else None


def problems(dep: Deployment) -> tuple[list[str], list[str]]:
    """(errors, warnings) about the deployment's pointer, for `check`."""
    path = dep.root / POINTER
    if path.is_file() and read_pointer(dep.root) is None:
        return [f"{POINTER.as_posix()} is not a JSON object"], []
    doc = pointer(dep)
    if doc is None:
        return [
            f"{POINTER.as_posix()} is missing: point the deployment at catalyst-users "
            "(`catalyst identity configure --issuer <url>`)"
        ], []
    from catalyst.identity.provider import pointer_problems

    found = pointer_problems(doc)
    if doc.get("provider") == "static":
        return [], [f"{POINTER.as_posix()}: the static provider verifies nobody (catalyst's tests only)"]
    return [f"{POINTER.as_posix()}: {p}" for p in found], []


def credentials_path(doc: dict[str, Any]) -> Path:
    """Owner-only tokens in catalyst's home, one file per issuer and client; never in a criterion."""
    import project_file

    key = hashlib.sha256(f"{doc.get('issuer', '')}\n{doc.get('client') or DEFAULT_CLIENT}".encode()).hexdigest()[:16]
    return project_file.home() / "identity" / f"{key}.json"


def facade(doc: dict[str, Any], transport: Any = None):
    """The catalyst-users backend the pointer names."""
    from catalyst.identity.errors import CatalystUsersError
    from catalyst.identity.provider import from_pointer

    try:
        return from_pointer(doc, store=credentials_path(doc), transport=transport)
    except CatalystUsersError as exc:
        raise ProviderError(str(exc)) from None


def facade_of(dep: Deployment, transport: Any = None):
    doc = pointer(dep)
    if doc is None:
        raise ProviderError(f"{POINTER.as_posix()} is missing: `catalyst identity configure --issuer <url>`")
    return facade(doc, transport)


def verify(doc: dict[str, Any], as_user: str | None = None, transport: Any = None):
    """The identity the facade says is logged in, now; ProviderError if there is none."""
    from catalyst.identity.errors import CatalystUsersError, NotLoggedInError

    backend = facade(doc, transport)
    try:
        return backend.whoami(as_user if backend.kind == "static" else None)
    except NotLoggedInError:
        system = system_backend(backend.issuer, transport)
        if system is None:
            raise ProviderError(
                f"no verified identity: not logged in to {backend.issuer} (`catalyst identity login`)"
            ) from None
        try:
            who = system.system_whoami()
        except CatalystUsersError as exc:
            raise ProviderError(f"no one is logged in, and the system account cannot sign in: {exc}") from None
        if as_user and as_user.strip().lower() not in {who.username.lower(), who.name.lower(), who.subject.lower()}:
            raise ProviderError(  # --as names someone else: never the system account for them
                f"no verified identity: not logged in to {backend.issuer} (`catalyst identity login`)"
            ) from None
        print(f"catalyst: no one is logged in: signing as the system account {who.username}", file=sys.stderr)
        return who
    except CatalystUsersError as exc:
        raise ProviderError(f"no verified identity ({exc}): `catalyst identity login`, then try again") from None


def system_backend(issuer: str, transport: Any = None):
    """This machine's system account (design 29 §3.4a, catalyst-users 0.4.0): the admin catalyst-users' setup named
    in `IAM/settings.json`, when those settings point at the same issuer; else None."""
    from catalyst.identity import config as users_config
    from catalyst.identity.errors import CatalystUsersError
    from catalyst.identity.provider import from_pointer

    try:
        settings = users_config.read_settings()
        if settings is None or not settings.get("username") or not settings.get("password_command"):
            return None
        system = from_pointer(users_config.settings_pointer(settings), transport=transport)
    except CatalystUsersError:
        return None
    return system if str(system.issuer).rstrip("/") == str(issuer).rstrip("/") else None


def access_token(doc: dict[str, Any]) -> str | None:
    """A fresh provider access token (a served criterion's client sends it), or None."""
    from catalyst.identity.errors import CatalystUsersError

    backend = facade(doc)
    if backend.kind != "keycloak":
        return None
    try:
        return backend._session().access_token()
    except CatalystUsersError:
        return None


# --- the role catalogue (fw-IDENTITY-000010) ----------------------------------------------
def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def role_id(role: dict[str, Any]) -> str:
    return str(role.get("id") or role.get("provider_role") or _slug(str(role.get("name") or "")))


def display_roles(catalogue: list[dict[str, Any]], provider_roles: tuple[str, ...]) -> list[str]:
    """The provider roles held, by their display name when the roles template names them."""
    names = {role_id(r): str(r.get("name")) for r in catalogue if r.get("name")}
    return sorted({names.get(r, r) for r in provider_roles})


# --- the snapshot (fw-IDENTITY-000009) ----------------------------------------------------
def snapshot_path(doc: dict[str, Any]) -> Path:
    return credentials_path(doc).with_suffix(".snapshot.json")


def _digest(data: dict[str, Any]) -> str:
    body = {k: v for k, v in data.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def write_snapshot(doc: dict[str, Any], user: dict[str, Any]) -> Path:
    """The logged-in identity as verified now, read-only, with a hash of its content."""
    path = snapshot_path(doc)
    data = {
        "issuer": user.get("iss"),
        "subject": user.get("sub"),
        "userid": user.get("userid") or None,
        "username": user.get("git_username"),
        "name": user.get("name"),
        "groups": list(user.get("groups") or []),
        "roles": list(user.get("roles") or []),
        "grants": list(user.get("grants") or []),
        "reconciliation": user.get("reconciliation") or "none",
        "verified": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    data["hash"] = _digest(data)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # written aside and renamed into place: parallel signatures (sub-agents) never write the read-only file itself
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.chmod(0o400)
    try:
        tmp.replace(path)
    except PermissionError:  # Windows will not replace a read-only file
        path.chmod(0o600)
        tmp.replace(path)
    return path


def read_snapshot(doc: dict[str, Any]) -> dict[str, Any] | None:
    """The snapshot, or None: none yet, or one whose content no longer matches its hash, which is discarded (its
    owner is authenticated anew at the next use)."""
    path = snapshot_path(doc)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("hash") != _digest(data):
        discard_snapshot(doc)
        return None
    return data


def discard_snapshot(doc: dict[str, Any]) -> None:
    path = snapshot_path(doc)
    try:
        path.chmod(0o600)
        path.unlink()
    except FileNotFoundError:  # already gone (another process discarded it)
        pass


# --- the signers ledger (fw-IDENTITY-000003) -------------------------------------------
def ledger(root: Path) -> list[dict]:
    """The ledger's well-formed lines, in order."""
    try:
        lines = (root / SIGNERS).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and all(entry.get(k) for k in ("userid", "iss", "sub", "username")):
            out.append(entry)
    return out


def ledger_problems(root: Path) -> list[str]:
    """Malformed lines and userids used twice, for `check`."""
    path = root / SIGNERS
    if not path.is_file():
        return []
    found, seen = [], {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            found.append(f"{SIGNERS.as_posix()}:{number}: not a JSON line")
            continue
        missing = [k for k in ("userid", "iss", "sub", "username") if not (isinstance(entry, dict) and entry.get(k))]
        if missing:
            found.append(f"{SIGNERS.as_posix()}:{number}: missing {', '.join(missing)}")
            continue
        other = seen.setdefault(entry["userid"], (entry["iss"], entry["sub"]))
        if other != (entry["iss"], entry["sub"]):
            found.append(f"{SIGNERS.as_posix()}:{number}: userid {entry['userid']} names two identities")
    return found


def ledger_history_problems(dep: Deployment) -> list[str]:
    """Lines the ledger had in a version the journal recorded but has no more: it is append-only."""
    from catalyst import journal

    path = dep.root / SIGNERS
    current = set(path.read_text(encoding="utf-8").splitlines()) if path.is_file() else set()
    lost: set[str] = set()
    for _, entry, _ in journal.read(dep):
        for f in (entry or {}).get("files") or []:
            if not (isinstance(f, dict) and str(f.get("path", "")).endswith(SIGNERS.as_posix())):
                continue
            for sha in (f.get("before"), f.get("after")):
                if not sha or not journal.blob_exists(dep.root, str(sha)):
                    continue
                old = journal.git(dep.root, "cat-file", "-p", str(sha), check=False)
                lost |= {line for line in old.splitlines() if line.strip()} - current
    return [
        f"{SIGNERS.as_posix()}: a line the journal recorded was changed or removed: {line}" for line in sorted(lost)
    ]


def as_user(entry: dict, roles: list[str] | None = None) -> dict:
    """A ledger line as the user record the rest of catalyst reads."""
    return {
        "name": entry.get("name") or entry["username"],
        "git_username": entry["username"],
        "userid": entry["userid"],
        "roles": list(roles or []),
        "active": True,
        "iss": entry["iss"],
        "sub": entry["sub"],
    }


def find(entries: list[dict], iss: str, sub: str) -> dict | None:
    return next((e for e in entries if e.get("iss") == iss and e.get("sub") == sub), None)


def enroll(dep: Deployment, who) -> dict:
    """The identity's ledger line; appended (and journaled) the first time it signs."""
    from catalyst import journal
    from catalyst.corpus import local_users
    from catalyst.ids import generate_userid

    entries = ledger(dep.root)
    found = find(entries, who.issuer, who.subject)
    if found is not None:
        return found
    people = local_users(dep.root)
    userid = generate_userid({str(u.get("userid")) for u in people} | {str(e["userid"]) for e in entries})
    taken = {str(u.get(k, "")).lower() for u in people for k in ("name", "git_username")} | {
        str(e["username"]).lower() for e in entries
    }
    username = who.username if who.username.lower() not in taken else f"{who.username}-{userid}"
    entry = {
        "userid": userid,
        "iss": who.issuer,
        "sub": who.subject,
        "username": username,
        "name": who.name,
        "first_signed": datetime.now(UTC).date().isoformat(),
    }
    path = dep.root / SIGNERS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    journal.append(
        dep,
        journal.AppendRequest(
            command="catalyst identity",
            action="create",
            artifact=f"signer {userid}",
            targets=[],
            intent=[f"{username} signs for the first time: their userid, issuer and subject join the signers ledger"],
            files=[str(path)],
            actor=username,
            tier="chore",
        ),
    )
    return entry


def link(dep: Deployment, retired: str, as_user_name: str | None = None, transport: Any = None) -> dict:
    """The verified identity takes a retired user's userid (migration 0.106.0, owner decision of 2026-10-23), so the
    IDs it creates keep ending with it: once per identity and per userid, only by the person themselves (the retired
    user's name or username is the identity's), journaled. Its ledger line is the one `enroll` would have written,
    with that userid."""
    from catalyst import journal
    from catalyst.corpus import local_users

    doc = pointer(dep)
    if doc is None:
        raise ProviderError(f"{POINTER.as_posix()} is missing: `catalyst identity configure --issuer <url>`")
    who = verify(doc, as_user_name, transport)
    wanted = retired.strip().lower()
    person = next(
        (
            u
            for u in local_users(dep.root)
            if wanted in {str(u.get(k, "")).lower() for k in ("name", "git_username", "userid")}
        ),
        None,
    )
    if person is None or not person.get("userid"):
        raise ProviderError(f"no retired user {retired!r} with a userid (IAM/users/users.retired.json)")
    theirs = {str(person.get(k, "")).lower() for k in ("name", "git_username")} - {""}
    if not theirs & {who.username.lower(), who.name.lower()}:
        raise ProviderError(
            f"{who.username} ({who.name}) is not {person.get('name')}: a retired user's userid is taken only by them"
        )
    entries = ledger(dep.root)
    if find(entries, who.issuer, who.subject) is not None:
        raise ProviderError(f"{who.username} already has a line in {SIGNERS.as_posix()}: it is never rewritten")
    if any(str(e["userid"]) == str(person["userid"]) for e in entries):
        raise ProviderError(f"userid {person['userid']} is already linked to another identity")
    taken = {str(e["username"]).lower() for e in entries}
    username = who.username if who.username.lower() not in taken else f"{who.username}-{person['userid']}"
    entry = {
        "userid": str(person["userid"]),
        "iss": who.issuer,
        "sub": who.subject,
        "username": username,
        "name": who.name,
        "first_signed": datetime.now(UTC).date().isoformat(),
    }
    path = dep.root / SIGNERS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    journal.append(
        dep,
        journal.AppendRequest(
            command="catalyst identity link",
            action="create",
            artifact=f"signer {entry['userid']}",
            targets=[],
            intent=[f"{username} signs as {person.get('name')} did before: they keep userid {entry['userid']}"],
            files=[str(path)],
            actor=username,
            tier="chore",
        ),
    )
    return entry


# --- the signer (fw-IDENTITY-000002, 000008) ------------------------------------------------
def signer(dep: Deployment, as_user_name: str | None = None, transport: Any = None) -> dict:
    """The verified identity signing, as a user record: its roles (display names), groups, grants and
    reconciliation level now. One that has never signed carries `pending` (and no userid) until `enrolled` adds it
    to the ledger, which the caller does only once its grants allow the command."""
    from catalyst.corpus import roles as catalogue

    doc = pointer(dep)
    if doc is None:
        raise ProviderError(f"{POINTER.as_posix()} is missing: `catalyst identity configure --issuer <url>`")
    if doc.get("provider") == "static" and os.environ.get(STATIC_FLAG) != "1":
        raise ProviderError(f"the static provider verifies nobody: catalyst's tests only ({STATIC_FLAG}=1)")
    who = verify(doc, as_user_name, transport)
    if as_user_name and doc.get("provider") != "static":
        wanted = as_user_name.strip().lower()
        entry = find(ledger(dep.root), who.issuer, who.subject)
        names = {who.username.lower(), who.name.lower(), who.subject.lower()} | (
            {str(entry["userid"]).lower(), str(entry["username"]).lower()} if entry else set()
        )
        if wanted not in names:
            raise ProviderError(
                f"--as {as_user_name}: you are logged in as {who.username}; you sign only as yourself "
                "(fw-IDENTITY-000002)"
            )
    entry = find(ledger(dep.root), who.issuer, who.subject)
    roles = display_roles(catalogue(dep), who.roles)
    if entry is not None:
        user = as_user(entry, roles)
    else:
        user = {"name": who.name, "git_username": who.username, "userid": "", "roles": roles, "active": True}
        user.update({"iss": who.issuer, "sub": who.subject, "pending": who})
    user.update({"groups": list(who.groups), "grants": list(who.grants), "reconciliation": who.reconciliation})
    user["provider_roles"] = list(who.roles)
    write_snapshot(doc, user)
    return user


def enrolled(dep: Deployment, user: dict) -> dict:
    """`user`, with its ledger line written if it had none (`pending`)."""
    who = user.get("pending")
    if who is None:
        return user
    done = {**as_user(enroll(dep, who), list(user.get("roles") or []))}
    for key in ("groups", "grants", "reconciliation", "provider_roles"):
        done[key] = user.get(key)
    doc = pointer(dep)
    if doc is not None:
        write_snapshot(doc, done)
    return done
