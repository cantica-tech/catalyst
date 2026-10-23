"""`catalyst serve` with an identity provider (fw-IDENTITY-000005, REQ-000086): the provider's tokens are
accepted by introspection; the signer of a push is the ledger's line for its identity; a push appends
ledger lines for its own identity only, and never changes one."""

from __future__ import annotations

import json
import time

import pytest

from catalyst import serve
from catalyst.identity.errors import ProviderUnavailableError
from catalyst.identity.http import Response
from catalyst_fixtures import USERID, write

ISSUER = "https://id.example.com/realms/catalyst"
DISCOVERY = {
    "issuer": ISSUER,
    "token_endpoint": f"{ISSUER}/token",
    "device_authorization_endpoint": f"{ISSUER}/device",
    "introspection_endpoint": f"{ISSUER}/introspect",
    "userinfo_endpoint": f"{ISSUER}/userinfo",
    "revocation_endpoint": f"{ISSUER}/revoke",
}
ROLES = {
    "roles": [
        {"name": "Admin", "actions": [], "reconciliation": "full", "provider_role": "catalyst-admin"},
        {"name": "Developer", "actions": [], "reconciliation": "propose", "provider_role": "developer"},
    ]
}


def _claims(sub: str, **over) -> dict:
    return {
        "active": True,
        "iss": ISSUER,
        "aud": ["catalyst-api"],
        "sub": sub,
        "exp": time.time() + 300,
        "realm_access": {"roles": ["developer"]},
        **over,
    }


class Provider:
    def __init__(self):
        self.tokens = {"tok-carol": _claims("sub-carol"), "tok-dan": _claims("sub-dan")}
        self.introspected = 0
        self.down = False

    def __call__(self, request, timeout):
        if self.down:
            raise ProviderUnavailableError("identity provider unreachable")
        if request.url.endswith("openid-configuration"):
            return Response(200, {}, json.dumps(DISCOVERY).encode())
        if request.url.endswith("/introspect"):
            assert request.headers["Authorization"].startswith("Basic ")
            self.introspected += 1
            token = dict(p.split("=", 1) for p in request.body.decode().split("&"))["token"]
            return Response(200, {}, json.dumps(self.tokens.get(token, {"active": False})).encode())
        return Response(404, {}, b"{}")


def _blob(text: str) -> tuple[str, bytes]:
    data = text.encode("utf-8")
    return serve.blob_sha(data), data


def _line(sub: str, userid: str, username: str) -> str:
    entry = {"userid": userid, "iss": ISSUER, "sub": sub, "username": username, "name": username.title()}
    return json.dumps({**entry, "first_signed": "2026-10-23"}) + "\n"


def _entry(actor: str, files: list[tuple[str, str | None, str]]) -> str:
    return json.dumps(
        {
            "timestamp": "2026-10-23T00:00:00Z",
            "actor": actor,
            "command": "/x",
            "action": "update",
            "artifact": "x",
            "targets": [],
            "intent": ["x"],
            "files": [{"path": serve.WC + p, "before": b, "after": a} for p, b, a in files],
            "writer": "catalyst/0.105.0",
        }
    )


@pytest.fixture
def seeded(tmp_path):
    """A server accepting the provider's tokens, holding users, roles and an empty ledger."""
    provider = Provider()
    app = serve.Server(tmp_path / "s.db", serve.ProviderTokens(ISSUER, "catalyst-api", "secret", provider))
    users = {"users": [{"name": "Ada", "git_username": "ada", "roles": ["Admin"], "active": True, "userid": USERID}]}
    files = {"IAM/users/users.json": json.dumps(users), "IAM/roles/roles.json": json.dumps(ROLES)}
    blobs = dict(_blob(t) for t in files.values())
    changes = [{"path": p, "before": None, "after": serve.blob_sha(t.encode())} for p, t in files.items()]
    app.push(USERID, 0, changes, blobs)
    return app, provider


def _push(app, principal, actor: str, ledger_before: str | None, ledger_after: str | None, base: int = 1):
    """One push: a note, its journal entry, and optionally the ledger's new version."""
    note, ndata = _blob(f"by {actor}\n")
    path = f"notes-{actor}-{base}.md"
    files: list[tuple[str, str | None, str]] = [(path, None, note)]
    changes = [{"path": path, "before": None, "after": note}]
    blobs = {note: ndata}
    if ledger_after is not None:
        after, adata = _blob(ledger_after)
        before = serve.blob_sha(ledger_before.encode()) if ledger_before else None
        files.append((serve.SIGNERS, before, after))
        changes.append({"path": serve.SIGNERS, "before": before, "after": after})
        blobs[after] = adata
    entry, edata = _blob(_entry(actor, files) + "\n")
    changes.append({"path": f"development/journal/{actor}@m{base}/2026-10.jsonl", "before": None, "after": entry})
    blobs[entry] = edata
    return app.push(principal, base, changes, blobs)


