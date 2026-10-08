#!/usr/bin/env python3
"""Prose feature freeze (roadmap R1.6, ADR-017): the kernel's rule surface may not
change until the R2 verbs exist.

The surface is what an agent must read and obey as prose: the invariants, the
meta-rules, the §4 slash commands, the entity types and the kernel's top-level
documents. Each is listed in the committed snapshot docs/FROZEN-SURFACE.json.
Any addition or removal fails: new behaviour goes into the CLI (code, tested),
not into more prose. Lifting an item out of the freeze is a reviewed change
backed by an ADR: `python3 scripts/check_frozen_surface.py --write`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KERNEL = ROOT / "framework" / "kernel"
SNAPSHOT = ROOT / "docs" / "FROZEN-SURFACE.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_command_parity import extract_section4_commands  # noqa: E402


def surface(kernel: Path = KERNEL) -> dict[str, list[str]]:
    read = lambda name: (kernel / name).read_text(encoding="utf-8")
    return {
        "invariants": sorted(set(re.findall(r"^- \*\*(INV-\d+)\b", read("INVARIANTS.md"), re.M)),
                             key=lambda i: int(i[4:])),
        "meta-rules": sorted(set(re.findall(r"^## \d+\. `(rr-[A-Z]+-\d+)`",
                                            read("rules-of-rules.template.md"), re.M))),
        "commands": sorted(extract_section4_commands(read("rules-of-development.template.md")) or ()),
        "entity-types": sorted({p.stem for p in (kernel / "entities").glob("*.yaml")}
                               | {p.name for p in (kernel / "definitions").iterdir() if p.is_dir()}),
        "documents": sorted(p.name for p in kernel.glob("*.md")),
    }


def check(kernel: Path = KERNEL, snapshot: Path = SNAPSHOT) -> list[str]:
    frozen = json.loads(snapshot.read_text(encoding="utf-8"))
    problems = []
    for kind, now in surface(kernel).items():
        was = set(frozen.get(kind, ()))
        problems += [f"{kind}: {x} added" for x in sorted(set(now) - was)]
        problems += [f"{kind}: {x} removed" for x in sorted(was - set(now))]
    return problems


def main(argv: list[str]) -> int:
    if "--write" in argv:
        SNAPSHOT.write_text(json.dumps(surface(), indent=2) + "\n", encoding="utf-8")
        print(f"frozen surface written: {SNAPSHOT.relative_to(ROOT).as_posix()}")
        return 0
    problems = check()
    for p in problems:
        print(f"prose freeze: {p}", file=sys.stderr)
    if problems:
        print("The kernel's prose surface is frozen until R2 (ADR-017): put new behaviour in the CLI.\n"
              "If an ADR lifts the freeze for this item: python3 scripts/check_frozen_surface.py --write",
              file=sys.stderr)
        return 1
    print("prose freeze: surface unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
