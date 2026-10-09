"""Read-only views (roadmap R2 W1): list, journal show, view, backlog."""

import json

import pytest

from catalyst import views
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst_fixtures import USER, USERID, artifact, make_project, write

ITEM, SUB, RULE = f"ITEM-000001-{USERID}", f"SUB-000001-{USERID}", f"br-AUTH-000001-{USERID}"


def _dep(tmp_path):
    dep = load(make_project(tmp_path))
    return dep, load_corpus(dep)


def test_list_takes_a_prefix_name_or_folder_and_filters(tmp_path):
    dep, corpus = _dep(tmp_path)
    for kind in ("ITEM", "item", "items"):
        assert [r["id"] for r in views.list_items(dep, corpus, kind, [])] == [ITEM]
    assert views.list_items(dep, corpus, "items", views.parse_filters(["status=open"]))
    assert not views.list_items(dep, corpus, "items", views.parse_filters(["status=Done"]))
    assert views.list_items(dep, corpus, "items", views.parse_filters(["title=First*"]))
    assert [u["name"] for u in views.list_items(dep, corpus, "users", [])] == [USER]
    assert [r["id"] for r in views.list_items(dep, corpus, "rule", [])] == [RULE]
    ids = [r["id"] for r in views.list_items(dep, corpus, "all", [])]
    assert ids == [RULE, ITEM, SUB]


def test_list_refuses_an_unknown_type_and_a_bad_filter(tmp_path):
    dep, corpus = _dep(tmp_path)
    with pytest.raises(views.ViewError, match="unknown type"):
        views.list_items(dep, corpus, "widgets", [])
    with pytest.raises(views.ViewError, match="key=value"):
        views.parse_filters(["status"])


def test_view_shows_links_both_ways(tmp_path):
    dep, corpus = _dep(tmp_path)
    item = views.view(dep, corpus, ITEM)
    assert item["links"]["Targets"] == [RULE] and item["links"]["Subs"] == [SUB]
    assert {"id": SUB, "field": "Item"} in item["linked_from"]
    rule = views.view(dep, corpus, RULE)
    assert rule["type"] == "rule" and {"id": ITEM, "field": "Targets"} in rule["linked_from"]
    with pytest.raises(views.ViewError):
        views.view(dep, corpus, "ITEM-999999-nope")


def test_journal_show_filters_and_orders(tmp_path):
    project = make_project(tmp_path)
    entries = [
        {
            "timestamp": "2026-10-02T00:00:00Z",
            "actor": "ada",
            "command": "/status",
            "action": "update",
            "artifact": ITEM,
            "targets": [RULE],
            "intent": ["b"],
            "files": [],
        },
        {
            "timestamp": "2026-10-01T00:00:00Z",
            "actor": "grace",
            "command": "/create-item",
            "action": "create",
            "artifact": ITEM,
            "targets": [],
            "intent": ["a"],
            "files": [],
        },
    ]
    write(project / ".criterion" / "development" / "journal.jsonl", "".join(json.dumps(e) + "\n" for e in entries))
    dep = load(project)
    assert [e["intent"] for e in views.journal_entries(dep)] == [["a"], ["b"]]
    assert [e["actor"] for e in views.journal_entries(dep, since="2026-10-02")] == ["ada"]
    assert [e["actor"] for e in views.journal_entries(dep, actor="GRA")] == ["grace"]
    assert [e["actor"] for e in views.journal_entries(dep, rule=RULE)] == ["ada"]
    assert views.journal_entries(dep, artifact="other") == []


def test_backlog_reads_open_states_and_links_from_the_etds(tmp_path):
    project = make_project(tmp_path)
    write(
        project / ".criterion" / "items" / "ITEM-000002-done.md",
        artifact(
            f"ITEM-000002-{USERID}",
            "Done item",
            {"ID": f"`ITEM-000002-{USERID}`", "Status": "Done", "Targets": f"`{RULE}`", "Domain": "`AUTH`"},
        ),
    )
    write(
        project / ".criterion" / "items" / "ITEM-000003-loose.md",
        artifact(
            f"ITEM-000003-{USERID}",
            "Loose item",
            {"ID": f"`ITEM-000003-{USERID}`", "Status": "Open", "Targets": "", "Domain": "`AUTH`"},
        ),
    )
    dep = load(project)
    b = views.backlog(dep, load_corpus(dep))
    assert b["open"]["ITEM"] == {"Open": [ITEM, f"ITEM-000003-{USERID}"]}  # Done is closed
    assert {"id": f"ITEM-000003-{USERID}", "field": "Targets"} in b["missing_links"]
    assert b["rules_without_open_work"] == []  # ITEM-000001 targets it


def test_the_cli_prints_text_and_json(tmp_path, capsys):
    project = make_project(tmp_path)
    assert main(["--project", str(project), "list", "items"]) == 0
    assert ITEM in capsys.readouterr().out
    assert main(["--project", str(project), "view", ITEM, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == ITEM
    assert main(["--project", str(project), "backlog"]) == 0
    assert "Open work:" in capsys.readouterr().out
    assert main(["--project", str(project), "journal", "show"]) == 0
    assert "(no journal entries)" in capsys.readouterr().out
    assert main(["--project", str(project), "list", "widgets"]) == 1
