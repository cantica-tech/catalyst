"""`catalyst serve` and the `serve` share driver (roadmap R3.9,
REQ-000018-yCNjAMXO): two machines share one criterion through a server,
which refuses a conflict, an unjournaled change, a wrong signer, a
duplicate ID and a reconciliation decision beyond the signer's role."""

from __future__ import annotations

import json
import re
import shutil
import threading
from pathlib import Path

import pytest

import test_catalyst_criterion as shared
from catalyst import journal as j, move, serve, store
from catalyst.__main__ import main
from catalyst.deployment import load
from catalyst_fixtures import USERID, artifact, make_project, write

BOB = "Bb12Cd34"


@pytest.fixture
def server(tmp_path):
    httpd = serve.make_server(tmp_path / "server" / "serve.db", "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd, f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def _app(server) -> serve.Server:
    return server[0].RequestHandlerClass.app


def _users(root, roles=True):
    users = json.loads((root / "IAM" / "users" / "users.json").read_text(encoding="utf-8"))
    users["users"].append({"name": "Bob", "git_username": "bob", "roles": ["Developer"], "active": True, "userid": BOB})
    write(root / "IAM" / "users" / "users.json", json.dumps(users))
    if roles:
        write(
            root / "IAM" / "roles" / "roles.json",
            json.dumps(
                {
                    "roles": [
                        {"name": "Admin", "actions": [], "reconciliation": "full"},
                        {"name": "Developer", "actions": [], "reconciliation": "propose"},
                    ]
                }
            ),
        )


@pytest.fixture
def machines(tmp_path, monkeypatch, capsys, server):
    """Ada shares her criterion through the server; Bob joins on another
    machine. Returns a function that switches between them."""
    _, url = server
    homes = {"ada": tmp_path / "machine-a", "bob": tmp_path / "machine-b"}
    monkeypatch.setenv("CATALYST_HOME", str(homes["ada"]))
    ada = make_project(tmp_path / "ada", git=True)
    _users(ada / ".criterion")
    move.to_home(ada, runtime=False)
    monkeypatch.chdir(ada)
    assert main(["share", "login", url, "--token", _app(server).issue(USERID)[1]]) == 0
    assert main(["share", "create", url, "--driver", "serve"]) == 3  # no assent, nothing published
    assert _app(server).head()["seq"] == 0
    assert main(["share", "create", url, "--driver", "serve", "--as", "ada", "--yes"]) == 0
    assert store.share_for(load(ada)).driver == "serve"

    monkeypatch.setenv("CATALYST_HOME", str(homes["bob"]))
    bob = tmp_path / "bob" / "app"
    bob.mkdir(parents=True)
    shutil.copyfile(ada / "catalyst.toml", bob / "catalyst.toml")  # what a clone of the product brings
    assert main(["share", "login", url, "--token", _app(server).issue(BOB)[1]]) == 0
    store.join(bob, runtime=False)
    capsys.readouterr()
    projects = {"ada": ada, "bob": bob}

    def at(who: str):
        monkeypatch.setenv("CATALYST_HOME", str(homes[who]))
        monkeypatch.chdir(projects[who])
        return projects[who]

    return at


def _edit(project, who: str, text: str) -> None:
    dep = load(project)
    item = dep.root / "items" / "ITEM-000001-first-item.md"
    item.write_text(item.read_text(encoding="utf-8") + text, encoding="utf-8")
    j.append(
        dep,
        j.AppendRequest(
            command="/update",
            action="update",
            artifact=f"ITEM-000001-{USERID}",
            targets=[f"br-AUTH-000001-{USERID}"],
            intent=[f"{who} notes {text.strip()}"],
            files=[str(item)],
            actor=who,
        ),
    )


def test_two_machines_share_one_criterion_through_a_server(machines, server, capsys):
    bob = machines("bob")
    assert (load(bob).root / "items" / "ITEM-000001-first-item.md").is_file()
    shared.add_item(bob, "bob", "From machine B")
    assert main(["share", "push", "-m", "B's item", "--as", "bob"]) == 3
    assert "items/ITEM-000002-from-machine-b.md" in capsys.readouterr().out
    assert main(["share", "push", "-m", "B's item", "--as", "bob", "--yes"]) == 0
    assert "as batch 2" in capsys.readouterr().out

    ada = machines("ada")
    assert main(["share", "status", "--fetch", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["behind"] == 1
    assert main(["share", "pull"]) == 0
    dep = load(ada)
    assert (dep.root / "items" / "ITEM-000002-from-machine-b.md").is_file()
    shards = {rel.split("/")[2] for rel in j.sources(dep) if rel.startswith(j.SHARDS + "/")}
    assert any(s.startswith("bob@") for s in shards)
    assert [i for i in j.verify(dep) if i.level == "error"] == []
    assert serve.ServeShare(dep).changes() == []  # pulled work is not a local change

    files, ids = _app(server).derived()
    _app(server).rebuild()
    assert _app(server).derived() == (files, ids)


def test_a_conflict_is_refused_with_nothing_applied_and_stops_the_pull(machines, server, capsys):
    from catalyst.store import ShareError

    _edit(machines("bob"), "bob", "\nBob's note\n")
    assert main(["share", "push", "-m", "note", "--as", "bob", "--yes"]) == 0
    ada = machines("ada")
    _edit(ada, "ada", "\nAda's note\n")
    head = _app(server).head()
    with pytest.raises(ShareError, match="push refused, nothing published") as err:
        store.share_for(load(ada)).push({}, "note")
    assert "items/ITEM-000001-first-item.md" in str(err.value)
    assert _app(server).head() == head
    with pytest.raises(ShareError, match="pull stopped, nothing written"):
        store.share_for(load(ada)).pull()
    assert "Bob's note" not in (load(ada).root / "items" / "ITEM-000001-first-item.md").read_text(encoding="utf-8")


def test_an_entry_signed_for_someone_else_is_refused(machines, server):
    from catalyst.store import ShareError

    bob = machines("bob")
    _edit(bob, "ada", "\nnot Ada\n")  # Bob's token, Ada's name
    with pytest.raises(ShareError, match="signed by 'ada'"):
        store.share_for(load(bob)).push({}, "x")


def test_an_unjournaled_change_is_refused(machines, server):
    from catalyst.store import ShareError

    bob = machines("bob")
    item = load(bob).root / "items" / "ITEM-000001-first-item.md"
    item.write_text(item.read_text(encoding="utf-8") + "\nquietly\n", encoding="utf-8")
    with pytest.raises(ShareError, match="without a journal entry"):
        store.share_for(load(bob)).push({}, "x")


def test_open_joins_a_served_criterion_or_says_to_log_in(machines, server, tmp_path, monkeypatch):
    from catalyst.open import open_project

    machines("ada")
    carol = tmp_path / "carol" / "app"
    carol.mkdir(parents=True)
    shutil.copyfile(machines("ada") / "catalyst.toml", carol / "catalyst.toml")
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "machine-c"))
    monkeypatch.setattr("catalyst.open._runtime", lambda o, criterion, act: None)
    opening = open_project(carol, act=True)
    assert any("share login" in t for t in opening.todo)
    serve.save_token(server[1], _app(server).issue(BOB)[1])
    opening = open_project(carol, act=True)
    assert any("pulled the criterion from the server" in d for d in opening.done), opening.render()
    assert (tmp_path / "machine-c" / "projects" / "app" / "criterion" / "items" / "ITEM-000001-first-item.md").is_file()


def test_a_token_never_reads_as_an_option():
    tokens = [serve.Server(serve.default_db().parent / "t.db").issue("x")[1] for _ in range(50)]
    assert all(t.startswith("cst_") for t in tokens) and len(set(tokens)) == 50


def test_without_a_token_nothing_is_reached(machines, server, monkeypatch):
    from catalyst.store import ShareError

    bob = machines("bob")
    (serve.credentials_file()).unlink()
    with pytest.raises(ShareError, match="share login"):
        store.share_for(load(bob)).pull()
    client = serve.Client(server[1], "not-a-token")
    with pytest.raises(serve.ServeError) as err:
        client.call("GET", "/head")
    assert err.value.status == 401


# --- the server's own checks, without clients -----------------------------------
def _blob(text: str) -> tuple[str, bytes]:
    data = text.encode("utf-8")
    return serve.blob_sha(data), data


def _entry(actor: str, path: str, before, after) -> str:
    return json.dumps(
        {
            "timestamp": "2026-10-10T00:00:00Z",
            "actor": actor,
            "command": "/x",
            "action": "update",
            "artifact": "x",
            "targets": [],
            "intent": ["x"],
            "files": [{"path": serve.WC + path, "before": before, "after": after}],
            "writer": "catalyst/0.53.0",
        }
    )


@pytest.fixture
def seeded(tmp_path):
    """A server holding users, roles and one reconciliation case."""
    app = serve.Server(tmp_path / "s.db")
    root = tmp_path / "c"
    write(
        root / "IAM" / "users" / "users.json",
        json.dumps({"users": [{"name": "Ada", "git_username": "ada", "roles": ["Admin"], "userid": USERID}]}),
    )
    _users(root)
    case = artifact(f"RECON-000001-{USERID}", "Case", {"ID": f"`RECON-000001-{USERID}`", "Status": "Open"})
    files = {
        "IAM/users/users.json": (root / "IAM" / "users" / "users.json").read_text(encoding="utf-8"),
        "IAM/roles/roles.json": (root / "IAM" / "roles" / "roles.json").read_text(encoding="utf-8"),
        "reconciliations/RECON-000001-case.md": case,
    }
    blobs = dict(_blob(t) for t in files.values())
    changes = [{"path": p, "before": None, "after": serve.blob_sha(t.encode())} for p, t in files.items()]
    app.push(USERID, 0, changes, blobs)
    return app, case


def _push_change(app, userid, actor, path, old: str | None, new: str):
    before = serve.blob_sha(old.encode()) if old is not None else None
    after, data = _blob(new)
    line = _entry(actor, path, before, after) + "\n"
    shard = f"development/journal/{actor}@m1/2026-10.jsonl"
    sha, sdata = _blob(line)
    return app.push(
        userid,
        1,
        [{"path": path, "before": before, "after": after}, {"path": shard, "before": None, "after": sha}],
        {**({} if after in serve.EMPTY else {after: data}), sha: sdata},
    )


def test_deciding_a_case_needs_a_full_reconciliation_role(seeded):
    app, case = seeded
    decided = case.replace("| Open |", "| Resolved-Accepted |")
    with pytest.raises(serve.ServeError, match="needs a `full`") as err:
        _push_change(app, BOB, "bob", "reconciliations/RECON-000001-case.md", case, decided)
    assert err.value.status == 403 and app.head()["seq"] == 1
    proposed = case + "\n| 2 | Bob | keep both |\n"
    assert _push_change(app, BOB, "bob", "reconciliations/RECON-000001-case.md", case, proposed)["seq"] == 2
    assert _push_change(app, USERID, "ada", "reconciliations/RECON-000001-case.md", proposed, decided)["seq"] == 3


def test_an_id_already_held_by_another_file_is_refused(seeded):
    app, case = seeded
    with pytest.raises(serve.ServeError, match=re.escape("already reconciliations/RECON-000001-case.md")) as err:
        _push_change(app, USERID, "ada", "reconciliations/RECON-000001-copy.md", None, case)
    assert err.value.status == 409


def test_a_journal_shard_is_append_only_and_blobs_must_match(seeded):
    app, _ = seeded
    sha, data = _blob("x\n")
    with pytest.raises(serve.ServeError, match="does not match"):
        app.push(USERID, 1, [{"path": "a.md", "before": None, "after": sha}], {sha: b"y\n"})
    first = _push_change(app, USERID, "ada", "notes.md", None, "one\n")
    assert first["seq"] == 2
    shard = "development/journal/ada@m1/2026-10.jsonl"
    current = dict(app.derived()[0] and [(p, s) for p, s, _ in app.derived()[0]])[shard]
    other, odata = _blob("rewritten\n")
    with pytest.raises(serve.ServeError, match="append-only"):
        app.push(USERID, 2, [{"path": shard, "before": current, "after": other}], {other: odata})
    with pytest.raises(serve.ServeError, match="criterion-relative"):
        app.push(USERID, 2, [{"path": "../escape", "before": None, "after": sha}], {sha: data})


def test_an_empty_file_needs_no_blob(seeded):
    """git does not always store the empty blob; both sides know it."""
    app, _ = seeded
    assert app.missing([serve.blob_sha(b"")]) == []
    assert _push_change(app, USERID, "ada", "empty.md", None, "")["seq"] == 2


# --- the read side (S3) ------------------------------------------------------------
def _cli_json(capsys, *argv) -> object:
    capsys.readouterr()
    assert main([*argv, "--json"]) == 0
    return json.loads(capsys.readouterr().out)


def _get(server, path: str):
    client = serve.Client(server[1], _app(server).issue(USERID)[1])
    return client.call("GET", path)


def test_the_read_side_answers_what_the_cli_answers(machines, server, capsys):
    shared.add_item(machines("bob"), "bob", "From machine B")
    assert main(["share", "push", "-m", "B's item", "--as", "bob", "--yes"]) == 0
    machines("ada")
    assert main(["share", "pull"]) == 0  # Ada's files are now the server's
    item = f"ITEM-000001-{USERID}"
    assert _get(server, "/list?type=ITEM") == _cli_json(capsys, "list", "ITEM")
    assert _get(server, "/list?type=ITEM&filter=Status%3DOpen") == _cli_json(
        capsys, "list", "ITEM", "--filter", "Status=Open"
    )
    assert _get(server, f"/view/{item}") == _cli_json(capsys, "view", item)
    assert _get(server, "/backlog") == _cli_json(capsys, "backlog")
    assert _get(server, "/journal?actor=bob") == _cli_json(capsys, "journal", "show", "--actor", "bob")
    assert _get(server, "/graph") == _cli_json(capsys, "graph")
    assert _get(server, f"/impact/{item}?direction=up") == _cli_json(capsys, "impact", item, "--up")
    # a served criterion has no git of its own: an entity's history takes its content from the server's blobs
    pushed = max(row["id"] for row in _get(server, "/list?type=ITEM"))
    served = _get(server, f"/history/{pushed}")
    assert served == _cli_json(capsys, "journal", "show", "--artifact", pushed, "--content")
    assert served["entries"] and all(e["content_after"] for e in served["entries"])
    # a server has no project history: its inbox holds the cases and the analyses only
    waiting = _get(server, "/inbox")
    assert waiting["items"] == [] and waiting["counts"]["unrecorded-commit"] == 0
    with pytest.raises(serve.ServeError) as err:
        _get(server, "/check")
    assert err.value.status == 501 and "--local" in str(err.value)
    with pytest.raises(serve.ServeError) as err:
        _get(server, "/view/ITEM-999999-nobody00")
    assert err.value.status == 404 and "no artifact or rule" in str(err.value)
    with pytest.raises(serve.ServeError) as err:
        serve.Client(server[1], "nope").call("GET", "/backlog")
    assert err.value.status == 401


def test_a_read_says_which_batch_it_answers_for_and_follows_new_ones(machines, server):
    import urllib.request

    token = _app(server).issue(USERID)[1]

    def batch_of(path: str) -> str:
        req = urllib.request.Request(server[1] + serve.API + path, headers={"Authorization": f"Bearer {token}"})  # noqa: S310 (the test's localhost server)
        with urllib.request.urlopen(req, timeout=10) as res:  # noqa: S310 (the test's localhost server)
            return res.headers["X-Catalyst-Batch"]

    assert batch_of("/backlog") == "1"
    shared.add_item(machines("bob"), "bob", "Second")
    assert main(["share", "push", "-m", "more", "--as", "bob", "--yes"]) == 0
    assert batch_of("/backlog") == "2"
    ids = {row["id"] for row in _get(server, "/list?type=ITEM")}
    assert any(i.startswith("ITEM-000002") for i in ids)


def test_the_events_stream_sends_each_new_batch(machines, server):
    import urllib.request

    token = _app(server).issue(USERID)[1]
    req = urllib.request.Request(server[1] + serve.API + "/events", headers={"Authorization": f"Bearer {token}"})  # noqa: S310 (the test's localhost server)
    with urllib.request.urlopen(req, timeout=20) as res:  # noqa: S310 (the test's localhost server)
        assert res.headers["Content-Type"] == "text/event-stream"
        lines = iter(res)
        assert next(lines) == b"event: batch\n" and next(lines) == b"data: 1\n"
        shared.add_item(machines("bob"), "bob", "Live")
        assert main(["share", "push", "-m", "live", "--as", "bob", "--yes"]) == 0
        seen = [next(lines) for _ in range(4)]
        assert b"data: 2\n" in seen, seen


# --- local mode: one project's own criterion, read-only --------------------------------
@pytest.fixture
def local(tmp_path, monkeypatch):
    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)
    httpd, token = serve.make_local(project, 0, poll=0.1)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield project, httpd, serve.Client(f"http://127.0.0.1:{httpd.server_address[1]}", token)
    httpd.shutdown()
    httpd.server_close()


