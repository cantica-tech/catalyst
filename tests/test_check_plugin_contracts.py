from pathlib import Path

import check_plugin_contracts as cpc

VALID_UUID = "123e4567-e89b-12d3-a456-426614174000"


def make_contract(
    tmp_path: Path,
    *,
    name="catalyst-git",
    version="1.2.3",
    active="true",
    uuid=VALID_UUID,
    write_version_txt=True,
    extra_metadata="",
) -> Path:
    plugin_dir = tmp_path / "plugins" / "repository" / name
    plugin_dir.mkdir(parents=True)
    contract = plugin_dir / "working-contract.md"
    contract.write_text(
        f"# {name}\n\n"
        "## Metadata\n\n"
        f"- Name: {name}\n"
        "- Description: A plugin\n"
        f"- UUID: {uuid}\n"
        f"- Version: {version}\n"
        f"- Active: {active}\n"
        "- Type: repository\n"
        f"{extra_metadata}"
        "\n## Operation\n\n- Name: not-metadata-here\n",
        encoding="utf-8",
    )
    if write_version_txt:
        (plugin_dir / "version.txt").write_text(f"{version}\n", encoding="utf-8")
    return plugin_dir


def test_parse_metadata_extracts_fields(tmp_path: Path):
    plugin_dir = make_contract(tmp_path)
    fields = cpc.parse_metadata(plugin_dir / "working-contract.md")
    assert fields["Name"] == "catalyst-git"
    assert fields["UUID"] == VALID_UUID
    assert fields["Version"] == "1.2.3"
    assert fields["Active"] == "true"
    assert fields["Type"] == "repository"


def test_parse_metadata_ignores_fields_outside_metadata_section(tmp_path: Path):
    plugin_dir = make_contract(tmp_path)
    fields = cpc.parse_metadata(plugin_dir / "working-contract.md")
    # the "- Name: not-metadata-here" line lives under "## Operation", not
    # "## Metadata", and must not clobber the real Name field.
    assert fields["Name"] == "catalyst-git"


def test_read_version_txt_present(tmp_path: Path):
    plugin_dir = make_contract(tmp_path, version="9.9.9")
    assert cpc.read_version_txt(plugin_dir) == "9.9.9"


def test_read_version_txt_missing(tmp_path: Path):
    plugin_dir = make_contract(tmp_path, write_version_txt=False)
    assert cpc.read_version_txt(plugin_dir) is None


def test_parse_catalog_pins_skips_header_and_separator(tmp_path: Path):
    type_dir = tmp_path / "plugins" / "repository"
    type_dir.mkdir(parents=True)
    (type_dir / "catalog.md").write_text(
        "| Plugin | Type | Release | Tag |\n"
        "|---|---|---|---|\n"
        "| [catalyst-git](https://github.com/x/catalyst-git) | repository | 1.2.3 | 1.2.3 |\n",
        encoding="utf-8",
    )
    pins = cpc.parse_catalog_pins(type_dir)
    assert pins == {"catalyst-git": {"release": "1.2.3", "tag": "1.2.3"}}


def test_parse_catalog_pins_missing_catalog_returns_empty(tmp_path: Path):
    type_dir = tmp_path / "plugins" / "repository"
    type_dir.mkdir(parents=True)
    assert cpc.parse_catalog_pins(type_dir) == {}


def test_normalize_url_variants_are_equal():
    variants = [
        "https://github.com/oliben67/catalyst-git.git",
        "https://github.com/oliben67/catalyst-git",
        "https://github.com/oliben67/catalyst-git/",
        "git@github.com:oliben67/catalyst-git.git",
        "HTTPS://GitHub.com/oliben67/catalyst-git.GIT",
    ]
    normalized = {cpc.normalize_url(v) for v in variants}
    assert normalized == {"github.com/oliben67/catalyst-git"}


def test_find_plugins_discovers_and_filters(tmp_path: Path):
    make_contract(tmp_path, name="catalyst-git")
    # a dir without a working-contract.md must not be picked up
    (tmp_path / "plugins" / "repository" / "no-contract").mkdir(parents=True)
    # a dot-dir must be skipped even if it somehow had a contract
    dotdir = tmp_path / "plugins" / "repository" / ".hidden"
    dotdir.mkdir(parents=True)
    (dotdir / "working-contract.md").write_text("# hidden\n", encoding="utf-8")

    # find_plugins() reads the module-level PLUGINS_DIR, so point it at our tmp tree
    original = cpc.PLUGINS_DIR
    try:
        cpc.PLUGINS_DIR = tmp_path / "plugins"
        found = cpc.find_plugins()
    finally:
        cpc.PLUGINS_DIR = original

    names = {p.name for p in found}
    assert names == {"catalyst-git"}


