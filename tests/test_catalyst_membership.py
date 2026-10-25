"""Project membership on the server (design 32, fw-IDENTITY-000012, fw-IDENTITY-000013): an encrypted, chained,
signed ledger in the server's database; admission failing closed; the members endpoints and `catalyst members`;
daily fingerprints journaled into the criterion; `serve members check`; the master key and break-glass."""

from __future__ import annotations

import base64
import json
import secrets
import shlex
import sqlite3
import sys
import threading
import urllib.request
from pathlib import Path

import pytest

pytest.importorskip("Crypto", reason="membership needs pycryptodome (requirements-dev.txt)")

from catalyst import membership, serve
from catalyst_fixtures import USERID
from test_catalyst_serve import machines, server  # noqa: F401 (the two-machine fixtures)

ISSUER = "https://id.example.com/realms/catalyst"
CRITERION = "alpha"


class Realm:
    """The provider as catalyst-users' facade shows it: people of the realm, and the criterion's members group."""

    def __init__(self, people=("ann", "bob", "cid", "mallory"), members=("ann",)):
        self.people = set(people)
        self.groups = {CRITERION: set(members)}
        self.down = False
        self.asked = 0

    def members(self, name, *, system=False):
        assert system
        return sorted(self.groups.get(name, set()))

    def is_member(self, name, username, *, system=False):
        assert system
        self.asked += 1
        if self.down:
            raise RuntimeError("unreachable")
        return username in self.groups.get(name, set())

    def add_member(self, name, username, *, system=False):
        if username not in self.people:
            raise RuntimeError(f"{username} is not a person of the realm {ISSUER}")
        self.groups.setdefault(name, set()).add(username)

    def remove_member(self, name, username, *, system=False):
        self.groups.get(name, set()).discard(username)


def _claims(username: str, admin_of: str | None = None, everything: bool = False) -> dict:
    claims = {"iss": ISSUER, "sub": f"sub-{username}", "preferred_username": username, "groups": []}
    if admin_of:
        claims["groups"] = [f"/criteria/{admin_of}/admins"]
    if everything:
        claims["resource_access"] = {"catalyst": {"roles": ["cmd:*"]}}
    return claims


ADMIN = _claims("olivier", everything=True)
CRIT_ADMIN = _claims("alice", admin_of=CRITERION)


@pytest.fixture
def key_command(tmp_path):
    """A key-management service's command printing the key: Python reading a file, on every platform."""
    key = tmp_path / "master.key"
    key.write_text(base64.b64encode(secrets.token_bytes(32)).decode())
    show = tmp_path / "show_key.py"
    show.write_text(f"print(open({key.as_posix()!r}).read())\n")
    return shlex.join([Path(sys.executable).as_posix(), show.as_posix()])


@pytest.fixture
def opened(tmp_path, key_command):
    """A server for `alpha`, its ledger open, ann adopted from the provider."""
    realm = Realm()
    app = serve.Server(tmp_path / "s.db", criterion=CRITERION, members=False)
    app.init_key(key_command)
    app.open_ledger({"name": "olivier", "userid": USERID}, ISSUER, realm.members(CRITERION, system=True), "test", realm)
    return app, realm


def _file(app, path: str) -> bytes:
    with app._conn() as c:
        sha = serve._current(c, path)
        return bytes(c.execute("SELECT bytes FROM blobs WHERE sha = ?", (sha,)).fetchone()[0]) if sha else b""


# --- the ledger ---------------------------------------------------------------------------------------------
def test_the_ledger_is_encrypted_chained_and_signed(opened):
    app, _ = opened
    ledger = app.admission.ledger
    ledger.append(membership.record("add", "alice", "joins", member="bob"))
    entries = ledger.entries()
    assert [e["op"] for e in entries] == ["open", "add"] and entries[0]["members"] == ["ann"]
    with sqlite3.connect(app.db) as c:
        heads = [h for (h,) in c.execute("SELECT head FROM ledger WHERE kind = 'members' ORDER BY seq")]
    assert entries[0]["prev"] == "" and entries[1]["prev"] == heads[0] and ledger.head() == heads[1]
    with sqlite3.connect(app.db) as c:
        raw = b"".join(str(v).encode() for row in c.execute("SELECT * FROM ledger") for v in row)
        meta = dict(c.execute("SELECT key, value FROM meta").fetchall())
    assert b"bob" not in raw and b"ann" not in raw and b"joins" not in raw  # nothing readable at rest
    key = (app.db.parent / "master.key").read_text().strip()
    assert meta["members.key_command"].endswith("show_key.py") and key not in json.dumps(meta)  # the key is not stored
    assert ledger.members() == {"ann", "bob"}


