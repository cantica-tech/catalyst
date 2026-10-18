"""Installed modules (roadmap R4.9, N1; REQ-000027): `init` and `sync` seed
a module the same way and record it in `modules/modules.json`; `module
list|verify` and `check` read that record."""

from __future__ import annotations

import json
import shutil
import subprocess

from catalyst import modules, sync
from catalyst.__main__ import main
from catalyst.check import run as run_checks
from catalyst.deployment import load
from catalyst_fixtures import journal_entries, write
from test_catalyst_sync import _deployment, _release


def _record(project):
    return json.loads((project / ".criterion" / modules.RECORD).read_text(encoding="utf-8"))["modules"]


def test_init_seeds_what_a_release_ships_and_records_it(tmp_path):
    project, _ = _deployment(tmp_path)
    root = project / ".criterion"
    tree = root / "modules" / "example-process"
    assert (tree / "manifest.json").is_file()  # as a release carries it
    (entry,) = _record(project)
    assert entry["id"] == "example-process" and entry["version"]
    assert entry["sha256"] == modules.tree_hash(tree)
    assert entry["source"] == "example-process" and entry["commit"] is None  # a plain directory: its name
    assert str(tmp_path) not in json.dumps(entry)  # never a path on this machine
    assert [f.state for f in modules.verify(root)] == ["ok"]
    assert not [e for e in run_checks(load(project)).errors if e.startswith("module:")]


def test_init_and_sync_seed_the_same_tree(tmp_path):
    project, deployed = _deployment(tmp_path)
    dep = load(project)
    src = sync.Sources(dep, _release(tmp_path, deployed), tmp_path / "example-process", None, None)
    kinds = {a.kind for a in sync.plan(dep, src, None).actions}
    src.close()
    assert "module" not in kinds and "record" not in kinds


def test_a_module_checked_out_with_other_line_endings_is_the_same_module(tmp_path):
    """A checkout that converts line endings (git on Windows by default)
    must not make `sync` see, and try to journal, a change in every file."""
    project, deployed = _deployment(tmp_path)
    converted = tmp_path / "converted" / "example-process"
    shutil.copytree(tmp_path / "example-process", converted)
    for f in converted.rglob("*"):
        if f.is_file():
            f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    dep = load(project)
    src = sync.Sources(dep, _release(tmp_path, deployed), converted, None, None)
    assert not {a.kind for a in sync.plan(dep, src, None).actions} & {"module", "record"}
    src.close()


