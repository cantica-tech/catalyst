"""`catalyst try <verb …>` (design 27, REQ-000054): the change made on a
scratch copy of the criterion and what it would do; nothing in the
criterion changes and the copy is removed."""

from __future__ import annotations

import json
import os
from pathlib import Path

import schema_check
from catalyst import gates, trial
from catalyst.__main__ import main
from catalyst_fixtures import USERID, journal_entries, write
from test_catalyst_gates import _iam
from test_catalyst_history import RULE, lived  # noqa: F401 (the fixture)
from test_catalyst_proposals import project  # noqa: F401 (the fixture)


def _tree(root: Path) -> dict[str, bytes]:
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", ".venv")]
        for name in filenames:
            path = Path(dirpath) / name
            out[path.relative_to(root).as_posix()] = path.read_bytes()
    return out


def test_a_try_reports_the_change_and_leaves_the_criterion_as_it_was(lived, tmp_path, monkeypatch, capsys):  # noqa: F811
    proj, item, _ = lived
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    root = proj / ".criterion"
    before, entries = _tree(root), len(journal_entries(root))
    assert main(["try", "--json", "rename", item, "--title", "A new title", "--as", "ada", "--intent", "x"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert schema_check.problems(report, schema_check.load("try")) == []
    assert report["ok"] and report["refused"] is None and report["change"].startswith("catalyst rename ")
    written = {f["path"]: f for f in report["files"]}
    assert any(p.endswith("-a-new-title.md") and f["before"] is None for p, f in written.items())
    assert report["impact"]["id"] == item
    assert _tree(root) == before and len(journal_entries(root)) == entries  # nothing kept
    assert not list((tmp_path / "home" / "scratch").iterdir())  # the copy is gone


def test_a_refused_change_is_the_answer(lived, tmp_path, monkeypatch, capsys):  # noqa: F811
    _, item, _ = lived
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    assert main(["try", "status", "set", item, "Done", "--as", "ada"]) == 1  # it is Done already
    out = capsys.readouterr().out
    assert "refused: catalyst: " in out and "already Done" in out
    assert main(["try", "share", "push", "-m", "x"]) == 1
    assert "writing verbs" in capsys.readouterr().err
    assert main(["try", "rename", item, "--title", "x", "--working-copy", "."]) == 1


def test_a_try_says_the_findings_it_clears_and_the_approvals_it_leaves(lived, tmp_path, monkeypatch, capsys):  # noqa: F811
    proj, _, _ = lived
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    _iam(proj)
    gated = json.loads((proj / ".criterion" / gates.GATES).read_text())
    gated["gates"][0]["approvals"] = 1
    write(proj / ".criterion" / gates.GATES, json.dumps(gated))
    assert main(["try", "--json", "approve", RULE, "--gate", "auth-rules", "--as", "bob"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert [f["text"] for f in report["check"]["cleared"] if "gates unapproved" in f["text"]]
    fields = ["--field", f"Targets={RULE}", "--field", "Domain=AUTH"]
    assert main(["try", "--json", "new", "ITEM", "--title", "Third", "--as", "ada", *fields]) == 0
    report = json.loads(capsys.readouterr().out)
    assert [(g["gate"], g["missing"]) for g in report["gates"]] == [("item-done", 1)]  # one move from Done


def test_trying_a_proposal_shows_what_accepting_it_writes(project, tmp_path, monkeypatch, capsys):  # noqa: F811 (the fixture)
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    item = f"ITEM-000001-{USERID}"
    path = next((project / ".criterion" / "items").glob("ITEM-000001-*.md"))
    src = write(tmp_path / "p.md", path.read_text(encoding="utf-8").replace("Text.", "Tried text."))
    assert main(["propose", item, "--from", str(src), "--as", "bob", "--json"]) == 0
    case = json.loads(capsys.readouterr().out)["case"]
    assert main(["try", "--json", "--proposal", case, "--as", "ada"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] and any(
        f["path"] == path.relative_to(project / ".criterion").as_posix() for f in report["files"]
    )
    assert "Tried text." not in path.read_text(encoding="utf-8")  # only the copy changed
    assert main(["try", "--proposal", case, "--as", "bob"]) == 1  # a `propose` role: the real refusal, said
    assert "refused: catalyst: `accept` needs a `full` reconciliation role" in capsys.readouterr().out


def test_a_try_needs_the_criterions_history(tmp_path):
    from catalyst.deployment import load
    from catalyst_fixtures import make_project

    plain = make_project(tmp_path / "plain", git=False)
    try:
        trial.make(load(plain))
    except trial.TryError as exc:
        assert "not a git repository" in str(exc)
    else:
        raise AssertionError("a try without git history must be refused")
