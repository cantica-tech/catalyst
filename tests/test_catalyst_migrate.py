"""`catalyst migrate` (roadmap R3.4, design G-43): what a deployment is behind
on, and the mechanical part of catching up."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import project_file
import schema_check
from catalyst import migrate
from catalyst.__main__ import main
from catalyst.deployment import load
from catalyst_fixtures import journal_entries
from test_catalyst_init import KERNEL
from test_catalyst_sync import _deployment

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _kernel(tmp: Path, rule_line: str | None = None) -> Path:
    """A copy of this checkout's kernel; with `rule_line`, its rule template gains that line."""
    out = tmp / "kernel"
    shutil.copytree(KERNEL, out)
    if rule_line:
        t = out / "templates" / "rule.template.md"
        t.write_text(t.read_text(encoding="utf-8") + f"\n{rule_line}\n", encoding="utf-8")
    return out


def _home(tmp_path):
    """A deployment moved to the home store, its layout current."""
    project, _ = _deployment(tmp_path)
    migrate.apply(project, None, "ada", ["to the home store first"], runtime=False)
    return project


def test_a_legacy_layout_is_planned_then_moved_to_the_home_store(tmp_path):
    project, _ = _deployment(tmp_path)
    p = migrate.plan(project, None)
    assert [s.kind for s in p.steps] == ["layout"] and p.steps[0].auto
    before, done = migrate.apply(project, None, "ada", ["the legacy layout, moved"], runtime=False)
    assert before.steps[0].taken and done
    assert (project / "catalyst.toml").is_file() and not list(project.glob("*.catalyst"))
    assert project_file.resolve(project) == project_file.home_criterion("app")
    assert migrate.plan(project, None).steps == []


def test_a_kernel_template_the_deployment_lacks_is_added_as_its_next_version_once(tmp_path):
    project = _home(tmp_path)
    kernel = _kernel(tmp_path, "A line the next kernel adds.")
    p = migrate.plan(project, kernel)
    (step,) = [s for s in p.steps if s.kind == "template"]
    assert step.auto and step.target == "rules/templates/TEMPLATE-RULE-v2.md"
    migrate.apply(project, kernel, "ada", ["the rule template's new line"])
    root = load(project).root
    added = root / "rules" / "templates" / "TEMPLATE-RULE-v2.md"
    assert "A line the next kernel adds." in added.read_text(encoding="utf-8")
    assert "Copy this file" not in added.read_text(encoding="utf-8")  # seeded as init seeds, never raw
    assert "| v2 | `TEMPLATE-RULE-v2.md` |" in (root / "rules" / "templates" / "templates-rule.md").read_text(
        encoding="utf-8"
    )
    entry = journal_entries(root)[-1]
    assert (entry["command"], entry["action"], entry["tier"]) == ("catalyst migrate", "update", "chore")
    assert {f["path"].rsplit("/", 1)[-1] for f in entry["files"]} == {"TEMPLATE-RULE-v2.md", "templates-rule.md"}
    assert [s for s in migrate.plan(project, kernel).steps if s.kind == "template"] == []  # held now


def test_a_template_copied_raw_counts_as_held_and_a_later_own_version_stays_latest(tmp_path):
    project = _home(tmp_path)
    kernel = _kernel(tmp_path, "A line the next kernel adds.")
    folder = load(project).root / "rules" / "templates"
    shutil.copyfile(kernel / "templates" / "rule.template.md", folder / "TEMPLATE-RULE-v2.md")  # raw, by hand
    (folder / "TEMPLATE-RULE-v3.md").write_text("# The team's own rule template\n", encoding="utf-8")
    assert [s for s in migrate.plan(project, kernel).steps if s.kind == "template"] == []


def test_a_module_template_is_offered_and_added_only_when_asked(tmp_path):
    project = _home(tmp_path)
    root = load(project).root
    tree = root / "modules" / "example-process"
    template = next(p for p in sorted(tree.rglob("*.template.md")) if "templates" in p.parts)
    template.write_text(template.read_text(encoding="utf-8") + "\nA row the module adds.\n", encoding="utf-8")
    offered = [s for s in migrate.plan(project, None).steps if s.kind == "template"]
    assert offered and all(not s.auto and s.type for s in offered)
    step = offered[0]
    migrate.apply(project, None, "ada", ["nothing optional taken"])
    assert not (root / step.target).exists()
    before, done = migrate.apply(project, None, "ada", ["the module's new row, asked for"], templates={step.type})
    assert (root / step.target).is_file() and [s.taken for s in before.steps if s.target == step.target] == [True]
    assert done == [f"added {step.detail[4:].split(' (optional')[0]}"]


def test_the_judgment_steps_since_a_version_are_listed_with_their_qualifiers_never_taken(tmp_path):
    project = _home(tmp_path)
    p = migrate.plan(project, KERNEL, since="0.92.0")
    judged = [s for s in p.steps if s.kind == "judgment"]
    assert judged and all(not s.auto and s.source for s in judged)
    roles = [s for s in judged if s.source == "kernel: migrations/0.93.0/roles-grant-commands.md"]
    assert any(s.detail.startswith("for each role") for s in roles)
    assert any(s.detail.startswith("(only if the owner asks)") for s in roles)
    assert not any("as its next version" in s.detail for s in judged)  # a template step is catalyst's
    later = migrate.plan(project, KERNEL, since="0.93.0").steps
    assert not [s for s in later if s.target == "kernel 0.93.0"]  # a migration at or before `since` is not listed


