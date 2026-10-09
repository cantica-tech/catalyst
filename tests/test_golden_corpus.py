"""Golden corpus (roadmap R1.4): the capture works on any deployment, and every
corpus captured locally is sound. Corpora hold private governance data, so they
are captured locally (scripts/capture_golden_corpus.py) and never committed;
the checks on real corpora skip when none is captured."""

import json
import sys
import tarfile
from pathlib import Path

import pytest

from catalyst_fixtures import make_project, write

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import capture_golden_corpus as corpus

CAPTURED = sorted(corpus.FIXTURES.glob("*-golden-corpus.tar.gz"))


def _names(archive: Path) -> list[str]:
    with tarfile.open(archive) as tar:
        return tar.getnames()


def test_capture_packs_the_pointer_and_working_copy_without_private_history(tmp_path):
    project = make_project(tmp_path / "p", git=True)
    write(project / ".criterion" / ".ledger" / "install.md", "ledger\n")
    write(project / ".criterion" / "._resource", "macOS\n")
    archive, summary = corpus.capture(project, "t", tmp_path / "out")
    names = _names(archive)
    assert any(n.endswith(".catalyst") and "/" not in n for n in names)
    assert ".criterion/development/journal.jsonl" in names
    assert not [n for n in names if "/.git" in n or ".ledger" in n or "._" in n]
    meta = json.loads(summary.read_text(encoding="utf-8"))
    assert meta["files"] == len(names) and meta["users"] >= 1 and meta["working_copy_head"]


def test_capture_is_deterministic(tmp_path):
    project = make_project(tmp_path / "p")
    first, _ = corpus.capture(project, "a", tmp_path / "out")
    second, _ = corpus.capture(project, "b", tmp_path / "out")
    assert first.read_bytes() == second.read_bytes()


@pytest.mark.skipif(not CAPTURED, reason="no golden corpus captured locally")
@pytest.mark.parametrize("archive", CAPTURED, ids=lambda p: p.name.split("-golden")[0])
def test_a_captured_corpus_is_sound(archive):
    names = _names(archive)
    meta = json.loads(archive.with_name(archive.name.replace(".tar.gz", ".json")).read_text(encoding="utf-8"))
    assert not [n for n in names if "/.git/" in n or n.endswith("/.git") or ".ledger/" in n]
    for required in ("development/journal.jsonl", "version.txt", "IAM/users/users.json"):
        assert f".criterion/{required}" in names, required
    assert meta["files"] == len(names) and meta["module"] and meta["kernel_version"]
