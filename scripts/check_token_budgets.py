#!/usr/bin/env python3
"""Token-budget regression check: measure what an agent reads now and compare it,
item by item, with the committed baseline (docs/BUDGETS-BASELINE.json).

An item fails when it grew by more than TOLERANCE over its baseline. Shrinking is
always fine. An item with no baseline entry fails too: new agent-facing text needs
a deliberate budget. Moving the baseline is a reviewed change:
`python3 scripts/measure_tokens.py --write-baseline`.

Items the environment cannot measure (command specs need a deployment's
.criterion) are skipped, never failed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_tokens import ROOT, measure_all  # noqa: E402

BASELINE = ROOT / "docs" / "BUDGETS-BASELINE.json"
TOLERANCE = 0.05   # 5% growth per item
SLACK = 25         # tokens: absorbs one-line edits in small files


def check() -> list[str]:
    baseline = {m["name"]: m for m in json.loads(BASELINE.read_text("utf-8"))["measurements"]}
    problems = []
    for item in measure_all():
        base = baseline.get(item.name)
        if base is None:
            problems.append(f"{item.name}: {item.tokens:,} tokens, no baseline entry")
        elif item.tokens > base["tokens"] * (1 + TOLERANCE) + SLACK:
            problems.append(f"{item.name}: {base['tokens']:,} -> {item.tokens:,} tokens "
                            f"(+{item.tokens - base['tokens']:,}, over {TOLERANCE:.0%})")
    return problems


def main() -> int:
    problems = check()
    for p in problems:
        print(f"token budget exceeded: {p}", file=sys.stderr)
    if problems:
        print("If the growth is intended: python3 scripts/measure_tokens.py --write-baseline",
              file=sys.stderr)
        return 1
    print("token budgets: within baseline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