def test_local_mode_answers_like_the_cli_and_refuses_writes(local, capsys):
    _, httpd, client = local
    assert httpd.server_address[0] == "127.0.0.1"
    item = f"ITEM-000001-{USERID}"
    assert client.call("GET", "/list?type=ITEM") == _cli_json(capsys, "list", "ITEM")
    assert client.call("GET", f"/view/{item}") == _cli_json(capsys, "view", item)
    assert client.call("GET", "/graph") == _cli_json(capsys, "graph")
    capsys.readouterr()
    main(["check", "--json"])
    assert client.call("GET", "/check") == json.loads(capsys.readouterr().out)
    for method, path in (("POST", "/push"), ("POST", "/have"), ("GET", "/changes"), ("GET", "/blobs/x")):
        with pytest.raises(serve.ServeError) as err:
            client.call(method, path, {} if method == "POST" else None)
        assert err.value.status == 405
    with pytest.raises(serve.ServeError) as err:
        serve.Client(client.url, "cst_wrong").call("GET", "/graph")
    assert err.value.status == 401


def test_local_mode_gives_the_commands_and_their_specs(local, capsys):
    """R6.8: a command palette reads what `catalyst spec` reads."""
    project, _, client = local
    assert client.call("GET", "/commands") == {"commands": []}  # no §4 yet
    with pytest.raises(serve.ServeError) as err:
        client.call("GET", "/spec/alpha")
    assert err.value.status == 404 and "no CODE-OF-CONDUCT.md" in str(err.value)
    section4 = (
        "# R\n\n## 4. Commands\n\n- `/alpha <x>` — do alpha.\n\nWhen the user enters `/alpha`, do it.\n\n## 5. Next\n"
    )
    write(project / ".criterion" / "CODE-OF-CONDUCT.md", section4)
    assert client.call("GET", "/commands") == _cli_json(capsys, "spec")
    names = [c["name"] for c in client.call("GET", "/commands")["commands"]]
    assert names and all(not n.startswith("/") for n in names)
    one = client.call("GET", f"/spec/{names[0]}")
    assert one == _cli_json(capsys, "spec", names[0]) and one["text"].startswith(f"# /{names[0]}")
    with pytest.raises(serve.ServeError) as err:
        client.call("GET", "/spec/no-such-command")
    assert err.value.status == 404 and "not in CODE-OF-CONDUCT.md" in str(err.value)


