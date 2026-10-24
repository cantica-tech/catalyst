"""A module's enum value is a value, never emptiness (INV-30, BUG-000035): catalyst reads `none`, `n/a` and `-` as
empty in a field, so a module that offers one as an allowed value (the knowledge-base module's `None`, once) must not
see it reported missing, failing a guard, unset in a condition, or blanked in its index."""

from __future__ import annotations

import pytest

from catalyst import conditions, indexes
from catalyst.check import run as run_checks
from catalyst.corpus import is_unset, load_corpus
from catalyst.deployment import load
from catalyst.guards import failures
from catalyst_fixtures import USERID, make_project, write

ITEM = f"ITEM-000001-{USERID}"


@pytest.mark.parametrize(
    ("raw", "allowed", "unset"),
    [
        ("None", ["None", "Public"], False),
        ("none", ["None"], False),
        ("`N/A`", ["N/A"], False),
        ("None", [], True),
        ("*(none yet)*", ["None"], True),
        ("", ["None"], True),
        (None, ["None"], True),
        ("Public", [], False),
    ],
)
def test_an_allowed_value_is_never_unset(raw, allowed, unset):
    assert is_unset(raw, allowed) is unset


@pytest.fixture
def project(tmp_path):
    project = make_project(tmp_path, git=True)
    schema = project / ".criterion" / "modules" / "example-process" / "schemas" / "item.yaml"
    text = schema.read_text(encoding="utf-8").replace(
        "  - name: Subs\n",
        "  - name: Hosting\n    kind: enum\n    required: true\n    allowed_values:\n      - None\n      - Cloud\n"
        "  - name: Subs\n",
    )
    write(schema, text + "  guards:\n    Done:\n      - nonempty: Hosting\n      - holds: Hosting is set\n")
    item = project / ".criterion" / "items" / "ITEM-000001-first-item.md"
    write(item, item.read_text(encoding="utf-8").replace("| **Subs** |", "| **Hosting** | None |\n| **Subs** |"))
    return project


def test_a_required_enum_field_holding_none_is_not_missing(project):
    errors = run_checks(load(project)).errors
    assert not [e for e in errors if "Hosting" in e], errors


def test_guards_and_conditions_see_the_value(project):
    dep = load(project)
    corpus = load_corpus(dep)
    art = corpus.artifacts[ITEM][0]
    assert not [f for f in failures(dep, corpus, art, "Done") if "Hosting" in f]
    assert conditions.value_of(art, "Hosting", dep.etds["ITEM"]) == "None"
    assert conditions.value_of(art, "Hosting") == ""  # without the type, the old reading


def test_the_index_shows_the_value(project):
    dep = load(project)
    corpus = load_corpus(dep)
    header = "| ID | Hosting |\n|---|---|\n"
    rendered = indexes.render("# Items index\n\n" + header, "Items", corpus.artifacts[ITEM], dep.etds["ITEM"])
    assert f"| [{ITEM}](ITEM-000001-first-item.md) | None |" in rendered
