"""Landing, phase 2 (design 33 §3; REQ-000101, fw-STRUCTURE-000024): `catalyst serve` holds each batch it accepts
and lands it in the criterion's repository as the landing policy says, takes in the shared branch, and stops on a
conflict for a human."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pytest

import schema_check
from catalyst import journal as j, landing, serve_landing
from catalyst.__main__ import main
from catalyst.deployment import load
from test_catalyst_serve import _app, _edit, machines, server  # noqa: F401 (the two-machine fixtures)


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(machines, server, tmp_path, monkeypatch):  # noqa: F811
    """The criterion's repository, holding what the server holds (its shared branch `criterion`), and the server
    connected to it with the `git` forge; agents' variables cleared, so a change is a person's."""
    for v in (j.VIA_VARIABLE, *j.AGENT_VARIABLES):
        monkeypatch.delenv(v, raising=False)
    app = _app(server)
    app.loaded()  # the server's files, as a tree
    bare, work = tmp_path / "criterion.git", tmp_path / "seed"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "criterion", str(work)], check=True)
    subprocess.run(["cp", "-R", f"{app.tree()}/.", str(work)], check=True)
    _git(work, "add", "-A")
    _git(work, "-c", "user.name=ada", "-c", "user.email=a@x", "commit", "-q", "-m", "the criterion")
    _git(work, "push", "-q", str(bare), "criterion")
    serve_landing.Lander.connect(app, str(bare), "git", None, "serve-landing", "criterion")
    return app, bare, work


def _lander(app, check=True, clock=None):
    return serve_landing.Lander(app, check=lambda _work: check, clock=clock or time.time)


def _note(project, who: str, path: str, text: str) -> None:
    """A journaled change to a file no entity is: unlinked."""
    dep = load(project)
    f = dep.root / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    j.append(
        dep,
        j.AppendRequest(
            command="chore",
            action="update",
            artifact=path,
            targets=[],
            intent=[f"{who} notes"],
            files=[str(f)],
            actor=who,
            tier="chore",
        ),
    )


def _push(who: str, message: str) -> None:
    assert main(["share", "push", "-m", message, "--as", who, "--yes"]) == 0


def _on_branch(bare: Path, path: str) -> str | None:
    done = subprocess.run(
        ["git", "-C", str(bare), "show", f"criterion:{path}"], capture_output=True, text=True, check=False
    )
    return done.stdout if done.returncode == 0 else None


def test_a_persons_unlinked_change_lands_and_merges(repo, machines, capsys):  # noqa: F811
    app, bare, _ = repo
    machines("bob")
    _note(Path.cwd(), "bob", "notes/bob.md", "Bob's note\n")
    _push("bob", "Bob's note")
    out = _lander(app).tick()
    assert out["errors"] == [] and out["taken_in"] is None
    assert [x["state"] for x in out["landed"]] == ["open"] and out["landed"][0]["rule"] == "explicit-unlinked"
    assert [m["state"] for m in out["merged"]] == ["merged"]
    assert _on_branch(bare, "notes/bob.md") == "Bob's note\n"
    log = _git(bare, "log", "-2", "--format=%an|%B", "criterion")
    assert "catalyst serve|" in log and "Signed-off-by: Bob" in log
    again = _lander(app).tick()
    assert again["landed"] == []  # landed once
    schema = json.loads((Path(__file__).resolve().parents[1] / "spec" / "serve-landing.schema.json").read_text())
    assert schema_check.problems(again, schema) == [] and schema_check.problems(_lander(app).list(), schema) == []
    assert [r["state"] for r in _lander(app).list()] == ["merged"]


def test_a_linked_change_waits_for_review(repo, machines):  # noqa: F811
    app, bare, _ = repo
    machines("bob")
    _edit(Path.cwd(), "bob", "\nBob's note\n")
    _push("bob", "Bob edits the item")
    out = _lander(app).tick()
    assert [w["state"] for w in out["waiting"]] == ["waiting-review"] and out["merged"] == []
    assert "Bob's note" not in (_on_branch(bare, "items/ITEM-000001-first-item.md") or "")
    branch = _lander(app).list()[0]["branch"]
    assert "Bob's note" in _git(bare, "show", f"{branch}:items/ITEM-000001-first-item.md")


def test_an_agents_session_lands_once_idle_as_one_pull_request(repo, machines, monkeypatch):  # noqa: F811
    app, _, _ = repo
    machines("bob")
    monkeypatch.setenv("CLAUDECODE", "1")
    _note(Path.cwd(), "bob", "notes/one.md", "one\n")
    _push("bob", "one")
    _note(Path.cwd(), "bob", "notes/two.md", "two\n")
    _push("bob", "two")
    assert _lander(app).tick()["landed"] == []  # the session may go on
    later = time.time() + 31 * 60
    out = _lander(app, clock=lambda: later).tick()
    assert len(out["landed"]) == 1 and out["landed"][0]["rule"] == "agent-session"
    assert len(out["landed"][0]["batches"]) == 2
    assert [w["state"] for w in out["waiting"]] == ["waiting-review"]


def test_a_conflict_stops_the_landing_with_nothing_pushed_then_retry(repo, machines):  # noqa: F811
    app, bare, work = repo
    machines("bob")
    _note(Path.cwd(), "bob", "notes/shared.md", "Bob's\n")
    _push("bob", "Bob's")
    (work / "notes").mkdir(exist_ok=True)
    (work / "notes" / "shared.md").write_text("an admin's\n", encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "-c", "user.name=ada", "-c", "user.email=a@x", "commit", "-q", "-m", "an admin's push")
    _git(work, "push", "-q", str(bare), "criterion")
    out = _lander(app).tick()
    assert [c["state"] for c in out["conflicts"]] == ["conflict"] and "notes/shared.md" in out["conflicts"][0]["note"]
    assert _on_branch(bare, "notes/shared.md") == "an admin's\n"
    assert not [b for b in _git(bare, "branch", "--list", "landing/*").split() if b]
    lid = out["conflicts"][0]["id"]
    assert _lander(app).tick()["landed"] == []  # a conflict waits for a human, never retried alone
    # a human settles it on the shared branch (here: the admin's file removed), then retries
    _git(work, "rm", "-q", "notes/shared.md")
    _git(work, "-c", "user.name=ada", "-c", "user.email=a@x", "commit", "-q", "-m", "settled")
    _git(work, "push", "-q", str(bare), "criterion")
    assert _lander(app).retry(lid)
    with pytest.raises(serve_landing.LandingError, match="only a conflicted"):
        _lander(app).retry(lid)
    out = _lander(app).tick()
    assert [m["state"] for m in out["merged"]] == ["merged"]
    assert _on_branch(bare, "notes/shared.md") == "Bob's\n"


def test_the_shared_branch_is_taken_in(repo, machines):  # noqa: F811
    app, bare, work = repo
    (work / "notes").mkdir(exist_ok=True)
    (work / "notes" / "admin.md").write_text("pushed by an admin\n", encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "-c", "user.name=ada", "-c", "user.email=a@x", "commit", "-q", "-m", "an admin's push")
    _git(work, "push", "-q", str(bare), "criterion")
    out = _lander(app).tick()
    assert out["taken_in"] and out["landed"] == []
    files = {row[0]: row[1] for row in app.derived()[0]}
    assert app.blob(files["notes/admin.md"]) == b"pushed by an admin\n"
    assert _lander(app).tick()["taken_in"] is None  # once


def test_a_failing_check_does_not_merge(repo, machines):  # noqa: F811
    app, bare, _ = repo
    machines("bob")
    _note(Path.cwd(), "bob", "notes/bad.md", "bad\n")
    _push("bob", "bad")
    out = _lander(app, check=False).tick()
    assert [w["state"] for w in out["waiting"]] == ["check-failed"]
    assert _on_branch(bare, "notes/bad.md") is None


def test_a_policy_naming_another_credential_lands_nothing(repo, machines):  # noqa: F811
    app, _, _ = repo
    app.set_meta("landing.name", "another")
    machines("bob")
    _note(Path.cwd(), "bob", "notes/x.md", "x\n")
    _push("bob", "x")
    out = _lander(app).tick()
    assert out["landed"] == [] and "names credential 'serve-landing'" in out["errors"][0]


def test_connect_asks_first_and_refuses_an_unreadable_repository(tmp_path, capsys):
    db = tmp_path / "s.db"
    assert main(["serve", "--db", str(db), "landing", "connect", str(tmp_path / "nowhere")]) == 3
    assert "re-run with --yes" in capsys.readouterr().out
    assert main(["serve", "--db", str(db), "landing", "connect", str(tmp_path / "nowhere"), "--yes"]) == 1
    assert "cannot be read" in capsys.readouterr().err
    assert main(["serve", "--db", str(db), "landing", "tick"]) == 1
    assert "lands nowhere yet" in capsys.readouterr().err


# --- the policy, applied, and the GitHub forge -------------------------------------------------------------------
def _batch(**kw) -> serve_landing.Batch:
    return serve_landing.Batch(1, "2026-10-26T00:00:00Z", "bob", kw.pop("roles", []), "m", [], **kw)


def test_the_standard_policy_matches_each_kind_of_change():
    policy = landing.policy("standard")
    rule = lambda **kw: serve_landing.rule_for(policy, _batch(**kw))["id"]  # noqa: E731
    assert rule(via="server", change="server") == "server-own"
    assert rule(via="agent", change="unlinked") == "agent-session"
    assert rule(via="person", change="unlinked") == "explicit-unlinked"
    assert rule(via="person", change="proposal-accepted") == "accepted-proposal"
    assert rule(via="person", change="linked") == "default"
    assert serve_landing._group({"group": {"by": "session", "idle_minutes": 5}}) == ("session", 5)
    assert serve_landing._group({"group": "window"}) == ("window", 60)
    picky = {"rules": [{"id": "leads", "match": {"who": ["Lead"], "types": ["REQ"]}}], "default": {}}
    assert serve_landing.rule_for(picky, _batch(roles=["Lead"], types=["REQ"]))["id"] == "leads"
    assert serve_landing.rule_for(picky, _batch(roles=["Lead"], types=["BUG"]))["id"] == "default"


class FakeGitHub:
    def __init__(self, runs=()):
        self.calls, self.runs, self.merged = [], list(runs), False

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url.split("/repos/o/r")[1], body))
        assert headers["Authorization"] == "Bearer t0k"
        if method == "POST":
            return 201, {"number": 7, "html_url": "https://github.com/o/r/pull/7"}
        if url.endswith("/check-runs"):
            return 200, {"check_runs": self.runs}
        if method == "PUT":
            self.merged = True
            return 200, {"merged": True}
        return 200, {"merged": self.merged, "state": "closed" if self.merged else "open"}


def test_the_github_forge_opens_waits_for_the_check_and_merges():
    fake = FakeGitHub()
    forge = serve_landing.GitHubForge("git@github.com:o/r.git", "criterion", "t0k", transport=fake, api="https://api")
    opened = forge.open("landing/bob/x-1", "t", "b")
    assert (opened.number, opened.url) == ("7", "https://github.com/o/r/pull/7")
    assert fake.calls[0] == (
        "POST",
        "/pulls",
        {"title": "t", "head": "landing/bob/x-1", "base": "criterion", "body": "b"},
    )
    assert forge.checks("7", "abc") == "pending"  # no run registered yet: never a pass
    fake.runs = [{"status": "in_progress", "conclusion": None}]
    assert forge.checks("7", "abc") == "pending"
    fake.runs = [{"status": "completed", "conclusion": "failure"}]
    assert forge.checks("7", "abc") == "failure"
    fake.runs = [{"status": "completed", "conclusion": "success"}]
    assert forge.checks("7", "abc") == "success" and forge.state("7", "abc") == "open"
    forge.merge("7", "abc")
    assert fake.calls[-1] == ("PUT", "/pulls/7/merge", {"merge_method": "merge", "sha": "abc"})
    assert forge.state("7", "abc") == "merged"
    with pytest.raises(serve_landing.LandingError, match="needs a token"):
        serve_landing.GitHubForge("https://github.com/o/r", "criterion", None)
    assert serve_landing._auth("https://github.com/o/r", "t")[1].startswith("http.extraHeader=Authorization: Basic ")
    assert serve_landing._auth("git@github.com:o/r.git", "t") == []


def test_every_accepted_batch_is_held_and_the_import_is_not(repo):
    app, _, _ = repo
    with app._conn() as c:
        rows = c.execute("SELECT seq, landing FROM held ORDER BY seq").fetchall()
    assert rows and rows[0][1] == serve_landing.TAKEN_IN  # the first push, an import
    assert json.loads(json.dumps(_lander(app).list())) == []