def test_the_cli_prints_what_its_schema_describes_and_applies(tmp_path, capsys):
    project = _home(tmp_path)
    kernel = _kernel(tmp_path, "A line the next kernel adds.")
    capsys.readouterr()
    args = ["--project", str(project), "migrate", "--kernel", str(kernel)]
    assert main([*args, "--json"]) == 0
    planned = json.loads(capsys.readouterr().out)
    assert schema_check.problems(planned, schema_check.load("migrate")) == []
    assert planned["applied"] is False and any(s["kind"] == "template" for s in planned["steps"])
    assert main([*args, "--apply", "--as", "ada", "--json"]) == 0
    applied = json.loads(capsys.readouterr().out)
    assert schema_check.problems(applied, schema_check.load("migrate")) == []
    assert applied["applied"] and applied["done"]
    assert main(args) == 0
    assert "nothing to migrate" in capsys.readouterr().out


def test_outside_a_project_it_says_so(tmp_path, capsys):
    (tmp_path / "empty").mkdir()
    subprocess.run(["git", "init", "-q", str(tmp_path / "empty")], check=True)
    assert main(["--project", str(tmp_path / "empty"), "migrate"]) == 1
    assert "no catalyst.toml" in capsys.readouterr().err


def test_a_migration_starting_before_the_previous_kernel_still_lists_its_judgment_steps(tmp_path):
    """0.104.0's migration starts at 0.103.0; a deployment synced from 0.103.1 still owes its steps (BUG-000028)."""
    project = _home(tmp_path)
    p = migrate.plan(project, KERNEL, since="0.103.1")
    sources = {s.source for s in p.steps if s.kind == "judgment"}
    assert "kernel: migrations/0.104.0/workflow-governance.md" in sources


# --- migration 0.106.0: people out of the criterion (design 29) -----------------------------
def _roles_template(root: Path) -> list[dict]:
    folder = root / "IAM" / "roles" / "templates"
    n, latest = migrate._latest_roles_template(folder)
    assert latest is not None
    return json.loads(latest.read_text(encoding="utf-8"))["roles"]


def _registry(project: Path, roles: list[dict]) -> Path:
    """The deployment's roles registry, journaled as a real one is, before the migration retires it."""
    from catalyst import journal

    dep = load(project)
    path = dep.root / "IAM" / "roles" / "roles.json"
    path.write_text(json.dumps({"roles": roles}), encoding="utf-8")
    journal.append(
        dep,
        journal.AppendRequest(
            command="/role",
            action="update",
            artifact="roles",
            targets=[],
            intent=["the roles"],
            files=[str(path)],
            actor="ada",
            tier="chore",
        ),
    )
    return dep.root


def test_the_built_in_kernel_role_ids_are_the_kernel_templates():
    roles = json.loads((KERNEL / "templates" / "roles.template.json").read_text(encoding="utf-8"))["roles"]
    assert migrate.KERNEL_ROLE_IDS == {r["name"]: r["id"] for r in roles}


def test_the_identity_step_keeps_the_kernel_roles_under_the_kernel_ids(tmp_path):
    """BUG-000031: a kept role is shown under the provider role of the same id, so a kernel role keeps the kernel's
    id (as `catalyst-users roles provision` names it), and another role its own or its name's slug."""
    project = _home(tmp_path)
    roles = [
        {"name": "Admin", "actions": ["*"], "reconciliation": "full"},
        {"name": "Tech Lead / Architect", "actions": [], "reconciliation": "full"},
        {"name": "Knowledge Curator", "actions": ["/kb-build"], "reconciliation": "propose"},
        {"name": "Auditor", "provider_role": "auditors", "actions": []},
    ]
    root = _registry(project, roles)
    migrate.apply(project, None, "ada", ["people out of the criterion"], runtime=False)
    ids = {r["name"]: r["id"] for r in _roles_template(root)}
    assert ids == {
        "Admin": "catalyst-admin",
        "Tech Lead / Architect": "tech-lead",
        "Knowledge Curator": "knowledge-curator",
        "Auditor": "auditors",
    }
    assert (root / "IAM" / "roles" / "roles.retired.json").is_file()
    assert not [s for s in migrate.plan(project, None).steps if s.kind == "identity"]


def test_a_roles_template_0_106_0_slugged_is_corrected_once(tmp_path):
    project = _home(tmp_path)
    root = _registry(project, [{"name": "Admin", "actions": ["*"]}])
    migrate.apply(project, None, "ada", ["people out of the criterion"], runtime=False)
    folder = root / "IAM" / "roles" / "templates"
    n, _ = migrate._latest_roles_template(folder)
    slugged = [{"name": "Admin", "id": "admin", "actions": ["*"]}, {"name": "Curator", "id": "curator"}]
    (folder / f"TEMPLATE-ROLES-v{n + 1}.json").write_text(json.dumps({"roles": slugged}), encoding="utf-8")
    step = [s for s in migrate.plan(project, None).steps if s.kind == "identity"]
    assert step and "kernel's ids" in step[0].detail
    migrate.apply(project, None, "ada", ["the kernel roles under the kernel's ids"], runtime=False)
    assert {r["name"]: r["id"] for r in _roles_template(root)} == {"Admin": "catalyst-admin", "Curator": "curator"}
    assert not [s for s in migrate.plan(project, None).steps if s.kind == "identity"]
