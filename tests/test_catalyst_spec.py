from __future__ import annotations

from catalyst.__main__ import main
from catalyst.deployment import load
from catalyst.spec import commands, spec
from catalyst_fixtures import make_project, write

COC = """# Rules of Development

## 3. Types

## 4. Slash-command entry points

- `/alpha <x>` — do alpha.
  More about alpha.
- `/beta` or `/b` — do beta.

When the user enters `/alpha <x>`, do the alpha thing.

Then finish alpha: see `/alpha`'s ending.

A paragraph about plugins that belongs to no command.

When the user enters `/beta`, do beta.

## 5. Next
"""


def project(tmp_path):
    p = make_project(tmp_path)
    write(p / ".criterion" / "CODE-OF-CONDUCT.md", COC)
    return p


def test_spec_selects_only_the_command(tmp_path):
    dep = load(project(tmp_path))
    text = spec(dep, "/alpha")
    assert "do alpha" in text and "More about alpha" in text and "alpha thing" in text
    assert "finish alpha" in text
    assert "plugins" not in text and "do beta" not in text
    assert commands(dep) == ["alpha", "beta"]


def test_spec_cli_and_budget(tmp_path, capsys):
    p = project(tmp_path)
    assert main(["--project", str(p), "spec", "beta"]) == 0
    assert "do beta" in capsys.readouterr().out
    assert main(["--project", str(p), "spec", "gamma"]) == 1
    assert main(["--project", str(p), "spec", "--budget", "1000"]) == 0
    assert main(["--project", str(p), "spec", "--budget", "5"]) == 1


def test_alias_reads_its_primary_commands_spec(tmp_path):
    dep = load(project(tmp_path))
    text = spec(dep, "b")
    assert "alias of /beta" in text and "When the user enters `/beta`" in text


CATALYZER = """# R

## 4. Commands

- `/catalyzer <sub>` — manage plugins.
- `/user-add <name>` — add a user.

Every `/catalyzer` subcommand resolves the plugin first.

Each plugin must carry name, uuid and version.

When the user enters `/user-add <name>`, add them.

## 5. Next
"""


def test_procedures_need_not_start_with_when_the_user_enters(tmp_path):
    p = make_project(tmp_path)
    write(p / ".criterion" / "CODE-OF-CONDUCT.md", CATALYZER)
    dep = load(p)
    assert "resolves the plugin first" in spec(dep, "catalyzer")
    from catalyst.spec import general

    assert "name, uuid and version" in general(dep)  # nothing is dropped


def test_prefix_is_not_an_alias(tmp_path):
    import pytest

    from catalyst.spec import SpecError

    p = make_project(tmp_path)
    write(p / ".criterion" / "CODE-OF-CONDUCT.md", CATALYZER)
    with pytest.raises(SpecError):
        spec(load(p), "user")


def test_every_paragraph_of_the_real_section4_lands_somewhere():
    """catalyst's own deployed CODE-OF-CONDUCT: the union of every command's
    spec and the general part covers every §4 paragraph."""
    from pathlib import Path

    from catalyst.spec import parse, section4_text

    coc = Path(__file__).resolve().parent.parent / "framework" / "kernel" / "rules-of-development.template.md"
    s = parse(coc.read_text(encoding="utf-8"))
    covered = sum(len(v) for v in s.procedures.values()) + len(s.general)
    paragraphs = [
        b
        for b in "\n".join(section4_text(coc.read_text(encoding="utf-8"))).split("\n\n")
        if b.strip() and not b.lstrip().startswith(("- `/", "#"))
    ]
    assert covered >= len([p for p in paragraphs if not p.startswith("  ")]) * 0.9


COLON_FORM = """# R

## 4. Slash-command entry points

- `/create-bug` — create a new bug artifact.
- `/create-req` or `/create-requirement` — create a new requirement artifact.

When the user enters `/create-bug: ...`, create a new bug artifact immediately
with the ID from `catalyst id next BUG`.

When the user enters `/create-req:` or `/create-requirement: ...`, create a
new requirement artifact immediately.

A paragraph that belongs to no command.

## 5. Next
"""


