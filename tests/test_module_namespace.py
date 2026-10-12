"""A module's own meta-rule and invariant namespace (module v3 M4,
REQ-000025, ADR-019), and `catalyst why` on deployed meta-rule IDs
(BUG-000006)."""

from __future__ import annotations

from catalyst import compose
from catalyst.__main__ import main
from catalyst.init import init
from catalyst_fixtures import write
from test_catalyst_init import KERNEL, request
from test_module_v3 import V3

NAMESPACED = V3.replace("format: 3\n", "format: 3\nnamespace: SE\naliases:\n  rr-META-009: rr-SE-001\n")


def _module(base):
    mod = base / "case-process"
    write(mod / "module.yaml", NAMESPACED)
    write(mod / "version.txt", "1.0.0\n")
    write(
        mod / "rules-of-rules.module.md",
        "# Case meta-rules\n\n> preamble\n\n## 1. `rr-SE-001` Cases are handled by people\n\nA person decides.\n",
    )
    write(
        mod / "INVARIANTS.module.md",
        "# Case invariants\n\n## The invariants\n\n- **INV-SE-1 — Every case has an owner.** Always.\n",
    )
    return mod


def test_short_namespaced_ids_are_widened_and_signed():
    text = "see `rr-SE-001`, `rr-META-012` and `rr-XX-001`"
    out = compose.sign_meta_ids(text, "Ab12Cd34", ("SE",))
    assert out == "see `rr-SE-000001-Ab12Cd34`, `rr-META-000012-Ab12Cd34` and `rr-XX-001`"


def test_the_kernel_lends_no_numbers_and_why_resolves_the_namespace(tmp_path, monkeypatch, capsys):
    req = request(tmp_path, module_id="case-process", module=_module(tmp_path / "mods"))
    init(req)
    assert req.at is not None
    handbook = (req.at / "rules" / "Rules-of-Rules.md").read_text(encoding="utf-8")
    assert "owned by the active module" not in handbook
    assert "`rr-SE-000001-" in handbook
    monkeypatch.chdir(req.project)
    capsys.readouterr()
    for key in ("rr-SE-001", "rr-SE-1"):
        assert main(["why", key]) == 0
        assert "Cases are handled by people" in capsys.readouterr().out
    assert main(["why", "rr-META-009"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("rr-META-009 is now rr-SE-001.") and "Cases are handled by people" in out
    signed = __import__("re").search(r"`(rr-SE-000001-[A-Za-z0-9]{8})`", handbook).group(1)
    widened = signed.replace("rr-SE-000001", "rr-META-000009")  # as artifacts deployed before 3.0 cite it
    assert main(["why", widened]) == 0
    assert capsys.readouterr().out.startswith(f"{widened} is now rr-SE-001.")
    from catalyst.corpus import load_corpus
    from catalyst.deployment import load as load_deployment

    corpus = load_corpus(load_deployment(req.project))
    assert corpus.rule_id(widened) == signed and corpus.rule_id("rr-META-000012-" + signed[-8:]) is not None
    assert corpus.rule_id("rr-META-000010-" + signed[-8:]) is None  # not aliased: still dangling
    assert main(["why", "INV-SE-1"]) == 0
    assert "Every case has an owner" in capsys.readouterr().out
    for key in ("rr-META-12", "rr-META-012"):  # BUG-000006: the deployed ID is widened and signed
        assert main(["why", key]) == 0
        assert "The journal is transaction-log-grade" in capsys.readouterr().out
    assert main(["id", "next-rule", "rr", "SE", "--as", "ada"]) == 0
    assert capsys.readouterr().out.strip().startswith("rr-SE-")
    assert main(["check"]) == 0, capsys.readouterr().out


def test_the_kernel_handbook_names_the_four_numbers_retired():
    text = (KERNEL / "rules-of-rules.template.md").read_text(encoding="utf-8")
    assert "owned by the active module" not in text
    assert "Numbers 9, 10, 21 and 22 were lent" in text
