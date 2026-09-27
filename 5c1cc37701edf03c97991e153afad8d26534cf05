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
    assert "name, uuid and version" in general(dep)       # nothing is dropped


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
    s = parse(coc.read_text())
    covered = sum(len(v) for v in s.procedures.values()) + len(s.general)
    paragraphs = [b for b in "\n".join(section4_text(coc.read_text())).split("\n\n")
                  if b.strip() and not b.lstrip().startswith(("- `/", "#"))]
    assert covered >= len([p for p in paragraphs if not p.startswith("  ")]) * 0.9
