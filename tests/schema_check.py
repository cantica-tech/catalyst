"""A checker for the part of JSON Schema the files in `spec/` use: `type`,
`required`, `properties`, `additionalProperties`, `items`, `enum`, `const`,
`minimum`, `anyOf` and `$ref` to `#/$defs/<name>`. The tests check every
read verb's output with it (no third-party validator is a dependency)."""

from __future__ import annotations

import json
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1] / "spec"
TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def load(name: str) -> dict:
    return json.loads((SPEC / f"{name}.schema.json").read_text(encoding="utf-8"))


def _is(value, kind: str) -> bool:
    if kind in ("integer", "number") and isinstance(value, bool):
        return False
    return isinstance(value, TYPES[kind])


def problems(value, schema: dict, root: dict | None = None, at: str = "$") -> list[str]:
    """What in `value` does not hold to `schema` ([]: it holds)."""
    root = root or schema
    if "$ref" in schema:
        return problems(value, root["$defs"][schema["$ref"].rsplit("/", 1)[1]], root, at)
    if "anyOf" in schema:  # checked with the schema's other keywords, as JSON Schema does
        tries = [problems(value, option, root, at) for option in schema["anyOf"]]
        if not any(not t for t in tries):
            return [f"{at}: matches none of anyOf ({min(tries, key=len)[0]})"]
        if len(schema) == 1:
            return []
        schema = {k: v for k, v in schema.items() if k != "anyOf"}
    kinds = schema.get("type")
    if kinds and not any(_is(value, k) for k in ([kinds] if isinstance(kinds, str) else kinds)):
        return [f"{at}: {type(value).__name__} is not {kinds}"]
    if "const" in schema and value != schema["const"]:
        return [f"{at}: not {schema['const']!r}"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{at}: {value!r} not in {schema['enum']}"]
    found = []
    if isinstance(value, dict):
        found += [f"{at}: no {k}" for k in schema.get("required", []) if k not in value]
        known = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for k, v in value.items():
            if k in known:
                found += problems(v, known[k], root, f"{at}.{k}")
            elif extra is False:
                found.append(f"{at}: unknown {k}")
            elif isinstance(extra, dict):
                found += problems(v, extra, root, f"{at}.{k}")
    if isinstance(value, list) and "items" in schema:
        for i, v in enumerate(value):
            found += problems(v, schema["items"], root, f"{at}[{i}]")
    if _is(value, "number") and "minimum" in schema and value < schema["minimum"]:
        found.append(f"{at}: below {schema['minimum']}")
    return found
