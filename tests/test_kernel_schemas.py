"""The kernel's file schemas hold for real modules (R4.4 phase 3): the
module manifest schema, from which MODULE-SPECIFICATION.md's table is
generated, accepts every module catalyst ships or runs in CI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import schema_check
from module_loader import parse_simple_yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "framework" / "kernel" / "schemas"
MODULES = [
    ROOT / "framework" / "modules" / "sample-process",
    ROOT.parent / "catalyst-software-engineering",
    ROOT.parent / "catalyst-cantica-knowledge-base",
]


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("module", MODULES, ids=[m.name for m in MODULES])
def test_every_module_manifest_holds_to_the_schema(module):
    if not (module / "module.yaml").is_file():
        pytest.skip(f"{module.name} is not checked out beside catalyst")
    manifest = parse_simple_yaml((module / "module.yaml").read_text(encoding="utf-8"))
    assert schema_check.problems(manifest, _schema("module-manifest")) == []


def test_a_manifest_needs_its_types_one_way_or_the_other():
    base = {"id": "x", "name": "X", "version": "1.0.0", "description": "d", "grounding_type": "rule"}
    assert schema_check.problems(base, _schema("module-manifest"))  # neither entity_types nor entities
    assert schema_check.problems({**base, "entities": {}}, _schema("module-manifest")) == []
    assert schema_check.problems({**base, "unknown": 1, "entities": {}}, _schema("module-manifest"))
