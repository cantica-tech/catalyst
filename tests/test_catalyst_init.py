from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from catalyst import compose
from catalyst.check import run as run_checks
from catalyst.deployment import load
from catalyst.init import InitError, InitRequest, init
from catalyst_fixtures import ITEM_SCHEMA, MODULE_YAML, SUB_SCHEMA, write

REPO = Path(__file__).resolve().parent.parent
KERNEL = REPO / "framework" / "kernel"


def example_module(base: Path) -> Path:
    mod = base / "example-process"
    write(mod / "module.yaml", MODULE_YAML + "\ntemplates:\n  - entity_type: ITEM\n"
          "    template_path: templates/item.template.md\n")
    write(mod / "version.txt", "0.2.0\n")
    write(mod / "schemas" / "item.yaml", ITEM_SCHEMA)
    write(mod / "schemas" / "sub.yaml", SUB_SCHEMA + "location: development\n")
    write(mod / "templates" / "item.template.md", "# `ITEM-NNNNNN` — {{title}}\n")
    write(mod / "code-of-conduct.module.md",
          "# module contribution\n\n## 3. Standard document types\n\n- `ITEM` — an item.\n\n"
          "## 4. Slash-command entry points\n\n- `/create-item` — create an item (`rr-META-009`).\n")
    write(mod / "rules-of-rules.module.md",
          "# module meta-rules\n\n> preamble\n\n## 9. `rr-META-009` Items\n\nItems are items.\n")
    write(mod / "definitions" / "item" / "DEFINITION-ITEM-v1.md", "# Item v1\n")
    write(mod / "definitions" / "item" / "DEFINITION-ITEM-v2.md", "# Item v2\n")
    return mod


def request(tmp: Path, **kw) -> InitRequest:
    project = tmp / "app"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    base = dict(project=project, name="app", module_id="example-process", user="Ada Lovelace",
                kernel=KERNEL, module=example_module(tmp), git_username="ada",
                rule_docs=[("business-rules.md", "br")], test_locations="`tests/`",
                at=tmp / "agent" / ".criterion", agent="test-agent")
    base.update(kw)
    return InitRequest(**base)


def test_init_produces_a_deployment_that_passes_every_check(tmp_path):
    req = request(tmp_path)
    init(req)
    dep = load(req.project)
    report = run_checks(dep)
    assert report.errors == [] and report.warnings == []
    root = dep.root
    assert (req.project / ".criterion").is_symlink()
    assert "/.criterion" in (req.project / ".gitignore").read_text()
    pointer = json.loads((req.project / "app.catalyst").read_text())
    assert pointer["module"] == "example-process" and pointer["repoed"] is False
    assert pointer["journal_since"] == ""        # no commit yet: the whole history is governed
    user = json.loads((root / "IAM" / "users" / "users.json").read_text())["users"][0]
    assert user["git_username"] == "ada" and len(user["userid"]) == 8
    coc = (root / "CODE-OF-CONDUCT.md").read_text()
    assert "### From module example-process" in coc and f"rr-META-000009-{user['userid']}" in coc
    assert "{{RULES_DIR}}" not in coc
    assert (root / "development" / "subs" / "subs.md").is_file()        # ETD location honoured
    assert (root / "items" / "templates" / "TEMPLATE-ITEM-v1.md").is_file()
    assert (root / "definitions" / "item.md").read_text() == "# Item v2\n"  # latest definition
    assert (root / "bin" / "catalyst.pyz").is_file()
    entries = (root / "development" / "journal.jsonl").read_text().splitlines()
    assert json.loads(entries[0])["command"] == "catalyst init"


def test_init_in_project_fallback_and_no_git(tmp_path):
    req = request(tmp_path, at=None)
    subprocess.run(["rm", "-rf", str(req.project / ".git")], check=True)
    init(req)
    assert (req.project / ".criterion").is_dir() and not (req.project / ".criterion").is_symlink()
    assert run_checks(load(req.project)).errors == []


def test_init_refuses_an_installed_project(tmp_path):
    req = request(tmp_path)
    init(req)
    with pytest.raises(InitError, match="already"):
        init(req)


def test_init_writes_command_files(tmp_path):
    req = request(tmp_path, commands_dir=Path(".claude/commands"))
    init(req)
    names = {p.stem for p in (req.project / ".claude" / "commands").glob("*.md")}
    assert "check-rules" in names and "dogfood" not in names


def test_compose_places_module_sections():
    coc = compose.insert_at_section_end("## 3. A\n\nkernel three\n\n## 4. B\n\nkernel four\n",
                                        3, "### From module m\n\nmodule three")
    assert coc.index("kernel three") < coc.index("module three") < coc.index("## 4. B")
    assert compose.sign_meta_ids("see rr-META-009 and rr-META-000009-Ab3xR9pQ", "Zz9zZz9z") == \
        "see rr-META-000009-Zz9zZz9z and rr-META-000009-Ab3xR9pQ"


