from pathlib import Path

import check_kernel_purity as ckp


def _write_module(base: Path) -> Path:
    mod = base / "catalyst-example-process"
    (mod / "schemas").mkdir(parents=True)
    (mod / "module.yaml").write_text(
        "id: example-process\n"
        "name: Example Process Module\n"
        "version: 1.0.0\n"
        "description: Fixture module.\n"
        "grounding_type: rule\n"
        "entity_types:\n"
        "  - id: ITEM\n"
        "    schema: schemas/item.yaml\n"
        "commands:\n"
        "  - name: create-item\n"
        "    description: Create an item\n"
        "    spec_path: commands/create-item.md\n"
        "templates:\n"
        "  - entity_type: ITEM\n"
        "    template_path: templates/item.template.md\n"
    , encoding="utf-8")
    (mod / "schemas" / "item.yaml").write_text(
        "id_prefix: ITEM\nname: Item\nplural_name: Items\nfolder: items\n"
    , encoding="utf-8")
    return mod


def _repo(tmp_path: Path, kernel_text: str) -> Path:
    root = tmp_path / "catalyst"
    (root / "framework" / "kernel").mkdir(parents=True)
    (root / "framework" / "modules").mkdir(parents=True)
    (root / "framework" / "modules" / "catalog.md").write_text(
        "| Id | Repository | Default branch |\n|---|---|---|\n"
        "| `example-process` | `git@example.com:x/catalyst-example-process.git` | `main` |\n"
    , encoding="utf-8")
    (root / "framework" / "kernel" / "GUIDE.md").write_text(kernel_text, encoding="utf-8")
    return root


def _run(root: Path):
    ids = ckp.catalog_module_ids(root / "framework" / "modules" / "catalog.md")
    denylists = [ckp.build_denylist(ckp.find_module_dir(i, root)) for i in ids]
    return ckp.check(ckp.scan_files(root), denylists, root)


def test_catalog_ids(tmp_path: Path):
    root = _repo(tmp_path, "")
    assert ckp.catalog_module_ids(root / "framework" / "modules" / "catalog.md") == ["example-process"]


def test_generic_kernel_text_passes(tmp_path: Path):
    _write_module(tmp_path)
    root = _repo(tmp_path, "The active module adds its entity types, e.g. `<PREFIX>-NNNNNN`.\n")
    errors, warnings = _run(root)
    assert errors == [] and warnings == []


def test_module_names_are_errors(tmp_path: Path):
    _write_module(tmp_path)
    root = _repo(
        tmp_path,
        "Create ITEM-000001 with /create-item in items/ from item.template.md.\n"
        "The example-process module.\n",
    )
    errors, _ = _run(root)
    labels = " ".join(errors)
    for expected in ("entity prefix 'ITEM'", "module command 'create-item'",
                     "entity folder 'items'", "module template 'item.template.md'",
                     "module id 'example-process'"):
        assert expected in labels


def test_entity_names_are_warnings_only(tmp_path: Path):
    _write_module(tmp_path)
    root = _repo(tmp_path, "Each Item has an owner.\n")
    errors, warnings = _run(root)
    assert errors == []
    assert any("entity name 'Item'" in w for w in warnings)


def test_prefix_inside_other_words_is_not_flagged(tmp_path: Path):
    _write_module(tmp_path)
    root = _repo(tmp_path, "ITEMS_TOTAL and SUBITEM are unrelated identifiers.\n")
    errors, _ = _run(root)
    assert errors == []