def test_local_mode_gives_findings_coverage_and_this_users_runs(local, tmp_path, monkeypatch):
    """REQ-000050: what a UI's read side needs, in local mode only for the runs."""
    project, _, client = local
    item = f"ITEM-000001-{USERID}"
    path = next((project / ".criterion").rglob(f"{item.rsplit('-', 1)[0]}-*.md"))
    path.write_text(
        path.read_text(encoding="utf-8").replace(f"br-AUTH-000001-{USERID}", "br-AUTH-999999"), encoding="utf-8"
    )
    checked = client.call("GET", "/check")
    assert checked["findings"] and all({"level", "text", "entity"} <= set(f) for f in checked["findings"])
    assert any(f["entity"] == item for f in checked["findings"])  # the finding names the item's file
    assert set(client.call("GET", "/backlog")["coverage"]) == {"rules", "cited"}
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    assert client.call("GET", "/runs") == {"runs": []}


def test_a_shared_server_keeps_nobodys_runs(server):
    with pytest.raises(serve.ServeError) as err:
        _get(server, "/runs")
    assert err.value.status == 404


def test_local_head_says_what_the_deployment_runs(local):
    """R6.5: a client sees a deployment behind the catalyst it reads it with."""
    from catalyst import __version__

    project, _, client = local
    head = client.call("GET", "/head")
    assert head["kernel"] == (project / ".criterion" / "version.txt").read_text(encoding="utf-8").strip()
    assert head["modules"] == [{"id": "example-process", "version": head["modules"][0]["version"]}]
    assert head["catalyst"] == __version__ and isinstance(head["seq"], int)
    assert head["project"] == "app"  # the project's name, for a client to keep things per project