def test_a_tampered_or_truncated_ledger_does_not_verify(opened):
    app, _ = opened
    ledger = app.admission.ledger
    ledger.append(membership.record("add", "alice", "joins", member="bob"))
    with sqlite3.connect(app.db) as c:
        ct = c.execute("SELECT ct FROM ledger WHERE seq = 1").fetchone()[0]
        flipped = base64.b64encode(bytes([base64.b64decode(ct)[0] ^ 1]) + base64.b64decode(ct)[1:]).decode()
        c.execute("UPDATE ledger SET ct = ? WHERE seq = 1", (flipped,))
    assert "does not chain" in ledger.verify()[1][0]
    with pytest.raises(membership.MembershipError, match="not intact"):
        ledger.entries()


def test_a_change_says_why():
    with pytest.raises(membership.MembershipError, match="reason"):
        membership.record("add", "alice", "  ", member="bob")


def test_the_server_refuses_to_start_on_a_ledger_it_cannot_read(opened, tmp_path):
    app, realm = opened
    with pytest.raises(serve.ServeError, match="does not decrypt"):
        serve.Server(app.db, backend=realm, master=secrets.token_bytes(32))
    assert serve.Server(app.db, backend=realm).admission is not None  # its recorded command reads the key


# --- admission: fail closed ---------------------------------------------------------------------------------
def test_admins_are_admitted_and_others_only_when_the_provider_and_the_ledger_agree(opened):
    app, realm = opened
    app.admit(ADMIN)
    app.admit(CRIT_ADMIN)
    app.admit(_claims("ann"))  # adopted at opening, and at the provider
    realm.groups[CRITERION].add("mallory")  # added in the provider's console, not through catalyst
    with pytest.raises(serve.ServeError, match="mallory is not a member of alpha") as refused:
        app.admit(_claims("mallory"))
    assert refused.value.status == 403
    realm.groups[CRITERION].discard("ann")  # removed at the provider: refused within the cache's few seconds
    app.admission.forget("ann")
    with pytest.raises(serve.ServeError, match="at the identity provider"):
        app.admit(_claims("ann"))
    with pytest.raises(serve.ServeError, match="only the identity provider's tokens"):
        app.admit(USERID)  # a `cst_` token's userid
    with pytest.raises(serve.ServeError, match="alpha"):
        app.admit(_claims("bob", admin_of="beta"))  # another criterion's admin is nobody here


def test_an_unreachable_provider_admits_nobody_but_admins(opened):
    app, realm = opened
    realm.down = True
    with pytest.raises(serve.ServeError) as refused:
        app.admit(_claims("ann"))
    assert refused.value.status == 503
    app.admit(CRIT_ADMIN)


# --- the members endpoints ----------------------------------------------------------------------------------
def test_admins_add_remove_and_adopt_members_at_the_provider_and_in_the_ledger(opened):
    app, realm = opened
    out = app.members_call(CRIT_ADMIN, "tok-alice", "POST", {"op": "add", "member": "bob", "reason": "reviews"})
    assert out == {"criterion": CRITERION, "op": "add", "member": "bob", "seq": 1}
    assert "bob" in realm.groups[CRITERION]
    app.admit(_claims("bob"))
    app.members_call(CRIT_ADMIN, "tok-alice", "POST", {"op": "remove", "member": "bob", "reason": "done"})
    assert "bob" not in realm.groups[CRITERION]
    with pytest.raises(serve.ServeError, match="bob is not a member"):
        app.admit(_claims("bob"))
    realm.groups[CRITERION].add("cid")  # the console again
    app.members_call(ADMIN, "tok-olivier", "POST", {"op": "adopt", "member": "cid", "reason": "found by check"})
    app.admit(_claims("cid"))
    listed = app.members_call(CRIT_ADMIN, "tok-alice", "GET", {})
    assert listed["members"] == ["ann", "cid"]
    entry = app.admission.ledger.entries()[1]
    assert entry["by"] == "alice" and entry["by_token"].startswith("sha256:") and "tok-alice" not in json.dumps(entry)


def test_members_are_managed_by_admins_only_and_people_of_the_realm_only(opened):
    app, _ = opened
    with pytest.raises(serve.ServeError, match="only the Admin") as refused:
        app.members_call(_claims("ann"), "t", "GET", {})
    assert refused.value.status == 403
    with pytest.raises(serve.ServeError, match="not a person of the realm"):
        app.members_call(CRIT_ADMIN, "t", "POST", {"op": "add", "member": "zoe", "reason": "outsider"})
    with pytest.raises(serve.ServeError, match="already a member"):
        app.members_call(CRIT_ADMIN, "t", "POST", {"op": "add", "member": "ann", "reason": "twice"})
    with pytest.raises(serve.ServeError, match="not a member at the identity provider"):
        app.members_call(CRIT_ADMIN, "t", "POST", {"op": "adopt", "member": "bob", "reason": "nothing to adopt"})
    with pytest.raises(serve.ServeError, match="reason"):
        app.members_call(CRIT_ADMIN, "t", "POST", {"op": "add", "member": "bob"})