def test_a_providers_token_is_accepted_only_when_introspection_says_so(seeded):
    app, provider = seeded
    assert app.user_for("tok-carol")["sub"] == "sub-carol"
    assert app.user_for("tok-carol")["sub"] == "sub-carol"
    assert provider.introspected == 1  # cached
    assert app.user_for("tok-forged") is None
    assert app.user_for("cst_unknown") is None  # a server token is never sent to the provider
    provider.tokens["tok-other-audience"] = _claims("sub-x", aud="account")
    provider.tokens["tok-other-issuer"] = _claims("sub-x", iss="https://evil.example.com/realms/catalyst")
    assert app.user_for("tok-other-audience") is None and app.user_for("tok-other-issuer") is None


def test_an_unreachable_provider_is_503(seeded):
    app, provider = seeded
    provider.down = True
    with pytest.raises(serve.ServeError) as err:
        app.user_for("tok-dan")
    assert err.value.status == 503


def test_the_signer_is_the_ledger_line_of_the_tokens_identity(seeded):
    app, _ = seeded
    carol = app.user_for("tok-carol")
    with pytest.raises(serve.ServeError, match="sign once with the CLI") as err:
        _push(app, carol, "carol", None, None)
    assert err.value.status == 403
    ledger = _line("sub-carol", "Ca12Rl34", "carol")
    assert _push(app, carol, "carol", None, ledger)["seq"] == 2
    with pytest.raises(serve.ServeError, match="this token is"):
        _push(app, carol, "ada", ledger, None, base=2)  # an entry signed for someone else


def test_a_push_appends_ledger_lines_for_its_own_identity_only(seeded):
    app, _ = seeded
    carol, dan = app.user_for("tok-carol"), app.user_for("tok-dan")
    mine = _line("sub-carol", "Ca12Rl34", "carol")
    with pytest.raises(serve.ServeError, match="its own identity only"):
        _push(app, carol, "carol", None, mine + _line("sub-dan", "Da12Nn34", "dan"))
    assert _push(app, carol, "carol", None, mine)["seq"] == 2
    both = mine + _line("sub-dan", "Da12Nn34", "dan")
    assert _push(app, dan, "dan", mine, both, base=2)["seq"] == 3
    with pytest.raises(serve.ServeError, match="append-only"):
        _push(app, dan, "dan", both, _line("sub-dan", "Da12Nn34", "dan"), base=3)


def test_the_first_push_imports_every_signers_line(tmp_path):
    provider = Provider()
    app = serve.Server(tmp_path / "s.db", serve.ProviderTokens(ISSUER, "catalyst-api", "secret", provider))
    both = _line("sub-carol", "Ca12Rl34", "carol") + _line("sub-dan", "Da12Nn34", "dan")
    first = _push(app, app.user_for("tok-carol"), "carol", None, both, base=0)
    assert first["seq"] == 1  # an import: dan's line comes with carol's
    with pytest.raises(serve.ServeError, match="its own identity only"):
        _push(app, app.user_for("tok-carol"), "carol", both, both + _line("sub-eve", "Ev12Ee34", "eve"))


def test_a_providers_signer_holds_its_mapped_roles(seeded):
    roles = json.dumps(ROLES).encode()
    user = serve._provider_user(_line("sub-carol", "Ca12Rl34", "carol").encode(), None, roles, _claims("sub-carol"))
    assert (user["userid"], user["git_username"], user["roles"]) == ("Ca12Rl34", "carol", ["Developer"])


def test_an_oidc_client_sends_its_provider_token(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from catalyst import provider

    monkeypatch.delenv("CATALYST_TOKEN", raising=False)
    dep = SimpleNamespace(
        root=tmp_path, pointer={"identity": "oidc", "identity_issuer": ISSUER, "share_url": "http://127.0.0.1:1"}
    )
    monkeypatch.setattr(provider, "session", lambda conf, transport=None: SimpleNamespace(access_token=lambda: "at-1"))
    assert serve.ServeShare(dep).client().token == "at-1"
    write(tmp_path / "x", "")  # a local deployment keeps the server's own token
    dep.pointer = {"share_url": "http://127.0.0.1:1"}
    monkeypatch.setattr(serve, "token_for", lambda url: "cst_mine")
    assert serve.ServeShare(dep).client().token == "cst_mine"
