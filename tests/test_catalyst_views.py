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


def test_graph_carries_rules_links_and_the_entity_types(tmp_path, monkeypatch, capsys):
    dep, corpus = _dep(tmp_path)
    g = views.graph(dep, corpus)
    assert {r["id"]: r["domain"] for r in g["rules"]} == {RULE: "AUTH"}
    assert [(r["title"], r["status"]) for r in g["rules"]] == [("Login flow", "✅")]
    assert g["domains"] == [{"code": "AUTH", "file": None, "title": ""}]  # its document is not written
    item = next(a for a in g["artifacts"] if a["id"] == ITEM)
    assert item["links"]["Subs"] == [SUB] and item["links"]["Targets"] == [RULE]
    assert item["file"] == "items/ITEM-000001-first-item.md"
    sub = next(a for a in g["artifacts"] if a["id"] == SUB)
    assert sub["links"]["Item"] == [ITEM]
    assert {"ITEM", "SUB"} <= set(g["types"])
    assert {f["name"] for f in g["types"]["ITEM"]["fields"]} >= {"Status", "Targets", "Subs"}
    assert g["types"]["ITEM"]["closed_states"] == list(dep.etds["ITEM"].workflow.closed_states)
    monkeypatch.chdir(tmp_path / "app")
    assert main(["graph", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == json.loads(json.dumps(g, default=str))
    assert main(["graph"]) == 0
    assert "1 rule(s)" in capsys.readouterr().out


ROW_SCHEMA = """id_prefix: ROW
name: Row
plural_name: Rows
folder: rows
grounding: none
naming: free-form
fields:
  - name: ID
    kind: text
"""


def test_graph_carries_table_rows_and_what_each_item_mentions(tmp_path):
    project = make_project(tmp_path)
    root = project / ".criterion"
    mod = root / "modules" / "example-process"
    write(mod / "schemas" / "row.yaml", ROW_SCHEMA)
    module = (mod / "module.yaml").read_text(encoding="utf-8")
    write(mod / "module.yaml", module + "  - id: ROW\n    schema: schemas/row.yaml\n")
    row = f"ROW-000001-{USERID}"
    write(
        root / "rows" / "rows.md",
        f"# Rows\n\n| ID | Title | Linked |\n|---|---|---|\n| `{row}` | First | `ITEM-000001` |\n",
    )
    item = root / "items" / "ITEM-000001-first-item.md"
    write(
        item,
        item.read_text(encoding="utf-8")
        + f"\nSee `{SUB}`, `{ITEM}` itself, `NOPE-000001` and `ITEM-000001-\n{USERID}`/`{row}`.\n",
    )
    rules = root / "rules" / "business" / "br-business-rules.md"
    write(
        rules, rules.read_text(encoding="utf-8").replace("**Status:** ✅\n", f"**Status:** ✅\n\nServed by `{ITEM}`.\n")
    )
    dep = load(project)
    g = views.graph(dep, load_corpus(dep))
    rows = [a for a in g["artifacts"] if a.get("row")]
    assert rows == [
        {
            "id": row,
            "type": "ROW",
            "file": "rows/rows.md",
            "line": 5,
            "row": True,
            "fields": {"ID": f"`{row}`", "Title": "First", "Linked": "`ITEM-000001`"},
            "links": {},
            "mentions": [ITEM],
        }
    ]
    first = next(a for a in g["artifacts"] if a["id"] == ITEM)
    # its whole text, field table included; its own ID and unknown tokens left out
    assert set(first["mentions"]) == {RULE, "AUTH", SUB, row}
    assert next(r for r in g["rules"] if r["id"] == RULE)["mentions"] == [ITEM]
    assert "0 rule" not in views.render_graph(g) and ", 2 open," in views.render_graph(g)


def test_graph_reads_a_one_file_rule_and_a_domain_document(tmp_path):
    from test_catalyst_rule_shapes import _per_file_rules

    project = make_project(tmp_path, git=True)
    rule, old = _per_file_rules(project)
    write(project / ".criterion" / "rules" / "domains" / "cor-CORE.INGEST-ingest.md", "# `CORE.INGEST` — Ingest\n")
    dep = load(project)
    g = views.graph(dep, load_corpus(dep))
    rules = {r["id"]: r for r in g["rules"]}
    assert (rules[rule]["title"], rules[rule]["status"]) == ("Logs", "✅ implemented")  # its rules.md entry
    assert rules[rule]["domain"] == "CORE.INGEST" and rules[old]["status"].startswith("🗑 retired")
    domain = next(d for d in g["domains"] if d["code"] == "CORE.INGEST")
    assert domain == {
        "code": "CORE.INGEST",
        "file": "rules/domains/cor-CORE.INGEST-ingest.md",
        "title": "`CORE.INGEST` — Ingest",
    }


def test_view_takes_an_id_as_people_write_it(tmp_path, capsys):
    """BUG-000012: view, impact and the history resolve an ID the same way."""
    dep, corpus = _dep(tmp_path)
    assert views.view(dep, corpus, "ITEM-000001")["id"] == ITEM  # short
    assert views.view(dep, corpus, RULE)["id"] == RULE
    assert views.resolve(corpus, "SUB-000001") == SUB
    assert views.resolve(corpus, "NOPE-000001") is None
    with pytest.raises(views.ViewError, match="no artifact or rule 'NOPE-000001'"):
        views.view(dep, corpus, "NOPE-000001")
    # the same number signed by two people: the short form names both, and says so
    other = "ITEM-000001-Zz9yX8wV"
    write(
        dep.root / "items" / "ITEM-000001-another.md",
        artifact(other, "Another", {"ID": f"`{other}`", "Status": "Open", "Targets": f"`{RULE}`", "Domain": "`AUTH`"}),
    )
    corpus = load_corpus(load(dep.project_root))
    with pytest.raises(views.ViewError, match=f"'ITEM-000001' names several: {ITEM}, {other}"):
        views.resolve(corpus, "ITEM-000001")
    assert views.view(dep, corpus, other)["id"] == other  # the full ID is never ambiguous


def test_view_takes_a_meta_rule_as_the_handbook_writes_it(tmp_path):
    project = make_project(tmp_path)
    write(
        project / ".criterion" / "rules" / "Rules-of-Rules.md",
        f"# Handbook\n\n## 15. `rr-META-000015-{USERID}` Shape\n\nText.\n",
    )
    dep = load(project)
    assert views.view(dep, load_corpus(dep), "rr-META-015")["id"] == f"rr-META-000015-{USERID}"


def test_view_gives_a_rule_its_title_status_domain_and_text(tmp_path):
    """R6.14: a rule's page shows the rule itself, read as `graph` reads it."""
    from test_catalyst_rule_shapes import _per_file_rules

    project = make_project(tmp_path, git=True)
    rule, old = _per_file_rules(project)
    write(
        project / ".criterion" / "rules" / "Rules-of-Rules.md",
        f"# Handbook\n\n## 15. `rr-META-000015-{USERID}` Shape\n\n✅ working. Text.\n\n## 16. Next\n",
    )
    dep = load(project)
    corpus = load_corpus(dep)
    one = views.view(dep, corpus, rule)
    assert (one["title"], one["status"], one["domain"]) == ("Logs", "✅ implemented", "CORE.INGEST")
    assert one["text"] == (project / ".criterion" / one["file"]).read_text(encoding="utf-8").rstrip("\n")  # its file
    meta = views.view(dep, corpus, f"rr-META-000015-{USERID}")
    assert (meta["title"], meta["status"]) == ("Shape", "✅ working. Text.")
    assert meta["text"].startswith("## 15.") and "Text." in meta["text"] and "Next" not in meta["text"]
    assert views.view(dep, corpus, old)["retired"] is True


def test_a_table_row_is_listed_with_its_place_and_viewed_from_it(tmp_path):
    """An item kept as a row (a free-form type) is one `list all` names with its file and line, and one `view`
    shows, by its full or short ID, as its fields and journal: never 'no artifact' (catalyst-docs' report)."""
    project = make_project(tmp_path)
    root = project / ".criterion"
    mod = root / "modules" / "example-process"
    write(mod / "schemas" / "row.yaml", ROW_SCHEMA)
    module = (mod / "module.yaml").read_text(encoding="utf-8")
    write(mod / "module.yaml", module + "  - id: ROW\n    schema: schemas/row.yaml\n")
    row = f"ROW-000001-{USERID}"
    write(
        root / "rows" / "rows.md",
        f"# Rows\n\n| ID | Title | Status |\n|---|---|---|\n| `{row}` | First row | Open |\n",
    )
    dep = load(project)
    corpus = load_corpus(dep)
    listed = [r for r in views.list_items(dep, corpus, "all", []) if r["type"] == "ROW"]
    assert listed == [{"id": row, "type": "ROW", "file": "rows/rows.md", "line": 5}]
    for asked in (row, "ROW-000001"):
        shown = views.view(dep, corpus, asked)
        assert shown["id"] == row and shown["row"] is True and shown["title"] == "First row"
        assert shown["status"] == "Open" and shown["file"] == "rows/rows.md" and shown["line"] == 5
        assert shown["fields"] == {"ID": f"`{row}`", "Title": "First row", "Status": "Open"}
        assert shown["text"].startswith(f"| `{row}`") and shown["links"] == {} and shown["journal"] == []
    assert "First row" in views.render_view(views.view(dep, corpus, row))


def test_view_takes_several_ids_in_one_process(tmp_path, capsys):
    """REQ-000105: `view --json ID ID` is one JSON array of the single views; one ID prints as before."""
    project = make_project(tmp_path)
    singles = []
    for i in (ITEM, RULE):
        assert main(["--project", str(project), "view", i, "--json"]) == 0
        singles.append(json.loads(capsys.readouterr().out))
    assert main(["--project", str(project), "view", ITEM, RULE, "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == singles
    assert main(["--project", str(project), "view", ITEM, RULE]) == 0
    out = capsys.readouterr().out
    assert out.index(ITEM) < out.index(f"{RULE}  (rule)")


def test_view_of_several_ids_fails_whole_on_an_unknown_one(tmp_path, capsys):
    project = make_project(tmp_path)
    assert main(["--project", str(project), "view", ITEM, "ITEM-999999-nope", "--json"]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and "ITEM-999999-nope" in captured.err
