"""The project file and the criterion's place (roadmap R3.1, stages A–B)."""
import json
import shutil
import sys

import pytest

import project_file as pf
from catalyst.corpus import load_corpus
from catalyst.validate import ERROR, validate
from catalyst.deployment import load
from catalyst_fixtures import make_project

needs_tomllib = pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib is Python 3.11+")


@needs_tomllib
def test_catalyst_toml_round_trips_and_wins_over_a_legacy_pointer(tmp_path):
    data = {"project_name": "app", "kernel_version": "0.48.0", "repoed": False, "targets": ["a", "b"],
            "note": 'quotes " and \\ and é'}
    pf.write(tmp_path / pf.NAME, data)
    (tmp_path / "app.catalyst").write_text(json.dumps({"project_name": "old"}), encoding="utf-8")
    assert pf.find(tmp_path).name == pf.NAME
    assert pf.read_dir(tmp_path) == data
    assert pf.read(tmp_path / pf.NAME)["note"] == 'quotes " and \\ and é'


def test_a_legacy_pointer_is_read_without_tomllib(tmp_path):
    (tmp_path / "app.catalyst").write_text(json.dumps({"project_name": "app"}), encoding="utf-8")
    assert pf.find(tmp_path).name == "app.catalyst"
    assert pf.read_dir(tmp_path) == {"project_name": "app"}
    (tmp_path / "src" / "deep").mkdir(parents=True)
    assert pf.find_up(tmp_path / "src" / "deep") == tmp_path
    assert pf.find_up(tmp_path.parent) is None


def test_the_home_store_wins_over_the_legacy_working_copy(tmp_path, monkeypatch):
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    project = tmp_path / "app"
    (project / ".criterion").mkdir(parents=True)
    (project / "app.catalyst").write_text(json.dumps({"project_name": "app"}), encoding="utf-8")
    assert pf.resolve(project) == project / ".criterion"
    home = tmp_path / "home" / "projects" / "app" / "criterion"
    home.mkdir(parents=True)
    assert pf.resolve(project) == home


def test_a_project_with_its_criterion_in_the_home_store_is_found_from_anywhere_inside(tmp_path, monkeypatch):
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    project = make_project(tmp_path / "w")
    target = pf.home_criterion("app")
    target.parent.mkdir(parents=True)
    shutil.move(str(project / ".criterion"), target)
    assert not (project / ".criterion").exists()
    (project / "src" / "deep").mkdir(parents=True)
    dep = load(project / "src" / "deep")
    assert dep.root == target and dep.project_root == project
    assert [f for f in validate(dep, load_corpus(dep)) if f.level == ERROR] == []


def test_a_missing_criterion_names_where_it_was_expected(tmp_path, monkeypatch):
    from catalyst.deployment import WorkingCopyMissing
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    (tmp_path / "app.catalyst").write_text(json.dumps({"project_name": "app"}), encoding="utf-8")
    with pytest.raises(WorkingCopyMissing, match="projects/app/criterion"):
        load(tmp_path)


def test_where_reports_the_home_store_or_a_legacy_working_copy(tmp_path, capsys):
    from catalyst.__main__ import main
    project = make_project(tmp_path / "w")
    assert main(["--project", str(project), "where", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["kind"] == "legacy" and out["name"] == "app"
    target = pf.home_criterion("app")
    target.parent.mkdir(parents=True)
    shutil.move(str(project / ".criterion"), target)
    assert main(["--project", str(project), "where", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["kind"] == "home"
    shutil.rmtree(target)
    assert main(["--project", str(project), "where"]) == 1
