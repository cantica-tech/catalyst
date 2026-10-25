"""`catalyst sync plan|apply` (roadmap R2 W4)."""

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

import schema_check
from catalyst import sync
from catalyst.__main__ import main
from catalyst.deployment import load
from catalyst.init import init
from catalyst_fixtures import journal_entries
from test_catalyst_init import KERNEL, request

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _release(tmp: Path, version: str, kernel: Path = KERNEL) -> Path:
    """A kernel release tree at `version` (a copy of this checkout's kernel)."""
    out = tmp / f"kernel-{version}"
    shutil.copytree(kernel, out)
    (out / "manifest.json").write_text(json.dumps({"version": version}), encoding="utf-8")
    return out


def _deployment(tmp_path):
    req = request(tmp_path)
    init(req)
    subprocess.run(["git", "-C", str(req.project / ".criterion"), "add", "-A"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(req.project / ".criterion"),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "commit",
            "-qm",
            "init",
        ],
        check=True,
    )
    deployed = (req.project / ".criterion" / "version.txt").read_text(encoding="utf-8").strip()
    pointer = next(req.project.glob("*.catalyst"))
    data = json.loads(pointer.read_text(encoding="utf-8"))
    data["agent"] = "claude-code"
    pointer.write_text(json.dumps(data), encoding="utf-8")
    return req.project, deployed


def test_plan_lists_the_changes_and_apply_makes_them_then_nothing_is_left(tmp_path):
    project, deployed = _deployment(tmp_path)
    base = _release(tmp_path, deployed)
    new = _release(tmp_path, "9.9.9")
    rod = new / "rules-of-development.template.md"
    rod.write_text(rod.read_text(encoding="utf-8") + "\n<!-- a change in 9.9.9 -->\n", encoding="utf-8")
    (new / "INVARIANTS.md").write_text((new / "INVARIANTS.md").read_text(encoding="utf-8") + "\n", encoding="utf-8")

    dep = load(project)
    src = sync.Sources(dep, new, None, base, None)
    p = sync.plan(dep, src, sync.commands_dir(dep, None))
    kinds = {(a.kind, a.change) for a in p.actions}
    assert ("document", "update") in kinds and ("invariants", "update") in kinds
    assert ("version", "update") in kinds
    _, touched = sync.apply(dep, src, sync.commands_dir(dep, None), "ada", [])
    src.close()
    root = project / ".criterion"
    assert (root / "version.txt").read_text(encoding="utf-8").strip() == "9.9.9"
    assert "a change in 9.9.9" in (root / "CODE-OF-CONDUCT.md").read_text(encoding="utf-8")
    assert json.loads(next(project.glob("*.catalyst")).read_text(encoding="utf-8"))["kernel_version"] == "9.9.9"
    last = journal_entries(root)[-1]
    assert last["command"] == "/sync-framework" and last["artifact"].startswith("kernel 9.9.9")

    dep = load(project)
    src = sync.Sources(dep, new, None, base, None)
    assert sync.plan(dep, src, sync.commands_dir(dep, None)).actions == []
    src.close()


def test_the_agent_files_catalyst_once_wrote_into_the_project_are_retired(tmp_path):
    project, deployed = _deployment(tmp_path)
    base = _release(tmp_path, deployed)
    (base / "commands").mkdir()
    (base / "commands" / "status.md").write_text("as released\n", encoding="utf-8")
    new = _release(tmp_path, "9.9.9")
    commands = project / ".claude" / "commands"
    commands.mkdir(parents=True)
    (commands / "status.md").write_text("as released\n", encoding="utf-8")  # shipped copy
    (commands / "check-rules.md").write_text("First run `catalyst spec check-rules`.\n", encoding="utf-8")
    (commands / "user-add.md").write_text("my own procedure\n", encoding="utf-8")  # edited
    (commands / "dogfood.md").write_text("not catalyst's\n", encoding="utf-8")
    settings = project / ".claude" / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [{"hooks": [{"type": "command", "command": '"$HOME/.catalyst/bin/catalyst" hook stop'}]}],
                    "SessionStart": [
                        {"hooks": [{"type": "command", "command": "python3 .criterion/bin/catalyst.pyz hook start"}]},
                        {"hooks": [{"type": "command", "command": "echo mine"}]},
                    ],
                },
                "permissions": {"allow": ["Bash(ls)"]},
            }
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(project), "add", ".claude"], check=True)  # tracked, as init left them
    subprocess.run(
        ["git", "-C", str(project), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "wiring"], check=True
    )
    dep = load(project)
    src = sync.Sources(dep, new, None, base, None)
    p = sync.plan(dep, src, sync.commands_dir(dep, None))
    changes = {(a.kind, a.target): a.change for a in p.actions if a.kind in ("command", "agent-hook")}
    assert changes == {
        ("command", ".claude/commands/status.md"): "remove",
        ("command", ".claude/commands/check-rules.md"): "remove",
        ("command", ".claude/commands/user-add.md"): "conflict",
        ("agent-hook", ".claude/settings.json"): "remove",
    }
    sync.apply(dep, src, sync.commands_dir(dep, None), "ada", [])
    src.close()
    assert sorted(f.name for f in commands.iterdir()) == ["dogfood.md", "user-add.md"]
    assert json.loads(settings.read_text(encoding="utf-8")) == {
        "hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "echo mine"}]}]},
        "permissions": {"allow": ["Bash(ls)"]},
    }


