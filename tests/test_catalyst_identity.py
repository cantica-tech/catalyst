"""People through catalyst-users (design 29, ADR-000049, REQ-000087): a criterion points at catalyst-users
(`IAM/identity.json`, fw-IDENTITY-000007); the signer is the identity catalyst-users verifies (fw-IDENTITY-000002),
recorded once in the append-only signers ledger (fw-IDENTITY-000003); its grants decide what it may do
(fw-IDENTITY-000008); it is kept per machine as a read-only snapshot (fw-IDENTITY-000009); with no one logged in, the
machine's system account signs (design 29 §3.4a)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qsl

import pytest

import schema_check
from catalyst import check, criterion, gates, provider
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst.identity.provider import Whoami
from catalyst_fixtures import USERID, journal_entries, write
from test_catalyst_history import _project

ISSUER = "https://id.example.com/realms/catalyst"
POINTER = {"provider": "keycloak", "issuer": ISSUER}
RULE = f"br-AUTH-000001-{USERID}"
FIELDS = ["--field", f"Targets={RULE}", "--field", "Domain=AUTH"]
TEMPLATE = {  # how roles are shown (fw-IDENTITY-000010); what they grant is the provider's
    "roles": [
        {"name": "Admin", "id": "catalyst-admin", "actions": []},
        {"name": "Developer", "id": "developer", "actions": []},
        {"name": "Reviewer", "id": "reviewer", "actions": []},
    ]
}
ALICE = Whoami(
    ISSUER,
    "sub-alice",
    "alice",
    "Alice Developer",
    groups=("/team",),
    roles=("developer", "reviewer"),
    grants=("cmd:*", "reconcile:propose"),
)
BOB = Whoami(ISSUER, "sub-bob", "bob", "Bob Reviewer", roles=("reviewer",), grants=("cmd:approve",))


@pytest.fixture
def deployment(tmp_path, monkeypatch, capsys):
    """A deployment pointing at catalyst-users, and a switch for who the provider says is logged in."""
    project = _project(tmp_path)
    root = project / ".criterion"
    write(root / "IAM" / "identity.json", json.dumps(POINTER))
    write(root / "IAM" / "roles" / "templates" / "TEMPLATE-ROLES-v9.json", json.dumps(TEMPLATE))
    monkeypatch.chdir(project)
    who = {"now": ALICE}

    def verify(doc, as_user=None, transport=None):
        if who["now"] is None:
            raise provider.ProviderError(f"no verified identity: not logged in to {ISSUER} (`catalyst identity login`)")
        assert doc["issuer"] == ISSUER
        return who["now"]

    monkeypatch.setattr(provider, "verify", verify)
    capsys.readouterr()
    return project, who


def _ledger(project: Path) -> list[dict]:
    return provider.ledger(project / ".criterion")


# --- the pointer (fw-IDENTITY-000007) -------------------------------------------------------
def test_check_reports_a_bad_pointer_and_warns_of_the_static_provider(tmp_path):
    project = _project(tmp_path)
    path = project / ".criterion" / "IAM" / "identity.json"
    for doc, expected in (
        ("[]", "is not a JSON object"),
        (json.dumps({"provider": "ldap"}), "unknown provider 'ldap'"),
        (json.dumps({"provider": "keycloak"}), 'needs a "url"'),
    ):
        write(path, doc)
        assert any(expected in e for e in check.run(load(project)).errors), expected
    write(path, json.dumps({"provider": "static"}))
    assert any("static provider verifies nobody" in w for w in check.run(load(project)).warnings)


def test_configure_writes_the_pointer_signed_by_the_identity_it_reaches(deployment, capsys):
    project, _ = deployment
    path = project / ".criterion" / "IAM" / "identity.json"
    path.unlink()
    assert main(["identity", "configure", "--issuer", ISSUER + "/", "--intent", "the company's Keycloak"]) == 0
    assert json.loads(path.read_text(encoding="utf-8")) == POINTER
    [*_, configured] = journal_entries(project / ".criterion")
    assert (configured["command"], configured["actor"], configured["intent"]) == (
        "catalyst identity",
        "alice",
        ["the company's Keycloak"],
    )


def test_init_points_at_this_machines_catalyst_users_by_default():
    """Without --identity-issuer, the provider this machine's catalyst-users is set up for (catalyst-users 0.4.0),
    its connection settings only: never its admin or password command."""
    from catalyst.__main__ import _identity_doc
    from catalyst.identity import config as users_config

    assert _identity_doc(SimpleNamespace(identity_issuer=None)) is None  # catalyst-users not set up
    users_config.write_settings(
        {
            "type": "keycloak",
            "username": "owner",
            "provider": {"url": "https://id.example.com", "realm": "catalyst", "client": "catalyst-cli"},
            "password_command": "get-password",
        }
    )
    assert _identity_doc(SimpleNamespace(identity_issuer=None)) == {
        "provider": "keycloak",
        "url": "https://id.example.com",
        "realm": "catalyst",
        "client": "catalyst-cli",
    }


# --- verified signers (fw-IDENTITY-000002) -------------------------------------------------
def test_the_signer_is_the_verified_identity(deployment, capsys):
    project, _ = deployment
    assert main(["new", "ITEM", "--title", "Signed", *FIELDS, "--intent", "a verified item"]) == 0
    item = capsys.readouterr().out.split()[0]
    [line] = _ledger(project)
    assert (line["iss"], line["sub"], line["username"], line["name"]) == (
        ISSUER,
        "sub-alice",
        "alice",
        "Alice Developer",
    )
    assert item.endswith(line["userid"]) and line["userid"] != USERID
    entries = journal_entries(project / ".criterion")
    enrolled, created = entries[-2], entries[-1]
    assert (enrolled["command"], enrolled["actor"], enrolled["tier"]) == ("catalyst identity", "alice", "chore")
    assert enrolled["files"][0]["path"].endswith("IAM/signers.jsonl")
    assert created["actor"] == "alice" and created["artifact"] == item
    assert main(["status", "set", item, "Done", "--intent", "done"]) == 0  # a second signature reuses the line
    assert len(_ledger(project)) == 1


def test_as_names_only_the_logged_in_identity(deployment, capsys):
    assert main(["new", "ITEM", "--title", "Mine", "--as", "alice", *FIELDS]) == 0
    capsys.readouterr()
    assert main(["new", "ITEM", "--title", "Theirs", "--as", "ada", *FIELDS]) == 1
    assert "you sign only as yourself" in capsys.readouterr().err


def test_no_verified_identity_signs_nothing_but_reads_work(deployment, capsys):
    project, who = deployment
    who["now"] = None
    assert main(["new", "ITEM", "--title", "Offline", *FIELDS]) == 1
    assert "catalyst identity login" in capsys.readouterr().err
    assert _ledger(project) == []
    assert main(["list", "ITEM"]) == 0


def test_a_refused_command_enrolls_nobody(deployment, capsys, monkeypatch):
    """Refused before it signs (grants decide: test_catalyst_permissions), an identity gets no ledger line."""
    from catalyst import permissions

    project, who = deployment
    who["now"] = Whoami(ISSUER, "sub-sam", "sam", "Sam", roles=("developer",), grants=("cmd:status",))
    monkeypatch.setattr(permissions, "refusal", lambda dep, user, command, also=(): f"{user['name']} may not run /new")
    assert main(["new", "ITEM", "--title", "Refused", *FIELDS]) == 1
    assert "may not run" in capsys.readouterr().err
    assert _ledger(project) == []


def test_people_and_roles_are_changed_in_catalyst_users(deployment, capsys):
    for argv in (["user", "add", "Grace", "Developer"], ["role", "add", "Auditor", "--action", "/journal"]):
        assert main(argv) == 1
        assert "catalyst-users" in capsys.readouterr().err


def test_a_taken_username_is_suffixed(deployment, capsys):
    project, who = deployment
    who["now"] = Whoami(ISSUER, "sub-other-ada", "ada", "Another Ada", grants=("cmd:*",))
    assert main(["new", "ITEM", "--title", "Clash", *FIELDS]) == 0
    [line] = _ledger(project)
    assert line["username"] == f"ada-{line['userid']}"


def test_whoami_shows_roles_by_the_template_and_the_grants(deployment, capsys):
    assert main(["identity", "whoami", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["userid"] is None and payload["roles"] == ["Developer", "Reviewer"]
    assert (payload["groups"], payload["grants"], payload["reconciliation"]) == (
        ["/team"],
        ["cmd:*", "reconcile:propose"],
        "propose",
    )
    assert schema_check.problems(payload, schema_check.load("identity-whoami")) == []
    assert main(["identity", "status", "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status == {"provider": "keycloak", "issuer": ISSUER, "logged_in": False}
    assert schema_check.problems(status, schema_check.load("identity-status")) == []


# --- the ledger (fw-IDENTITY-000003) --------------------------------------------------------
def test_check_reports_a_broken_or_rewritten_ledger(deployment, capsys):
    project, _ = deployment
    assert main(["new", "ITEM", "--title", "Signed", *FIELDS]) == 0
    capsys.readouterr()
    path = project / ".criterion" / provider.SIGNERS
    good = path.read_text(encoding="utf-8")
    twin = {**json.loads(good), "sub": "someone-else"}
    write(path, good + "not json\n" + json.dumps({"userid": "x"}) + "\n" + json.dumps(twin) + "\n")
    found = provider.ledger_problems(project / ".criterion")
    assert any("not a JSON line" in p for p in found) and any("missing iss" in p for p in found)
    assert any("names two identities" in p for p in found)
    write(path, "")  # the journaled line removed
    assert any("changed or removed" in e for e in check.run(load(project)).errors)


def test_a_shared_criterion_merges_the_ledger_by_union(deployment):
    project, _ = deployment
    assert "IAM/signers.jsonl" in criterion.attribute_paths(load(project))


def test_an_approval_counts_with_the_roles_it_recorded(deployment, capsys):
    project, who = deployment
    write(
        project / ".criterion" / gates.GATES,
        json.dumps(
            {
                "gates": [
                    {"id": "item-done", "covers": {"type": "ITEM", "to": "Done"}, "approvals": 1, "role": "Reviewer"}
                ]
            }
        ),
    )
    assert main(["new", "ITEM", "--title", "Gated", *FIELDS]) == 0
    item = capsys.readouterr().out.split()[0]
    assert main(["approve", item, "--gate", "item-done"]) == 1  # alice wrote it
    assert "never approves their own change" in capsys.readouterr().err
    who["now"] = BOB
    assert main(["approve", item, "--gate", "item-done", "--intent", "reviewed", "--json"]) == 0
    entry = json.loads(capsys.readouterr().out)
    assert entry["roles"] == ["Reviewer"] and entry["actor"] == "bob" and entry["missing"] == 0
    assert schema_check.problems(entry, schema_check.load("approve")) == []
    dep = load(project)
    gate = gates.load(dep, load_corpus(dep))[0]
    assert gates.counted(dep, load_corpus(dep), gate, item) == (["bob"], 0)


# --- the snapshot (fw-IDENTITY-000009) ------------------------------------------------------
def test_each_signature_writes_a_read_only_snapshot_and_an_edited_one_is_discarded(deployment, capsys):
    project, _ = deployment
    assert main(["new", "ITEM", "--title", "Signed", *FIELDS]) == 0
    doc = provider.pointer(load(project))
    snap = provider.read_snapshot(doc)
    assert (snap["username"], snap["grants"], snap["roles"]) == (
        "alice",
        ["cmd:*", "reconcile:propose"],
        ["Developer", "Reviewer"],
    )
    assert snap["userid"] == _ledger(project)[0]["userid"]
    path = provider.snapshot_path(doc)
    if sys.platform != "win32":
        assert oct(path.stat().st_mode & 0o777) == "0o400"
    path.chmod(0o600)
    edited = {**json.loads(path.read_text(encoding="utf-8")), "roles": ["Admin"]}
    path.write_text(json.dumps(edited), encoding="utf-8")
    assert provider.read_snapshot(doc) is None and not path.exists()  # never trusted: its owner signs in anew


# --- the provider, through the vendored facade ---------------------------------------------
DISCOVERY = {
    "issuer": ISSUER,
    **{k: f"{ISSUER}/{k}" for k in ("token_endpoint", "device_authorization_endpoint", "userinfo_endpoint")},
    **{k: f"{ISSUER}/{k}" for k in ("introspection_endpoint", "revocation_endpoint")},
}


def _keycloak(claims_by_token: dict[str, dict], passwords: dict[str, str] | None = None):
    """A provider answering discovery, userinfo by bearer token, and the password grant."""
    from catalyst.identity.http import Response

    def transport(request, timeout):
        if request.url.endswith("openid-configuration"):
            return Response(200, {}, json.dumps(DISCOVERY).encode())
        if request.url.endswith("userinfo_endpoint"):
            token = request.headers.get("Authorization", "").removeprefix("Bearer ")
            found = claims_by_token.get(token)
            return Response(200, {}, json.dumps(found).encode()) if found else Response(401, {}, b"{}")
        if request.url.endswith("token_endpoint"):
            form = dict(parse_qsl((request.body or b"").decode()))
            if form.get("grant_type") == "password" and (passwords or {}).get(form.get("username")) == form.get(
                "password"
            ):
                body = {"access_token": f"at-{form['username']}", "expires_in": 300}
                return Response(200, {}, json.dumps(body).encode())
            return Response(401, {}, json.dumps({"error": "invalid_grant"}).encode())
        return Response(404, {}, b"{}")

    return transport


def test_verify_asks_the_provider(tmp_path):
    import time

    from catalyst.identity.credentials import CredentialStore
    from catalyst.identity.oidc import Tokens

    claims = {"sub": "s1", "preferred_username": "alice", "name": "Alice", "realm_access": {"roles": ["developer"]}}
    transport = _keycloak({"at": claims})
    with pytest.raises(provider.ProviderError, match="catalyst identity login"):
        provider.verify(POINTER, None, transport)  # no tokens yet, and no system account
    path = provider.credentials_path(POINTER)
    CredentialStore(path).save(ISSUER, "catalyst-cli", Tokens("at", "rt", time.time() + 300))
    who = provider.verify(POINTER, None, transport)
    assert (who.issuer, who.subject, who.username, who.roles) == (ISSUER, "s1", "alice", ("developer",))


def _system_account(realm: str = "catalyst") -> None:
    from catalyst.identity import config as users_config

    users_config.write_settings(
        {
            "type": "keycloak",
            "username": "sysadmin",
            "provider": {"url": "https://id.example.com", "realm": realm, "password_client": "catalyst-admin-cli"},
            "password_command": [sys.executable, "-c", "print('sys-pw')"],
        }
    )


def test_with_no_one_logged_in_the_machines_system_account_signs(capsys):
    """Design 29 §3.4a: no person logged in, the admin of this machine's catalyst-users (0.4.0) signs, and says so."""
    claims = {
        "sub": "sub-sys",
        "preferred_username": "sysadmin",
        "name": "System",
        "resource_access": {"catalyst": {"roles": ["cmd:*"]}},
    }
    transport = _keycloak({"at-sysadmin": claims}, {"sysadmin": "sys-pw"})
    _system_account()
    who = provider.verify(POINTER, None, transport)
    assert (who.username, who.subject, who.grants) == ("sysadmin", "sub-sys", ("cmd:*",))
    assert "signing as the system account sysadmin" in capsys.readouterr().err
    with pytest.raises(provider.ProviderError, match="not logged in"):
        provider.verify(POINTER, "alice", transport)  # --as a person: never the system account for them


def test_the_system_account_of_another_provider_never_signs():
    _system_account(realm="other")
    with pytest.raises(provider.ProviderError, match="not logged in"):
        provider.verify(POINTER, None, _keycloak({}, {"sysadmin": "sys-pw"}))


def test_the_zipapp_stays_standard_library_only():
    scripts = str(Path(__file__).resolve().parents[1] / "scripts")
    modules = "catalyst.provider, catalyst.identity.session, catalyst.identity.providers.keycloak"
    code = f"import sys; sys.path.insert(0, {scripts!r}); import {modules}"
    assert subprocess.run([sys.executable, "-I", "-S", "-c", code], capture_output=True, check=False).returncode == 0