def test_a_server_without_a_ledger_has_no_members_endpoint(tmp_path):
    app = serve.Server(tmp_path / "s.db", criterion=CRITERION)
    app.admit(USERID)  # nothing to fail closed on
    with pytest.raises(serve.ServeError, match="no membership ledger") as refused:
        app.members_call(ADMIN, "t", "GET", {})
    assert refused.value.status == 409


def test_the_http_api_fails_closed(opened):
    app, realm = opened

    class Tokens:
        issuer = ISSUER

        def claims(self, token):
            return {"tok-ann": _claims("ann"), "tok-mallory": _claims("mallory"), "tok-alice": CRIT_ADMIN}.get(token)

    app.provider_tokens = Tokens()
    realm.groups[CRITERION].add("mallory")
    handler = type("H", (serve.Handler,), {"app": app, "origins": frozenset()})
    httpd = serve._Server(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}/v1"

    def call(token, path, body=None):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body else None)  # noqa: S310
        req.add_header("Authorization", f"Bearer {token}")
        if body:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=10) as res:  # noqa: S310
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    try:
        assert call("tok-ann", "/head")[0] == 200
        status, payload = call("tok-mallory", "/head")
        assert status == 403 and "mallory is not a member" in payload["error"]
        assert call("tok-ann", "/members")[0] == 403
        status, payload = call("tok-alice", "/members", {"op": "adopt", "member": "mallory", "reason": "checked"})
        assert status == 200 and payload["seq"] == 1
        assert call("tok-mallory", "/head")[0] == 200
    finally:
        httpd.shutdown()
        httpd.server_close()


# --- fingerprints --------------------------------------------------------------------------------------------
def test_opening_writes_a_fingerprint_journaled_by_the_servers_own_batch(opened):
    app, _ = opened
    fingerprints = _file(app, membership.FINGERPRINTS).decode()
    (line,) = fingerprints.splitlines()
    fp = json.loads(line)
    assert set(fp) == {"day", "heads"} and fp["heads"]["members"] == app.admission.ledger.head()
    assert "ann" not in fingerprints and "olivier" not in fingerprints
    with app._conn() as c:
        (shard,) = [p for (p,) in c.execute("SELECT path FROM files") if p.startswith("development/journal/")]
        sha = serve._current(c, membership.FINGERPRINTS)
    assert shard.startswith("development/journal/olivier@serve/")
    (entry,) = serve.entries_in(b"", _file(app, shard))
    assert entry["files"] == [{"path": ".criterion/" + membership.FINGERPRINTS, "before": None, "after": sha}]
    assert entry["actor"] == "olivier" and entry["tier"] == "chore" and entry["writer"].startswith("catalyst/")
    assert serve.blob_sha(_file(app, membership.FINGERPRINTS)) == sha
    assert not app.fingerprint_due()


def test_a_fingerprint_says_nothing_of_how_many_changed(opened):
    app, _ = opened
    first = json.loads(_file(app, membership.FINGERPRINTS).decode().splitlines()[0])
    for name in ("bob", "cid"):
        app.members_call(CRIT_ADMIN, "t", "POST", {"op": "add", "member": name, "reason": "joins"})
    app.fingerprint()
    second = json.loads(_file(app, membership.FINGERPRINTS).decode().splitlines()[1])
    assert set(second) == set(first) == {"day", "heads"}
    assert len(second["heads"]["members"]) == len(first["heads"]["members"])  # a hash, whatever the count


# --- the check ----------------------------------------------------------------------------------------------
def test_the_check_passes_then_reports_drift_and_a_rewritten_ledger(opened):
    app, realm = opened
    assert app.members_check() == []
    realm.groups[CRITERION].add("mallory")
    assert app.members_check() == [
        "mallory is a member at the provider, but no ledger entry added them (adopt or remove)"
    ]
    realm.groups[CRITERION].discard("mallory")
    app.members_call(CRIT_ADMIN, "t", "POST", {"op": "add", "member": "bob", "reason": "joins"})
    app.fingerprint()
    with sqlite3.connect(app.db) as c:  # someone deletes the entry that added bob, and removes him at the provider
        c.execute("DELETE FROM ledger WHERE seq = 1")
    realm.groups[CRITERION].discard("bob")
    assert any("match no entry: rewritten" in f for f in app.members_check())


