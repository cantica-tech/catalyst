import json
import shutil
from pathlib import Path

import check_deployment as cd
from module_loader import load_module


def write_example_module(base: Path) -> Path:
    """A tiny generic process module (`example-process`) at
    base/framework/modules/example-process/: an ITEM entity (folder `items`),
    a free-form-named NOTE entity (folder `notes`, under development/), one
    required path and one definition directory per entity."""
    mdir = base / "framework" / "modules" / "example-process"
    (mdir / "schemas").mkdir(parents=True)
    (mdir / "module.yaml").write_text(
        "id: example-process\n"
        "name: Example Process Module\n"
        "version: 0.1.0\n"
        "description: A fictional module for tests.\n"
        "grounding_type: rule\n"
        "\n"
        "entity_types:\n"
        "  - id: ITEM\n"
        "    schema: schemas/item.yaml\n"
        "  - id: NOTE\n"
        "    schema: schemas/note.yaml\n"
        "\n"
        "required_paths:\n"
        "  - path: development/LEDGER-OF-ITEMS.md\n"
        "    invariant: INV-EX-1\n"
        "    seed: templates/ledger.template.md\n"
    , encoding="utf-8")
    (mdir / "schemas" / "item.yaml").write_text(
        "id_prefix: ITEM\nname: Item\nplural_name: Items\nfolder: items\n"
        "grounding: required\ngrounding_field: Targets\n"
    , encoding="utf-8")
    (mdir / "schemas" / "note.yaml").write_text(
        "id_prefix: NOTE\nname: Note\nplural_name: Notes\nfolder: notes\n"
        "grounding: none\nnaming: free-form\n"
    , encoding="utf-8")
    for d in ("item", "note"):
        (mdir / "definitions" / d).mkdir(parents=True)
    return mdir


def add_example_module_artifacts(root: Path) -> None:
    """Make a valid deployment also satisfy the example-process module."""
    (root / "items").mkdir()
    (root / "items" / "items.md").write_text("# Items index\n", encoding="utf-8")
    (root / "development" / "notes").mkdir()
    (root / "development" / "notes" / "notes.md").write_text("# Notes index\n", encoding="utf-8")
    (root / "development" / "LEDGER-OF-ITEMS.md").write_text("# Ledger\n", encoding="utf-8")
    for d in ("item", "note"):
        (root / "definitions" / f"{d}.md").write_text(f"# `{d}`\n", encoding="utf-8")


def example_model(tmp_path: Path) -> cd.DeploymentModel:
    write_example_module(tmp_path)
    module = load_module(tmp_path, "example-process")
    assert module is not None
    return cd.build_model(module)


def make_valid_deployment(tmp_path: Path) -> Path:
    """A minimal `.criterion/` tree that satisfies every check in
    check_deployment.py, so each test can start from a known-good baseline
    and break exactly one thing."""
    root = tmp_path / ".criterion"
    rules = root / "rules"
    business = rules / "business"
    business.mkdir(parents=True)
    (rules / "templates").mkdir()

    (rules / "templates" / "TEMPLATE-RULE-v1.md").write_text("# Rule template\n", encoding="utf-8")
    (root / "version.txt").write_text("0.37.0\n", encoding="utf-8")
    (rules / "rules.md").write_text(
        "# Rules index\n\n- br-AUTH-000001-Ab3xR9pQ-login-flow\n"
    , encoding="utf-8")
    (business / "br-AUTH-000001-Ab3xR9pQ-login-flow.md").write_text(
        "## `br-AUTH-000001-Ab3xR9pQ` Login flow\n\n"
        "## Contents\n\n...\n\n"
        "## Linked Artifacts — Quick Index\n\n(none)\n"
    , encoding="utf-8")
    development = root / "development"
    development.mkdir()
    workflows = root / "workflows"
    workflows.mkdir()
    (workflows / "workflows.md").write_text("# Workflows index\n\n*(none)*\n", encoding="utf-8")
    iam = root / "IAM"
    users_dir = iam / "users"
    roles_dir = iam / "roles"
    users_dir.mkdir(parents=True)
    roles_dir.mkdir()
    (users_dir / "users.json").write_text(json.dumps({
        "users": [
            {"name": "Ada", "roles": ["Developer"], "registered": "2026-08-23",
             "active": True, "notes": "", "userid": "Ab3xR9pQ"},
        ]
    }), encoding="utf-8")
    (roles_dir / "roles.json").write_text(json.dumps({
        "roles": [{"name": "Developer", "actions": ["/reconcile"]}]
    }), encoding="utf-8")
    (development / "journal.jsonl").write_text(
        json.dumps({
            "timestamp": "2026-08-23T19:00:00Z",
            "actor": "Ada",
            "command": "/reconcile",
            "action": "create",
            "artifact": "RECON-000001",
            "targets": ["br-AUTH-000001-Ab3xR9pQ"],
            "intent": ["resolve a real case"],
            "files": [
                {"path": "reconciliations/RECON-000001-x.md",
                 "before": None,
                 "after": "a" * 40},
            ],
        }) + "\n"
    , encoding="utf-8")
    definitions = root / "definitions"
    definitions.mkdir()
    for entity_type in cd.KERNEL_ENTITY_TYPES:
        (definitions / f"{entity_type}.md").write_text(
            f"# `{entity_type}` — entity definition (v1)\n\n"
            "## Description\n\nA definition.\n"
        , encoding="utf-8")
    return root


