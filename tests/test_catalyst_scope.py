"""What a deployment governs (fw-STRUCTURE-000017): nested deployments and
`.catalystignore`, applied by unrecorded changes, trace, the commit-msg
hook's routing, init and criterion."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from catalyst import criterion as cr
from catalyst import scope
from catalyst import unrecorded
from catalyst.deployment import load
from catalyst.trace import route, trace
from catalyst_fixtures import USER, make_project, write


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout.strip()


@pytest.fixture(autouse=True)
def fresh_cache():
    scope.clear_cache()
    yield
    scope.clear_cache()


@pytest.fixture
def monorepo(tmp_path, monkeypatch):
    """One git repository: a root deployment (app/), a nested one
    (app/inner/app/), an opted-out folder (app/legacy/) and an opted-out
    path list (app/.catalystignore: vendor)."""
    root = make_project(tmp_path)                        # tmp/app
    inner = make_project(root / "inner")                 # tmp/app/inner/app
    write(root / "legacy" / ".catalystignore", "# not governed by catalyst\n")
    write(root / ".catalystignore", "vendor\n")
    for p in ("src/a.py", "legacy/old.py", "vendor/lib.py", "inner/app/src/b.py"):
        write(root / p, f"# {p}\n")
    git(root, "init", "-q")
    git(root, "config", "user.name", USER)
    git(root, "config", "user.email", "ada@example.com")
    write(root / ".gitignore", ".criterion/\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "baseline")
    base = git(root, "rev-parse", "HEAD")
    for project in (root, inner):
        pointer = project / "app.catalyst"
        data = json.loads(pointer.read_text(encoding="utf-8"))
        data["journal_since"] = base
        pointer.write_text(json.dumps(data), encoding="utf-8")
    git(root, "commit", "-q", "-am", "chore: baselines")
    monkeypatch.chdir(root)
    return {"root": root, "inner": inner}


def test_governs_nested_deployments_and_catalystignore(monorepo):
    root, inner = monorepo["root"], monorepo["inner"]
    assert scope.governs(root, "src/a.py")
    assert not scope.governs(root, "inner/app/src/b.py")          # the nested deployment's
    assert scope.governs(inner, "src/b.py")
    assert not scope.governs(root, "legacy/old.py")               # empty .catalystignore
    assert not scope.governs(root, "vendor/lib.py")               # listed in app/.catalystignore
    assert not scope.governs(root, "vendor")
    assert scope.governs(root, "vendored.py")                     # a prefix of a name is not the name
    assert not scope.governs(root, ".criterion/x.md")
    assert not scope.governs(root, "../elsewhere.py")
    assert scope.owner(root, "inner/app/src/b.py") == inner.absolute()
    assert scope.owner(root, "src/a.py") == root.absolute()
    assert scope.owner(root, "legacy/old.py") is None
    assert scope.opted_out(root / "legacy") and scope.opted_out(root / "legacy" / "deep")
    assert scope.opted_out(root / "vendor") and not scope.opted_out(root / "src")


def test_unrecorded_and_trace_see_only_the_deployments_own_files(monorepo):
    root = monorepo["root"]
    for p in ("legacy/old.py", "vendor/lib.py", "inner/app/src/b.py"):
        write(root / p, f"# {p} changed\n")
    git(root, "commit", "-q", "-am", "elsewhere: no ID")             # touches no file root governs
    write(root / "src" / "a.py", "# changed\n")
    git(root, "commit", "-q", "-am", "mine: no ID")
    # the fixture's own pointer edit after the baseline is unrecorded too — correctly
    changed = {p for c in unrecorded.since_baseline(load(root)) for p, _, _ in c.changes}
    assert changed == {"app.catalyst", "src/a.py"}
    checked, failures = trace(root, "HEAD~2..HEAD", None, scoped=True)
    assert checked == 1 and [f.subject for f in failures] == ["mine: no ID"]
    checked, _ = trace(root, "HEAD~2..HEAD", None)                    # unscoped: both
    assert checked == 2
    # the nested deployment sees its own file, not the root's
    inner_changed = {p for c in unrecorded.since_baseline(load(monorepo["inner"])) for p, _, _ in c.changes}
    assert inner_changed == {"app.catalyst", "src/b.py"}


def test_staged_files_are_scoped_too(monorepo):
    root = monorepo["root"]
    write(root / "vendor" / "lib.py", "# staged\n")
    write(root / "inner" / "app" / "src" / "b.py", "# staged\n")
    git(root, "add", "-A")
    assert unrecorded.staged(load(root)) == []


def test_init_refuses_an_opted_out_directory(monorepo, tmp_path):
    from catalyst.init import InitError, InitRequest, init
    target = monorepo["root"] / "legacy"
    kernel = Path(__file__).resolve().parents[1] / "framework" / "kernel"
    req = InitRequest(project=target, kernel=kernel, name="legacy", module_id="example-process",
                      module=tmp_path / "nowhere", user=USER, git_username="ada",
                      rule_docs=[("rules.md", "br")], at=tmp_path / "wc")
    with pytest.raises(InitError, match="opted out"):
        init(req)


def test_check_reports_a_pointer_in_an_opted_out_directory(monorepo):
    from catalyst.check import run as run_checks
    write(monorepo["inner"] / ".catalystignore", "")
    scope.clear_cache()
    assert any(e.startswith("scope:") for e in run_checks(load(monorepo["inner"])).errors)


def test_the_hook_routes_each_staged_file_to_its_deployment(monorepo, tmp_path):
    root, inner = monorepo["root"], monorepo["inner"]
    record = tmp_path / "calls"
    fake_cli = [sys.executable, "-c",
                "import sys; a = sys.argv; p = a[a.index('--project') + 1]; "
                f"open({str(record)!r}, 'a').write(p + '\\n'); "
                "sys.exit(1 if p.endswith('inner/app') else 0)"]
    msg = tmp_path / "MSG"
    msg.write_text("chore: x\n", encoding="utf-8")

    def calls():
        found = record.read_text(encoding="utf-8").splitlines() if record.exists() else []
        record.unlink(missing_ok=True)
        return found

    write(root / "src" / "a.py", "# 1\n")
    git(root, "add", "src/a.py")
    assert route(root, msg, fake_cli) == 0 and calls() == [str(root.absolute())]
    write(root / "inner" / "app" / "src" / "b.py", "# 2\n")
    git(root, "add", "-A")
    assert route(root, msg, fake_cli) == 1                          # the inner one refuses: it fails
    assert sorted(calls()) == sorted([str(root.absolute()), str(inner.absolute())])
    git(root, "reset", "-q")
    write(root / "legacy" / "old.py", "# 3\n")
    git(root, "add", "legacy/old.py")
    assert route(root, msg, fake_cli) == 0
    assert calls() == [str(root.absolute())]                        # nothing owned: the top's deployment


def test_criterion_create_for_a_project_in_a_subfolder(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "always")
    remote = tmp_path / "criterion.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    top = tmp_path / "repo"
    project = make_project(top)                                   # repo/app, inside repo's git
    agent = tmp_path / "agent" / ".criterion"
    agent.parent.mkdir()
    shutil.move(str(project / ".criterion"), str(agent))
    (project / ".criterion").symlink_to(agent)
    git(top, "init", "-q")
    git(top, "config", "user.name", USER)
    git(top, "config", "user.email", "ada@example.com")
    write(project / ".gitignore", "/.criterion\n")
    git(top, "add", "-A")
    git(top, "commit", "-q", "-m", "init")
    monkeypatch.chdir(project)
    cr.create(load(project), str(remote), "criterion", cr.CI_TEMPLATE)
    assert cr.is_submodule(project) and not cr.is_submodule(top)
    gitmodules = (top / ".gitmodules").read_text(encoding="utf-8")
    assert "path = app/.criterion" in gitmodules
    assert ".gitmodules" in git(top, "diff", "--cached", "--name-only").split()


def test_the_installed_hook_routes_real_commits(monorepo):
    """End to end: the vendored CLIs, the installed hook, real `git commit`."""
    import package_release
    from catalyst.trace import install_hook
    root, inner = monorepo["root"], monorepo["inner"]
    cli = package_release.build_cli(Path(__file__).resolve().parents[1], root / ".criterion" / "bin" / "catalyst.pyz")
    (inner / ".criterion" / "bin").mkdir(parents=True, exist_ok=True)
    shutil.copy(cli, inner / ".criterion" / "bin" / "catalyst.pyz")
    hook = install_hook(root)
    assert 'ROUTER = ".criterion/bin/catalyst.pyz"' in hook.read_text(encoding="utf-8")

    def commit(message: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", message],
                              capture_output=True, text=True, encoding="utf-8")

    write(root / "inner" / "app" / "src" / "b.py", "# inner change\n")
    git(root, "add", "-A")
    refused = commit("inner work without an ID")
    assert refused.returncode != 0 and "commit refused" in refused.stderr
    assert commit("ITEM-000001: inner work").returncode == 0      # resolves in the inner deployment
    write(root / "legacy" / "old.py", "# not governed\n")
    git(root, "add", "-A")
    assert commit("chore: legacy only").returncode == 0