def test_local_mode_follows_the_criterion_and_says_so(local):
    import time
    import urllib.request

    project, _, client = local
    first = client.call("GET", "/head")["seq"]
    req = urllib.request.Request(  # noqa: S310 (the test's localhost server)
        client.url + serve.API + "/events", headers={"Authorization": f"Bearer {client.token}"}
    )
    with urllib.request.urlopen(req, timeout=20) as res:  # noqa: S310 (the test's localhost server)
        lines = iter(res)
        assert next(lines) == b"event: batch\n" and next(lines) == f"data: {first}\n".encode()
        item = project / ".criterion" / "items" / "ITEM-000001-first-item.md"
        time.sleep(0.05)
        item.write_text(item.read_text(encoding="utf-8").replace("First item", "Renamed item"), encoding="utf-8")
        # the next batch it reports is a later one; one write may be polled as
        # two changes (emptied, then written), so its number is not fixed
        later = None
        for _ in range(12):
            line = next(lines)
            if line.startswith(b"data: "):
                later = int(line[len(b"data: ") :])
                break
        assert later is not None and later > first, later
    titles = {row["id"]: row["title"] for row in client.call("GET", "/list?type=ITEM")}
    assert titles[f"ITEM-000001-{USERID}"] == "Renamed item"


def test_serve_local_prints_where_and_how_to_reach_it(tmp_path, monkeypatch):
    import subprocess
    import sys

    project = make_project(tmp_path, git=True)
    proc = subprocess.Popen(
        [sys.executable, "-m", "catalyst", "serve", "--local", "--project", str(project)],
        stdout=subprocess.PIPE,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(Path(serve.__file__).resolve().parents[1])},
    )
    try:
        assert proc.stdout is not None
        hello = json.loads(proc.stdout.readline())
        assert hello["url"].startswith("http://127.0.0.1:") and hello["token"].startswith("cst_")
        assert serve.Client(hello["url"], hello["token"]).call("GET", "/head")["seq"] == 1
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_the_server_binds_without_asking_dns_its_own_name(tmp_path, monkeypatch):
    """BUG-000018: binding made a reverse DNS lookup (`socket.getfqdn`) and hung
    while no name server answered; serving never asks DNS now."""
    import socket
    import threading

    def no_dns(*_a, **_kw):
        raise AssertionError("serve asked DNS for its own name")

    monkeypatch.setattr(socket, "getfqdn", no_dns)
    project = make_project(tmp_path, git=True)
    httpd, token = serve.make_local(project, 0, poll=0.1)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        assert httpd.server_name == "127.0.0.1" and httpd.server_port == httpd.server_address[1]
        client = serve.Client(f"http://127.0.0.1:{httpd.server_address[1]}", token)
        assert isinstance(client.call("GET", "/head")["seq"], int)
    finally:
        httpd.shutdown()
        httpd.server_close()


