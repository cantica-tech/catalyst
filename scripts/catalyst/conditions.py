"""Conditions on an entity's field values (workflow governance, W1), one
language for every place a move may depend on one: a guard's `holds`, a
gate's `when`, a governing workflow's `When` column.

A condition is one line of text, `<Field> <test>`:

- `<Field> is <value>`, `<Field> is not <value>`
- `<Field> in <value>, <value>, …`, `<Field> not in <value>, …`
- `<Field> at least <value>`, `<Field> at most <value>`: ordered by the
  field's enum values (`Public` < `Internal` < …), else as numbers, else as
  dates (`YYYY-MM-DD`)
- `<Field> is set`, `<Field> is empty`

Values may be quoted or in backticks. An empty or `*(none yet)*` cell is
empty. A field the type does not declare, or a value outside its enum, is
refused when the condition is checked (`problems`), never guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from catalyst.corpus import Artifact, is_empty, norm_field

# longest first: "is not" before "is", "not in" before "in"
TESTS = ("at least", "at most", "not in", "is not", "is set", "is empty", "in", "is")
_SPLIT = re.compile(
    r"^(?P<field>.+?)\s+(?P<test>at least|at most|not in|is not|is set|is empty|in|is)(?:\s+(?P<value>.*))?$"
)


class ConditionError(Exception):
    pass


@dataclass(frozen=True)
class Condition:
    field: str
    test: str
    values: tuple[str, ...] = ()

    def __str__(self) -> str:
        if self.test in ("is set", "is empty"):
            return f"{self.field} {self.test}"
        return f"{self.field} {self.test} {', '.join(self.values)}"


def _clean(value: str) -> str:
    return value.strip().strip("`").strip("\"'").strip()


def parse(text: str) -> Condition:
    """The condition `text` states; a ConditionError when it states none."""
    m = _SPLIT.match(" ".join(str(text).split()))
    if not m:
        raise ConditionError(
            f"`{text}` is not a condition (`<Field> is|is not|in|not in|at least|at most <value>`, "
            "`<Field> is set|is empty`)"
        )
    field, test, value = _clean(m.group("field")), m.group("test"), m.group("value") or ""
    if test in ("is set", "is empty"):
        if value.strip():
            raise ConditionError(f"`{text}`: `{test}` takes no value")
        return Condition(field, test)
    values = tuple(_clean(v) for v in (value.split(",") if test in ("in", "not in") else [value]))
    if not all(values):
        raise ConditionError(f"`{text}`: `{test}` needs a value")
    return Condition(field, test, values)


def _field(etd, name: str):
    return next((f for f in etd.fields if norm_field(f.name) == norm_field(name)), None)


def problems(cond: Condition, etd) -> list[str]:
    """What is wrong with `cond` for entities of `etd`, one line each."""
    fd = _field(etd, cond.field)
    if fd is None and cond.field != "Status":
        return [f"`{cond}`: {etd.name} has no field `{cond.field}`"]
    allowed = list(etd.workflow.states) if fd is None else list(fd.allowed_values or [])
    if allowed:
        unknown = [v for v in cond.values if v not in allowed]
        if unknown:
            return [f"`{cond}`: {', '.join(unknown)} is not a value of `{cond.field}` ({', '.join(allowed)})"]
    elif cond.test in ("at least", "at most") and not all(_number(v) is not None or _date(v) for v in cond.values):
        return [f"`{cond}`: `{cond.field}` has no order (an enum, a number or a date)"]
    return []


def _number(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _date(value: str) -> str | None:
    return value if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) else None


def value_of(art: Artifact, name: str) -> str:
    raw = art.get(name) or ""
    return "" if is_empty(raw) else _clean(raw)


def _rank(value: str, order: list[str]):
    if order:
        return order.index(value) if value in order else None
    n = _number(value)
    if n is not None:
        return n
    return _date(value)


def holds(cond: Condition, art: Artifact, etd) -> bool:
    """Whether `art` meets `cond`. A value the comparison cannot place fails it."""
    value = value_of(art, cond.field)
    if cond.test == "is set":
        return bool(value)
    if cond.test == "is empty":
        return not value
    if cond.test == "is":
        return value == cond.values[0]
    if cond.test == "is not":
        return value != cond.values[0]
    if cond.test == "in":
        return value in cond.values
    if cond.test == "not in":
        return value not in cond.values
    fd = _field(etd, cond.field)
    order = list(etd.workflow.states) if cond.field == "Status" else list((fd.allowed_values if fd else None) or [])
    mine, theirs = _rank(value, order), _rank(cond.values[0], order)
    if isinstance(mine, str) and isinstance(theirs, str):  # dates
        return mine >= theirs if cond.test == "at least" else mine <= theirs
    if isinstance(mine, (int, float)) and isinstance(theirs, (int, float)):
        return mine >= theirs if cond.test == "at least" else mine <= theirs
    return False  # a value the comparison cannot place, or a date against a number
