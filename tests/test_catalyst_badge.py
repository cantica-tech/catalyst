"""The README badge (`catalyst badge`, R6.28; REQ-000062)."""

from __future__ import annotations

import pytest

from catalyst import badge
from catalyst.__main__ import main
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst_fixtures import make_project


def test_the_check_badge_says_passing_or_counts_the_errors(tmp_path, monkeypatch):
    from catalyst import check
    from catalyst.init import init
    from test_catalyst_init import request

    req = request(tmp_path)
    init(req)  # a deployment as init makes it: check passes
    dep = load(req.project)
    label, value, colour = badge.measure(dep, load_corpus(dep), "check")
    assert (label, value) == ("catalyst", "passing") and colour in (badge.GOOD, badge.WARN)
    monkeypatch.setattr(check, "run", lambda dep: check.Report(errors=["a", "b"]))
    assert badge.measure(dep, load_corpus(dep), "check") == ("catalyst", "2 errors", badge.BAD)
    monkeypatch.setattr(check, "run", lambda dep: check.Report(errors=["a"]))
    assert badge.measure(dep, load_corpus(dep), "check")[1] == "1 error"


def test_the_chain_badge_counts_the_live_rules_something_rests_on(tmp_path):
    project = make_project(tmp_path)
    dep = load(project)
    assert badge.measure(dep, load_corpus(dep), "chain") == ("rules in use", "1/1", badge.GOOD)
    with pytest.raises(ValueError):
        badge.measure(dep, load_corpus(dep), "stars")


def test_the_svg_says_it_in_text_and_is_written_where_asked(tmp_path, capsys):
    image = badge.svg("catalyst", "passing", badge.GOOD)
    assert image.startswith("<svg") and 'aria-label="catalyst: passing"' in image and "<title>" in image
    assert "<script" not in image and "&" not in badge.svg("a", "b", "#000").split("<title>")[0]
    project = make_project(tmp_path)
    out = tmp_path / "badge.svg"
    assert main(["--project", str(project), "badge", "--metric", "chain", "--out", str(out)]) == 0
    assert "rules in use" in out.read_text(encoding="utf-8") and "rules in use 1/1" in capsys.readouterr().out