def test_the_hash_does_not_depend_on_line_endings(tmp_path):
    project, _ = _deployment(tmp_path)
    tree = project / ".criterion" / "modules" / "example-process"
    before = modules.tree_hash(tree)
    yaml = tree / "module.yaml"
    yaml.write_bytes(yaml.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    assert modules.tree_hash(tree) == before
    yaml.write_bytes(yaml.read_bytes() + b"# edited\r\n")
    assert modules.tree_hash(tree) != before


def test_a_module_file_changed_by_hand_fails_verify_and_check(tmp_path, capsys):
    project, _ = _deployment(tmp_path)
    assert main(["--project", str(project), "module", "verify"]) == 0
    assert "matches its record" in capsys.readouterr().out
    yaml = project / ".criterion" / "modules" / "example-process" / "module.yaml"
    write(yaml, yaml.read_text(encoding="utf-8") + "# edited by hand\n")
    (finding,) = modules.verify(project / ".criterion")
    assert finding.state == "changed" and finding.actual != finding.sha256
    assert main(["--project", str(project), "module", "verify", "example-process"]) == 1
    assert "differs from its record" in capsys.readouterr().out
    assert any(e.startswith("module: example-process differs") for e in run_checks(load(project)).errors)
    assert main(["--project", str(project), "module", "verify", "nope"]) == 1


def test_a_deployment_from_before_the_record_is_recorded_by_its_next_sync(tmp_path, capsys):
    project, deployed = _deployment(tmp_path)
    root = project / ".criterion"
    (root / modules.RECORD).unlink()
    assert [f.state for f in modules.verify(root)] == ["unrecorded"]
    assert main(["--project", str(project), "module", "verify"]) == 0  # not an error
    assert "not recorded" in capsys.readouterr().out
    assert not [e for e in run_checks(load(project)).errors if e.startswith("module:")]

    dep = load(project)
    src = sync.Sources(dep, _release(tmp_path, deployed), None, None, None)
    assert ("record", "add") in {(a.kind, a.change) for a in sync.plan(dep, src, None).actions}
    sync.apply(dep, src, None, "ada", [])
    src.close()
    (entry,) = _record(project)
    assert entry["source"] is None and entry["sha256"] == modules.tree_hash(root / "modules" / "example-process")
    assert any(f["path"].endswith(modules.RECORD) for f in journal_entries(root)[-1]["files"])
    dep = load(project)
    src = sync.Sources(dep, tmp_path / f"kernel-{deployed}", None, None, None)
    assert sync.plan(dep, src, None).actions == []
    src.close()


def test_a_synced_module_is_recorded_with_its_source(tmp_path):
    project, deployed = _deployment(tmp_path)
    root = project / ".criterion"
    module = tmp_path / "next" / "example-process"
    shutil.copytree(tmp_path / "example-process", module)
    write(module / "guidance.md", "# Guidance\n")
    git = ["git", "-C", str(module), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q", str(module)], check=True)
    subprocess.run(
        [*git, "remote", "add", "origin", "https://user:secret@example.test/acme/example-process.git"], check=True
    )
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "a release"], check=True)
    head = subprocess.run([*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()

    dep = load(project)
    src = sync.Sources(dep, _release(tmp_path, deployed), module, None, None)
    kinds = {a.kind for a in sync.plan(dep, src, None).actions}
    assert {"module", "record"} <= kinds
    sync.apply(dep, src, None, "ada", [])
    src.close()
    (entry,) = _record(project)
    assert entry["source"] == "https://example.test/acme/example-process.git"  # credentials never recorded
    assert entry["commit"] == head
    assert (root / "modules" / "example-process" / "guidance.md").is_file()
    assert not (root / "modules" / "example-process" / ".git").exists()
    assert [f.state for f in modules.verify(root)] == ["ok"]


def test_module_list_prints_the_record(tmp_path, capsys):
    project, _ = _deployment(tmp_path)
    assert main(["--project", str(project), "module", "list"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("example-process ") and "sha256 " in out
    assert main(["--project", str(project), "module", "list", "--json"]) == 0
    (row,) = json.loads(capsys.readouterr().out)
    assert row["id"] == "example-process" and row["state"] == "ok"


def test_a_module_in_a_larger_repository_is_recorded_with_its_folder(tmp_path):
    repo = tmp_path / "mono"
    module = repo / "modules" / "example-process"
    shutil.copytree(_deployment(tmp_path)[0] / ".criterion" / "modules" / "example-process", module)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", "git@example.test:acme/mono.git"], check=True)
    assert modules.source_of(module)[0] == "git@example.test:acme/mono.git#modules/example-process"
    assert modules.source_of(tmp_path / "x.zip") == ("x.zip", None)
    assert modules.source_of(None) == (None, None)


def _recorded_at(project, url: str) -> None:
    path = project / ".criterion" / modules.RECORD
    data = json.loads(path.read_text(encoding="utf-8"))
    data["modules"][0]["source"] = url
    path.write_text(json.dumps(data), encoding="utf-8")


def _ls_remote(monkeypatch, tags: list[str], code: int = 0) -> list[list[str]]:
    calls: list[list[str]] = []
    real = subprocess.run

    def fake(cmd, *a, **kw):
        if cmd[:2] == ["git", "ls-remote"]:
            calls.append(cmd)
            out = "".join(f"{i:040x}\trefs/tags/{t}\n" for i, t in enumerate(tags))
            return subprocess.CompletedProcess(cmd, code, out, "" if code == 0 else "denied")
        return real(cmd, *a, **kw)

    monkeypatch.setattr(modules.subprocess, "run", fake)
    return calls


def test_module_available_lists_the_release_tags_newest_first(tmp_path, monkeypatch, capsys):
    """REQ-000060: the releases at the recorded repository, which are newer."""
    project, _ = _deployment(tmp_path)
    _recorded_at(project, "https://user:secret@example.test/acme/example-process.git")
    calls = _ls_remote(monkeypatch, ["0.1.0", "v0.3.0", "0.2.0", "nightly", "0.10.0"])
    found = modules.available(project / ".criterion", "example-process")
    assert calls[0][-1] == "https://user:secret@example.test/acme/example-process.git"
    assert found["source"] == "https://example.test/acme/example-process.git"  # credentials never shown
    assert [r["tag"] for r in found["releases"]] == ["0.10.0", "v0.3.0", "0.2.0", "0.1.0"]
    import schema_check

    assert schema_check.problems(found, schema_check.load("module-releases")) == []
    by = {r["version"]: r for r in found["releases"]}
    assert by["0.2.0"]["installed"] and by["0.3.0"]["newer"] and not by["0.1.0"]["newer"]
    assert main(["--project", str(project), "module", "available", "example-process", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == found


def test_module_available_refuses_without_a_repository_or_a_reachable_one(tmp_path, monkeypatch):
    import pytest

    project, _ = _deployment(tmp_path)
    root = project / ".criterion"
    with pytest.raises(modules.ModuleError, match="no repository to list"):
        modules.available(root, "example-process")  # installed from a directory
    with pytest.raises(modules.ModuleError, match="no module 'other'"):
        modules.available(root, "other")
    _recorded_at(project, "https://example.test/acme/example-process.git")
    _ls_remote(monkeypatch, [], code=128)
    with pytest.raises(modules.ModuleError, match="cannot reach"):
        modules.available(root, "example-process")
    with pytest.raises(modules.ModuleError, match="not a release"):
        _ls_remote(monkeypatch, ["0.2.0"])
        modules.upgrade_plan(load(project), "example-process", "9.9.9")


def test_the_local_server_answers_the_modules_routes(tmp_path, monkeypatch):
    import threading

    import pytest

    from catalyst import serve

    project, _ = _deployment(tmp_path)
    _recorded_at(project, "https://example.test/acme/example-process.git")
    _ls_remote(monkeypatch, ["0.2.0", "0.3.0"])
    monkeypatch.setattr(modules, "upgrade_plan", lambda dep, mid, tag: {"id": mid, "to": tag, "actions": []})
    httpd, token = serve.make_local(project, 0, poll=0.1)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        client = serve.Client(f"http://127.0.0.1:{httpd.server_address[1]}", token)
        (row,) = client.call("GET", "/modules")["modules"]
        assert row["id"] == "example-process"
        assert [r["tag"] for r in client.call("GET", "/modules/example-process/available")["releases"]] == [
            "0.3.0",
            "0.2.0",
        ]
        assert client.call("GET", "/modules/example-process/plan?to=0.3.0") == {
            "id": "example-process",
            "to": "0.3.0",
            "actions": [],
        }
        with pytest.raises(serve.ServeError) as err:
            client.call("GET", "/modules/example-process/plan")
        assert err.value.status == 400
        with pytest.raises(serve.ServeError) as err:
            client.call("GET", "/modules/other/available")
        assert err.value.status == 404
    finally:
        httpd.shutdown()
        httpd.server_close()
