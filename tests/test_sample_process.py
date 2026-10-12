"""The in-repo `sample-process` module (module v3 M5, REQ-000026): a second
process module, in format v3, that is not about software. CI installs it and
runs its work cycle, so the kernel is proven to know no particular module
(INV-30, law L9)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from catalyst.__main__ import main
from catalyst.init import init
from module_loader import load_module
from test_catalyst_init import KERNEL, request

SAMPLE = KERNEL.parent / "modules" / "sample-process"


def _main(capsys, *args: str) -> tuple[int, str]:
    capsys.readouterr()
    code = main(list(args))
    return code, capsys.readouterr().out


def test_the_sample_is_a_v3_module_with_its_own_namespace():
    manifest = load_module(module_dir=SAMPLE)
    assert manifest is not None and manifest.namespace == "SP"
    assert set(manifest.entity_types) == {"POLICY", "TASK"}
    assert all(e.generated for e in manifest.entity_types.values())
    assert not (SAMPLE / "schemas").exists()
    assert [t.id for t in manifest.tiers] == ["chore", "task"]


def test_install_and_run_the_sample_process(tmp_path, monkeypatch, capsys):
    req = request(tmp_path, module_id="sample-process", module=SAMPLE, rule_docs=[])
    init(req)
    root = req.at
    assert root is not None
    assert "| **Policy** | *(none yet)* |" in (root / "tasks" / "templates" / "TEMPLATE-TASK-v1.md").read_text(
        encoding="utf-8"
    )
    assert "the ground every task stands on" in (root / "definitions" / "policy.md").read_text(encoding="utf-8")
    monkeypatch.chdir(req.project)

    code, out = _main(capsys, "new", "POLICY", "--title", "Keep records", "--as", "ada", "--json")
    assert code == 0, out
    policy = json.loads(out)["id"]
    code, out = _main(
        capsys, "new", "TASK", "--title", "File them", "--field", f"Policy={policy}", "--as", "ada", "--json"
    )
    assert code == 0, out
    task = json.loads(out)["id"]
    policy_file = next((root / "policies").glob("POLICY-*.md"))
    assert f"`{task}`" in policy_file.read_text(encoding="utf-8")  # the back-reference

    assert _main(capsys, "status", "set", policy, "Active", "--as", "ada")[0] == 1  # Statement unwritten
    assert _main(capsys, "status", "set", task, "Done", "--as", "ada")[0] == 1  # Outcome unwritten
    for f, old, new in (
        (policy_file, "What the policy requires, in one or two sentences.", "Every record is kept a year."),
        (next((root / "tasks").glob("TASK-*.md")), "What was done, and how it was checked.", "Filed; counted."),
    ):
        f.write_text(f.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
        code, out = _main(
            capsys, "journal", "append", "--command", "/x", "--action", "update", "--artifact", policy,
            "--intent", "written", "--file", str(f), "--as", "ada",
        )  # fmt: skip
        assert code == 0, out
    assert _main(capsys, "status", "set", policy, "Active", "--as", "ada")[0] == 0
    assert _main(capsys, "status", "set", task, "Done", "--as", "ada")[0] == 0

    code, out = _main(capsys, "spec", "create-task")
    assert code == 0 and "catalyst new TASK --title" in out
    code, out = _main(capsys, "check")
    assert code == 0, out
    parity = subprocess.run(
        ["python3", str(KERNEL.parent.parent / "scripts" / "check_command_parity.py"), "--require"],
        cwd=req.project,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(KERNEL.parent.parent / "scripts")},
    )
    assert parity.returncode == 0, parity.stdout + parity.stderr


def test_the_kernel_names_nothing_of_the_sample():
    """The sample is the kernel's fixture, not part of it: no kernel source
    names its types."""
    scripts = Path(KERNEL.parent.parent / "scripts" / "catalyst")
    for f in scripts.glob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert "POLICY-" not in text and "sample-process" not in text, f