def _raw(url: str, method: str = "GET", headers: dict | None = None):
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, method=method, headers=headers or {})  # noqa: S310 (the test's localhost server)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310 (the test's localhost server)
            return r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers)


def test_an_allowed_origin_reads_with_its_token_and_writes_nothing(tmp_path):
    """Owner decision B8: pages of an allowed origin read through serve, each
    with its reader's token; nothing is allowed by default, nothing is written."""
    import threading

    import pytest

    project = make_project(tmp_path, git=True)
    with pytest.raises(serve.ServeError):
        serve.make_local(project, 0, origins=("https://wiki.example.com/path",))
    httpd, token = serve.make_local(project, 0, poll=0.1, origins=("https://wiki.example.com",))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}/v1"
    auth = {"Authorization": f"Bearer {token}"}
    try:
        status, h = _raw(f"{base}/head", headers={**auth, "Origin": "https://wiki.example.com"})
        assert status == 200 and h.get("Access-Control-Allow-Origin") == "https://wiki.example.com"
        status, h = _raw(f"{base}/head", headers={**auth, "Origin": "https://evil.example"})
        assert status == 200 and "Access-Control-Allow-Origin" not in h  # the browser keeps it from that page
        status, _ = _raw(f"{base}/head", headers={"Origin": "https://wiki.example.com"})
        assert status == 401  # the reader's token is still needed
        status, h = _raw(
            f"{base}/head",
            "OPTIONS",
            {"Origin": "https://wiki.example.com", "Access-Control-Request-Method": "GET"},
        )
        assert status == 204 and h.get("Access-Control-Allow-Methods") == "GET"
        status, _ = _raw(
            f"{base}/push",
            "OPTIONS",
            {"Origin": "https://wiki.example.com", "Access-Control-Request-Method": "POST"},
        )
        assert status == 403
        status, _ = _raw(f"{base}/push", "POST", {**auth, "Origin": "https://wiki.example.com"})
        assert status == 403
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_the_deployment_names_its_embedding_origins(tmp_path):
    import json as _json

    project = make_project(tmp_path, git=True)
    pointer = project / "app.catalyst"
    data = _json.loads(pointer.read_text(encoding="utf-8"))
    data["embed_origins"] = "https://wiki.example.com, http://localhost:3000"
    pointer.write_text(_json.dumps(data), encoding="utf-8")
    assert serve.deployment_origins(project) == ("https://wiki.example.com", "http://localhost:3000")
    httpd, _ = serve.make_local(project, 0)
    try:
        from typing import cast

        handler = cast("type[serve.Handler]", httpd.RequestHandlerClass)
        assert handler.origins == {"https://wiki.example.com", "http://localhost:3000"}
    finally:
        httpd.server_close()


def test_the_definitions_are_listed_and_served(tmp_path, capsys):
    """R5.3: a client reads the deployed definitions from catalyst, not the files."""
    import json as _json
    import threading

    import schema_check
    from catalyst.__main__ import main
    from catalyst.init import init
    from test_catalyst_init import request

    req = request(tmp_path)
    init(req)
    assert main(["--project", str(req.project), "definition", "list", "--json"]) == 0
    listed = _json.loads(capsys.readouterr().out)
    assert schema_check.problems(listed, schema_check.load("definitions")) == []
    by = {d["slug"]: d for d in listed["definitions"]}
    assert "README" not in by and by["domain"]["version"] and by["domain"]["description"]
    httpd, token = serve.make_local(req.project, 0, poll=0.1)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        client = serve.Client(f"http://127.0.0.1:{httpd.server_address[1]}", token)
        assert client.call("GET", "/definitions") == listed
    finally:
        httpd.shutdown()
        httpd.server_close()
