"""The history of one entity (roadmap R5.9; REQ-000031): every journal
entry that changed its file, with the content before and after, from the
CLI and the server, against its schema."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from catalyst import history, serve, views
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst_fixtures import USERID
from test_catalyst_edit import _project
from test_catalyst_impact import _valid

RULE = f"br-AUTH-000001-{USERID}"
SCHEMA = Path(__file__).resolve().parents[1] / "spec" / "history.schema.json"


@pytest.fixture
def lived(tmp_path, monkeypatch, capsys):
    """A project where an item was created, given a sub, then closed."""
    project = _project(tmp_path)  # the fixture project, with its item and sub templates
    monkeypatch.chdir(project)
    fields = ["--field", f"Targets={RULE}", "--field", "Domain=AUTH"]
    assert main(["new", "ITEM", "--title", "Second", "--as", "ada", *fields, "--intent", "a second item"]) == 0
    item = capsys.readouterr().out.split()[0]
    assert main(["new", "SUB", "--title", "Its sub", "--as", "ada", "--field", f"Item={item}"]) == 0
    sub = capsys.readouterr().out.split()[0]
    assert main(["status", "set", item, "Done", "--as", "ada", "--intent", "finished"]) == 0
    capsys.readouterr()
    return project, item, sub


def test_every_change_to_the_entity_with_its_content(lived):
    project, item, sub = lived
    dep = load(project)
    h = history.history(dep, load_corpus(dep), item)
    assert (h["id"], h["type"]) == (item, "ITEM") and h["file"].startswith("items/ITEM-000002-")
    created, linked, closed = h["entries"]
    assert (created["action"], created["artifact"], created["intent"]) == ("create", item, ["a second item"])
    assert created["before"] is None and created["content_before"] is None
    assert "| **Status** | Open |" in created["content_after"]
    # the sub's creation wrote the item's derived field: journaled under the sub, part of the item's history
    assert linked["artifact"] == sub and sub in linked["content_after"] and sub not in linked["content_before"]
    assert linked["content_before"] == created["content_after"]
    assert closed["action"] == "status-change" and closed["intent"] == ["finished"]
    assert "| **Status** | Done |" in closed["content_after"] and "| **Status** | Open |" in closed["content_before"]
    assert history.history(dep, load_corpus(dep), "ITEM-000002")["id"] == item  # a short ID resolves
    assert history.history(dep, load_corpus(dep), RULE)["type"] == "rule"
    with pytest.raises(views.ViewError):
        history.history(dep, load_corpus(dep), "NOPE-000001")


def test_content_that_is_gone_is_null_and_the_entry_stays(lived):
    project, item, _ = lived
    dep = load(project)
    first = history.history(dep, load_corpus(dep), item)["entries"][0]["after"]
    kept = history.git_blob(dep)
    h = history.history(dep, load_corpus(dep), item, lambda sha: None if sha == first else kept(sha))
    assert len(h["entries"]) == 3 and h["entries"][0]["after"] == first
    assert h["entries"][0]["content_after"] is None and h["entries"][1]["content_before"] is None
    assert h["entries"][2]["content_after"] is not None
    assert "content no longer available" in history.render(h)


def test_the_verb_prints_the_history_and_its_diffs(lived, capsys):
    _, item, _ = lived
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert main(["journal", "show", "--artifact", item, "--content", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert _valid(payload, schema, schema) == [] and len(payload["entries"]) == 3
    assert _valid({"id": item}, schema, schema)  # the check itself refuses a wrong payload
    assert main(["journal", "show", "--artifact", item, "--content"]) == 0
    text = capsys.readouterr().out
    assert "-| **Status** | Open |" in text and "+| **Status** | Done |" in text and text.rstrip().endswith("3 changes")
    assert main(["journal", "show", "--content"]) == 1
    assert "name it with --artifact" in capsys.readouterr().err
    assert main(["journal", "show", "--artifact", "NOPE-000001", "--content"]) == 1
    assert main(["journal", "show", "--artifact", item]) == 0  # without --content: the entries, as before
    assert "entr" in capsys.readouterr().out


def test_the_server_answers_like_the_verb(lived, capsys):
    project, item, _ = lived
    httpd, token = serve.make_local(project, 0, poll=0.1)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        client = serve.Client(f"http://127.0.0.1:{httpd.server_address[1]}", token)
        main(["journal", "show", "--artifact", item, "--content", "--json"])
        assert client.call("GET", f"/history/{item}") == json.loads(capsys.readouterr().out)
        with pytest.raises(serve.ServeError) as err:
            client.call("GET", "/history/NOPE-000001")
        assert err.value.status == 404
    finally:
        httpd.shutdown()
        httpd.server_close()
