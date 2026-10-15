"""Agent-facing text may not grow past its committed token baseline (R1.1)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_token_budgets as budgets


def test_token_budgets_within_baseline():
    problems = budgets.check()
    assert not problems, "\n".join(problems)


def test_growth_beyond_tolerance_fails(monkeypatch):
    real = budgets.measure_all()
    grown = [b._replace(tokens=b.tokens * 2 + 100) if i == 0 else b for i, b in enumerate(real)]
    monkeypatch.setattr(budgets, "measure_all", lambda: grown)
    assert any(real[0].name in p for p in budgets.check())


def test_unbaselined_item_fails(monkeypatch):
    real = budgets.measure_all()
    extra = real[0]._replace(name="new-doc.md")
    monkeypatch.setattr(budgets, "measure_all", lambda: [*real, extra])
    assert any("new-doc.md" in p for p in budgets.check())


def test_command_specs_are_measured_in_any_checkout():
    """Specs come from the kernel's composed catalogue, not a deployment: an
    empty measurement would let every command spec grow unchecked."""
    from measure_tokens import measure_command_specs

    names = {b.name for b in measure_command_specs()}
    assert {"spec: /share", "spec: /check-rules", "spec: --general"} <= names and len(names) >= 15


SAMPLE = Path(__file__).resolve().parents[1] / "framework" / "modules" / "sample-process"
SIBLING = Path(__file__).resolve().parents[2] / "catalyst-software-engineering"


@pytest.mark.parametrize("module", [SAMPLE, SIBLING], ids=["sample-process", "software-engineering"])
def test_no_command_of_a_fresh_install_needs_more_than_1000_words(tmp_path, module, capsys):
    """CLI.md: catalyst holds a deployment to 1,000 words per command
    (`catalyst spec --budget 1000`), checked on a fresh install of each
    module the repository can reach (the software-engineering module when
    its checkout is beside catalyst)."""
    from catalyst.__main__ import main
    from catalyst.init import init
    from module_loader import load_module
    from test_catalyst_init import request

    if not (module / "module.yaml").is_file():
        pytest.skip(f"{module.name} is not checked out beside catalyst")
    manifest = load_module(module_dir=module)
    assert manifest is not None
    req = request(tmp_path, module_id=manifest.id, module=module, rule_docs=[])
    init(req)
    capsys.readouterr()
    assert main(["--project", str(req.project), "spec", "--budget", "1000"]) == 0, capsys.readouterr().out
