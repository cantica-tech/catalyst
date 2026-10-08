"""The kernel's prose surface is frozen until R2 (roadmap R1.6, ADR-017)."""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_frozen_surface as freeze  # noqa: E402


def test_surface_matches_the_frozen_snapshot():
    problems = freeze.check()
    assert not problems, "\n".join(problems)


def test_the_surface_is_read_from_the_kernel():
    s = freeze.surface()
    assert "INV-1" in s["invariants"] and "rr-META-001" in s["meta-rules"]
    assert s["commands"] and "INVARIANTS.md" in s["documents"] and "workflow" in s["entity-types"]


def test_an_added_invariant_or_document_fails(tmp_path):
    kernel = tmp_path / "kernel"
    shutil.copytree(freeze.KERNEL, kernel)
    with (kernel / "INVARIANTS.md").open("a", encoding="utf-8") as f:
        f.write("\n- **INV-999 — Something new.** More prose.\n")
    (kernel / "NEW-GUIDE.md").write_text("# New\n", encoding="utf-8")
    problems = freeze.check(kernel)
    assert "invariants: INV-999 added" in problems and "documents: NEW-GUIDE.md added" in problems


def test_a_removed_item_fails(tmp_path):
    snapshot = tmp_path / "frozen.json"
    s = freeze.surface()
    s["commands"].append("retired-command")
    snapshot.write_text(json.dumps(s), encoding="utf-8")
    assert freeze.check(snapshot=snapshot) == ["commands: retired-command removed"]