def test_migrations_between_the_versions_are_listed_in_order(tmp_path):
    index = tmp_path / "migrations.md"
    index.write_text(
        "| [`0.46.0/a.md`](0.46.0/a.md) | `0.45.0` | `0.46.0` | a |\n"
        "| [`0.47.0/b.md`](0.47.0/b.md) | `0.46.1` | `0.47.0` | b |\n"
        "| [`0.48.0/c.md`](0.48.0/c.md) | `0.47.0` | `0.48.0` | c |\n",
        encoding="utf-8",
    )
    assert [m["file"] for m in sync.migrations(index, "0.46.0", "0.47.0", "kernel")] == ["0.47.0/b.md"]
    assert [m["file"] for m in sync.migrations(index, "0.45.0", "0.48.0", "kernel")] == [
        "0.46.0/a.md",
        "0.47.0/b.md",
        "0.48.0/c.md",
    ]


def test_the_cli_plans_without_writing(tmp_path, capsys):
    project, deployed = _deployment(tmp_path)
    base = _release(tmp_path, deployed)
    new = _release(tmp_path, "9.9.9")
    before = (project / ".criterion" / "version.txt").read_text(encoding="utf-8")
    assert main(["--project", str(project), "sync", "plan", "--kernel", str(new), "--base-kernel", str(base)]) == 0
    assert "Plan: kernel" in capsys.readouterr().out
    args = ["--project", str(project), "sync", "plan", "--kernel", str(new), "--base-kernel", str(base), "--json"]
    assert main(args) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["to_kernel"] == "9.9.9" and schema_check.problems(plan, schema_check.load("sync-plan")) == []
    assert (project / ".criterion" / "version.txt").read_text(encoding="utf-8") == before
    assert main(["--project", str(project), "sync", "plan", "--kernel", str(tmp_path / "nope")]) == 1


def test_verbatim_kernel_documents_follow_the_release_unless_edited(tmp_path):
    project, deployed = _deployment(tmp_path)
    base = _release(tmp_path, deployed)
    new = _release(tmp_path, "9.9.9")
    (new / "ANALYSIS-PLAYBOOK.md").write_text("playbook 9.9.9\n", encoding="utf-8")
    (new / "definitions" / "README.md").write_text("readme 9.9.9\n", encoding="utf-8")
    (project / ".criterion" / "definitions" / "README.md").write_text("my notes\n", encoding="utf-8")
    dep = load(project)
    src = sync.Sources(dep, new, None, base, None)
    p = sync.plan(dep, src, None)
    changes = {a.target: a.change for a in p.actions if a.kind == "kernel-doc"}
    assert changes == {".criterion/ANALYSIS-PLAYBOOK.md": "update", ".criterion/definitions/README.md": "conflict"}
    sync.apply(dep, src, None, "ada", [])
    src.close()
    root = project / ".criterion"
    assert (root / "ANALYSIS-PLAYBOOK.md").read_text(encoding="utf-8") == "playbook 9.9.9\n"
    assert (root / "definitions" / "README.md").read_text(encoding="utf-8") == "my notes\n"


def test_apply_brings_the_criterions_runtime_to_the_vendored_cli(tmp_path, monkeypatch):
    """BUG-000010: the launcher and the hooks run the criterion's `.venv`."""
    from catalyst import runtime as rt

    project, _ = _deployment(tmp_path)
    root = project / ".criterion"
    (root / "bin").mkdir(exist_ok=True)
    (root / "bin" / "catalyst.pyz").write_bytes(b"pyz")
    assert sync.refresh_runtime(load(project)) is None  # no runtime of its own: nothing to refresh
    (root / ".venv").mkdir()
    (root / ".venv" / rt.MARKER).write_text("0.1.0\n", encoding="utf-8")
    asked = []
    monkeypatch.setattr(rt, "pyz_version", lambda pyz: "9.9.9")
    monkeypatch.setattr(rt, "install_into", lambda c, v, pyz: (asked.append((c, v)), (c / ".venv", True))[1])
    assert sync.refresh_runtime(load(project)) == "9.9.9"
    assert asked == [(root, "9.9.9")]
    monkeypatch.setattr(rt, "install_into", lambda c, v, pyz: (c / ".venv", False))
    assert sync.refresh_runtime(load(project)) is None  # already there