def test_recompose_merges_template_changes_and_keeps_local_edits(tmp_path):
    import shutil
    from catalyst.compose import deployed_params, recompose
    req = request(tmp_path)
    init(req)
    root = load(req.project).root
    base_kernel = tmp_path / "kernel-old"
    shutil.copytree(KERNEL, base_kernel)
    new_kernel = tmp_path / "kernel-new"
    shutil.copytree(KERNEL, new_kernel)
    ror_t = new_kernel / "rules-of-rules.template.md"
    ror_t.write_text(ror_t.read_text() + "\n## 99. `rr-META-099` A new kernel rule\n\nNew.\n")
    ror = root / "rules" / "Rules-of-Rules.md"
    ror.write_text(ror.read_text().replace("Meta-rules governing", "Meta-rules (local note) governing", 1))
    params = deployed_params(root, "example-process")
    results = recompose(root, params, (base_kernel, req.module), (new_kernel, req.module))
    text = ror.read_text()
    assert "(local note)" in text and f"rr-META-000099-{params.userid}" in text
    assert {r.path: r.conflicts for r in results}["rules/Rules-of-Rules.md"] == 0


def test_failed_install_rolls_back_and_can_be_rerun(tmp_path, monkeypatch):
    import catalyst.init as ci
    req = request(tmp_path, commands_dir=Path(".claude/commands"))
    before = (req.project / ".gitignore").exists()

    def boom(*a, **k):
        raise RuntimeError("disk full")
    monkeypatch.setattr(ci, "_git", boom)
    with pytest.raises(InitError, match="rolled back"):
        init(req)
    assert not list(req.project.glob("*.catalyst"))
    assert not (req.project / ".criterion").exists() and not (req.project / ".criterion").is_symlink()
    assert not req.at.exists() and not (req.project / ".claude").exists()
    assert (req.project / ".gitignore").exists() == before
    monkeypatch.undo()
    init(req)                                               # re-run succeeds
    assert run_checks(load(req.project)).errors == []


def test_init_validates_name_and_location(tmp_path):
    with pytest.raises(InitError, match="--name"):
        init(request(tmp_path, name="../escape"))
    (tmp_path / "b").mkdir()
    with pytest.raises(InitError, match="outside the project"):
        init(request(tmp_path / "b", at=tmp_path / "b" / "app" / "inner"))


def test_seeded_templates_are_resolved(tmp_path):
    req = request(tmp_path)
    init(req)
    root = load(req.project).root
    rule_t = (root / "rules" / "templates" / "TEMPLATE-RULE-v1.md").read_text()
    assert "{{RULES_DIR}}" not in rule_t and "Copy this file" not in rule_t


def test_composition_parameters_are_saved_and_read_back(tmp_path):
    from catalyst.compose import deployed_params
    req = request(tmp_path, rule_docs=[("z-rules.md", "z"), ("a-rules.md", "a")])
    init(req)
    p = deployed_params(load(req.project).root, "example-process")
    assert p.rule_docs == ["z-rules.md", "a-rules.md"] and p.test_locations == "`tests/`"


def test_commands_from_a_release_are_generated_from_section4(tmp_path):
    import shutil
    release = tmp_path / "release-kernel"
    shutil.copytree(KERNEL, release)
    (release / "manifest.json").write_text('{"version": "9.9.9"}')
    req = request(tmp_path, kernel=release, commands_dir=Path(".claude/commands"))
    init(req)
    names = {p.stem for p in (req.project / ".claude" / "commands").glob("*.md")}
    assert "check-rules" in names and "create-item" in names          # kernel + module §4
    assert "create-bug" not in names                                  # another module's command
    assert json.loads((req.project / "app.catalyst").read_text())["kernel_version"] == "9.9.9"


def test_recompose_skips_frozen_documents(tmp_path):
    from catalyst.compose import deployed_params, recompose
    req = request(tmp_path)
    init(req)
    root = load(req.project).root
    (root / ".frozen").write_text("CODE-OF-CONDUCT.md\n")
    results = {r.path: r for r in recompose(root, deployed_params(root, "example-process"),
                                             (KERNEL, req.module), (KERNEL, req.module))}
    assert results["CODE-OF-CONDUCT.md"].frozen


def test_single_template_named_like_its_folder_is_the_item_template(tmp_path):
    req = request(tmp_path)
    mod = req.module
    (mod / "templates" / "items.template.md").write_text("# `ITEM-NNNNNN` — item named like its folder\n")
    y = mod / "module.yaml"
    y.write_text(y.read_text().replace("templates/item.template.md", "templates/items.template.md"))
    init(req)
    root = load(req.project).root
    assert "named like its folder" in (root / "items" / "templates" / "TEMPLATE-ITEM-v1.md").read_text()
    assert (root / "items" / "items.md").read_text().startswith("# Items index")


def test_init_after_a_first_commit_sets_the_baseline_there(tmp_path):
    req = request(tmp_path)
    (req.project / "main.py").write_text("print('hi')\n")
    subprocess.run(["git", "-C", str(req.project), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(req.project), "-c", "user.name=a", "-c", "user.email=a@a",
                    "commit", "-qm", "skeleton"], check=True)
    head = subprocess.check_output(["git", "-C", str(req.project), "rev-parse", "HEAD"], text=True).strip()
    init(req)
    assert json.loads((req.project / "app.catalyst").read_text())["journal_since"] == head
