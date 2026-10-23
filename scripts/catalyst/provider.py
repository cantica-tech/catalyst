"""The deployment's identity provider (design 28, ADR-000048; fw-IDENTITY-000001..000004).

`identity = "local"` (the default) keeps `IAM/users/users.json` as the registry. `identity = "oidc"`
makes an OIDC provider's accounts the deployment's people:

- the signer is the identity logged in with `catalyst identity login`, verified at each signature (its
  token refreshed under 30 seconds of life, the provider asked who it is); none, nothing is signed;
- each identity that signs gets one line in the append-only ledger `IAM/signers.jsonl` (a userid, its
  `iss` and `sub`, a snapshot of its username and name), journaled the first time; the journal's actor
  is the ledger's username;
- its roles are the deployment's roles whose `provider_role` the provider gives it.

The OIDC code is catalyst-users' core, vendored under `catalyst.identity` (fw-IDENTITY-000006).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from catalyst.deployment import Deployment

LOCAL, OIDC = "local", "oidc"
PROVIDERS = (LOCAL, OIDC)
SIGNERS = Path("IAM") / "signers.jsonl"
DEFAULT_CLIENT = "catalyst-cli"
LEDGER_KEYS = ("userid", "iss", "sub", "username", "name", "first_signed")


class ProviderError(Exception):
    pass


@dataclass(frozen=True)
class ProviderSettings:
    """What the vendored OIDC client reads from its settings (`catalyst.identity.config.Settings`), for any
    issuer, not only Keycloak's `<server>/realms/<realm>`."""

    issuer: str
    client_id: str = DEFAULT_CLIENT
    api_client_id: str = "catalyst-api"
    api_client_secret: str | None = field(default=None, repr=False)
    timeout: float = 10.0


# --- configuration (fw-IDENTITY-000001) ---------------------------------------------
def kind(pointer: dict | None) -> str:
    return str((pointer or {}).get("identity") or LOCAL)


def settings(pointer: dict | None) -> ProviderSettings:
    data = pointer or {}
    issuer = str(data.get("identity_issuer") or "").rstrip("/")
    if kind(data) != OIDC:
        raise ProviderError('this deployment\'s identity provider is "local" (catalyst.toml `identity`)')
    if not issuer:
        raise ProviderError(
            'identity = "oidc" needs `identity_issuer` in catalyst.toml (`catalyst identity configure`)'
        )
    return ProviderSettings(issuer=issuer, client_id=str(data.get("identity_client") or DEFAULT_CLIENT))


def problems(pointer: dict | None) -> list[str]:
    """What is wrong with the deployment's identity settings, for `check`."""
    found = kind(pointer)
    if found not in PROVIDERS:
        return [f"identity: unknown provider {found!r} (one of {', '.join(PROVIDERS)})"]
    if found == OIDC and not str((pointer or {}).get("identity_issuer") or ""):
        return ['identity: identity = "oidc" needs `identity_issuer`']
    return []


def is_oidc(dep: Deployment) -> bool:
    return kind(dep.pointer) == OIDC


# --- the logged-in identity (fw-IDENTITY-000002) --------------------------------------
def credentials_path(conf: ProviderSettings) -> Path:
    """Owner-only tokens in catalyst's home, one file per issuer and client; never in a criterion."""
    import project_file

    key = hashlib.sha256(f"{conf.issuer}\n{conf.client_id}".encode()).hexdigest()[:16]
    return project_file.home() / "identity" / f"{key}.json"


def session(conf: ProviderSettings, transport=None):
    from catalyst.identity.credentials import CredentialStore
    from catalyst.identity.http import Http
    from catalyst.identity.oidc import OIDCClient
    from catalyst.identity.session import Session

    client = OIDCClient(conf, Http(transport, timeout=conf.timeout))  # type: ignore[arg-type]
    return Session(client, CredentialStore(credentials_path(conf)))


@dataclass(frozen=True)
class Verified:
    """Who the provider says is logged in, now."""

    iss: str
    sub: str
    username: str
    name: str
    provider_roles: tuple[str, ...]


def verify(conf: ProviderSettings, transport=None) -> Verified:
    """The logged-in identity, as the provider confirms it now; ProviderError if there is none."""
    from catalyst.identity.errors import CatalystUsersError, NotLoggedInError

    try:
        s = session(conf, transport)
        claims = s.oidc.userinfo(s.access_token())
    except NotLoggedInError:
        raise ProviderError(
            f"no verified identity: not logged in to {conf.issuer} (`catalyst identity login`)"
        ) from None
    except CatalystUsersError as exc:
        raise ProviderError(f"no verified identity ({exc}): `catalyst identity login`, then try again") from None
    username = str(claims.get("preferred_username") or claims.get("sub"))
    roles = set((claims.get("realm_access") or {}).get("roles") or ()) | set(claims.get("roles") or ())
    given = " ".join(p for p in (claims.get("given_name"), claims.get("family_name")) if p)
    return Verified(
        iss=conf.issuer,
        sub=str(claims["sub"]),
        username=username,
        name=str(claims.get("name") or given or username),
        provider_roles=tuple(sorted(str(r) for r in roles)),
    )


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


def enroll(dep: Deployment, who: Verified) -> dict:
    """The identity's ledger line; appended (and journaled) the first time it signs."""
    from catalyst import journal
    from catalyst.corpus import local_users
    from catalyst.ids import generate_userid

    entries = ledger(dep.root)
    found = find(entries, who.iss, who.sub)
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
        "iss": who.iss,
        "sub": who.sub,
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


# --- roles (fw-IDENTITY-000004) ----------------------------------------------------
def roles_for(roles: list[dict], provider_roles: tuple[str, ...]) -> list[str]:
    """The deployment's roles this identity holds: those whose `provider_role` the provider gives it."""
    held = set(provider_roles)
    return [str(r["name"]) for r in roles if r.get("provider_role") and str(r["provider_role"]) in held]


def unmapped_roles(roles: list[dict]) -> list[str]:
    return [str(r.get("name")) for r in roles if not r.get("provider_role")]


# --- the signer (fw-IDENTITY-000002) ------------------------------------------------
def signer(dep: Deployment, roles: list[dict], as_user_name: str | None = None, transport=None) -> dict:
    """The verified identity signing in an `oidc` deployment, as a user record with its roles now. One that
    has never signed carries `pending` (and no userid) until `enrolled` adds it to the ledger, which the
    caller does only once its roles grant the command."""
    who = verify(settings(dep.pointer), transport)
    held = roles_for(roles, who.provider_roles)
    entry = find(ledger(dep.root), who.iss, who.sub)
    if entry is not None:
        user = as_user(entry, held)
    else:
        user = {"name": who.name, "git_username": who.username, "userid": "", "roles": held, "active": True}
        user.update({"iss": who.iss, "sub": who.sub, "pending": who})
    if as_user_name:
        wanted = as_user_name.strip().lower()
        names = {str(user.get(k, "")).lower() for k in ("name", "git_username", "userid")} | {who.username.lower()}
        if wanted not in names - {""}:
            raise ProviderError(
                f"--as {as_user_name}: you are logged in as {who.username}; with an identity provider you sign "
                "only as yourself (fw-IDENTITY-000002)"
            )
    return user


def enrolled(dep: Deployment, user: dict) -> dict:
    """`user`, with its ledger line written if it had none (`pending`)."""
    who = user.get("pending")
    if who is None:
        return user
    return as_user(enroll(dep, who), list(user.get("roles") or []))
