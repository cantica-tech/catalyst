"""`catalyst inbox` (roadmap R5.7; REQ-000032): what waits for a person,
with its evidence and what settles it, from the CLI and the server,
against its schema."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from catalyst import inbox, serve
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst_fixtures import USERID, artifact, write
from test_catalyst_impact import _valid
from test_catalyst_unrecorded import fresh_project, git, manual_commit

SCHEMA = Path(__file__).resolve().parents[1] / "spec" / "inbox.schema.json"
ITEM, CASE, STUDY = f"ITEM-000001-{USERID}", f"RECON-000001-{USERID}", f"ANALYSIS-000001-{USERID}"


def _inbox(project) -> dict:
    dep = load(project)
    return inbox.inbox(dep, load_corpus(dep))


def _case(project, status: str) -> None:
    fields = {"ID": f"`{CASE}`", "Status": status, "Entity": f"`{ITEM}`"}
    write(
        project / ".criterion" / "reconciliations" / "RECON-000001-login-flow.md", artifact(CASE, "Login flow", fields)
    )


def test_nothing_waits_in_a_project_that_is_in_order(tmp_path, monkeypatch, capsys):
    project = fresh_project(tmp_path, monkeypatch)
    found = _inbox(project)
    assert found == {"items": [], "counts": dict.fromkeys(inbox.KINDS, 0)}
    assert main(["inbox"]) == 0 and capsys.readouterr().out == "nothing waits\n"


def test_work_done_outside_catalyst_waits_until_it_is_adopted(tmp_path, monkeypatch, capsys):
    project = fresh_project(tmp_path, monkeypatch)
    sha = manual_commit(project, msg="A hand edit")
    (item,) = _inbox(project)["items"]
    assert (item["kind"], item["id"], item["title"]) == ("unrecorded-commit", sha[:10], "A hand edit")
    assert item["evidence"]["commit"] == sha and [f["path"] for f in item["evidence"]["files"]] == ["src/app.py"]
    assert item["settle"][0].startswith(f"catalyst journal adopt {sha[:10]}")
    assert main(["journal", "adopt", sha, "--as", "ada", "--intent", "kept"]) == 0
    capsys.readouterr()
    assert [i for i in _inbox(project)["items"] if i["kind"] == "unrecorded-commit"] == []


def test_an_unjournaled_file_waits(tmp_path, monkeypatch):
    project = fresh_project(tmp_path, monkeypatch)
    write(project / "notes.txt", "not journaled\n")
    found = _inbox(project)
    assert found["counts"]["unrecorded-change"] == 1
    (item,) = found["items"]
    assert (item["kind"], item["id"], item["evidence"]) == ("unrecorded-change", "notes.txt", {"path": "notes.txt"})
    assert "catalyst journal append --file notes.txt" in item["settle"][0]


def test_an_open_case_and_an_analysis_to_decide_wait(tmp_path, monkeypatch):
    project = fresh_project(tmp_path, monkeypatch)
    _case(project, "Open")
    fields = {"ID": f"`{STUDY}`", "Status": "Deciding", "Scope": "src/"}
    write(project / ".criterion" / "analyses" / "ANALYSIS-000001-src.md", artifact(STUDY, "A study", fields))
    git(project, "add", "-A")  # the criterion sits beside the project here; nothing of the project changed
    waiting = {i["kind"]: i for i in _inbox(project)["items"] if i["kind"] in ("reconciliation", "analysis")}
    case, study = waiting["reconciliation"], waiting["analysis"]
    assert (case["id"], case["title"], case["evidence"]) == (CASE, "Login flow", {"status": "Open", "entity": ITEM})
    assert case["settle"] == [f"catalyst reconcile {CASE} {d}" for d in inbox.DECISIONS]
    assert (study["id"], study["evidence"]) == (STUDY, {"status": "Deciding", "scope": "src/"})
    # a case that is resolved or closed, an analysis in another phase: not waiting
    _case(project, "Resolved-Accepted")
    fields["Status"] = "Closed"
    write(project / ".criterion" / "analyses" / "ANALYSIS-000001-src.md", artifact(STUDY, "A study", fields))
    assert [i for i in _inbox(project)["items"] if i["kind"] in ("reconciliation", "analysis")] == []


def test_the_verb_prints_what_the_schema_describes(tmp_path, monkeypatch, capsys):
    project = fresh_project(tmp_path, monkeypatch)
    sha = manual_commit(project)
    write(project / "notes.txt", "x\n")
    _case(project, "Under Review")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert main(["inbox", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert _valid(payload, schema, schema) == []
    assert {i["kind"] for i in payload["items"]} >= {"unrecorded-commit", "unrecorded-change", "reconciliation"}
    assert _valid({"items": [{"kind": "x"}], "counts": {}}, schema, schema)  # the check refuses a wrong payload
    assert main(["inbox"]) == 0
    text = capsys.readouterr().out
    assert "commits made outside catalyst: 1" in text and sha[:10] in text and "reconciliation cases: 1" in text
    assert text.rstrip().endswith("waiting")


def test_the_server_answers_like_the_verb(tmp_path, monkeypatch, capsys):
    project = fresh_project(tmp_path, monkeypatch)
    manual_commit(project)
    httpd, token = serve.make_local(project, 0, poll=0.1)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        client = serve.Client(f"http://127.0.0.1:{httpd.server_address[1]}", token)
        capsys.readouterr()
        main(["inbox", "--json"])
        assert client.call("GET", "/inbox") == json.loads(capsys.readouterr().out)
    finally:
        httpd.shutdown()
        httpd.server_close()