# --- the master key and break-glass --------------------------------------------------------------------------
def test_break_glass_recovers_with_a_quorum_and_replaces_the_key(opened, monkeypatch):
    app, realm = opened
    stored = {}

    def store(db, key):
        stored["key"] = key
        return "stored-in-keychain"

    monkeypatch.setattr(membership, "store_master", store)
    shares = app.escrow(["alice", "erin", "carol"], 2)
    assert [s["holder"] for s in shares] == ["alice", "erin", "carol"] and all(s["threshold"] == 2 for s in shares)
    with pytest.raises(serve.ServeError, match="2 different holders"):
        app.break_glass([shares[0]], ["alice"], "one is not enough", realm)
    res = app.break_glass([shares[0], shares[1]], ["alice", "erin"], "Admin unreachable", realm)
    assert app.meta("members.key_command") == "stored-in-keychain" and len(stored["key"]) == 32
    entries = app.admission.ledger.entries()
    assert entries[-1]["op"] == "break-glass" and entries[-1]["holders"] == ["alice", "erin"]
    assert app.admission.ledger.members() == {"ann"}  # the entries were not re-encrypted, only the keys re-wrapped
    with app._conn() as c:
        shard = next(p for (p,) in c.execute("SELECT path FROM files") if p.startswith("development/journal/"))
    last = serve.entries_in(b"", _file(app, shard))[-1]
    assert "break-glass used by alice, erin" in last["intent"][0] and res["seq"] > 0
    with pytest.raises(serve.ServeError, match="does not decrypt"):  # the old shares are void
        app.break_glass([shares[1], shares[2]], ["erin", "carol"], "again", realm)


def test_a_key_management_service_holds_the_key(tmp_path, key_command):
    app = serve.Server(tmp_path / "s.db", criterion=CRITERION, members=False)
    assert app.init_key(key_command) == key_command
    with pytest.raises(serve.ServeError, match="already has a master key"):
        app.init_key(key_command)
    other = serve.Server(tmp_path / "t.db", criterion=CRITERION, members=False)
    with pytest.raises(serve.ServeError, match="cannot be read"):
        other.init_key("false")


# --- the command line ---------------------------------------------------------------------------------------
def test_members_need_a_server(tmp_path, monkeypatch, capsys):
    from catalyst import __main__ as cli

    class Dep:
        def __init__(self):
            self.pointer = {"share": "git", "project_name": CRITERION}

    monkeypatch.setattr(cli, "open_deployment", lambda args: Dep())
    with pytest.raises(SystemExit, match="admins only"):
        cli.main(["members", "list"])


def test_serve_members_open_asks_the_admin_first(tmp_path, monkeypatch, capsys, key_command):
    from catalyst import __main__ as cli

    realm = Realm(members=("ann", "bob"))
    db = tmp_path / "s.db"
    serve.Server(db, criterion=CRITERION, members=False).init_key(key_command)
    actor = {"name": "olivier", "userid": USERID, "grants": ["cmd:*"]}
    monkeypatch.setattr(cli, "_host_identity", lambda app: (actor, ISSUER, realm))
    assert cli.main(["serve", "--db", str(db), "members", "open"]) == cli.NEEDS_ASSENT
    out = capsys.readouterr().out
    assert "ann" in out and "bob" in out and "--yes" in out
    assert not membership.Ledger.is_open(serve.Server(db, members=False)._conn)
    assert cli.main(["serve", "--db", str(db), "members", "open", "--yes"]) == 0
    assert "2 member(s) adopted" in capsys.readouterr().out
    monkeypatch.setattr(cli, "_host_identity", lambda app: ({**actor, "grants": []}, ISSUER, realm))
    with pytest.raises(SystemExit, match="only the Admin"):
        cli.main(["serve", "--db", str(serve.Server(tmp_path / "u.db", criterion=CRITERION).db), "members", "open"])


def test_the_admission_cache_keeps_an_answer_seconds_only(opened):
    app, realm = opened
    now = [0.0]
    app.admission.clock = lambda: now[0]
    app.admit(_claims("ann"))
    app.admit(_claims("ann"))
    assert realm.asked == 1
    now[0] += membership.PROVIDER_TTL + 0.1
    app.admit(_claims("ann"))
    assert realm.asked == 2


def test_a_clone_pulls_the_fingerprint_batch_and_its_journal_verifies(machines, server, capsys, key_command):  # noqa: F811
    """The server's own batch is a journaled change like any other: a clone's journal verifies after pulling it."""
    from catalyst import journal as j
    from catalyst.__main__ import main
    from catalyst.deployment import load

    app = server[0].RequestHandlerClass.app
    app.set_meta("criterion", CRITERION)
    app.criterion = CRITERION
    app.init_key(key_command)
    app.open_ledger({"name": "ada", "userid": USERID}, ISSUER, ["ann"], "test", Realm())
    app.admission = None  # ada pulls with the server's own token here; an admin's provider token in production
    ada = machines("ada")
    assert main(["share", "pull"]) == 0
    dep = load(ada)
    assert (dep.root / membership.FINGERPRINTS).is_file()
    assert "ann" not in (dep.root / membership.FINGERPRINTS).read_text()
    assert [i for i in j.verify(dep) if i.level == "error"] == []
