"""Version ranges: a module's `kernel_version` (`>=0.52.0`, `>=0.52,<1.0`,
`==0.54.0`) checked against a kernel version (fw-STRUCTURE-000016), the way
a client checks its own requirement. A version reads as its leading numbers
(`0.54.0+g6548800` is 0.54.0); a missing part is 0."""

from __future__ import annotations

import re

OPS = (">=", "<=", "==", "!=", ">", "<")


class VersionError(ValueError):
    pass


def parse(version: str) -> tuple[int, ...]:
    m = re.match(r"^\s*v?(\d+(?:\.\d+)*)", str(version))
    if not m:
        raise VersionError(f"'{version}' is not a version")
    return tuple(int(p) for p in m.group(1).split("."))


def _cmp(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    width = max(len(a), len(b))
    a, b = a + (0,) * (width - len(a)), b + (0,) * (width - len(b))
    return (a > b) - (a < b)


def satisfies(version: str, spec: str | None) -> bool:
    """Whether `version` is inside `spec`, a comma-separated list of clauses;
    no spec is no constraint."""
    if not spec or not str(spec).strip():
        return True
    v = parse(version)
    for raw in str(spec).split(","):
        clause = raw.strip()
        if not clause:
            continue
        op = next((o for o in OPS if clause.startswith(o)), "==")
        c = _cmp(v, parse(clause[len(op) :] if clause.startswith(op) else clause))
        ok = {">=": c >= 0, "<=": c <= 0, "==": c == 0, "!=": c != 0, ">": c > 0, "<": c < 0}[op]
        if not ok:
            return False
    return True