def test_find_deploy_root_locates_from_nested_dir(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    nested = root / "rules" / "business"
    assert cd.find_deploy_root(nested) == root


def test_find_deploy_root_returns_none_when_absent(tmp_path: Path):
    assert cd.find_deploy_root(tmp_path) is None


def test_find_deploy_root_follows_criterion_symlink(tmp_path: Path):
    """0.37.0: the pointer holds no path; <project>/.criterion is a
    gitignored symlink into agent-owned space."""
    project = tmp_path / "project"
    nested = project / "src"
    nested.mkdir(parents=True)
    agent_owned = tmp_path / "agent-space" / ".criterion"
    agent_owned.mkdir(parents=True)
    (project / "myapp.catalyst").write_text(json.dumps({"project_name": "myapp"}), encoding="utf-8")
    (project / ".criterion").symlink_to(agent_owned)
    assert cd.find_deploy_root(project).resolve() == agent_owned.resolve()
    assert cd.find_deploy_root(nested).resolve() == agent_owned.resolve()
    assert cd.find_project_root(nested) == project


def test_find_deploy_root_symlink_wins_over_legacy_agent_source(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    current = tmp_path / "current" / ".criterion"
    stale = tmp_path / "stale" / ".criterion"
    current.mkdir(parents=True)
    stale.mkdir(parents=True)
    (project / "myapp.catalyst").write_text(json.dumps({
        "project_name": "myapp",
        "agent-source": str(stale),
    }), encoding="utf-8")
    (project / ".criterion").symlink_to(current)
    assert cd.find_deploy_root(project).resolve() == current.resolve()


def test_find_deploy_root_dangling_symlink_falls_back_to_legacy_pointer(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    legacy = tmp_path / "agent-space" / ".criterion"
    legacy.mkdir(parents=True)
    (project / "myapp.catalyst").write_text(json.dumps({
        "project_name": "myapp",
        "agent-source": str(legacy),
    }), encoding="utf-8")
    (project / ".criterion").symlink_to(tmp_path / "gone")
    assert cd.find_deploy_root(project) == legacy


def test_find_deploy_root_pathless_pointer_without_criterion(tmp_path: Path):
    """A 0.37.0 pointer on a machine where the working copy isn't set up
    yet (fresh clone, CI) resolves to nothing rather than guessing."""
    (tmp_path / "myapp.catalyst").write_text(json.dumps({"project_name": "myapp"}), encoding="utf-8")
    assert cd.find_deploy_root(tmp_path) is None


def test_find_deploy_root_follows_pointer_file(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    agent_owned = tmp_path / "agent-space" / ".criterion"
    agent_owned.mkdir(parents=True)
    (project / "myapp.catalyst").write_text(json.dumps({
        "project_name": "myapp",
        "agent-source": str(agent_owned),
    }), encoding="utf-8")
    assert cd.find_deploy_root(project) == agent_owned


def test_find_deploy_root_pointer_resolved_from_nested_dir(tmp_path: Path):
    project = tmp_path / "project"
    nested = project / "some" / "nested" / "dir"
    nested.mkdir(parents=True)
    agent_owned = tmp_path / "agent-space" / ".criterion"
    agent_owned.mkdir(parents=True)
    (project / "myapp.catalyst").write_text(json.dumps({
        "project_name": "myapp",
        "agent-source": str(agent_owned),
    }), encoding="utf-8")
    assert cd.find_deploy_root(nested) == agent_owned


def test_find_deploy_root_falls_back_to_legacy_dir_on_stale_pointer(tmp_path: Path):
    """A pointer whose agent-source no longer exists (moved/deleted) must not
    mask a legacy in-tree .criterion/ that's actually still there."""
    root = make_valid_deployment(tmp_path)
    (tmp_path / "myapp.catalyst").write_text(json.dumps({
        "project_name": "myapp",
        "agent-source": str(tmp_path / "nowhere"),
    }), encoding="utf-8")
    assert cd.find_deploy_root(tmp_path) == root


def test_find_deploy_root_ignores_malformed_pointer(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (tmp_path / "myapp.catalyst").write_text("not json{", encoding="utf-8")
    assert cd.find_deploy_root(tmp_path) == root


def test_valid_deployment_has_no_errors(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    assert cd.check_naming(root) == []
    assert cd.check_single_rule_template(root) == []
    assert cd.check_rule_indexing(root) == []
    assert cd.check_required_headings(root) == []
    assert cd.check_rule_id_shape(root) == []
    assert cd.check_workflows_index_exists(root) == []
    assert cd.check_users_and_roles_exist(root) == []
    assert cd.check_users_have_userid(root) == []
    assert cd.check_journal_exists(root) == []
    assert cd.check_definitions_exist(root) == []


def test_check_naming_rejects_bare_id_filename(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    bad = root / "rules" / "business" / "br-AUTH-002.md"
    bad.write_text("# bare id, no summary\n", encoding="utf-8")
    errors = cd.check_naming(root)
    assert any("br-AUTH-002.md" in e for e in errors)


def test_check_naming_ignores_index_and_template_files(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    # rules.md and rules/templates/TEMPLATE-RULE-v1.md are already present
    # and bare-named; a clean tree must not flag them.
    assert cd.check_naming(root) == []


def test_check_naming_ignores_fixed_uppercase_documents(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "development" / "SUMMARY.md").write_text("# Summary\n", encoding="utf-8")
    assert cd.check_naming(root) == []


def test_check_naming_ignores_free_form_module_entity_files(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    add_example_module_artifacts(root)
    model = example_model(tmp_path)
    # NOTE declares `naming: free-form`: a trailing-digits name must not be
    # flagged as a bare ID (INV-7) the way br-AUTH-002.md would be.
    (root / "development" / "notes" / "product-2026.md").write_text("# n\n", encoding="utf-8")
    assert cd.check_naming(root, model) == []


def test_check_naming_walks_module_entity_folders(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    add_example_module_artifacts(root)
    model = example_model(tmp_path)
    (root / "items" / "ITEM-000001-ok.md").write_text("# ok\n", encoding="utf-8")
    assert cd.check_naming(root, model) == []
    (root / "items" / "ITEM-000002.md").write_text("# bare\n", encoding="utf-8")
    errors = cd.check_naming(root, model)
    assert any("ITEM-000002.md" in e for e in errors)
    # Kernel-only: the module's top-level folder is not walked at all.
    assert not any("items/" in e for e in cd.check_naming(root))


def test_build_model_kernel_only_uses_kernel_entities():
    model = cd.build_model(None)
    assert model.module_id is None
    assert "reconciliations" in model.checked_dirs
    assert "workflows.md" in model.index_names
    assert model.entity_types == cd.KERNEL_ENTITY_TYPES
    assert model.module_folders == ()


def test_build_model_adds_active_module_entities(tmp_path: Path):
    model = example_model(tmp_path)
    assert model.module_id == "example-process"
    assert "items" in model.checked_dirs
    assert "items.md" in model.index_names
    assert {"item", "note"} <= set(model.entity_types)
    assert model.free_form_folders == {"notes"}
    assert model.module_folders == ("items", "notes")


def test_check_single_rule_template_missing(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "rules" / "templates" / "TEMPLATE-RULE-v1.md").unlink()
    errors = cd.check_single_rule_template(root)
    assert any("no TEMPLATE-RULE" in e for e in errors)


def test_check_single_rule_template_multiple_versions_is_fine(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    # INV-20: versioning means adding a new file, never editing in place —
    # v1 and v2 coexisting in templates/ is the normal, expected state.
    (root / "rules" / "templates" / "TEMPLATE-RULE-v2.md").write_text("v2\n", encoding="utf-8")
    assert cd.check_single_rule_template(root) == []


def test_check_single_rule_template_wrong_location(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "rules" / "business" / "TEMPLATE-RULE-v1.md").write_text("misplaced\n", encoding="utf-8")
    errors = cd.check_single_rule_template(root)
    assert any("must live in rules/templates/" in e for e in errors)


def test_check_single_rule_template_missing_rules_dir(tmp_path: Path):
    root = tmp_path / ".criterion"
    root.mkdir()
    errors = cd.check_single_rule_template(root)
    assert errors == ["INV-8: rules/ directory is missing"]


def test_check_rule_indexing_flags_orphan_rule(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "rules" / "business" / "br-AUTH-002-logout-flow.md").write_text(
        "# br-AUTH-002-logout-flow\n\n## Contents\n\n## Linked Artifacts — Quick Index\n"
    , encoding="utf-8")
    errors = cd.check_rule_indexing(root)
    assert any("br-AUTH-002-logout-flow" in e and "orphan" in e for e in errors)


def test_check_rule_indexing_ignores_domain_files(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    domains = root / "rules" / "domains"
    domains.mkdir()
    (domains / "br-AUTH-user-authentication.md").write_text(
        "# br-AUTH — User authentication\n\n**Document:** ...\n"
    , encoding="utf-8")
    # Domain files are not rule documents (INV-20) — exempt from both the
    # rules.md orphan check and the ## Contents / Linked Artifacts heading check.
    assert cd.check_rule_indexing(root) == []
    assert cd.check_required_headings(root) == []


def test_check_naming_ignores_templates_catalog_files(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "rules" / "templates" / "templates-rule.md").write_text(
        "| Version | File | Timestamp | Notes |\n|---|---|---|---|\n"
        "| v1 | TEMPLATE-RULE-v1.md | 2026-08-23 | Initial version. |\n"
    , encoding="utf-8")
    assert cd.check_naming(root) == []


def test_check_naming_ignores_tickets_boards_workflows_indexes(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    work_items = root / "work-items"
    (work_items / "tickets").mkdir(parents=True)
    (work_items / "tickets" / "tickets.md").write_text("# Tickets index\n", encoding="utf-8")
    (work_items / "boards").mkdir(parents=True)
    (work_items / "boards" / "boards.md").write_text("# Boards index\n", encoding="utf-8")
    (work_items / "workflows").mkdir(parents=True)
    (work_items / "workflows" / "workflows.md").write_text("# Workflows index\n", encoding="utf-8")
    assert cd.check_naming(root) == []


def test_check_naming_ignores_reconciliations_index(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    reconciliations = root / "reconciliations"
    reconciliations.mkdir(parents=True)
    (reconciliations / "reconciliations.md").write_text("# Reconciliations index\n", encoding="utf-8")
    (reconciliations / "RECON-000001-rights-mismatch-on-br-auth.md").write_text(
        "# RECON-000001-rights-mismatch-on-br-auth\n"
    , encoding="utf-8")
    assert cd.check_naming(root) == []


def test_check_naming_rejects_bare_id_reconciliation_filename(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    reconciliations = root / "reconciliations"
    reconciliations.mkdir(parents=True)
    bad = reconciliations / "RECON-000002.md"
    bad.write_text("# bare id, no summary\n", encoding="utf-8")
    errors = cd.check_naming(root)
    assert any("RECON-000002.md" in e for e in errors)


def test_check_rule_indexing_missing_global_index(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "rules" / "rules.md").unlink()
    errors = cd.check_rule_indexing(root)
    assert any("rules/rules.md global index is missing" in e for e in errors)


def test_check_required_headings_missing_contents(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    rule = root / "rules" / "business" / "br-AUTH-000001-Ab3xR9pQ-login-flow.md"
    rule.write_text("## `br-AUTH-000001-Ab3xR9pQ` Login flow\n\n## Linked Artifacts — Quick Index\n", encoding="utf-8")
    errors = cd.check_required_headings(root)
    assert any("missing '## Contents'" in e for e in errors)


def test_check_required_headings_missing_linked_artifacts(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    rule = root / "rules" / "business" / "br-AUTH-000001-Ab3xR9pQ-login-flow.md"
    rule.write_text("## `br-AUTH-000001-Ab3xR9pQ` Login flow\n\n## Contents\n", encoding="utf-8")
    errors = cd.check_required_headings(root)
    assert any("missing '## Linked Artifacts" in e for e in errors)


def test_valid_deployment_with_module_has_no_errors(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    add_example_module_artifacts(root)
    model = example_model(tmp_path)
    assert cd.check_naming(root, model) == []
    assert cd.check_module_required_paths(root, model) == []
    assert cd.check_module_indexes(root, model) == []
    assert cd.check_definitions_exist(root, model) == []


def test_check_module_required_paths_missing(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    add_example_module_artifacts(root)
    model = example_model(tmp_path)
    (root / "development" / "LEDGER-OF-ITEMS.md").unlink()
    errors = cd.check_module_required_paths(root, model)
    assert len(errors) == 1
    assert "INV-EX-1" in errors[0]
    assert "development/LEDGER-OF-ITEMS.md is missing" in errors[0]
    assert "templates/ledger.template.md" in errors[0]


def test_check_module_required_paths_kernel_only_is_noop(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    assert cd.check_module_required_paths(root, cd.build_model()) == []


def test_check_module_indexes_missing(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    add_example_module_artifacts(root)
    model = example_model(tmp_path)
    (root / "development" / "notes" / "notes.md").unlink()
    errors = cd.check_module_indexes(root, model)
    assert len(errors) == 1
    assert "development/notes/notes.md is missing" in errors[0]


def test_check_module_indexes_absent_folder_is_fine(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    assert cd.check_module_indexes(root, example_model(tmp_path)) == []


def test_check_workflows_index_exists_missing(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "workflows" / "workflows.md").unlink()
    errors = cd.check_workflows_index_exists(root)
    assert any(
        "INV-24" in e and "workflows/workflows.md is missing" in e
        for e in errors
    )


def test_check_workflows_index_exists_missing_workflows_dir(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    shutil.rmtree(root / "workflows")
    errors = cd.check_workflows_index_exists(root)
    assert any("INV-24" in e for e in errors)


def test_check_users_and_roles_exist_missing_users(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "IAM" / "users" / "users.json").unlink()
    errors = cd.check_users_and_roles_exist(root)
    assert any("INV-16" in e and "IAM/users/users.json is missing" in e
               for e in errors)
    assert not any("roles.json" in e for e in errors)


def test_check_users_and_roles_exist_missing_roles(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "IAM" / "roles" / "roles.json").unlink()
    errors = cd.check_users_and_roles_exist(root)
    assert any("INV-16" in e and "IAM/roles/roles.json is missing" in e
               for e in errors)
    assert not any("users.json is missing" in e for e in errors)


def test_check_users_and_roles_exist_missing_both(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "IAM" / "users" / "users.json").unlink()
    (root / "IAM" / "roles" / "roles.json").unlink()
    errors = cd.check_users_and_roles_exist(root)
    assert len(errors) == 2


def test_check_users_and_roles_exist_missing_iam_dir(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    shutil.rmtree(root / "IAM")
    errors = cd.check_users_and_roles_exist(root)
    assert len(errors) == 2


def test_check_users_and_roles_exist_no_active_user(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "IAM" / "users" / "users.json").write_text(json.dumps({
        "users": [
            {"name": "Ada", "roles": ["Developer"], "registered": "2026-08-23",
             "active": False, "notes": ""},
        ]
    }), encoding="utf-8")
    errors = cd.check_users_and_roles_exist(root)
    assert any("INV-16" in e and "no active user" in e for e in errors)


def test_check_users_and_roles_exist_empty_users_array(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "IAM" / "users" / "users.json").write_text(json.dumps({"users": []}), encoding="utf-8")
    errors = cd.check_users_and_roles_exist(root)
    assert any("no active user" in e for e in errors)


def test_check_users_have_userid_missing(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "IAM" / "users" / "users.json").write_text(json.dumps({
        "users": [
            {"name": "Ada", "roles": ["Developer"], "registered": "2026-08-23",
             "active": True, "notes": ""},
        ]
    }), encoding="utf-8")
    errors = cd.check_users_have_userid(root)
    assert any("INV-26" in e and "Ada" in e for e in errors)


def test_check_users_have_userid_no_uppercase(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "IAM" / "users" / "users.json").write_text(json.dumps({
        "users": [
            {"name": "Ada", "roles": ["Developer"], "registered": "2026-08-23",
             "active": True, "notes": "", "userid": "ab3xr9pq"},
        ]
    }), encoding="utf-8")
    errors = cd.check_users_have_userid(root)
    assert any("INV-26" in e and "Ada" in e for e in errors)


def test_check_users_have_userid_duplicate(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "IAM" / "users" / "users.json").write_text(json.dumps({
        "users": [
            {"name": "Ada", "roles": ["Developer"], "registered": "2026-08-23",
             "active": True, "notes": "", "userid": "Ab3xR9pQ"},
            {"name": "Bea", "roles": ["Developer"], "registered": "2026-08-24",
             "active": True, "notes": "", "userid": "Ab3xR9pQ"},
        ]
    }), encoding="utf-8")
    errors = cd.check_users_have_userid(root)
    assert any("INV-26" in e and "more than one user" in e for e in errors)


def test_check_rule_id_shape_short_digits(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    rule = root / "rules" / "business" / "br-AUTH-000001-Ab3xR9pQ-login-flow.md"
    rule.write_text(
        "## `br-AUTH-001-Ab3xR9pQ` Login flow\n\n"
        "## Contents\n\n## Linked Artifacts — Quick Index\n"
    , encoding="utf-8")
    errors = cd.check_rule_id_shape(root)
    assert any("INV-26 width" in e and "3-digit" in e for e in errors)


def test_check_rule_id_shape_missing_userid_suffix(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    rule = root / "rules" / "business" / "br-AUTH-000001-Ab3xR9pQ-login-flow.md"
    rule.write_text(
        "## `br-AUTH-000001` Login flow\n\n"
        "## Contents\n\n## Linked Artifacts — Quick Index\n"
    , encoding="utf-8")
    errors = cd.check_rule_id_shape(root)
    assert any("INV-26 signer" in e and "no valid trailing userid" in e
               for e in errors)


def test_check_rule_id_shape_unknown_userid(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    rule = root / "rules" / "business" / "br-AUTH-000001-Ab3xR9pQ-login-flow.md"
    rule.write_text(
        "## `br-AUTH-000001-Zz9kM2wT` Login flow\n\n"
        "## Contents\n\n## Linked Artifacts — Quick Index\n"
    , encoding="utf-8")
    errors = cd.check_rule_id_shape(root)
    assert any("INV-26 signer" in e and "does not match any registered user" in e
               for e in errors)


def test_check_rule_id_shape_applies_to_rr_meta_ids_too(tmp_path: Path):
    # rr-META-* is exempt from check_rule_indexing (never listed in
    # rules.md) but NOT from the id-shape convention itself — rr-META-003
    # names `rr` as one of DOC_PREFIX's own examples, same grammar as
    # every other rule.
    root = make_valid_deployment(tmp_path)
    (root / "rules" / "Rules-of-Rules.md").write_text(
        "## 1. `rr-META-010` A three-digit, unsuffixed self-governing id\n"
    , encoding="utf-8")
    errors = cd.check_rule_id_shape(root)
    assert any("INV-26 width" in e and "rr-META-010" in e for e in errors)
    assert any("INV-26 signer" in e and "rr-META-010" in e for e in errors)


def test_check_rule_id_shape_ignores_pure_bullet_list_index(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    # rules.md is a bullet-list index, not a rule document — bullets are
    # never headings, so this is really just confirming the file is
    # skipped rather than merely never matching.
    (root / "rules" / "rules.md").write_text(
        "# Rules index\n\n- rr-META-010 (not a real heading)\n"
    , encoding="utf-8")
    errors = cd.check_rule_id_shape(root)
    assert errors == []


def test_check_users_and_roles_exist_invalid_json(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "IAM" / "users" / "users.json").write_text("{not valid json", encoding="utf-8")
    errors = cd.check_users_and_roles_exist(root)
    assert any("not valid JSON" in e for e in errors)


def test_check_journal_exists_missing(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "development" / "journal.jsonl").unlink()
    errors = cd.check_journal_exists(root)
    assert any("INV-17" in e and "development/journal.jsonl is missing" in e
               for e in errors)


def test_check_journal_exists_empty_file_is_valid(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "development" / "journal.jsonl").write_text("", encoding="utf-8")
    assert cd.check_journal_exists(root) == []


def test_check_journal_exists_rejects_malformed_json_line(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "development" / "journal.jsonl").write_text("{not valid json\n", encoding="utf-8")
    errors = cd.check_journal_exists(root)
    assert any("journal.jsonl:1 is not valid JSON" in e for e in errors)


def test_check_journal_exists_rejects_non_object_line(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "development" / "journal.jsonl").write_text("[1, 2, 3]\n", encoding="utf-8")
    errors = cd.check_journal_exists(root)
    assert any("journal.jsonl:1 is not a JSON object" in e for e in errors)


def test_check_journal_exists_rejects_missing_required_field(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    entry = json.loads(
        (root / "development" / "journal.jsonl").read_text(encoding="utf-8").strip()
    )
    del entry["intent"]
    (root / "development" / "journal.jsonl").write_text(json.dumps(entry) + "\n", encoding="utf-8")
    errors = cd.check_journal_exists(root)
    assert any("missing field 'intent'" in e for e in errors)


def test_check_journal_exists_rejects_bad_file_hash(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    entry = json.loads(
        (root / "development" / "journal.jsonl").read_text(encoding="utf-8").strip()
    )
    entry["files"][0]["after"] = "not-a-hash"
    (root / "development" / "journal.jsonl").write_text(json.dumps(entry) + "\n", encoding="utf-8")
    errors = cd.check_journal_exists(root)
    assert any("not a 40-hex git hash or null" in e for e in errors)


def test_check_journal_exists_null_hash_is_valid(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    entry = json.loads(
        (root / "development" / "journal.jsonl").read_text(encoding="utf-8").strip()
    )
    entry["files"][0]["after"] = None
    (root / "development" / "journal.jsonl").write_text(json.dumps(entry) + "\n", encoding="utf-8")
    assert cd.check_journal_exists(root) == []


def test_check_journal_exists_rejects_files_entry_missing_path(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    entry = json.loads(
        (root / "development" / "journal.jsonl").read_text(encoding="utf-8").strip()
    )
    entry["files"] = [{"before": None, "after": "a" * 40}]
    (root / "development" / "journal.jsonl").write_text(json.dumps(entry) + "\n", encoding="utf-8")
    errors = cd.check_journal_exists(root)
    assert any("missing 'path'" in e for e in errors)


def test_check_journal_exists_ignores_blank_lines(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    existing = (root / "development" / "journal.jsonl").read_text(encoding="utf-8")
    (root / "development" / "journal.jsonl").write_text(existing + "\n\n   \n", encoding="utf-8")
    assert cd.check_journal_exists(root) == []


def test_check_definitions_exist_missing_dir(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    shutil.rmtree(root / "definitions")
    errors = cd.check_definitions_exist(root)
    assert any("definitions/ is missing" in e for e in errors)


def test_check_definitions_exist_missing_one_type(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "definitions" / "rule.md").unlink()
    errors = cd.check_definitions_exist(root)
    assert len(errors) == 1
    assert "definitions/rule.md is missing" in errors[0]


def test_check_definitions_exist_missing_module_type(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    add_example_module_artifacts(root)
    model = example_model(tmp_path)
    (root / "definitions" / "item.md").unlink()
    errors = cd.check_definitions_exist(root, model)
    assert len(errors) == 1
    assert "definitions/item.md is missing" in errors[0]
    assert "example-process" in errors[0]


def test_main_returns_zero_when_no_deployment(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cd.main() == 0
    assert "skipping deployment validation" in capsys.readouterr().out


def test_main_returns_zero_for_valid_deployment(tmp_path: Path, monkeypatch):
    make_valid_deployment(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert cd.main() == 0


def test_main_returns_one_for_broken_deployment(tmp_path: Path, monkeypatch):
    root = make_valid_deployment(tmp_path)
    (root / "rules" / "templates" / "TEMPLATE-RULE-v1.md").unlink()
    monkeypatch.chdir(tmp_path)
    assert cd.main() == 1


def test_main_uses_module_declared_by_pointer(tmp_path: Path, monkeypatch, capsys):
    project = tmp_path / "app"
    project.mkdir()
    deploy = make_valid_deployment(tmp_path / "agent")
    write_example_module(project)
    (project / "app.catalyst").write_text(json.dumps(
        {"module": "example-process", "agent-source": str(deploy)}), encoding="utf-8")
    monkeypatch.chdir(project)
    # The module's required path and indexes are missing: main must fail.
    assert cd.main() == 1
    add_example_module_artifacts(deploy)
    capsys.readouterr()
    assert cd.main() == 0
    assert "module example-process" in capsys.readouterr().out


def test_version_drift_missing_version_file(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (root / "version.txt").unlink()
    assert cd.check_version_drift(root, tmp_path) == [".criterion/version.txt is missing"]


def test_version_drift_pointer_mismatch(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (tmp_path / "myapp.catalyst").write_text(json.dumps({"kernel_version": "0.36.0"}), encoding="utf-8")
    errors = cd.check_version_drift(root, tmp_path)
    assert errors == ["version drift: the pointer's kernel_version is 0.36.0 "
                      "but .criterion/version.txt is 0.37.0"]


def test_version_drift_legacy_framework_version_field(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (tmp_path / "myapp.catalyst").write_text(json.dumps({"framework_version": "0.32.1"}), encoding="utf-8")
    assert "framework_version is 0.32.1" in cd.check_version_drift(root, tmp_path)[0]


def test_version_drift_agreeing_versions(tmp_path: Path):
    root = make_valid_deployment(tmp_path)
    (tmp_path / "myapp.catalyst").write_text(json.dumps({"kernel_version": "0.37.0"}), encoding="utf-8")
    assert cd.check_version_drift(root, tmp_path) == []


def test_version_drift_kernel_repo_behind(tmp_path: Path):
    """In catalyst's own repository the dogfood deployment must track the
    kernel's own version."""
    root = make_valid_deployment(tmp_path)
    (tmp_path / "framework" / "kernel").mkdir(parents=True)
    (tmp_path / "version.txt").write_text("0.38.0\n", encoding="utf-8")
    errors = cd.check_version_drift(root, tmp_path)
    assert errors == ["version drift: the kernel is 0.38.0 but this repository's "
                      "own deployment is 0.37.0 — run /sync-framework"]



def test_require_fails_when_no_deployment(tmp_path: Path, monkeypatch, capsys):
    """CI passes --require: a gate that finds nothing to check must fail, not
    skip (local development without a deployment still skips)."""
    monkeypatch.chdir(tmp_path)
    assert cd.main(["--require"]) == 1
    assert "--require" in capsys.readouterr().out
    assert cd.main([]) == 0


def test_require_still_fails_a_broken_deployment(tmp_path: Path, monkeypatch):
    root = make_valid_deployment(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert cd.main(["--require"]) == 0
    (root / "rules" / "templates" / "TEMPLATE-RULE-v1.md").unlink()
    assert cd.main(["--require"]) == 1
