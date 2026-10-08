from __future__ import annotations

import json
from pathlib import Path

import pytest

from catalyst.__main__ import main
from catalyst.corpus import load_corpus, norm_field, ref_values
from catalyst.deployment import DeploymentNotFound, load
from catalyst.validate import ERROR, WARNING, validate
from catalyst_fixtures import USERID, artifact, make_project, write


def findings(project: Path):
    dep = load(project)
    return validate(dep, load_corpus(dep))


def codes(project: Path, level: str | None = None) -> list[str]:
    return [f.code for f in findings(project) if level is None or f.level == level]


def item_file(project: Path) -> Path:
    return project / ".criterion" / "items" / "ITEM-000001-first-item.md"


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_valid_fixture_is_clean(tmp_path):
    assert findings(make_project(tmp_path)) == []


def test_load_finds_module_and_kernel_etds(tmp_path):
    dep = load(make_project(tmp_path) / ".criterion" / "items")
    assert {"ITEM", "SUB", "RECON", "WORKFLOW"} <= set(dep.etds)
    assert dep.module.id == "example-process"


def test_load_without_deployment(tmp_path):
    with pytest.raises(DeploymentNotFound):
        load(tmp_path)


def test_field_name_matching_and_ref_parsing():
    assert norm_field("Requirement(s)") == norm_field("Requirements")
    assert ref_values("`A-1`, `B-2`") == ["A-1", "B-2"]
    assert ref_values("*(none yet)*") == []
    assert ref_values("X-1, Y-2") == ["X-1", "Y-2"]


def test_dangling_reference_is_an_error(tmp_path):
    project = make_project(tmp_path)
    edit(item_file(project), f"`br-AUTH-000001-{USERID}`", f"`br-AUTH-000009-{USERID}`")
    assert "dangling-ref" in codes(project, ERROR)
    assert "ungrounded" in codes(project, ERROR)


def test_missing_required_field(tmp_path):
    project = make_project(tmp_path)
    edit(item_file(project), "| **Domain** | `AUTH` |\n", "")
    assert codes(project, ERROR) == ["required-field"]


def test_inherited_grounding_needs_a_resolvable_parent(tmp_path):
    project = make_project(tmp_path)
    sub = project / ".criterion" / "subs" / "SUB-000001-first-sub.md"
    edit(sub, "| **Item** |", "| **Requirement** |")    # legacy field name
    assert sorted(codes(project, ERROR)) == ["required-field", "ungrounded"]


def test_unregistered_signer(tmp_path):
    project = make_project(tmp_path)
    edit(item_file(project), "| **Signed-off-by** | Ada Lovelace |", "| **Signed-off-by** | Mallory |")
    assert codes(project, ERROR) == ["signer"]


def test_signer_may_be_git_username(tmp_path):
    project = make_project(tmp_path)
    edit(item_file(project), "| **Signed-off-by** | Ada Lovelace |", "| **Signed-off-by** | ada |")
    assert findings(project) == []


def test_enum_outside_allowed_values_is_a_warning(tmp_path):
    project = make_project(tmp_path)
    edit(item_file(project), "| **Status** | Open |", "| **Status** | shipped |")
    assert codes(project) == ["enum-value"]
    assert codes(project, WARNING) == ["enum-value"]


def test_one_sided_backref_is_a_warning(tmp_path):
    project = make_project(tmp_path)
    edit(item_file(project), f"| **Subs** | `SUB-000001-{USERID}` |", "| **Subs** | *(none)* |")
    assert codes(project) == ["backref"]


def test_reference_to_wrong_type_is_a_warning(tmp_path):
    project = make_project(tmp_path)
    sub = project / ".criterion" / "subs" / "SUB-000001-first-sub.md"
    edit(sub, f"| **Item** | `ITEM-000001-{USERID}` |", f"| **Item** | `br-AUTH-000001-{USERID}` |")
    assert "ref-type" in codes(project, WARNING)
    assert codes(project, ERROR) == []


def test_duplicate_artifact_id(tmp_path):
    project = make_project(tmp_path)
    write(project / ".criterion" / "items" / "ITEM-000001-copy.md", item_file(project).read_text(encoding="utf-8"))
    assert "duplicate-id" in codes(project, ERROR)


def test_id_shape_and_filename(tmp_path):
    project = make_project(tmp_path)
    edit(item_file(project), f"`ITEM-000001-{USERID}`", "`ITEM-000001-Zz9zZz9z`")
    assert "id-shape" in codes(project, ERROR)


def test_rule_missing_from_index(tmp_path):
    project = make_project(tmp_path)
    doc = project / ".criterion" / "rules" / "business" / "br-business-rules.md"
    edit(doc, "## Linked Artifacts", f"### `br-AUTH-000002-{USERID}` Logout\n\n## Linked Artifacts")
    assert codes(project, ERROR) == ["rule-unindexed"]


def test_module_placeholder_heading_is_not_a_definition(tmp_path):
    project = make_project(tmp_path)
    write(project / ".criterion" / "rules" / "Rules-of-Rules.md",
          f"## 9. `rr-META-000009-{USERID}` — owned by the active module\n\n"
          f"### From module example-process\n\n## 9. `rr-META-000009-{USERID}` Items\n")
    assert findings(project) == []


