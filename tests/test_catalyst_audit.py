"""The audit pack (`catalyst audit`, R6.27; REQ-000061): each rule's chain to
everything that rests on it, the record's integrity, as data and as a page."""

from __future__ import annotations

import json

import schema_check
from catalyst import audit
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst_fixtures import USER, USERID, make_project

RULE = f"br-AUTH-000001-{USERID}"


def test_the_pack_holds_each_rule_with_what_rests_on_it(tmp_path):
    project = make_project(tmp_path)
    dep = load(project)
    pack = audit.build(dep, load_corpus(dep))
    assert schema_check.problems(pack, schema_check.load("audit")) == []
    (rule,) = pack["rules"]
    assert rule["id"] == RULE and rule["strength"] == "must"
    chain = {c["id"]: c for c in rule["chain"]}
    item, sub = f"ITEM-000001-{USERID}", f"SUB-000001-{USERID}"
    assert chain[item]["depth"] == 1 and chain[item]["via"] == {"id": RULE, "field": "Targets", "on": item}
    assert chain[sub]["depth"] == 2  # a sub rests on the item, which rests on the rule
    assert pack["signers"] == [{"name": USER, "signed": 2}]
    assert pack["project"] == "app" and pack["integrity"]["unapproved_rules"] == []


def test_the_page_is_self_contained_and_says_what_holds(tmp_path, capsys):
    project = make_project(tmp_path)
    out = tmp_path / "audit.html"
    assert main(["--project", str(project), "audit", "--html", str(out)]) == 0
    page = out.read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>") and "<script" not in page and "http" not in page.split("</style>")[0]
    assert f"<code>{RULE}</code>" in page and "Integrity" in page
    assert "print it for a PDF" in capsys.readouterr().out
    assert main(["--project", str(project), "audit", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["rules"][0]["id"] == RULE


def test_a_rule_nothing_rests_on_is_said(tmp_path):
    project = make_project(tmp_path)
    doc = project / ".criterion" / "rules" / "business" / "br-business-rules.md"
    other = f"br-AUTH-000002-{USERID}"
    doc.write_text(
        doc.read_text(encoding="utf-8").replace("## Linked Artifacts", f"### `{other}` Logout\n\n## Linked Artifacts"),
        encoding="utf-8",
    )
    index = project / ".criterion" / "rules" / "rules.md"
    index.write_text(index.read_text(encoding="utf-8") + f"- `{other}` — Logout\n", encoding="utf-8")
    dep = load(project)
    pack = audit.build(dep, load_corpus(dep))
    assert [r["chain"] for r in pack["rules"] if r["id"] == other] == [[]]
    assert "Nothing rests on it." in audit.render_html(pack)
    assert "1 with nothing resting on them" in audit.render(pack)


def test_the_local_server_answers_the_pack(tmp_path):
    import threading

    from catalyst import serve

    project = make_project(tmp_path, git=True)
    httpd, token = serve.make_local(project, 0, poll=0.1)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        client = serve.Client(f"http://127.0.0.1:{httpd.server_address[1]}", token)
        pack = client.call("GET", "/audit")
        assert schema_check.problems(pack, schema_check.load("audit")) == []
        assert pack["rules"][0]["id"] == RULE
    finally:
        httpd.shutdown()
        httpd.server_close()
