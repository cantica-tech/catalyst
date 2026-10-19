"""R4.8: `status set --through` reaches a later state through the states
between, each transition, gate and guard checked, in one journal entry; an
intent too thin to tell why is warned about."""

from __future__ import annotations

import pytest

from catalyst.__main__ import main
from catalyst.journal import intent_thin
from catalyst_fixtures import USERID, journal_entries, make_project, write

ITEM = f"ITEM-000001-{USERID}"


@pytest.fixture
def staged(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path, git=True)
    item = project / ".criterion" / "modules" / "example-process" / "schemas" / "item.yaml"
    text = item.read_text(encoding="utf-8")
    text = text.replace("      - Open\n      - Done\n", "      - Open\n      - Review\n      - Done\n", 1)
    text = text.replace(
        "  states:\n    - Open\n    - Done\n",
        "  states:\n    - Open\n    - Review\n    - Done\n"
        "  transitions:\n    - from: Open\n      to: Review\n    - from: Review\n      to: Open\n"
        "    - from: Review\n      to: Done\n",
        1,
    )
    write(item, text + "  guards:\n    Done:\n      - section_written: Notes\n")
    template = project / ".criterion" / "items" / "templates" / "TEMPLATE-ITEM-v1.md"
    write(template, "# `ITEM-NNNNNN` — {{title}}\n\n## Notes\n\nWhat was noticed.\n")
    item_file = project / ".criterion" / "items" / "ITEM-000001-first-item.md"
    write(item_file, item_file.read_text(encoding="utf-8") + "\n## Notes\n\nWhat was noticed.\n")
    monkeypatch.chdir(project)
    capsys.readouterr()
    return project, item_file


def _status(item_file) -> str:
    return next(line for line in item_file.read_text(encoding="utf-8").splitlines() if "**Status**" in line)


def test_a_state_two_steps_away_is_refused_without_through(staged, capsys):
    _, item_file = staged
    assert main(["status", "set", ITEM, "Done", "--as", "ada"]) == 1
    assert "--through walks the states between" in capsys.readouterr().err
    assert "Open" in _status(item_file)


def test_through_checks_every_state_and_writes_one_entry(staged, capsys):
    project, item_file = staged
    why = "the review found nothing to change"
    assert main(["status", "set", ITEM, "Done", "--through", "--as", "ada", "--intent", why]) == 1
    assert "cannot become Done" in capsys.readouterr().err  # the guard of the last state, nothing written
    assert "Open" in _status(item_file)
    item_file.write_text(
        item_file.read_text(encoding="utf-8").replace("What was noticed.", "Reviewed by hand."), encoding="utf-8"
    )
    assert main(["status", "set", ITEM, "Done", "--through", "--as", "ada", "--intent", why]) == 0
    assert "Done" in _status(item_file)
    (entry,) = [e for e in journal_entries(project / ".criterion") if e["command"] == "/status"]
    assert entry["intent"] == [why, f"{ITEM}: Open -> Review -> Done"]


def test_through_does_not_go_with_force(staged, capsys):
    assert main(["status", "set", ITEM, "Done", "--through", "--force", "--as", "ada"]) == 1
    assert "does not go with --force" in capsys.readouterr().err


@pytest.mark.parametrize(
    "intent, thin",
    [
        (["work starts"], True),
        (["acceptance met"], True),
        (["R4.8"], True),
        (["R0.5, ADR-002"], True),
        (["design 25 a3"], True),
        ([], False),
        (["written and verified"], False),
        (["the review found nothing to change"], False),
        (["R4.8: placeholder intents warned about"], False),
    ],
)
def test_a_thin_intent(intent, thin):
    assert intent_thin(intent) is thin


def test_a_thin_intent_is_warned_about_and_the_change_still_made(staged, capsys):
    _, item_file = staged
    assert main(["status", "set", ITEM, "Review", "--as", "ada", "--intent", "work starts"]) == 0
    assert "says too little to tell why" in capsys.readouterr().err
    assert "Review" in _status(item_file)
    assert main(["status", "set", ITEM, "Open", "--as", "ada", "--intent", "the review is not ready yet"]) == 0
    assert "says too little" not in capsys.readouterr().err
