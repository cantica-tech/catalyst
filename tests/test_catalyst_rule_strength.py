"""A rule's strength (decision S, REQ-000056): a `**Strength**` line of its
text, `must` when it states none; `check` errors on any other value; `view`,
`list` and `graph` carry it."""

from __future__ import annotations

from pathlib import Path

import pytest

from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst.validate import ERROR, validate
from catalyst.views import graph, list_items, view
from catalyst_fixtures import USERID, make_project, write

RULE = f"br-AUTH-000001-{USERID}"


def _doc(project: Path) -> Path:
    return project / ".criterion" / "rules" / "business" / "br-business-rules.md"


def _state(project: Path, line: str) -> None:
    doc = _doc(project)
    text = doc.read_text(encoding="utf-8")
    write(doc, text.replace("**Status:** ✅\n", f"**Status:** ✅\n{line}\n"))


def _strength(project: Path) -> str:
    dep = load(project)
    return load_corpus(dep).rules[RULE][0].strength


def test_a_rule_stating_none_is_must(tmp_path):
    project = make_project(tmp_path)
    assert _strength(project) == "must"


@pytest.mark.parametrize(
    "line,expected",
    [
        ("**Strength:** should", "should"),
        ("- **Strength**: `may`", "may"),
        ("**Strength**: MUST", "must"),
        ("* **Strength:** Should", "should"),
    ],
)
def test_the_strength_line_is_read(tmp_path, line, expected):
    project = make_project(tmp_path)
    _state(project, line)
    assert _strength(project) == expected
    dep = load(project)
    assert not [f for f in validate(dep, load_corpus(dep)) if f.code == "rule-strength"]


def test_an_unknown_strength_is_an_error(tmp_path):
    project = make_project(tmp_path)
    _state(project, "**Strength:** shall")
    dep = load(project)
    errors = [f for f in validate(dep, load_corpus(dep)) if f.level == ERROR]
    assert [f.code for f in errors] == ["rule-strength"]
    assert "shall" in errors[0].message


def test_a_one_file_rule_states_its_strength(tmp_path):
    project = make_project(tmp_path)
    root = project / ".criterion"
    other = f"br-AUTH-000002-{USERID}"
    write(root / "rules" / "business" / f"{other}-logout.md", "# Logout\n\n- **Strength**: may\n\nText.\n")
    write(root / "rules" / "rules.md", f"# Rules index\n\n- `{RULE}` — Login flow\n- `{other}-logout` — Logout\n")
    dep = load(project)
    assert load_corpus(dep).rules[other][0].strength == "may"


def test_view_list_and_graph_carry_it(tmp_path):
    project = make_project(tmp_path)
    _state(project, "**Strength:** should")
    dep = load(project)
    corpus = load_corpus(dep)
    assert view(dep, corpus, RULE)["strength"] == "should"
    assert [r["strength"] for r in list_items(dep, corpus, "rule", [])] == ["should"]
    assert [r["strength"] for r in graph(dep, corpus)["rules"]] == ["should"]
