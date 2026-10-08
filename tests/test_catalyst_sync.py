"""`catalyst sync plan|apply` (roadmap R2 W4)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from catalyst import sync
from catalyst.__main__ import main
from catalyst.deployment import load
from catalyst.init import init
from test_catalyst_init import KERNEL, request

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _release(tmp: Path, version: str, kernel: Path = KERNEL) -> Path:
    """A kernel release tree at `version` (a copy of this checkout's kernel)."""
    out = tmp / f"kernel-{version}"
    shutil.copytree(kernel, out)
    (out / "manifest.json").write_text(json.dumps({"version": version}), encoding="utf-8")
    shutil.copytree(KERNEL.parent.parent / ".claude" / "commands", out / "commands")
    return out


def _deployment(tmp_path):
    req = request(tmp_path, commands_dir=Path(".claude/commands"))
    init(req)
    subprocess.run(["git", "-C", str(req.project / ".criterion"), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(req.project / ".criterion"), "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-qm", "init"], check=True)
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
    status = new / "commands" / "status.md"
    status.write_text(status.read_text(encoding="utf-8") + "\nNew line.\n", encoding="utf-8")

    dep = load(project)
    src = sync.Sources(dep, new, None, base, None)
    p = sync.plan(dep, src, sync.commands_dir(dep, None))
    kinds = {(a.kind, a.change) for a in p.actions}
    assert ("document", "update") in kinds and ("invariants", "update") in kinds
    assert ("command", "update") in kinds and ("version", "update") in kinds
    _, touched = sync.apply(dep, src, sync.commands_dir(dep, None), "ada", [])
    src.close()
    root = project / ".criterion"
    assert (root / "version.txt").read_text(encoding="utf-8").strip() == "9.9.9"
    assert "a change in 9.9.9" in (root / "CODE-OF-CONDUCT.md").read_text(encoding="utf-8")
    assert (project / ".claude" / "commands" / "status.md").read_text(encoding="utf-8").endswith("New line.\n")
    assert json.loads(next(project.glob("*.catalyst")).read_text(encoding="utf-8"))["kernel_version"] == "9.9.9"
    last = json.loads((root / "development" / "journal.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert last["command"] == "/sync-framework" and last["artifact"].startswith("kernel 9.9.9")

    dep = load(project)
    src = sync.Sources(dep, new, None, base, None)
    assert sync.plan(dep, src, sync.commands_dir(dep, None)).actions == []
    src.close()


def test_a_locally_edited_command_file_is_reported_not_overwritten(tmp_path):
    project, deployed = _deployment(tmp_path)
    base = _release(tmp_path, deployed)
    new = _release(tmp_path, "9.9.9")
    (new / "commands" / "status.md").write_text("release text\n", encoding="utf-8")
    mine = project / ".claude" / "commands" / "status.md"
    mine.write_text("my own edit\n", encoding="utf-8")
    dep = load(project)
    src = sync.Sources(dep, new, None, base, None)
    p = sync.plan(dep, src, sync.commands_dir(dep, None))
    assert any(a.kind == "command" and a.change == "conflict" and a.target.endswith("status.md") for a in p.actions)
    sync.apply(dep, src, sync.commands_dir(dep, None), "ada", [])
    src.close()
    assert mine.read_text(encoding="utf-8") == "my own edit\n"


def test_migrations_between_the_versions_are_listed_in_order(tmp_path):
    index = tmp_path / "migrations.md"
    index.write_text("| [`0.46.0/a.md`](0.46.0/a.md) | `0.45.0` | `0.46.0` | a |\n"
                     "| [`0.47.0/b.md`](0.47.0/b.md) | `0.46.1` | `0.47.0` | b |\n"
                     "| [`0.48.0/c.md`](0.48.0/c.md) | `0.47.0` | `0.48.0` | c |\n", encoding="utf-8")
    assert [m["file"] for m in sync.migrations(index, "0.46.0", "0.47.0", "kernel")] == ["0.47.0/b.md"]
    assert [m["file"] for m in sync.migrations(index, "0.45.0", "0.48.0", "kernel")] == [
        "0.46.0/a.md", "0.47.0/b.md", "0.48.0/c.md"]


def test_the_cli_plans_without_writing(tmp_path, capsys):
    project, deployed = _deployment(tmp_path)
    base = _release(tmp_path, deployed)
    new = _release(tmp_path, "9.9.9")
    before = (project / ".criterion" / "version.txt").read_text(encoding="utf-8")
    assert main(["--project", str(project), "sync", "plan", "--kernel", str(new), "--base-kernel", str(base)]) == 0
    assert "Plan: kernel" in capsys.readouterr().out
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
