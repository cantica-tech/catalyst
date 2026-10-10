#!/usr/bin/env python3
"""Token budget measurement for catalyst.

Measures token usage (approximate as bytes/4) for:
- BOOTSTRAP + INVARIANTS (grounding docs; of INVARIANTS.md, the laws a
  session loads — its brief, up to the marker)
- Every spec <cmd> output
- Install path (BOOTSTRAP up to fresh checkout state)
- Each prose command file

Establishes baselines and CI gates to prevent regression.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent


def loaded_text(path: Path) -> str:
    """What an agent reads of a file: the laws file's brief, else all of it."""
    text = path.read_text("utf-8")
    if path.name.startswith("INVARIANTS"):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from catalyst.laws import brief

        return brief(text)
    return text


class TokenBudget(NamedTuple):
    """Token budget entry: doc/command, byte count, token estimate (bytes/4)."""

    name: str
    bytes: int
    tokens: int
    category: str


def count_tokens_approx(text: str) -> tuple[int, int]:
    """Count bytes and estimate tokens as bytes/4 (conservative estimate)."""
    byte_count = len(text.encode("utf-8"))
    token_est = max(1, byte_count // 4)
    return byte_count, token_est


def measure_bootstrap_invariants() -> list[TokenBudget]:
    """Measure BOOTSTRAP.md + kernel INVARIANTS.md + any module INVARIANTS."""
    results = []

    # Kernel INVARIANTS
    inv_file = ROOT / "framework/kernel/INVARIANTS.md"
    if inv_file.exists():
        text = loaded_text(inv_file)
        bytes_count, tokens = count_tokens_approx(text)
        results.append(
            TokenBudget(name="framework/kernel/INVARIANTS.md", bytes=bytes_count, tokens=tokens, category="grounding")
        )

    # BOOTSTRAP (shared by all agents)
    bootstrap_file = ROOT / "BOOTSTRAP.md"
    if bootstrap_file.exists():
        text = bootstrap_file.read_text("utf-8")
        bytes_count, tokens = count_tokens_approx(text)
        results.append(TokenBudget(name="BOOTSTRAP.md", bytes=bytes_count, tokens=tokens, category="grounding"))

    return results


def measure_command_specs() -> list[TokenBudget]:
    """Measure `catalyst spec` for every kernel command, and `spec --general`,
    from the kernel's own command catalogue composed in memory — the same in
    any checkout and in CI, with or without a deployment. A module's commands
    are its own repository's budget."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from catalyst import compose, spec

    params = compose.Params(module_id="", userid="Ab12Cd34")
    s = spec.parse(compose.code_of_conduct(ROOT / "framework" / "kernel", None, params))
    results = []
    for name in sorted(s.bullets):
        _, tokens = count_tokens_approx(spec.spec_text(s, name))
        results.append(
            TokenBudget(
                name=f"spec: /{name}",
                bytes=len(spec.spec_text(s, name).encode()),
                tokens=tokens,
                category="command-spec",
            )
        )
    general = "\n\n".join(s.general)
    results.append(
        TokenBudget(
            name="spec: --general",
            bytes=len(general.encode()),
            tokens=count_tokens_approx(general)[1],
            category="command-spec",
        )
    )
    return results


def measure_command_files() -> list[TokenBudget]:
    """Measure token cost of each deployed .claude/commands/*.md file."""
    results = []

    commands_dir = ROOT / ".claude/commands"
    if not commands_dir.exists():
        return results

    for cmd_file in sorted(commands_dir.glob("*.md")):
        text = cmd_file.read_text("utf-8")
        bytes_count, tokens = count_tokens_approx(text)
        results.append(
            TokenBudget(
                name=f"command-file: {cmd_file.name}", bytes=bytes_count, tokens=tokens, category="command-file"
            )
        )

    return results


def measure_install_path() -> list[TokenBudget]:
    """Measure token cost of BOOTSTRAP + init checklist + docs read during install.

    This is approximate: actual install path varies by module and setup.
    Conservative estimate: BOOTSTRAP + INVARIANTS + INSTANTIATION-GUIDE + CHECKLIST.
    """
    results = []

    docs = [
        ("BOOTSTRAP.md", ROOT / "BOOTSTRAP.md", "install"),
        ("framework/kernel/INVARIANTS.md", ROOT / "framework/kernel/INVARIANTS.md", "install"),
        ("framework/kernel/INSTANTIATION-GUIDE.md", ROOT / "framework/kernel/INSTANTIATION-GUIDE.md", "install"),
        (
            "framework/kernel/INSTANTIATION-CHECKLIST.md",
            ROOT / "framework/kernel/INSTANTIATION-CHECKLIST.md",
            "install",
        ),
    ]

    for name, path, category in docs:
        if path.exists():
            text = loaded_text(path)
            bytes_count, tokens = count_tokens_approx(text)
            results.append(TokenBudget(name=name, bytes=bytes_count, tokens=tokens, category=category))

    return results


def format_report(budgets: list[TokenBudget]) -> str:
    """Format measurements as a human-readable report."""
    lines = [
        "# Token Budget Report",
        "",
        "| Category | Name | Bytes | Tokens |",
        "|---|---|---:|---:|",
    ]

    by_category = {}
    for b in budgets:
        if b.category not in by_category:
            by_category[b.category] = []
        by_category[b.category].append(b)

    total_bytes = 0
    total_tokens = 0

    for category in sorted(by_category.keys()):
        for b in sorted(by_category[category], key=lambda x: x.tokens, reverse=True):
            lines.append(f"| {category} | {b.name} | {b.bytes:,} | {b.tokens:,} |")
            total_bytes += b.bytes
            total_tokens += b.tokens

    lines.append("")
    lines.append(f"**Total:** {total_bytes:,} bytes ≈ {total_tokens:,} tokens")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("**Note:** Token estimates use bytes÷4 (conservative). Actual LLM token counts")
    lines.append("may vary by model (GPT-3.5, GPT-4, Claude, etc.). Baseline established 2026-10-07.")

    return "\n".join(lines)


def save_baselines(budgets: list[TokenBudget], baseline_file: Path) -> None:
    """Save measurements to a baseline file for regression testing."""
    baseline_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": "1.0",
        "timestamp": __import__("datetime")
        .datetime.now(__import__("datetime").timezone.utc)
        .isoformat(timespec="seconds"),
        "measurements": [
            {
                "name": b.name,
                "bytes": b.bytes,
                "tokens": b.tokens,
                "category": b.category,
            }
            for b in budgets
        ],
    }

    baseline_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def measure_all() -> list[TokenBudget]:
    """Every measurement this repository can take (command specs need a deployment)."""
    return [
        *measure_bootstrap_invariants(),
        *measure_command_specs(),
        *measure_command_files(),
        *measure_install_path(),
    ]


def main() -> int:
    """Print the report; `--write-baseline` also replaces docs/BUDGETS-BASELINE.json."""
    all_budgets: list[TokenBudget] = []

    print("Measuring token budgets...", file=sys.stderr)

    # Measure grounding docs
    print("  Grounding docs (BOOTSTRAP, INVARIANTS)...", file=sys.stderr)
    all_budgets.extend(measure_bootstrap_invariants())

    # Measure command specs
    print("  Command specs...", file=sys.stderr)
    all_budgets.extend(measure_command_specs())

    # Measure command files
    print("  Command files...", file=sys.stderr)
    all_budgets.extend(measure_command_files())

    # Measure install path
    print("  Install path docs...", file=sys.stderr)
    all_budgets.extend(measure_install_path())

    # Generate report
    report = format_report(all_budgets)
    print(report)

    # The baseline moves only on purpose: a deliberate, reviewed change of budget.
    if "--write-baseline" in sys.argv[1:]:
        baseline_file = ROOT / "docs/BUDGETS-BASELINE.json"
        save_baselines(all_budgets, baseline_file)
        print(f"\nBaseline saved to {baseline_file.relative_to(ROOT)}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
