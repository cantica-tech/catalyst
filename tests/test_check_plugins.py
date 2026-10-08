from pathlib import Path

import check_plugins as cpg


def write_gitmodules(root: Path, entries: list[tuple[str, str]]) -> None:
    lines = []
    for name, path in entries:
        lines.append(f'[submodule "{name}"]')
        lines.append(f"\tpath = {path}")
        lines.append(f"\turl = https://example.com/{name}.git")
    (root / ".gitmodules").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_load_submodule_entries_parses_paths(tmp_path: Path):
    write_gitmodules(tmp_path, [("catalyst-git", "framework/kernel/plugins/repository/catalyst-git")])
    entries = cpg.load_submodule_entries(tmp_path)
    assert entries == [('submodule "catalyst-git"', "framework/kernel/plugins/repository/catalyst-git")]


def test_load_submodule_entries_missing_file_returns_empty(tmp_path: Path):
    assert cpg.load_submodule_entries(tmp_path) == []


def test_validate_plugin_structure_valid(tmp_path: Path):
    plugin_dir = tmp_path / "framework" / "kernel" / "plugins" / "repository" / "catalyst-git"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "README.md").write_text("# readme\n", encoding="utf-8")
    (plugin_dir / "working-contract.md").write_text("# contract\n", encoding="utf-8")
    assert cpg.validate_plugin_structure(tmp_path) == []


def test_validate_plugin_structure_missing_readme(tmp_path: Path):
    plugin_dir = tmp_path / "framework" / "kernel" / "plugins" / "repository" / "catalyst-git"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "working-contract.md").write_text("# contract\n", encoding="utf-8")
    errors = cpg.validate_plugin_structure(tmp_path)
    assert any("README.md is missing" in e for e in errors)


def test_validate_plugin_structure_missing_contract(tmp_path: Path):
    plugin_dir = tmp_path / "framework" / "kernel" / "plugins" / "repository" / "catalyst-git"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "README.md").write_text("# readme\n", encoding="utf-8")
    errors = cpg.validate_plugin_structure(tmp_path)
    assert any("working-contract.md is missing" in e for e in errors)


def test_validate_plugin_structure_skips_dotdirs(tmp_path: Path):
    (tmp_path / "framework" / "kernel" / "plugins" / "repository" / ".git").mkdir(parents=True)
    assert cpg.validate_plugin_structure(tmp_path) == []


def test_validate_plugin_structure_missing_repository_dir(tmp_path: Path):
    errors = cpg.validate_plugin_structure(tmp_path)
    assert errors == ["framework/kernel/plugins/repository directory is missing"]


def test_validate_submodule_policy_present(tmp_path: Path):
    write_gitmodules(tmp_path, [("catalyst-git", "framework/kernel/plugins/repository/catalyst-git")])
    (tmp_path / "framework" / "kernel" / "plugins" / "repository" / "catalyst-git").mkdir(parents=True)
    assert cpg.validate_submodule_policy(tmp_path) == []


def test_validate_submodule_policy_missing_checkout(tmp_path: Path):
    write_gitmodules(tmp_path, [("catalyst-git", "framework/kernel/plugins/repository/catalyst-git")])
    errors = cpg.validate_submodule_policy(tmp_path)
    assert any("framework/kernel/plugins/repository/catalyst-git is not present" in e for e in errors)


def test_validate_submodule_policy_ignores_non_plugin_submodules(tmp_path: Path):
    write_gitmodules(tmp_path, [("other", "vendor/other")])
    assert cpg.validate_submodule_policy(tmp_path) == []


def test_parse_submodule_status_flags_uninitialized_plugin():
    status = (
        "-abc123 framework/kernel/plugins/repository/catalyst-git\n"
        " 1234567 vendor/other (heads/main)\n"
    )
    errors = cpg.parse_submodule_status(status, {"framework/kernel/plugins/repository/catalyst-git"})
    assert any(
        "framework/kernel/plugins/repository/catalyst-git is not initialized" in e for e in errors
    )


def test_parse_submodule_status_ignores_non_plugin_paths():
    status = "-abc123 vendor/other\n"
    errors = cpg.parse_submodule_status(status, {"framework/kernel/plugins/repository/catalyst-git"})
    assert errors == []


def test_parse_submodule_status_clean_checkout_has_no_errors():
    status = " 1234567 framework/kernel/plugins/repository/catalyst-git (heads/development)\n"
    errors = cpg.parse_submodule_status(status, {"framework/kernel/plugins/repository/catalyst-git"})
    assert errors == []


def test_validate_plugin_sources_uses_git_status(tmp_path: Path, monkeypatch):
    write_gitmodules(tmp_path, [("catalyst-git", "framework/kernel/plugins/repository/catalyst-git")])

    def fake_run_git(args: list[str], cwd: Path) -> str:
        assert args == ["submodule", "status"]
        assert cwd == tmp_path
        return "-abc123 framework/kernel/plugins/repository/catalyst-git\n"

    monkeypatch.setattr(cpg, "run_git", fake_run_git)
    errors = cpg.validate_plugin_sources(tmp_path)
    assert any("not initialized or checked out" in e for e in errors)


def test_validate_plugin_sources_clean_has_no_errors(tmp_path: Path, monkeypatch):
    write_gitmodules(tmp_path, [("catalyst-git", "framework/kernel/plugins/repository/catalyst-git")])

    def fake_run_git(args: list[str], cwd: Path) -> str:
        return " 1234567 framework/kernel/plugins/repository/catalyst-git (heads/development)\n"

    monkeypatch.setattr(cpg, "run_git", fake_run_git)
    assert cpg.validate_plugin_sources(tmp_path) == []