def test_validate_plugin_valid_contract_has_no_errors(tmp_path: Path):
    plugin_dir = make_contract(tmp_path)
    assert cpc.validate_plugin(plugin_dir, framework_url=None) == []


def test_validate_plugin_missing_field(tmp_path: Path):
    plugin_dir = tmp_path / "plugins" / "repository" / "bad"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "working-contract.md").write_text("## Metadata\n\n- Name: bad\n- Version: 1.0.0\n", encoding="utf-8")
    (plugin_dir / "version.txt").write_text("1.0.0\n", encoding="utf-8")
    errors = cpc.validate_plugin(plugin_dir, framework_url=None)
    assert any("missing metadata field 'UUID'" in e for e in errors)
    assert any("missing metadata field 'Active'" in e for e in errors)


def test_validate_plugin_leftover_placeholder(tmp_path: Path):
    plugin_dir = make_contract(tmp_path, extra_metadata="")
    contract = plugin_dir / "working-contract.md"
    text = contract.read_text(encoding="utf-8").replace("A plugin", "<describe the plugin>")
    contract.write_text(text, encoding="utf-8")
    errors = cpc.validate_plugin(plugin_dir, framework_url=None)
    assert any("placeholder left in 'Description'" in e for e in errors)


def test_validate_plugin_bad_uuid(tmp_path: Path):
    plugin_dir = make_contract(tmp_path, uuid="not-a-uuid")
    errors = cpc.validate_plugin(plugin_dir, framework_url=None)
    assert any("not a well-formed UUID" in e for e in errors)


def test_validate_plugin_active_not_boolean(tmp_path: Path):
    plugin_dir = make_contract(tmp_path, active="yes")
    errors = cpc.validate_plugin(plugin_dir, framework_url=None)
    assert any("Active must be true|false" in e for e in errors)


def test_validate_plugin_missing_version_txt(tmp_path: Path):
    plugin_dir = make_contract(tmp_path, write_version_txt=False)
    errors = cpc.validate_plugin(plugin_dir, framework_url=None)
    assert any("version.txt is missing" in e for e in errors)


def test_validate_plugin_version_mismatch(tmp_path: Path):
    plugin_dir = make_contract(tmp_path, version="1.2.3")
    (plugin_dir / "version.txt").write_text("1.2.4\n", encoding="utf-8")
    errors = cpc.validate_plugin(plugin_dir, framework_url=None)
    assert any("Version '1.2.3' != version.txt '1.2.4'" in e for e in errors)


def test_validate_plugin_catalog_tag_mismatch(tmp_path: Path):
    plugin_dir = make_contract(tmp_path, name="catalyst-git", version="1.2.3")
    (plugin_dir.parent / "catalog.md").write_text(
        "| Plugin | Type | Release | Tag |\n"
        "|---|---|---|---|\n"
        "| [catalyst-git](https://x) | repository | 1.2.3 | 1.9.9 |\n",
        encoding="utf-8",
    )
    errors = cpc.validate_plugin(plugin_dir, framework_url=None)
    assert any("catalog Tag '1.9.9' != version.txt '1.2.3'" in e for e in errors)


def test_validate_plugin_catalog_release_allows_v_prefix(tmp_path: Path):
    plugin_dir = make_contract(tmp_path, name="catalyst-git", version="1.2.3")
    (plugin_dir.parent / "catalog.md").write_text(
        "| Plugin | Type | Release | Tag |\n"
        "|---|---|---|---|\n"
        "| [catalyst-git](https://x) | repository | v1.2.3 | 1.2.3 |\n",
        encoding="utf-8",
    )
    errors = cpc.validate_plugin(plugin_dir, framework_url=None)
    assert errors == []


def test_require_fails_when_no_plugin_is_checked_out(tmp_path: Path, monkeypatch, capsys):
    """CI passes --require (submodules checked out): finding no plugin to
    check fails instead of skipping; locally it still skips."""
    monkeypatch.setattr(cpc, "PLUGINS_DIR", tmp_path / "plugins")
    assert cpc.main([]) == 0
    assert cpc.main(["--require"]) == 1
    assert "--require" in capsys.readouterr().out