def test_colon_form_procedures_belong_to_their_command(tmp_path):
    p = make_project(tmp_path)
    write(p / ".criterion" / "CODE-OF-CONDUCT.md", COLON_FORM)
    dep = load(p)
    assert "catalyst id next BUG" in spec(dep, "create-bug")
    assert "new requirement artifact immediately" in spec(dep, "create-requirement")
    assert main(["--project", str(p), "spec", "--general"]) == 0


def test_colon_form_is_not_general(tmp_path, capsys):
    p = make_project(tmp_path)
    write(p / ".criterion" / "CODE-OF-CONDUCT.md", COLON_FORM)
    assert main(["--project", str(p), "spec", "--general"]) == 0
    out = capsys.readouterr().out
    assert "belongs to no command" in out
    assert "id next BUG" not in out and "requirement artifact immediately" not in out


def test_bullet_without_a_command_name_is_skipped(tmp_path):
    p = make_project(tmp_path)
    write(p / ".criterion" / "CODE-OF-CONDUCT.md", "## 4. C\n\n- `/x|y` — odd.\n- `/ok` — fine.\n\n## 5. N\n")
    assert commands(load(p)) == ["ok"]


PARTED = """# Rules of Development

## 4. Slash-command entry points

- `/create <type> <title>` — create an artifact; each type is a part.
- `/user` (`/user-add`, `/user-list`) — users: `add <name>`, `list`.

When the user enters `/create <type> <title>`, follow that type's part.

When the user enters `/user add <name>`, run `catalyst user add`.

### From module example

- `/create bug <title>` (`/create-bug`) — a bug.
- `/create req <title>` (`/create-req`, `/create-requirement`) — a requirement.

When the user enters `/create bug: ...` or `/create-bug: ...`, run `catalyst new BUG`.

Then write the bug's sections, as `/create` requires.

When the user enters `/create-req:` or `/create-requirement: ...`, run `catalyst new REQ`.

## 5. Next
"""


def test_a_command_with_parts_reads_one_part(tmp_path):
    from catalyst.spec import parse, spec_text

    s = parse(PARTED)
    bug = spec_text(s, "create-bug")
    assert "a bug." in bug and "catalyst new BUG" in bug and "the bug's sections" in bug
    assert "follow that type's part" in bug and "catalyst new REQ" not in bug and "a requirement." not in bug
    assert spec_text(s, "create", "bug") == bug
    req = spec_text(s, "create-requirement")
    assert "catalyst new REQ" in req and "catalyst new BUG" not in req and "the bug's sections" not in req
    whole = spec_text(s, "create")
    assert "a bug." in whole and "a requirement." in whole and "catalyst new" not in whole
    assert "`catalyst spec create <part>`" in whole and "create-bug" in whole
    # a command without parts reads whole, whatever the part asked
    assert spec_text(s, "user", "add") == spec_text(s, "user") and "`/user-add`" in spec_text(s, "user")


def test_the_catalogue_lists_each_command_and_each_part_once(tmp_path, capsys):
    """R6.8: what a command palette reads, from the same §4 as `catalyst spec`."""
    import json

    import schema_check
    from catalyst.spec import catalogue, parse

    by = {c["name"]: c for c in catalogue(parse(PARTED))}
    assert sorted(by) == ["create", "user"]
    create = by["create"]
    assert create["usage"] == "/create <type> <title>" and create["summary"].startswith("create an artifact")
    assert [(p["part"], p["usage"], p["aliases"]) for p in create["parts"]] == [
        ("bug", "/create bug <title>", ["create-bug"]),
        ("req", "/create req <title>", ["create-req", "create-requirement"]),
    ]
    assert by["user"]["aliases"] == ["user-add", "user-list"] and by["user"]["parts"] == []
    p = make_project(tmp_path)
    write(p / ".criterion" / "CODE-OF-CONDUCT.md", PARTED)
    capsys.readouterr()
    assert main(["--project", str(p), "spec", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert schema_check.problems(listed, schema_check.load("commands")) == []
    assert main(["--project", str(p), "spec", "create", "bug", "--json"]) == 0
    one = json.loads(capsys.readouterr().out)
    assert schema_check.problems(one, schema_check.load("command-spec")) == []
    assert one["part"] == "bug" and one["text"] == spec(load(p), "create", "bug")
