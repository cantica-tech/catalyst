"""Identity providers (design 28, ADR-000048, REQ-000086): `local` unchanged; with `oidc` the signer is the
verified identity (fw-IDENTITY-000002), recorded once in the append-only signers ledger
(fw-IDENTITY-000003), holding the roles its provider roles map to (fw-IDENTITY-000004)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import schema_check
from catalyst import check, criterion, gates, provider
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst_fixtures import USERID, journal_entries, write
from test_catalyst_history import _project

ISSUER = "https://id.example.com/realms/catalyst"
RULE = f"br-AUTH-000001-{USERID}"
FIELDS = ["--field", f"Targets={RULE}", "--field", "Domain=AUTH"]
ROLES = {
    "roles": [
        {"name": "Admin", "actions": ["*"], "reconciliation": "full", "provider_role": "catalyst-admin"},
        {"name": "Developer", "actions": ["/new", "/status", "/rename"], "provider_role": "developer"},
        {"name": "Reviewer", "actions": ["/approve"], "provider_role": "reviewer"},
        {"name": "Stakeholder", "actions": []},
    ]
}
ALICE = provider.Verified(ISSUER, "sub-alice", "alice", "Alice Developer", ("developer", "reviewer"))
BOB = provider.Verified(ISSUER, "sub-bob", "bob", "Bob Reviewer", ("reviewer",))


def _pointer(project: Path, **keys) -> None:
    path = project / "app.catalyst"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(keys)
    write(path, json.dumps(data))


@pytest.fixture
def oidc(tmp_path, monkeypatch, capsys):
    """An `oidc` deployment and a switch for who the provider says is logged in."""
    project = _project(tmp_path)
    write(project / ".criterion" / "IAM" / "roles" / "roles.json", json.dumps(ROLES))
    _pointer(project, identity="oidc", identity_issuer=ISSUER)
    monkeypatch.chdir(project)
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    who = {"now": ALICE}

    def verify(conf, transport=None):
        if who["now"] is None:
            raise provider.ProviderError("no verified identity (not logged in): `catalyst identity login`")
        assert conf.issuer == ISSUER
        return who["now"]

    monkeypatch.setattr(provider, "verify", verify)
    capsys.readouterr()
    return project, who


def _ledger(project: Path) -> list[dict]:
    return provider.ledger(project / ".criterion")


# --- configuration (fw-IDENTITY-000001) ----------------------------------------------------
def test_local_is_the_default_and_unchanged(tmp_path, monkeypatch, capsys):
    project = _project(tmp_path)
    monkeypatch.chdir(project)
    dep = load(project)
    assert provider.kind(dep.pointer) == "local" and not provider.is_oidc(dep)
    assert main(["new", "ITEM", "--title", "Local", "--as", "ada", *FIELDS]) == 0
    assert capsys.readouterr().out.split()[0].endswith(USERID)
    assert not (project / ".criterion" / provider.SIGNERS).exists()


def test_configure_writes_the_project_file(tmp_path, monkeypatch, capsys):
    project = _project(tmp_path)
    write(project / "catalyst.toml", 'project_name = "app"\nkernel_version = "0.38.0"\nmodule = "example-process"\n')
    (project / "app.catalyst").unlink()
    monkeypatch.chdir(project)
    with pytest.raises(SystemExit, match="needs --issuer"):
        main(["identity", "configure", "oidc"])
    assert main(["identity", "configure", "oidc", "--issuer", ISSUER + "/", "--client", "cli"]) == 0
    text = (project / "catalyst.toml").read_text(encoding="utf-8")
    assert 'identity = "oidc"' in text and f'identity_issuer = "{ISSUER}"' in text and 'identity_client = "cli"' in text
    capsys.readouterr()
    assert main(["identity", "configure", "local"]) == 1  # signed under oidc: needs a login
    assert "not logged in" in capsys.readouterr().err
    monkeypatch.setattr(provider, "verify", lambda conf, transport=None: ALICE)
    assert main(["identity", "configure", "local", "--intent", "back to the registry"]) == 0
    assert "identity" not in (project / "catalyst.toml").read_text(encoding="utf-8")
    [*_, switched] = journal_entries(project / ".criterion")
    assert (switched["command"], switched["actor"], switched["intent"]) == (
        "catalyst identity",
        "alice",
        ["back to the registry"],
    )


def test_check_reports_bad_provider_settings(tmp_path, monkeypatch):
    project = _project(tmp_path)
    _pointer(project, identity="ldap")
    assert any("unknown provider 'ldap'" in e for e in check.run(load(project)).errors)
    _pointer(project, identity="oidc")
    assert any("needs `identity_issuer`" in e for e in check.run(load(project)).errors)


# --- verified signers (fw-IDENTITY-000002) -------------------------------------------------
def test_the_signer_is_the_verified_identity(oidc, capsys):
    project, _ = oidc
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
    # a second signature reuses the ledger line
    assert main(["status", "set", item, "Done", "--intent", "done"]) == 0
    assert len(_ledger(project)) == 1


def test_as_names_only_the_logged_in_identity(oidc, capsys):
    assert main(["new", "ITEM", "--title", "Mine", "--as", "alice", *FIELDS]) == 0
    capsys.readouterr()
    assert main(["new", "ITEM", "--title", "Theirs", "--as", "ada", *FIELDS]) == 1
    assert "you sign only as yourself" in capsys.readouterr().err


def test_no_verified_identity_signs_nothing_but_reads_work(oidc, capsys):
    project, who = oidc
    who["now"] = None
    assert main(["new", "ITEM", "--title", "Offline", *FIELDS]) == 1
    assert "catalyst identity login" in capsys.readouterr().err
    assert not (project / ".criterion" / provider.SIGNERS).exists()
    assert main(["list", "ITEM"]) == 0


def test_a_refused_command_enrolls_nobody(oidc, capsys, monkeypatch):
    from catalyst import permissions

    project, who = oidc
    who["now"] = provider.Verified(ISSUER, "sub-sam", "sam", "Sam", ())  # holds no mapped role
    monkeypatch.setattr(permissions, "refusal", lambda dep, user, command, also=(): f"{user['name']} may not run /new")
    assert main(["new", "ITEM", "--title", "Refused", *FIELDS]) == 1
    assert "may not run" in capsys.readouterr().err
    assert _ledger(project) == []


def test_user_commands_refuse_with_a_provider(oidc, capsys):
    assert main(["user", "add", "Grace", "Developer"]) == 1
    assert "identity provider" in capsys.readouterr().err


def test_a_taken_username_is_suffixed(oidc, capsys):
    project, who = oidc
    who["now"] = provider.Verified(ISSUER, "sub-other-ada", "ada", "Another Ada", ("developer",))
    assert main(["new", "ITEM", "--title", "Clash", *FIELDS]) == 0
    [line] = _ledger(project)
    assert line["username"] == f"ada-{line['userid']}"


# --- the ledger (fw-IDENTITY-000003) --------------------------------------------------------
def test_ledger_signers_are_registered_users(oidc, capsys):
    project, _ = oidc
    assert main(["new", "ITEM", "--title", "Signed", *FIELDS]) == 0
    capsys.readouterr()
    dep = load(project)
    corpus = load_corpus(dep)
    alice = corpus.user("alice")
    assert alice and alice["iss"] == ISSUER and alice["roles"] == []
    assert schema_check.problems(alice, schema_check.load("user")) == []
    assert [e for e in check.run(dep).errors if e.startswith(("identity", "chain"))] == []


def test_check_reports_a_broken_or_rewritten_ledger(oidc, capsys):
    project, _ = oidc
    assert main(["new", "ITEM", "--title", "Signed", *FIELDS]) == 0
    capsys.readouterr()
    path = project / ".criterion" / provider.SIGNERS
    good = path.read_text(encoding="utf-8")
    line = json.loads(good)
    twin = {**line, "sub": "someone-else"}
    write(path, good + "not json\n" + json.dumps({"userid": "x"}) + "\n" + json.dumps(twin) + "\n")
    found = provider.ledger_problems(project / ".criterion")
    assert any("not a JSON line" in p for p in found) and any("missing iss" in p for p in found)
    assert any("names two identities" in p for p in found)
    write(path, "")  # the journaled line removed
    assert any("changed or removed" in e for e in check.run(load(project)).errors)


def test_a_shared_criterion_merges_the_ledger_by_union(oidc):
    project, _ = oidc
    assert "IAM/signers.jsonl" in criterion.attribute_paths(load(project))


# --- roles (fw-IDENTITY-000004) -----------------------------------------------------------
def test_roles_come_through_provider_role():
    assert provider.roles_for(ROLES["roles"], ("developer", "reviewer", "unknown")) == ["Developer", "Reviewer"]
    assert provider.unmapped_roles(ROLES["roles"]) == ["Stakeholder"]


def test_check_warns_of_an_unmapped_role(oidc):
    project, _ = oidc
    assert any("role Stakeholder has no provider_role" in w for w in check.run(load(project)).warnings)


def test_role_commands_set_the_provider_role(oidc, capsys):
    project, _ = oidc
    assert main(["role", "add", "Auditor", "--action", "/journal", "--provider-role", "auditor", "--json"]) == 0
    added = json.loads(capsys.readouterr().out)
    assert added["provider_role"] == "auditor" and schema_check.problems(added, schema_check.load("role")) == []
    assert main(["role", "modify", "Developer", "--provider-role", "dev"]) == 0
    roles = json.loads((project / ".criterion" / "IAM" / "roles" / "roles.json").read_text(encoding="utf-8"))
    dev = next(r for r in roles["roles"] if r["name"] == "Developer")
    assert dev["provider_role"] == "dev" and dev["actions"] == ["/new", "/status", "/rename"]  # actions kept


def test_an_approval_counts_with_the_roles_it_recorded(oidc, capsys):
    project, who = oidc
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


# --- the provider, through the vendored client ---------------------------------------------
def test_verify_asks_the_provider(tmp_path, monkeypatch):
    from catalyst.identity.http import Response
    from catalyst.identity.oidc import Tokens

    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    conf = provider.ProviderSettings(issuer=ISSUER)
    discovery = {
        "issuer": ISSUER,
        **{k: f"{ISSUER}/{k}" for k in ("token_endpoint", "device_authorization_endpoint", "userinfo_endpoint")},
        **{k: f"{ISSUER}/{k}" for k in ("introspection_endpoint", "revocation_endpoint")},
    }
    claims = {"sub": "s1", "preferred_username": "alice", "name": "Alice", "realm_access": {"roles": ["developer"]}}

    def transport(request, timeout):
        if request.url.endswith("openid-configuration"):
            return Response(200, {}, json.dumps(discovery).encode())
        if request.url.endswith("userinfo_endpoint"):
            assert request.headers["Authorization"] == "Bearer at"
            return Response(200, {}, json.dumps(claims).encode())
        return Response(404, {}, b"{}")

    with pytest.raises(provider.ProviderError, match="catalyst identity login"):
        provider.verify(conf, transport)  # no tokens yet
    import time

    provider.session(conf, transport).store.save(ISSUER, conf.client_id, Tokens("at", "rt", time.time() + 300))
    path = provider.credentials_path(conf)
    assert path.parent.parent == tmp_path / "home" and oct(path.stat().st_mode & 0o777) == "0o600"
    who = provider.verify(conf, transport)
    assert (who.iss, who.sub, who.username, who.provider_roles) == (ISSUER, "s1", "alice", ("developer",))


def test_identity_whoami_and_status_print_their_schemas(oidc, capsys):
    assert main(["identity", "whoami", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["userid"] is None and payload["roles"] == ["Developer", "Reviewer"]
    assert schema_check.problems(payload, schema_check.load("identity-whoami")) == []
    assert main(["identity", "status", "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status == {"provider": "oidc", "issuer": ISSUER, "client": "catalyst-cli", "logged_in": False}
    assert schema_check.problems(status, schema_check.load("identity-status")) == []


def test_the_zipapp_stays_standard_library_only(tmp_path):
    scripts = str(Path(__file__).resolve().parents[1] / "scripts")
    code = f"import sys; sys.path.insert(0, {scripts!r}); import catalyst.provider, catalyst.identity.session"
    assert subprocess.run(["python3", "-I", "-S", "-c", code], capture_output=True, check=False).returncode == 0
