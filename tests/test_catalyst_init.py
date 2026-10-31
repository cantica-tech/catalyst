from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from catalyst import compose
from catalyst.check import run as run_checks
from catalyst.deployment import load
from catalyst.init import InitError, InitRequest, init
from catalyst_fixtures import ITEM_SCHEMA, MODULE_YAML, SUB_SCHEMA, journal_entries, write

REPO = Path(__file__).resolve().parent.parent
KERNEL = REPO / "framework" / "kernel"


def example_module(base: Path) -> Path:
    mod = base / "example-process"
    write(
        mod / "module.yaml",
        MODULE_YAML + "\ntemplates:\n  - entity_type: ITEM\n    template_path: templates/item.template.md\n",
    )
    write(mod / "version.txt", "0.2.0\n")
    write(mod / "schemas" / "item.yaml", ITEM_SCHEMA)
    write(mod / "schemas" / "sub.yaml", SUB_SCHEMA + "location: development\n")
    write(mod / "templates" / "item.template.md", "# `ITEM-NNNNNN` — {{title}}\n")
    write(
        mod / "code-of-conduct.module.md",
        "# module contribution\n\n## 3. Standard document types\n\n- `ITEM` — an item.\n\n"
        "## 4. Slash-command entry points\n\n- `/create-item` — create an item (`rr-META-009`).\n",
    )
    write(
        mod / "rules-of-rules.module.md",
        "# module meta-rules\n\n> preamble\n\n## 9. `rr-META-009` Items\n\nItems are items.\n",
    )
    write(mod / "definitions" / "item" / "DEFINITION-ITEM-v1.md", "# Item v1\n")
    write(mod / "definitions" / "item" / "DEFINITION-ITEM-v2.md", "# Item v2\n")
    return mod


def request(tmp: Path, **kw) -> InitRequest:
    project = tmp / "app"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    base = dict(
        project=project,
        name="app",
        module_id="example-process",
        user="Ada Lovelace",
        kernel=KERNEL,
        module=example_module(tmp),
        git_username="ada",
        rule_docs=[("business-rules.md", "br")],
        test_locations="`tests/`",
        at=tmp / "agent" / ".criterion",
        agent="test-agent",
    )
    base.update(kw)
    return InitRequest(**base)