def test_index_drift_and_orphans(tmp_path):
    project = make_project(tmp_path)
    write(project / ".criterion" / "items" / "ITEM-000002-second.md",
          artifact(f"ITEM-000002-{USERID}", "Second", {
              "ID": f"`ITEM-000002-{USERID}`", "Status": "Open", "Targets": f"`br-AUTH-000001-{USERID}`",
              "Domain": "`AUTH`", "Signed-off-by": "Ada Lovelace"}))
    assert codes(project) == ["index-drift"]
    edit(project / ".criterion" / "items" / "items.md", "| First item |", "| First item |\n"
         f"| [ITEM-000003-{USERID}](ITEM-000003-gone.md) | Gone | Open |")
    assert "index-orphan" in codes(project, ERROR)


def test_cli_exit_codes_and_json(tmp_path, capsys):
    project = make_project(tmp_path)
    assert main(["--project", str(project), "validate"]) == 0
    edit(item_file(project), "| **Status** | Open |", "| **Status** | shipped |")
    assert main(["--project", str(project), "validate"]) == 0
    assert main(["--project", str(project), "validate", "--strict"]) == 1
    capsys.readouterr()
    assert main(["--project", str(project), "validate", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True and out["findings"][0]["code"] == "enum-value"


def test_cli_without_deployment(tmp_path, capsys):
    assert main(["--project", str(tmp_path), "validate"]) == 2
    assert "no catalyst deployment" in capsys.readouterr().err


def test_field_row_with_a_notes_cell(tmp_path):
    project = make_project(tmp_path)
    edit(item_file(project), "| **Status** | Open |", "| **Status** | Open | since `ITEM-000099-Zz9zZz9z` |")
    assert findings(project) == []


def test_runs_from_inside_a_symlinked_working_copy(tmp_path, monkeypatch):
    import shutil
    project = make_project(tmp_path)
    real = tmp_path / "agent-space" / ".criterion"
    real.parent.mkdir()
    shutil.move(str(project / ".criterion"), str(real))
    (project / ".criterion").symlink_to(real)
    logical = project / ".criterion" / "items"
    monkeypatch.chdir(logical)
    monkeypatch.setenv("PWD", str(logical))
    dep = load()
    assert dep.project_root == project and "ITEM" in dep.etds
    monkeypatch.chdir(real)
    monkeypatch.setenv("PWD", str(real))
    with pytest.raises(DeploymentNotFound, match="no \\*.catalyst pointer"):
        load()


def test_pointer_without_working_copy_fails_check(tmp_path):
    import shutil
    project = make_project(tmp_path)
    shutil.rmtree(project / ".criterion")
    assert main(["--project", str(project), "check"]) == 1     # a broken project fails
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    assert main(["--project", str(elsewhere), "check"]) == 0   # not a project: skipped


def test_closed_entity_needs_its_required_when_closed_fields(tmp_path):
    project = make_project(tmp_path)
    schema = project / ".criterion" / "modules" / "example-process" / "schemas" / "item.yaml"
    schema.write_text(schema.read_text(encoding="utf-8").replace(
        "  - name: Subs\n    kind: ref-list\n    required: false",
        "  - name: Subs\n    kind: ref-list\n    required: false\n    required_when_closed: true"), encoding="utf-8")
    edit(item_file(project), f"| **Subs** | `SUB-000001-{USERID}` |", "| **Subs** | *(none)* |")
    assert "closed-incomplete" not in codes(project)          # still Open: fine
    edit(item_file(project), "| **Status** | Open |", "| **Status** | Done |")
    assert "closed-incomplete" in codes(project, ERROR)


def test_target_type_may_list_alternatives(tmp_path):
    project = make_project(tmp_path)
    schema = project / ".criterion" / "modules" / "example-process" / "schemas" / "sub.yaml"
    schema.write_text(schema.read_text(encoding="utf-8").replace("target_type: ITEM", "target_type: ITEM|rule"), encoding="utf-8")
    sub = project / ".criterion" / "subs" / "SUB-000001-first-sub.md"
    edit(sub, f"| **Item** | `ITEM-000001-{USERID}` |", f"| **Item** | `br-AUTH-000001-{USERID}` |")
    assert "ref-type" not in codes(project)


def test_decorated_closed_status_counts_as_closed(tmp_path):
    project = make_project(tmp_path)
    schema = project / ".criterion" / "modules" / "example-process" / "schemas" / "item.yaml"
    schema.write_text(schema.read_text(encoding="utf-8").replace(
        "  - name: Subs\n    kind: ref-list\n    required: false",
        "  - name: Subs\n    kind: ref-list\n    required: false\n    required_when_closed: true"), encoding="utf-8")
    edit(item_file(project), f"| **Subs** | `SUB-000001-{USERID}` |", "| **Subs** | *(none)* |")
    edit(item_file(project), "| **Status** | Open |", "| **Status** | **Done** ✅ |")
    assert "closed-incomplete" in codes(project, ERROR)