def test_a_dropped_kernel_type_leaves_a_deployment_that_holds_none_of_it(tmp_path):
    project, deployed = _deployment(tmp_path)
    root = project / ".criterion"
    for rel in ("development/meta-tags/meta-tags.md", "development/meta-tags/templates/TEMPLATE-META-TAG-v1.md"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("# a seeded file\n", encoding="utf-8")
    (root / "definitions" / "meta-tag.md").write_text("# Meta-tag\n", encoding="utf-8")
    git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "an older kernel's meta-tags"], check=True)
    base, new = _release(tmp_path, deployed), _release(tmp_path, "9.9.9")
    dep = load(project)
    src = sync.Sources(dep, new, None, base, None)
    assert ("retired-type", "remove") in {(a.kind, a.change) for a in sync.plan(dep, src, None).actions}
    _, touched = sync.apply(dep, src, None, "ada", [])
    src.close()
    assert not (root / "development" / "meta-tags").exists() and not (root / "definitions" / "meta-tag.md").exists()
    assert root / "definitions" / "meta-tag.md" in touched  # journaled with the sync

    (root / "development" / "meta-tags").mkdir(parents=True)
    (root / "development" / "meta-tags" / "tag-owner-REQ-000001.md").write_text("# a tag\n", encoding="utf-8")
    dep = load(project)
    src = sync.Sources(dep, new, None, new, None)
    actions = [(a.kind, a.change) for a in sync.plan(dep, src, None).actions]
    src.close()
    assert ("retired-type", "skip") in actions and ("retired-type", "remove") not in actions


def test_a_dropped_type_stays_while_the_shared_gate_runs_an_older_kernel(tmp_path, monkeypatch):
    project, deployed = _deployment(tmp_path)
    root = project / ".criterion"
    (root / "definitions" / "meta-tag.md").write_text("# Meta-tag\n", encoding="utf-8")
    monkeypatch.setattr(sync, "gate_version", lambda dep: "0.68.1")
    actions = [(a.kind, a.change, a.detail) for a in sync._retired_types(load(project))]
    assert actions[0][:2] == ("retired-type", "skip") and "once the shared criterion runs 0.69.0" in actions[0][2]
    monkeypatch.setattr(sync, "gate_version", lambda dep: "0.69.0")
    assert [(a.kind, a.change) for a in sync._retired_types(load(project))] == [("retired-type", "remove")]


def test_a_type_the_module_adds_gets_its_folder_and_can_be_created(tmp_path):
    """A sync that brings a new type scaffolds its folder, templates and index
    as `init` does, so `catalyst new` works at once (REQ-000057)."""
    project, deployed = _deployment(tmp_path)
    base = _release(tmp_path, deployed)
    mod = tmp_path / "example-process-0.3.0"
    shutil.copytree(tmp_path / "example-process", mod)
    yaml = (mod / "module.yaml").read_text(encoding="utf-8")
    yaml = yaml.replace("version: 0.2.0", "version: 0.3.0").replace(
        "  - id: SUB\n    schema: schemas/sub.yaml\n",
        "  - id: SUB\n    schema: schemas/sub.yaml\n  - id: NOTE\n    schema: schemas/note.yaml\n",
    )
    yaml += "  - entity_type: NOTE\n    template_path: templates/note.template.md\n"
    (mod / "module.yaml").write_text(yaml, encoding="utf-8")
    (mod / "version.txt").write_text("0.3.0\n", encoding="utf-8")
    (mod / "schemas" / "note.yaml").write_text(
        "id_prefix: NOTE\nname: Note\nplural_name: Notes\nfolder: notes\ngrounding: none\n\nfields:\n"
        "  - name: ID\n    kind: text\n    required: true\n  - name: Status\n    kind: enum\n    required: true\n"
        "    allowed_values:\n      - Open\n      - Done\n",
        encoding="utf-8",
    )
    (mod / "templates" / "note.template.md").write_text(
        "# `NOTE-NNNNNN` — {{title}}\n\n| Field | Value |\n|---|---|\n| **ID** | `NOTE-NNNNNN` |\n"
        "| **Status** | Open |\n\n## Text\n\nText.\n",
        encoding="utf-8",
    )
    dep = load(project)
    src = sync.Sources(dep, KERNEL, mod, base, None)
    p = sync.plan(dep, src, sync.commands_dir(dep, None))
    assert ("type-folder", ".criterion/notes", "add") in {(a.kind, a.target, a.change) for a in p.actions}
    _, touched = sync.apply(dep, src, sync.commands_dir(dep, None), "ada", [])
    src.close()
    root = project / ".criterion"
    assert (root / "notes" / "templates" / "TEMPLATE-NOTE-v1.md").is_file()
    assert (root / "notes" / "notes.md").is_file()
    assert root / "notes" / "notes.md" in touched
    assert main(["--project", str(project), "new", "NOTE", "--title", "First note", "--as", "ada"]) == 0
    assert list((root / "notes").glob("NOTE-000001-*.md"))


def test_the_cli_is_built_from_a_checkout_when_packaging_is_not_importable(tmp_path, monkeypatch):
    """Run from a deployment's single-file CLI, `package_release` is not importable: the checkout builds its own CLI
    in a subprocess (BUG-000036: `catalyst module upgrade … --kernel <checkout>` crashed)."""
    from types import SimpleNamespace

    from catalyst.sync import Sources

    monkeypatch.setitem(sys.modules, "package_release", None)  # `import package_release` raises ImportError
    built = Sources._find_cli(SimpleNamespace(kernel=KERNEL, tmp=tmp_path))  # type: ignore[arg-type]
    assert built == tmp_path / "catalyst.pyz" and zipfile.is_zipfile(built)
