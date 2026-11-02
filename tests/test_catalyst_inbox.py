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


REVIEW_MODULE = """id: review-process
name: Review Process
version: 1.0.0
description: A module declaring the two work types the inbox reviews, with the software-engineering module's states.
grounding_type: rule
format: 3
entities:
  BUG:
    name: Bug
    folder: bugs
    grounding: required
    grounding_field: Targets
    fields:
      Targets: { kind: ref-list, to: rule, required: true }
    states: [Open, "Under Review", Fixed, Closed, WontFix]
    closed: [Closed, WontFix]
    sections:
      - Description: What is wrong.
  REQ:
    name: Requirement
    folder: requirements
    grounding: required
    grounding_field: Targets
    fields:
      Targets: { kind: ref-list, to: rule, required: true }
    states: [Draft, Proposed, Vetted, Active, Completed, Abandoned]
    closed: [Completed, Abandoned]
    sections:
      - Description: What is needed.
"""


def _review_deployment():
    """The two work types the review reads, as the software-engineering module declares them (its `states` and
    `closed`), built from a v3 module spec, with no project behind them."""
    from types import SimpleNamespace

    from module_loader import parse_simple_yaml, v3_entity

    spec = parse_simple_yaml(REVIEW_MODULE)["entities"]
    etds = {p: v3_entity(p, spec[p]) for p in ("BUG", "REQ")}
    return SimpleNamespace(etds=etds)


def _review_corpus(*artifacts: tuple[str, str, str]):
    """A corpus holding (prefix, ID, status) artifacts."""
    from types import SimpleNamespace

    from catalyst.corpus import Artifact

    by_prefix: dict[str, list] = {}
    for prefix, art_id, status in artifacts:
        art = Artifact(
            id=art_id, prefix=prefix, file=Path(f"{art_id}.md"), title=f"A {prefix}", fields={"Status": status}
        )
        by_prefix.setdefault(prefix, []).append(art)
    return SimpleNamespace(by_prefix=by_prefix, artifacts={}, rules={}, domains=set(), users=[], index_rows={})


def _review_items(dep, corpus) -> list[dict]:
    """The `review` items of an inbox run; the other sources need a project, so the test isolates this one."""
    from unittest.mock import patch

    with (
        patch.object(inbox.unrecorded, "since_baseline", return_value=[]),
        patch("catalyst.check.unrecorded_changes", return_value=[]),
        patch.object(inbox.gates, "waiting", return_value=[]),
        patch("catalyst.workflows.overdue", return_value=[]),
    ):
        found = inbox.inbox(dep, corpus)
    return [i for i in found["items"] if i["kind"] == "review"]


def test_an_open_bug_or_requirement_waits_for_review_until_it_is_closed():
    """Open work to review (`review`): a BUG or REQ whose status is outside its type's closed states, the same
    "open" as `catalyst backlog`. Its settle commands are the status changes its type's workflow allows."""
    dep = _review_deployment()
    bug, req = f"BUG-000001-{USERID}", f"REQ-000001-{USERID}"
    review = _review_items(dep, _review_corpus(("BUG", bug, "Open"), ("REQ", req, "Draft")))
    assert sorted(i["id"] for i in review) == sorted([bug, req])
    bug_item = next(i for i in review if i["id"] == bug)
    assert bug_item["kind"] == "review" and bug_item["evidence"] == {"status": "Open", "entity": bug}
    assert f"catalyst status set {bug} Fixed --intent <why>" in bug_item["settle"]
    assert (
        f"catalyst status set {bug} Open --intent <why>" not in bug_item["settle"]
    )  # its current status is not a move
    # closed (Closed for a bug, Completed for a requirement): not waiting
    assert _review_items(dep, _review_corpus(("BUG", bug, "Closed"), ("REQ", req, "Completed"))) == []
    # a WontFix bug is closed too; an Under Review bug is still open
    assert _review_items(dep, _review_corpus(("BUG", bug, "WontFix"))) == []
    assert [i["id"] for i in _review_items(dep, _review_corpus(("BUG", bug, "Under Review")))] == [bug]


def test_the_review_items_validate_against_the_schema(capsys):
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    dep = _review_deployment()
    found = {"items": _review_items(dep, _review_corpus(("BUG", f"BUG-000001-{USERID}", "Open"))), "counts": {}}
    found["counts"] = dict.fromkeys(inbox.KINDS, 0) | {"review": len(found["items"])}
    assert _valid(found, schema, schema) == []


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
