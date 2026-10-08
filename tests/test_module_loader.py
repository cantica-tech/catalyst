import json
from pathlib import Path

from module_loader import (
    get_active_etds,
    get_grounding_type,
    load_kernel_entities,
    load_module,
    resolve_command,
    resolve_deploy_root,
    resolve_module_id,
)


def write_example_module(mdir: Path) -> Path:
    """A tiny generic process module (`example-process`) at `mdir`."""
    (mdir / "schemas").mkdir(parents=True)
    (mdir / "module.yaml").write_text(
        "id: example-process\n"
        "name: Example Process Module\n"
        "version: 0.2.0\n"
        "description: A fictional module for tests.\n"
        "grounding_type: rule\n"
        "\n"
        "entity_types:\n"
        "  - id: ITEM\n"
        "    schema: schemas/item.yaml\n"
        "\n"
        "commands:\n"
        "  - name: create-item\n"
        "    description: Create a new item\n"
        "    argument_hint: \"[<rule-id>]\"\n"
        "    spec_path: commands/create-item.md\n"
        "\n"
        "templates:\n"
        "  - entity_type: ITEM\n"
        "    template_path: templates/item.template.md\n"
        "\n"
        "required_paths:\n"
        "  - path: development/ITEMS-SUMMARY.md\n"
        "    invariant: INV-EX-1\n"
    , encoding="utf-8")
    (mdir / "schemas" / "item.yaml").write_text(
        "id_prefix: ITEM\n"
        "name: Item\n"
        "plural_name: Items\n"
        "folder: items\n"
        "grounding: required\n"
        "grounding_field: Targets\n"
        "\n"
        "fields:\n"
        "  - name: ID\n"
        "    kind: text\n"
        "    required: true\n"
        "  - name: Targets\n"
        "    kind: ref-list\n"
        "    required: true\n"
        "    target_type: rule\n"
        "\n"
        "workflow:\n"
        "  initial: Open\n"
        "  states:\n"
        "    - Open\n"
        "    - Done\n"
        "  closed_states:\n"
        "    - Done\n"
    , encoding="utf-8")
    return mdir


def test_resolve_module_id_none_when_undeclared(tmp_path: Path):
    assert resolve_module_id(tmp_path) is None
    assert resolve_module_id(None) is None


def test_resolve_module_id_from_pointer(tmp_path: Path):
    (tmp_path / "app.catalyst").write_text(json.dumps({"module": "example-process"}), encoding="utf-8")
    assert resolve_module_id(tmp_path) == "example-process"


def test_resolve_module_id_from_criterion_config(tmp_path: Path):
    (tmp_path / ".criterion").mkdir()
    (tmp_path / ".criterion" / "config.yaml").write_text("module: example-process\n", encoding="utf-8")
    assert resolve_module_id(tmp_path) == "example-process"


def test_resolve_module_id_from_criterion_module_yaml(tmp_path: Path):
    (tmp_path / ".criterion").mkdir()
    (tmp_path / ".criterion" / "module.yaml").write_text("id: example-process\n", encoding="utf-8")
    assert resolve_module_id(tmp_path) == "example-process"


def test_load_module_none_when_undeclared_or_missing(tmp_path: Path):
    assert load_module(tmp_path) is None
    assert load_module(tmp_path, "no-such-module") is None


def test_load_module_from_project_framework_modules(tmp_path: Path):
    write_example_module(tmp_path / "framework" / "modules" / "example-process")
    manifest = load_module(tmp_path, "example-process")
    assert manifest is not None
    assert manifest.id == "example-process"
    assert manifest.version == "0.2.0"
    assert get_grounding_type(manifest) == "rule"
    etds = get_active_etds(manifest)
    assert list(etds) == ["ITEM"]
    item = etds["ITEM"]
    assert item.folder == "items"
    assert item.grounding == "required"
    assert item.grounding_field == "Targets"
    assert item.naming == "id-summary"
    assert item.workflow.closed_states == ["Done"]
    assert [f.name for f in item.fields] == ["ID", "Targets"]
    assert manifest.templates[0].template_path == "templates/item.template.md"
    assert manifest.required_paths[0].path == "development/ITEMS-SUMMARY.md"
    assert manifest.required_paths[0].invariant == "INV-EX-1"
    assert manifest.path == tmp_path / "framework" / "modules" / "example-process"


def test_load_module_declared_by_pointer_from_sibling_checkout(tmp_path: Path):
    project = tmp_path / "app"
    project.mkdir()
    write_example_module(tmp_path / "catalyst-example-process")
    (project / "app.catalyst").write_text(json.dumps({"module": "example-process"}), encoding="utf-8")
    manifest = load_module(project)
    assert manifest is not None
    assert manifest.path == tmp_path / "catalyst-example-process"


def test_load_module_from_deployment_modules_dir(tmp_path: Path):
    project = tmp_path / "app"
    project.mkdir()
    deploy = tmp_path / "agent" / ".criterion"
    write_example_module(deploy / "modules" / "example-process")
    (project / "app.catalyst").write_text(json.dumps(
        {"module": "example-process", "agent-source": str(deploy)}), encoding="utf-8")
    assert resolve_deploy_root(project) == deploy
    manifest = load_module(project)
    assert manifest is not None
    assert manifest.path == deploy / "modules" / "example-process"


def test_resolve_deploy_root_prefers_criterion_symlink(tmp_path: Path):
    project = tmp_path / "app"
    project.mkdir()
    deploy = tmp_path / "agent" / ".criterion"
    write_example_module(deploy / "modules" / "example-process")
    (project / "app.catalyst").write_text(json.dumps({"module": "example-process"}), encoding="utf-8")
    (project / ".criterion").symlink_to(deploy)
    assert resolve_deploy_root(project).resolve() == deploy.resolve()
    manifest = load_module(project)
    assert manifest is not None
    assert manifest.path.resolve() == (deploy / "modules" / "example-process").resolve()


def test_resolve_command(tmp_path: Path):
    write_example_module(tmp_path / "framework" / "modules" / "example-process")
    manifest = load_module(tmp_path, "example-process")
    cmd = resolve_command(manifest, "/create-item")
    assert cmd is not None
    assert cmd.name == "create-item"
    assert cmd.argument_hint == "[<rule-id>]"
    assert resolve_command(manifest, "unknown-cmd") is None


def test_load_kernel_entities():
    etds = load_kernel_entities()
    assert {"RECON", "WORKFLOW"} <= set(etds)
    assert etds["RECON"].folder == "reconciliations"
    assert etds["WORKFLOW"].folder == "workflows"


def test_load_kernel_entities_missing_dir(tmp_path: Path):
    assert load_kernel_entities(tmp_path / "nope") == {}


def test_load_sample_process_module():
    repo_root = Path(__file__).resolve().parent.parent
    manifest = load_module(project_root=repo_root, module_id="sample-process")
    assert manifest.id == "sample-process"
    assert manifest.grounding_type == "policy"
    assert "POLICY" in manifest.entity_types
    assert "TASK" in manifest.entity_types
    assert manifest.entity_types["TASK"].grounding == "required"
    assert manifest.entity_types["TASK"].grounding_field == "Policy"
