"""The laws (roadmap R4.1): the session loads the laws, `catalyst why`
explains every law, invariant and meta-rule."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from catalyst import laws
from catalyst.__main__ import main
from catalyst_fixtures import USERID, make_project, write

KERNEL = Path(__file__).resolve().parent.parent / "framework" / "kernel"


def test_the_kernel_has_ten_laws_and_every_invariant_resolves():
    text = (KERNEL / "INVARIANTS.md").read_text(encoding="utf-8")
    brief = laws.brief(text)
    assert re.findall(r"^- \*\*(L\d+) — ", brief, re.M) == [f"L{n}" for n in range(1, 11)]
    assert "INV-17 —" not in brief and len(brief) < 4000  # the session loads the laws only
    cited = {law for row in text.splitlines() if row.startswith("| INV-") for law in re.findall(r"\bL\d+\b", row)}
    assert cited <= {f"L{n}" for n in range(1, 11)}
    for n in sorted({int(i) for i in re.findall(r"^- \*\*INV-(\d+)\b", text, re.M)}):
        explained = laws.why(KERNEL, f"INV-{n}")
        assert explained, n
        assert "law:" in explained or "owned by the active module" in explained, n


def test_why_explains_laws_invariants_meta_rules_and_ids(tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path, git=True)
    root = project / ".criterion"
    shutil.copyfile(KERNEL / "INVARIANTS.md", root / "INVARIANTS.md")
    write(
        root / "INVARIANTS.module.md",
        "# Module\n\n## The law\n\n- **XM-L1 — Be modular.** Always.\n\n"
        f"{laws.MARKER}\n\n| Invariant | Law | Enforced by |\n|---|---|---|\n| INV-9 module rule | XM-L1 | `check` |\n\n"
        "- **INV-9 — Module rule.** The module's own text.\n",
    )
    write(
        root / "rules" / "Rules-of-Rules.md",
        "# Rules\n\n## 12. `rr-META-012` The journal\n\nReplayable.\n\n## 13. Next\n",
    )
    monkeypatch.chdir(project)
    assert main(["why", "L3"]) == 0 and "Assent before push" in capsys.readouterr().out
    assert main(["why", "inv-4"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("INV-4 assent before push — law: L3") and "exit `3`" in out
    assert main(["why", "INV-9"]) == 0
    out = capsys.readouterr().out
    assert "law: XM-L1" in out and "The module's own text." in out and "owned by the active module" not in out
    assert main(["why", "XM-L1"]) == 0 and "INV-9 module rule" in capsys.readouterr().out
    assert main(["why", "rr-META-012"]) == 0
    assert capsys.readouterr().out.strip() == "## 12. `rr-META-012` The journal\n\nReplayable."
    assert main(["why", f"ITEM-000001-{USERID}"]) == 0 and "ITEM-000001" in capsys.readouterr().out
    assert main(["why", "L42"]) == 1


def test_a_deployment_from_before_the_laws_loads_its_invariants_whole(tmp_path):
    write(tmp_path / "INVARIANTS.md", "# Catalyst Invariants\n\n- **INV-1 — Old.** Text.\n")
    assert laws.session_brief(tmp_path) == "# Catalyst Invariants\n\n- **INV-1 — Old.** Text.\n"
