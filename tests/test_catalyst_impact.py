"""`catalyst impact` (roadmap R5.6; REQ-000030): what an entity rests on and
what rests on it, from the CLI and the server, against its schema."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

import schema_check
from catalyst import impact, serve, views
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst_fixtures import USERID, make_project, write

ITEM, SUB, RULE = f"ITEM-000001-{USERID}", f"SUB-000001-{USERID}", f"br-AUTH-000001-{USERID}"
SCHEMA = Path(__file__).resolve().parents[1] / "spec" / "impact.schema.json"


def _dep(tmp_path):
    """The fixture's chain: SUB rests on ITEM (its `Item`), ITEM on the rule
    (its `Targets`) and on the domain AUTH, the rule on AUTH. `ITEM.Subs`
    is derived from `SUB.Item`."""
    dep = load(make_project(tmp_path))
    return dep, load_corpus(dep)


def _reached(entries: list[dict]) -> list[tuple]:
    return [(e["id"], e["depth"], e["via"]["on"], e["via"]["field"]) for e in entries]


def test_upstream_and_downstream_are_followed_to_the_end(tmp_path):
    dep, corpus = _dep(tmp_path)
    sub = impact.impact(dep, corpus, SUB)
    assert _reached(sub["upstream"]) == [
        (ITEM, 1, SUB, "Item"),
        ("AUTH", 2, ITEM, "Domain"),
        (RULE, 2, ITEM, "Targets"),
    ]
    assert sub["downstream"] == [] and (sub["type"], sub["status"]) == ("SUB", "Open")
    rule = impact.impact(dep, corpus, RULE)
    assert _reached(rule["upstream"]) == [("AUTH", 1, RULE, "domain")]
    assert _reached(rule["downstream"]) == [(ITEM, 1, ITEM, "Targets"), (SUB, 2, SUB, "Item")]
    domain = impact.impact(dep, corpus, "AUTH")
    assert domain["type"] == "domain" and domain["upstream"] == []
    assert [(i, d) for i, d, _, _ in _reached(domain["downstream"])] == [(ITEM, 1), (RULE, 1), (SUB, 2)]


def test_a_derived_field_adds_no_link(tmp_path):
    dep, corpus = _dep(tmp_path)
    item = impact.impact(dep, corpus, ITEM)
    assert SUB not in [e["id"] for e in item["upstream"]]  # `ITEM.Subs` mirrors `SUB.Item`
    assert _reached(item["downstream"]) == [(SUB, 1, SUB, "Item")]


def test_direction_depth_and_short_ids(tmp_path):
    dep, corpus = _dep(tmp_path)
    up = impact.impact(dep, corpus, "SUB-000001", "up", 1)
    assert "downstream" not in up and _reached(up["upstream"]) == [(ITEM, 1, SUB, "Item")]
    down = impact.impact(dep, corpus, RULE, "down")
    assert "upstream" not in down and len(down["downstream"]) == 2
    for bad in (("NOPE-000001", "both", None), (ITEM, "sideways", None), (ITEM, "both", 0)):
        with pytest.raises(views.ViewError):
            impact.impact(dep, corpus, *bad)


def test_a_cycle_ends():
    nodes = {i: {"id": i, "type": "X", "title": "", "status": None} for i in "abc"}
    step = {"a": [("F", "b")], "b": [("F", "c")], "c": [("F", "a")]}
    reached = impact._closure("a", step, nodes, None, carried_by_reached=False)
    assert [(e["id"], e["depth"]) for e in reached] == [("b", 1), ("c", 2)]


def test_what_is_only_cited_in_prose_is_reported_apart(tmp_path):
    project = make_project(tmp_path)
    sub = project / ".criterion" / "subs" / "SUB-000001-first-sub.md"
    write(sub, sub.read_text(encoding="utf-8") + f"\nSee also `{RULE}` and `{ITEM}`.\n")
    dep = load(project)
    corpus = load_corpus(dep)
    found = impact.impact(dep, corpus, SUB)
    assert found["mentions"] == [RULE]  # the item is linked by a field: not a mention
    assert impact.impact(dep, corpus, RULE)["mentioned_by"] == [SUB]
    assert impact.impact(dep, corpus, SUB, "up", 1)["upstream"][0]["id"] == ITEM  # the mention is not followed


def _valid(value, schema: dict, root: dict | None = None) -> list[str]:
    """The shared checker of `spec/` schemas (`tests/schema_check.py`)."""
    return schema_check.problems(value, schema, root)


def test_the_verb_prints_what_the_schema_describes(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path)
    monkeypatch.chdir(project)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    for args in ([ITEM], [RULE, "--down"], ["AUTH", "--depth", "1"], [SUB, "--up"]):
        assert main(["impact", *args, "--json"]) == 0
        assert _valid(json.loads(capsys.readouterr().out), schema, schema) == []
    assert _valid({"id": 1}, schema, schema)  # the check itself refuses a wrong payload
    assert main(["impact", ITEM]) == 0
    text = capsys.readouterr().out
    assert "rests on: 2" in text and f"via {SUB}.Item" in text
    assert main(["impact", "NOPE-000001"]) == 1
    assert "no artifact, rule or domain" in capsys.readouterr().err


def test_the_server_answers_like_the_verb(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path, git=True)
    monkeypatch.chdir(project)
    httpd, token = serve.make_local(project, 0, poll=0.1)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        client = serve.Client(f"http://127.0.0.1:{httpd.server_address[1]}", token)
        capsys.readouterr()
        main(["impact", RULE, "--json"])
        assert client.call("GET", f"/impact/{RULE}") == json.loads(capsys.readouterr().out)
        main(["impact", SUB, "--up", "--depth", "1", "--json"])
        assert client.call("GET", f"/impact/{SUB}?direction=up&depth=1") == json.loads(capsys.readouterr().out)
        with pytest.raises(serve.ServeError) as err:
            client.call("GET", "/impact/NOPE-000001")
        assert err.value.status == 404
    finally:
        httpd.shutdown()
        httpd.server_close()