def test_init_produces_a_deployment_that_passes_every_check(tmp_path):
    req = request(tmp_path)
    init(req)
    dep = load(req.project)
    report = run_checks(dep)
    static = "identity: IAM/identity.json: the static provider verifies nobody"  # the tests' pointer (design 29)
    assert report.errors == [] and [w for w in report.warnings if not w.startswith(("legacy:", static))] == []
    root = dep.root
    assert (req.project / ".criterion").is_symlink()
    assert "/.criterion" in (req.project / ".gitignore").read_text(encoding="utf-8")
    pointer = json.loads((req.project / "app.catalyst").read_text(encoding="utf-8"))
    assert pointer["module"] == "example-process" and pointer["repoed"] is False
    assert pointer["journal_since"] == ""  # no commit yet: the whole history is governed
    # the installer signs first, in the signers ledger; no users.json (design 29)
    user = json.loads((root / "IAM" / "signers.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert user["username"] == "ada" and len(user["userid"]) == 8
    assert not (root / "IAM" / "users" / "users.json").exists()
    coc = (root / "CODE-OF-CONDUCT.md").read_text(encoding="utf-8")
    assert "### From module example-process" in coc and f"rr-META-000009-{user['userid']}" in coc
    assert "{{RULES_DIR}}" not in coc
    assert (root / "development" / "subs" / "subs.md").is_file()  # ETD location honoured
    assert (root / "items" / "templates" / "TEMPLATE-ITEM-v1.md").is_file()
    assert (root / "definitions" / "item.md").read_text(encoding="utf-8") == "# Item v2\n"  # latest definition
    assert (root / "bin" / "catalyst.pyz").is_file()
    # the analysis process ships with the deployment (BUG-000002)
    assert (root / "ANALYSIS-PLAYBOOK.md").read_text(encoding="utf-8").startswith("# Analysis Playbook")
    assert (root / "analyses" / "analyses.md").is_file()
    assert (root / "analyses" / "templates" / "TEMPLATE-ANALYSIS-v1.md").is_file()
    assert (root / "definitions" / "analysis.md").is_file()
    assert journal_entries(root)[0]["command"] == "catalyst init"
    assert not (root / "development" / "journal.jsonl").exists()  # shards only since 0.50


def test_init_puts_the_criterion_in_the_home_store_and_one_file_in_the_project(tmp_path):
    import project_file

    req = request(tmp_path, at=None, runtime=False)
    before = {p.name for p in req.project.iterdir()}
    init(req)
    assert {p.name for p in req.project.iterdir()} - before == {"catalyst.toml"}
    root = project_file.home_criterion("app")
    dep = load(req.project)
    assert dep.root == root and (root / "version.txt").is_file()
    assert run_checks(dep).errors == []
    with pytest.raises(InitError, match="already exists"):  # one name per machine
        (tmp_path / "other").mkdir()
        init(request(tmp_path / "other", at=None, runtime=False))


def test_init_without_git_works_in_the_home_store(tmp_path):
    req = request(tmp_path, at=None, runtime=False)
    subprocess.run(["rm", "-rf", str(req.project / ".git")], check=True)
    init(req)
    assert run_checks(load(req.project)).errors == []


def test_init_refuses_an_installed_project(tmp_path):
    req = request(tmp_path)
    init(req)
    with pytest.raises(InitError, match="already"):
        init(req)


def test_init_writes_no_agent_files_into_the_project(tmp_path):
    req = request(tmp_path, agent="claude-code")
    steps = init(req)
    assert not (req.project / ".claude").exists()
    assert any("catalyst agent install" in s for s in steps)


def test_compose_places_module_sections():
    coc = compose.insert_at_section_end(
        "## 3. A\n\nkernel three\n\n## 4. B\n\nkernel four\n", 3, "### From module m\n\nmodule three"
    )
    assert coc.index("kernel three") < coc.index("module three") < coc.index("## 4. B")
    assert (
        compose.sign_meta_ids("see rr-META-009 and rr-META-000009-Ab3xR9pQ", "Zz9zZz9z")
        == "see rr-META-000009-Zz9zZz9z and rr-META-000009-Ab3xR9pQ"
    )


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
    ror_t.write_text(
        ror_t.read_text(encoding="utf-8") + "\n## 99. `rr-META-099` A new kernel rule\n\nNew.\n", encoding="utf-8"
    )
    ror = root / "rules" / "Rules-of-Rules.md"
    ror.write_text(
        ror.read_text(encoding="utf-8").replace(
            "The rules a person or an agent", "The rules (local note) a person or an agent", 1
        ),
        encoding="utf-8",
    )
    params = deployed_params(root, "example-process")
    results = recompose(root, params, (base_kernel, req.module), (new_kernel, req.module))
    text = ror.read_text(encoding="utf-8")
    assert "(local note)" in text and f"rr-META-000099-{params.userid}" in text
    assert {r.path: r.conflicts for r in results}["rules/Rules-of-Rules.md"] == 0


def test_failed_install_rolls_back_and_can_be_rerun(tmp_path, monkeypatch):
    import catalyst.init as ci

    req = request(tmp_path)
    before = (req.project / ".gitignore").exists()

    def boom(*a, **k):
        raise RuntimeError("disk full")

    real_git = ci._git
    monkeypatch.setattr(ci, "_git", boom)
    with pytest.raises(InitError, match="rolled back"):
        init(req)
    assert not list(req.project.glob("*.catalyst"))
    assert not (req.project / ".criterion").exists() and not (req.project / ".criterion").is_symlink()
    assert not req.at.exists()
    assert (req.project / ".gitignore").exists() == before
    monkeypatch.setattr(ci, "_git", real_git)  # not undo(): that would drop the tests' static identity too
    init(req)  # re-run succeeds
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
    rule_t = (root / "rules" / "templates" / "TEMPLATE-RULE-v1.md").read_text(encoding="utf-8")
    assert "{{RULES_DIR}}" not in rule_t and "Copy this file" not in rule_t


def test_composition_parameters_are_saved_and_read_back(tmp_path):
    from catalyst.compose import deployed_params

    req = request(tmp_path, rule_docs=[("z-rules.md", "z"), ("a-rules.md", "a")])
    init(req)
    p = deployed_params(load(req.project).root, "example-process")
    assert p.rule_docs == ["z-rules.md", "a-rules.md"] and p.test_locations == "`tests/`"


def test_a_release_kernel_sets_the_deployed_version(tmp_path):
    import shutil

    release = tmp_path / "release-kernel"
    shutil.copytree(KERNEL, release)
    (release / "manifest.json").write_text('{"version": "9.9.9"}', encoding="utf-8")
    init(request(tmp_path, kernel=release))
    assert json.loads((tmp_path / "app" / "app.catalyst").read_text(encoding="utf-8"))["kernel_version"] == "9.9.9"


def test_recompose_skips_frozen_documents(tmp_path):
    from catalyst.compose import deployed_params, recompose

    req = request(tmp_path)
    init(req)
    root = load(req.project).root
    (root / ".frozen").write_text("CODE-OF-CONDUCT.md\n", encoding="utf-8")
    results = {
        r.path: r
        for r in recompose(root, deployed_params(root, "example-process"), (KERNEL, req.module), (KERNEL, req.module))
    }
    assert results["CODE-OF-CONDUCT.md"].frozen


def test_single_template_named_like_its_folder_is_the_item_template(tmp_path):
    req = request(tmp_path)
    mod = req.module
    (mod / "templates" / "items.template.md").write_text(
        "# `ITEM-NNNNNN` — item named like its folder\n", encoding="utf-8"
    )
    y = mod / "module.yaml"
    y.write_text(
        y.read_text(encoding="utf-8").replace("templates/item.template.md", "templates/items.template.md"),
        encoding="utf-8",
    )
    init(req)
    root = load(req.project).root
    assert "named like its folder" in (root / "items" / "templates" / "TEMPLATE-ITEM-v1.md").read_text(encoding="utf-8")
    assert (root / "items" / "items.md").read_text(encoding="utf-8").startswith("# Items index")


def test_init_after_a_first_commit_sets_the_baseline_there(tmp_path):
    req = request(tmp_path)
    (req.project / "main.py").write_text("print('hi')\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(req.project), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(req.project), "-c", "user.name=a", "-c", "user.email=a@a", "commit", "-qm", "skeleton"],
        check=True,
    )
    head = subprocess.check_output(
        ["git", "-C", str(req.project), "rev-parse", "HEAD"], text=True, encoding="utf-8"
    ).strip()
    init(req)
    assert json.loads((req.project / "app.catalyst").read_text(encoding="utf-8"))["journal_since"] == head


# --- install order, --at, rollback, grounding (BOOTSTRAP §2, INV-6) -------------
def _ledger(where: Path) -> Path:
    return write(where / ".ledger" / "install.todo.md", "- [ ] install\n")


def test_a_ledger_only_in_project_criterion_is_adopted_and_moved_to_the_working_copy(tmp_path):
    req = request(tmp_path)
    _ledger(req.project / ".criterion")
    init(req)
    assert (req.project / ".criterion").is_symlink()
    assert (req.at / ".ledger" / "install.todo.md").read_text(encoding="utf-8") == "- [ ] install\n"
    assert run_checks(load(req.project)).errors == []


def test_a_ledger_only_in_project_criterion_moves_into_the_home_store(tmp_path):
    import project_file

    req = request(tmp_path, at=None, runtime=False)
    _ledger(req.project / ".criterion")
    init(req)
    home = project_file.home_criterion("app")
    assert (home / ".ledger" / "install.todo.md").is_file() and (home / "CODE-OF-CONDUCT.md").is_file()
    assert not (req.project / ".criterion").exists()


def test_a_ledger_only_target_is_adopted(tmp_path):
    req = request(tmp_path)
    _ledger(req.at)
    init(req)
    assert (req.at / ".ledger" / "install.todo.md").is_file() and (req.at / "CODE-OF-CONDUCT.md").is_file()


def test_at_names_the_working_copy_or_its_parent(tmp_path):
    """`--at <dir>/.criterion` is the working copy; any other `--at` is the
    directory that holds it (INV-6: the working copy is always `.criterion`)."""
    agent_space = tmp_path / "agent-space"
    write(agent_space / "memory" / "MEMORY.md", "notes\n")
    req = request(tmp_path, at=agent_space)
    init(req)
    assert (agent_space / ".criterion" / "CODE-OF-CONDUCT.md").is_file()
    assert (agent_space / "memory" / "MEMORY.md").read_text(encoding="utf-8") == "notes\n"
    assert Path(__import__("os").path.realpath(req.project / ".criterion")) == (agent_space / ".criterion").resolve()


def test_a_non_empty_target_is_refused_untouched(tmp_path):
    req = request(tmp_path)
    write(req.at / "stray.md", "x\n")
    with pytest.raises(InitError, match="not empty"):
        init(req)
    assert sorted(p.name for p in req.at.iterdir()) == ["stray.md"]
    assert not (req.project / ".criterion").exists()


def test_an_in_project_criterion_with_more_than_a_ledger_is_refused(tmp_path):
    req = request(tmp_path)
    _ledger(req.project / ".criterion")
    write(req.project / ".criterion" / "other.md", "x\n")
    with pytest.raises(InitError, match="already exists"):
        init(req)


def test_rollback_leaves_an_existing_empty_target_empty(tmp_path, monkeypatch):
    import catalyst.init as ci

    req = request(tmp_path)
    req.at.mkdir(parents=True)
    real_git = ci._git
    monkeypatch.setattr(ci, "_git", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk full")))
    with pytest.raises(InitError, match="rolled back"):
        init(req)
    assert req.at.is_dir() and list(req.at.iterdir()) == []
    monkeypatch.setattr(ci, "_git", real_git)
    init(req)
    assert run_checks(load(req.project)).errors == []


def test_rollback_puts_an_adopted_ledger_back(tmp_path, monkeypatch):
    import catalyst.init as ci

    req = request(tmp_path)
    _ledger(req.project / ".criterion")
    monkeypatch.setattr(ci, "_git", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk full")))
    with pytest.raises(InitError, match="rolled back"):
        init(req)
    assert not (req.project / ".criterion").is_symlink()
    assert (req.project / ".criterion" / ".ledger" / "install.todo.md").read_text(encoding="utf-8") == "- [ ] install\n"
    assert not req.at.exists()


def test_init_deploys_the_invariants_and_the_session_start_hook_prints_them(tmp_path, capsys):
    from catalyst.__main__ import main

    req = request(tmp_path)
    write(req.module / "INVARIANTS.module.md", "# Module invariants\n\nM-1.\n")
    init(req)
    root = load(req.project).root
    assert (root / "INVARIANTS.md").read_text(encoding="utf-8") == (KERNEL / "INVARIANTS.md").read_text(
        encoding="utf-8"
    )
    assert (root / "INVARIANTS.module.md").read_text(encoding="utf-8").startswith("# Module invariants")
    capsys.readouterr()
    assert main(["--project", str(req.project), "hook", "start"]) == 0
    out = capsys.readouterr().out
    report, _, rest = out.partition("\n# ")  # the open report, then the invariants
    assert report.startswith("catalyst: app — criterion ")
    assert ("# " + rest).startswith((KERNEL / "INVARIANTS.md").read_text(encoding="utf-8").splitlines()[0])
    assert "M-1." in rest
    assert run_checks(load(req.project)).errors == []


def test_session_start_hook_is_silent_outside_a_deployment(tmp_path, capsys):
    from catalyst.__main__ import main

    assert main(["--project", str(tmp_path), "hook", "start"]) == 0


def test_init_announces_its_writes_into_the_product_repository(tmp_path):
    req = request(tmp_path)
    steps = init(req)
    assert any("refs/catalyst/journal" in s and "product repository" in s for s in steps)
    ref = subprocess.run(
        ["git", "-C", str(req.project), "rev-parse", "--verify", "-q", "refs/catalyst/journal"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert ref.returncode == 0


def test_iam_template_catalogs_are_named_after_the_singular_type(tmp_path):
    req = request(tmp_path)
    init(req)
    root = load(req.project).root
    assert (root / "IAM" / "users" / "templates" / "templates-user.md").is_file()
    assert (root / "IAM" / "roles" / "templates" / "templates-role.md").is_file()


def _cli_init(tmp: Path, *extra: str) -> tuple[int, Path]:
    from catalyst.__main__ import main

    project = tmp / "app"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    subprocess.run(["git", "-C", str(project), "config", "user.name", "Grace Hopper"], check=True)
    code = main(
        [
            "--project",
            str(project),
            "init",
            "--name",
            "app",
            "--kernel",
            str(KERNEL),
            "--rule-doc",
            "business-rules:br",
            "--at",
            str(tmp / "agent" / ".criterion"),
            *extra,
        ]
    )
    return code, project


def test_init_takes_the_user_from_git_config_and_records_the_agent(tmp_path):
    mod = example_module(tmp_path)
    code, project = _cli_init(
        tmp_path, "--module", "example-process", "--module-dir", str(mod), "--agent", "claude-code"
    )
    assert code == 0
    # people are catalyst-users' (design 29): the installer is the tests' static pointer's one person
    identity = json.loads((project / ".criterion" / "IAM" / "identity.json").read_text(encoding="utf-8"))
    assert [(p["name"], p["username"]) for p in identity["people"]] == [("Grace Hopper", "Grace Hopper")]
    assert not (project / ".criterion" / "IAM" / "users" / "users.json").exists()
    assert not (project / ".claude").exists()


def test_init_without_a_module_lists_the_ones_it_finds_and_installs_nothing(tmp_path, capsys):
    write(tmp_path / "catalyst-example-process" / "module.yaml", MODULE_YAML)
    code, project = _cli_init(tmp_path)
    err = capsys.readouterr().err
    assert code == 2 and "pass --module" in err and "example-process" in err
    assert not (project / "app.catalyst").exists() and not (tmp_path / "agent").exists()


@pytest.mark.skipif(
    __import__("shutil").which("uv") is None and __import__("sys").version_info < (3, 11),
    reason="a runtime needs uv or Python 3.11+",
)
def test_init_fills_the_criterions_runtime(tmp_path):
    import project_file
    from catalyst import runtime as rt

    init(request(tmp_path, at=None))
    venv = project_file.home_criterion("app") / ".venv"
    assert rt.installed_version(venv) and rt.venv_python(venv).exists()
    assert "/.venv" in (venv.parent / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_init_signs_as_whoever_the_provider_verifies_unless_a_name_is_given(tmp_path, monkeypatch):
    """BUG-000040: with a provider, `init` asks for no particular person unless `--user`/`--git-username` named one,
    so a git user.name that differs from the provider's name never refuses the install; the deployment then records
    the verified identity, not the git name."""
    from catalyst import init as init_mod
    from catalyst.identity.provider import Whoami

    asked = []
    issuer = "https://id.example.com/realms/catalyst"

    def verify(doc, as_user=None, transport=None):
        asked.append(as_user)
        return Whoami(issuer=issuer, subject="sub-ada", username="ada", name="Ada Lovelace")

    monkeypatch.setattr(init_mod.provider, "verify", verify)
    identity = {"provider": "keycloak", "issuer": issuer, "client": "catalyst-cli", "catalyst_client": "catalyst"}
    req = request(tmp_path, user="Someone Else", git_username="someone", identity=identity, runtime=False, at=None)
    init(req)
    assert asked == [None]
    pointer = (req.project / "catalyst.toml").read_text(encoding="utf-8")
    assert 'created_by = "Ada Lovelace"' in pointer and "Someone Else" not in pointer
    (tmp_path / "b").mkdir()
    other = request(tmp_path / "b", name="app2", identity=identity, runtime=False, at=None, verify_as="ada")
    init(other)
    assert asked == [None, "ada"]


def test_init_with_its_runtime_installs_the_catalyst_command(tmp_path, monkeypatch):
    """BUG-000041: filling the criterion's runtime, `init` also installs the launcher, as `catalyst runtime install`
    does, so a fresh machine has a `catalyst` command (and the commit-msg hook its CLI) right after `init`."""
    import project_file
    from catalyst import runtime as rt

    monkeypatch.setattr(rt, "install_into", lambda c, v, pyz: (c / ".venv", True))
    steps = init(request(tmp_path, at=None, runtime=True))
    launcher = project_file.home() / "bin" / "catalyst"
    assert launcher.is_file() and any("installed the catalyst command" in s for s in steps)


def test_init_labels_the_runtime_as_open_does(tmp_path, monkeypatch):
    """BUG-000055: `init` fills the criterion's runtime under the vendored CLI's own label (`X.Y.Z+g<sha>` for a
    development build), as `catalyst open` does, so one build never fills two runtimes."""
    from catalyst import runtime as rt

    labels = []
    monkeypatch.setattr(rt, "pyz_version", lambda pyz: "9.9.9+gabcdef123456")
    monkeypatch.setattr(rt, "install_into", lambda c, v, pyz: (labels.append(v), (c / ".venv", True))[1])
    steps = init(request(tmp_path, at=None, runtime=True))
    assert labels == ["9.9.9+gabcdef123456"] and any("catalyst 9.9.9+gabcdef123456" in s for s in steps)


def test_init_journals_before_its_first_commit_with_new_files_new(tmp_path):
    """BUG-000056 (rr-META-000012): the install entry is in the criterion's first commit, nothing is left
    untracked, and each installed file is recorded as new (no `before`), not as before == after."""
    import subprocess

    import project_file
    from catalyst_fixtures import journal_entries

    req = request(tmp_path, at=None, runtime=False)
    init(req)
    root = project_file.home_criterion(req.name)
    status = subprocess.run(["git", "-C", str(root), "status", "--porcelain"], capture_output=True, text=True)
    assert status.stdout.strip() == ""
    [entry] = [e for e in journal_entries(root) if e["command"] == "catalyst init"]
    assert entry["files"] and all(f["before"] is None and f["after"] for f in entry["files"])
