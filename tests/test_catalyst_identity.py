"""People through catalyst-users (design 29, ADR-000049, REQ-000087): a criterion points at catalyst-users
(`IAM/identity.json`, fw-IDENTITY-000007); the signer is the identity catalyst-users verifies (fw-IDENTITY-000002),
recorded once in the append-only signers ledger (fw-IDENTITY-000003); its grants decide what it may do
(fw-IDENTITY-000008); it is kept per machine as a read-only snapshot (fw-IDENTITY-000009); with no one logged in, the
machine's system account signs (design 29 §3.4a)."""

from __future__ import annotations

import json
import os
import shlex
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
    assert _identity_doc(SimpleNamespace(identity_issuer=None)) == {  # in the pointer's one shape (BUG-000057)
        "provider": "keycloak",
        "issuer": "https://id.example.com/realms/catalyst",
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
    assert status == {"provider": "keycloak", "issuer": ISSUER, "logged_in": False, "session": "none"}
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
    assert provider.verify(POINTER, "System", transport).username == "sysadmin"  # --as by its name, too
    with pytest.raises(provider.ProviderError, match=r"no verified identity for alice: .* system account is sysadmin"):
        provider.verify(POINTER, "alice", transport)  # --as a person: never the system account for them


def test_the_system_account_of_another_provider_never_signs():
    _system_account(realm="other")
    with pytest.raises(provider.ProviderError, match="not logged in"):
        provider.verify(POINTER, None, _keycloak({}, {"sysadmin": "sys-pw"}))


def test_the_system_account_is_found_at_another_spelling_of_its_provider(capsys):
    """BUG-000058: catalyst-users' settings at `localhost`, the pointer at `127.0.0.1/`: one provider, so the system
    account signs, reached at the pointer's spelling (`system_pointer`)."""
    from catalyst.identity import config as users_config

    users_config.write_settings(
        {
            "type": "keycloak",
            "username": "sysadmin",
            "provider": {"url": "http://localhost:8080", "realm": "catalyst"},
            "password_command": [sys.executable, "-c", "print('sys-pw')"],
        }
    )
    claims = {"sub": "sub-sys", "preferred_username": "sysadmin", "name": "System"}
    spelled = "http://127.0.0.1:8080/realms/catalyst"
    system = provider.system_backend(spelled + "/")
    assert system is not None and system.issuer == spelled
    assert provider.system_backend("http://localhost:8080/realms/other") is None
    from catalyst.identity.http import Response

    seen = []
    keycloak = _keycloak({"at-sysadmin": claims}, {"sysadmin": "sys-pw"})
    discovery = {k: str(v).replace(ISSUER, spelled) for k, v in DISCOVERY.items()}

    def transport(request, timeout):
        seen.append(request.url)
        if request.url.endswith("openid-configuration"):
            return Response(200, {}, json.dumps(discovery).encode())
        return keycloak(request, timeout)

    who = provider.verify({"provider": "keycloak", "issuer": spelled}, None, transport)
    assert who.username == "sysadmin"
    assert seen and all(url.startswith(spelled) for url in seen)  # the caller's spelling, never the settings'


# --- one shape, one login per provider (BUG-000057, REQ-000107, REQ-000108) ---------------------
def test_both_pointer_shapes_and_loopback_spellings_share_one_login():
    by_url = {"provider": "keycloak", "url": "http://127.0.0.1:8080/", "realm": "catalyst", "client": "c"}
    by_issuer = {"provider": "keycloak", "issuer": "http://localhost:8080/realms/catalyst/", "client": "c"}
    assert provider.normalised(by_url) == {
        "provider": "keycloak",
        "issuer": "http://127.0.0.1:8080/realms/catalyst",
        "client": "c",
    }
    assert provider.credentials_path(by_url) == provider.credentials_path(by_issuer)
    assert provider.credentials_path(by_issuer) != provider.credentials_path({**by_issuer, "client": "other"})
    assert provider.snapshot_path(by_url) == provider.snapshot_path(by_issuer)


def test_check_warns_of_a_pointer_named_by_url_and_realm(tmp_path):
    project = _project(tmp_path)
    write(project / ".criterion" / "IAM" / "identity.json", json.dumps({"provider": "keycloak", "url": "http://k"}))
    errors, warnings = provider.problems(load(project))
    assert errors == [] and any("catalyst migrate --apply" in w for w in warnings)


def test_the_ledger_counts_spellings_of_one_provider_as_one_person(deployment, capsys):
    """BUG-000057: the person is iss + sub, the issuer compared as one provider is named; the first spelling stays."""
    project, who = deployment
    local = "http://localhost:8080/realms/catalyst"
    who["now"] = Whoami(local, "sub-ada", "ada", "Ada", grants=("cmd:*",))
    assert main(["new", "ITEM", "--title", "From localhost", *FIELDS]) == 0
    who["now"] = Whoami("http://127.0.0.1:8080/realms/catalyst/", "sub-ada", "ada", "Ada", grants=("cmd:*",))
    assert main(["new", "ITEM", "--title", "From 127.0.0.1", *FIELDS]) == 0
    [line] = _ledger(project)
    assert line["iss"] == local
    assert provider.find(_ledger(project), "HTTP://127.0.0.1:8080/realms/catalyst", "sub-ada") == line
    assert provider.find(_ledger(project), "http://localhost:8080/realms/other", "sub-ada") is None
    signers = project / ".criterion" / "IAM" / "signers.jsonl"
    twin = {**line, "iss": "http://127.0.0.1:8080/realms/catalyst"}
    signers.write_text(signers.read_text(encoding="utf-8") + json.dumps(twin) + "\n", encoding="utf-8")
    assert provider.ledger_problems(project / ".criterion") == []  # one identity, spelled twice


def _with_transport(monkeypatch, transport) -> None:
    real = provider.facade
    monkeypatch.setattr(provider, "facade", lambda doc, transport_=None: real(doc, transport))


def test_login_with_a_password_from_stdin_or_a_command(monkeypatch, capsys):
    """REQ-000107 (catalyst-users 0.11.0's id-AUTH-000007): `identity login --password` reads the password from
    standard input or `--password-command`, never an argument, and logs in through the password client."""
    import io

    claims = {"sub": "s-alice", "preferred_username": "alice", "name": "Alice"}
    _with_transport(monkeypatch, _keycloak({"at-alice": claims}, {"alice": "s3cret"}))
    monkeypatch.setattr("sys.stdin", io.StringIO("s3cret\n"))
    assert main(["identity", "login", "--issuer", ISSUER, "--password", "--username", "alice", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["username"] == "alice"
    assert provider.logged_in(POINTER)
    assert main(["identity", "logout", "--issuer", ISSUER]) == 0
    assert not provider.logged_in(POINTER)
    argv = [sys.executable, "-c", "print('s3cret')"]
    # quoted by the platform's rules (catalyst-users 0.11.1's split_command): a Windows path keeps its backslashes
    command = subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    args = ["identity", "login", "--issuer", ISSUER, "--password", "--username", "alice", "--password-command", command]
    assert main(args) == 0
    assert "alice (Alice)" in capsys.readouterr().out
    monkeypatch.setattr("sys.stdin", io.StringIO("wrong\n"))
    assert main(["identity", "login", "--issuer", ISSUER, "--password", "--username", "alice"]) == 1
    monkeypatch.setattr("sys.stdin", io.StringIO("s3cret\n"))
    assert main(["identity", "login", "--issuer", ISSUER, "--password"]) == 1  # no terminal: --username is needed
    assert "needs --username" in capsys.readouterr().err


def test_one_login_serves_catalyst_users_and_catalyst_for_the_same_provider(monkeypatch, capsys):
    """REQ-000108: catalyst-users set up for the pointer's provider (same spelling, same login client): the kernel
    keeps its tokens in catalyst-users' credentials file, so either tool's login is the other's. Another provider
    keeps catalyst's own file."""
    import io

    from catalyst.identity import config as users_config
    from catalyst.identity.credentials import CredentialStore

    users_config.write_settings(
        {"type": "keycloak", "provider": {"url": "https://id.example.com", "realm": "catalyst"}}
    )
    shared = users_config.home() / "credentials.json"
    assert provider.token_store(POINTER) == shared
    assert provider.token_store({**POINTER, "client": "another-cli"}) == provider.credentials_path(
        {**POINTER, "client": "another-cli"}
    )
    other = {"provider": "keycloak", "issuer": "https://id.example.com/realms/other"}
    assert provider.token_store(other) == provider.credentials_path(other)
    claims = {"sub": "s-alice", "preferred_username": "alice", "name": "Alice"}
    _with_transport(monkeypatch, _keycloak({"at-alice": claims}, {"alice": "s3cret"}))
    monkeypatch.setattr("sys.stdin", io.StringIO("s3cret\n"))
    assert main(["identity", "login", "--issuer", ISSUER, "--password", "--username", "alice"]) == 0
    assert CredentialStore(shared).load(ISSUER, "catalyst-admin-cli") is not None  # catalyst-users reads this login
    assert not provider.credentials_path(POINTER).exists()
    capsys.readouterr()
    assert main(["identity", "status", "--issuer", ISSUER, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["logged_in"] is True


def test_the_session_start_says_once_who_signs_when_no_one_is_logged_in(deployment, monkeypatch, capsys):
    """REQ-000109: `hook start` (even `--quiet`) says when no one is logged in, and who would sign: the system
    account, or nobody. Nothing when someone is."""
    import io
    import time

    from catalyst.identity.credentials import CredentialStore
    from catalyst.identity.oidc import Tokens

    project, _ = deployment

    def start(*extra: str) -> str:
        monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
        capsys.readouterr()
        assert main(["--project", str(project), "hook", "start", *extra]) == 0
        return capsys.readouterr().out

    assert "no system account can sign" in start("--quiet")
    _system_account()
    out = start("--quiet")
    assert "signed by the system account sysadmin" in out and out.count("no one is logged in") == 1
    assert "signed by the system account sysadmin" in start()
    CredentialStore(provider.token_store(POINTER)).save(ISSUER, "catalyst-cli", Tokens("at", "rt", time.time() + 300))
    assert start("--quiet") == ""
    assert "no one is logged in" not in start()


def test_the_zipapp_stays_standard_library_only():
    scripts = str(Path(__file__).resolve().parents[1] / "scripts")
    modules = "catalyst.provider, catalyst.identity.session, catalyst.identity.providers.keycloak"
    code = f"import sys; sys.path.insert(0, {scripts!r}); import {modules}"
    assert subprocess.run([sys.executable, "-I", "-S", "-c", code], capture_output=True, check=False).returncode == 0


# --- keeping a userid across the move (migration 0.106.0) ----------------------------------
def test_link_keeps_a_retired_users_userid_for_that_person_only(deployment, capsys):
    """`catalyst identity link`: the verified identity takes the userid it had in the retired registry, once, so
    the IDs it creates keep ending with it; nobody else may take it."""
    project, who = deployment
    who["now"] = Whoami(ISSUER, "sub-ada", "ada", "Ada Lovelace", grants=("cmd:*",))
    assert main(["identity", "link", "ada"]) == 0
    assert capsys.readouterr().out.strip() == f"ada signs with userid {USERID}"
    [line] = _ledger(project)
    assert (line["userid"], line["iss"], line["sub"]) == (USERID, ISSUER, "sub-ada")
    assert journal_entries(project / ".criterion")[-1]["command"] == "catalyst identity link"
    assert main(["new", "ITEM", "--title", "Still mine", *FIELDS]) == 0
    assert capsys.readouterr().out.split()[0].endswith(USERID)  # the same suffix as before the move
    assert main(["identity", "link", "ada"]) == 1  # once
    assert "never rewritten" in capsys.readouterr().err
    who["now"] = Whoami(ISSUER, "sub-other", "ada", "Ada Lovelace", grants=("cmd:*",))
    assert main(["identity", "link", "ada"]) == 1  # one identity per userid
    assert "already linked" in capsys.readouterr().err


def test_link_refuses_someone_who_is_not_the_retired_user(deployment, capsys):
    project, who = deployment
    who["now"] = Whoami(ISSUER, "sub-mallory", "mallory", "Mallory", grants=("cmd:*",))
    assert main(["identity", "link", "ada"]) == 1
    assert "taken only by them" in capsys.readouterr().err
    assert main(["identity", "link", "nobody"]) == 1
    assert "no retired user 'nobody'" in capsys.readouterr().err
    assert _ledger(project) == []


def test_configure_can_link_before_its_own_signature(deployment, capsys):
    """Moving a deployment: configure's own signature would draw a new userid, so --link keeps the old one first."""
    project, who = deployment
    (project / ".criterion" / "IAM" / "identity.json").unlink()
    who["now"] = Whoami(ISSUER, "sub-ada", "ada", "Ada Lovelace", grants=("cmd:*",))
    assert main(["identity", "configure", "--issuer", ISSUER, "--link", "ada", "--intent", "moving to Keycloak"]) == 0
    [line] = _ledger(project)
    assert line["userid"] == USERID
    assert journal_entries(project / ".criterion")[-1]["actor"] == "ada"


# --- a criterion's admins (fw-IDENTITY-000011) -----------------------------------------------
def test_a_criterion_admin_holds_every_grant_in_their_criterion(deployment, capsys):
    project, who = deployment
    name = load(project).pointer["project_name"]
    who["now"] = Whoami(ISSUER, "sub-kim", "kim", "Kim Admin", roles=("criterion-admin",), administers=(name,))
    assert main(["new", "ITEM", "--title", "By the criterion's admin", *FIELDS]) == 0
    signer = provider.signer(load(project))
    assert (signer["grants"], signer["reconciliation"], signer["administers"]) == (
        ["cmd:*", "reconcile:full"],
        "full",
        [name],
    )
    capsys.readouterr()
    assert main(["identity", "whoami", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["administers"] == [name] and payload["reconciliation"] == "full"
    assert schema_check.problems(payload, schema_check.load("identity-whoami")) == []


def test_administering_another_criterion_grants_nothing_here(deployment, capsys):
    project, who = deployment
    who["now"] = Whoami(ISSUER, "sub-lee", "lee", "Lee Elsewhere", grants=("cmd:status",), administers=("other",))
    signer = provider.signer(load(project))
    assert (signer["grants"], signer["reconciliation"], signer["administers"]) == (["cmd:status"], "none", ["other"])
    assert provider.in_criterion("other", who["now"]) == (["cmd:*", "cmd:status", "reconcile:full"], "full")
    assert provider.in_criterion(load(project).pointer["project_name"], who["now"]) == (["cmd:status"], "none")
    assert provider.in_criterion("other", BOB) == (["cmd:approve"], "none")


def test_catalyst_users_home_is_in_catalysts(tmp_path, monkeypatch):
    """catalyst-users 0.6.0 vendored (REQ-000092): moving catalyst's home moves the system account's settings too."""
    from catalyst.identity import config as users_config

    monkeypatch.delenv("CATALYST_USERS_HOME", raising=False)
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    assert users_config.home() == tmp_path / "home" / "users"
    assert users_config.settings_file() == tmp_path / "home" / "users" / "IAM" / "settings.json"


# --- a lapsed session (BUG-000059) -----------------------------------------------------------
def _jwt(claims: dict) -> str:
    import base64

    part = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"e30.{part}.sig"


def _store(access: str, expires_in: float, refresh_in: float | None, refresh: str | None = "rt") -> None:
    import time

    from catalyst.identity.credentials import CredentialStore
    from catalyst.identity.oidc import Tokens

    now = time.time()
    tokens = Tokens(access, refresh, now + expires_in, None if refresh_in is None else now + refresh_in)
    CredentialStore(provider.token_store(POINTER)).save(ISSUER, "catalyst-cli", tokens)


def test_status_tells_an_expired_session_from_an_active_one(capsys):
    """BUG-000059: `identity status` read stored tokens as logged in whatever their expiry; it now says, without the
    network, whether the session is active, refreshable on next use, or expired."""

    def status(json_out: bool = True):
        capsys.readouterr()
        assert main(["identity", "status", "--issuer", ISSUER, *(["--json"] if json_out else [])]) == 0
        out = capsys.readouterr().out
        return json.loads(out) if json_out else out

    assert (status()["logged_in"], status()["session"]) == (False, "none")
    _store("at", 300, 3600)
    assert (status()["logged_in"], status()["session"]) == (True, "active")
    assert schema_check.problems(status(), schema_check.load("identity-status")) == []
    _store("at", -10, 3600)
    assert status()["session"] == "refreshable"
    _store("at", -10, None)  # a refresh token with no stated expiry: the provider decides
    assert status()["session"] == "refreshable"
    _store("at", -10, -5)
    assert (status()["logged_in"], status()["session"]) == (True, "expired")
    assert "logged in, session expired — run catalyst identity login" in status(json_out=False)
    _store("at", -10, None, refresh=None)
    assert status()["session"] == "expired"


def _refreshing(base, refreshed: dict[str, str], seen: list[str]):
    """`base`, also answering the refresh grant: `refreshed` maps a refresh token to the new access token."""
    from catalyst.identity.http import Response

    def transport(request, timeout):
        if request.url.endswith("token_endpoint"):
            form = dict(parse_qsl((request.body or b"").decode()))
            if form.get("grant_type") == "refresh_token":
                seen.append(form.get("refresh_token", ""))
                new = refreshed.get(form.get("refresh_token", ""))
                if new:
                    body = {"access_token": new, "refresh_token": "rt2", "expires_in": 300, "refresh_expires_in": 1800}
                    return Response(200, {}, json.dumps(body).encode())
                return Response(400, {}, json.dumps({"error": "invalid_grant"}).encode())
        return base(request, timeout)

    return transport


def test_an_expired_access_token_is_refreshed_before_anyone_else_signs(capsys):
    claims = {"sub": "s1", "preferred_username": "alice", "name": "Alice"}
    seen: list[str] = []
    transport = _refreshing(_keycloak({"at-new": claims}), {"rt": "at-new"}, seen)
    _system_account()
    _store(_jwt({"preferred_username": "alice"}), -10, 3600)
    assert provider.verify(POINTER, None, transport).username == "alice"
    assert seen == ["rt"] and "system account" not in capsys.readouterr().err
    assert provider.session_state(POINTER) == "active"  # the refreshed tokens are stored


def test_a_lapsed_session_says_so_and_who_signs_instead(capsys):
    """The person's session lapsed (the refresh is refused): the system account signs, and stderr says whose session
    lapsed and who signs instead — never "no one is logged in"."""
    sys_claims = {"sub": "sub-sys", "preferred_username": "sysadmin", "name": "System"}
    seen: list[str] = []
    transport = _refreshing(_keycloak({"at-sysadmin": sys_claims}, {"sysadmin": "sys-pw"}), {}, seen)
    _system_account()
    _store(_jwt({"preferred_username": "alice"}), -10, -5)
    capsys.readouterr()
    assert provider.verify(POINTER, None, transport).username == "sysadmin"
    err = capsys.readouterr().err
    assert "alice's session at" in err and "has lapsed" in err and "signing as the system account sysadmin" in err
    assert "no one is logged in" not in err and seen == ["rt"]  # the refresh was tried first


def test_a_lapsed_session_with_no_system_account_says_it_lapsed():
    _store("opaque", -10, -5)
    with pytest.raises(provider.ProviderError, match=r"the stored session at .* has lapsed"):
        provider.verify(POINTER, None, _refreshing(_keycloak({}), {}, []))


def test_the_session_start_says_a_session_lapsed(deployment, monkeypatch, capsys):
    import io

    project, _ = deployment
    _system_account()
    _store(_jwt({"preferred_username": "alice"}), -10, -5)
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    capsys.readouterr()
    assert main(["--project", str(project), "hook", "start", "--quiet"]) == 0
    out = capsys.readouterr().out
    assert "alice's session" in out and "has lapsed" in out and "signed by the system account sysadmin" in out
    _store("at", -10, 3600)  # refreshable: nothing to say
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    assert main(["--project", str(project), "hook", "start", "--quiet"]) == 0
    assert capsys.readouterr().out == ""


# --- commands split by the platform's rules (BUG-000062) -------------------------------------
@pytest.mark.parametrize(
    ("windows", "program"), [(True, "C:\\Tools\\print token.exe"), (False, "/opt/tools/print token")]
)
def test_the_landing_token_and_master_key_commands_split_by_the_platform_s_rules(monkeypatch, windows, program):
    """`serve_landing.read_token` and `membership.read_master` split their command with the vendored
    `split_command`, Windows rules on Windows (a path keeps its backslashes), POSIX rules elsewhere; both splitters
    are exercised whatever the runner's OS."""
    import base64

    from catalyst import membership, serve_landing

    key = base64.b64encode(b"k" * 32).decode()
    seen: list[list[str]] = []

    def run(argv, **kw):
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout=key + "\n", stderr="")

    monkeypatch.setattr(serve_landing.subprocess, "run", run)
    monkeypatch.setattr(membership.subprocess, "run", run)
    command = subprocess.list2cmdline([program, "--name", "a b"]) if windows else shlex.join([program, "--name", "a b"])
    assert serve_landing.read_token(command, windows=windows) == key
    assert membership.read_master(command, windows=windows) == b"k" * 32
    assert seen == [[program, "--name", "a b"]] * 2


def test_an_unsplittable_or_empty_command_is_refused_without_running():
    from catalyst import membership, serve_landing

    for bad in ("'unterminated", ""):
        with pytest.raises(serve_landing.LandingError):
            serve_landing.read_token(bad, windows=False)
        with pytest.raises(membership.MembershipError):
            membership.read_master(bad, windows=False)
