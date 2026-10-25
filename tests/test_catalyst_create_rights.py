"""Who may create which type (design 31 §4.1, `fw-STRUCTURE-000020`): an admin any; anyone else a module's type the
module leaves open to contributors, with `cmd:create` or `create:<TYPE>`."""

from __future__ import annotations

import pytest

from catalyst.deployment import load
from catalyst.permissions import creation_refusal
from catalyst_fixtures import make_project


def person(*grants: str, roles: tuple[str, ...] = ()) -> dict:
    return {"name": "Bob", "roles": list(roles), "grants": list(grants)}


@pytest.fixture
def dep(tmp_path):
    return load(make_project(tmp_path))


def test_an_admin_creates_any_type(dep):
    assert creation_refusal(dep, person("cmd:*"), "ITEM") is None
    assert creation_refusal(dep, person("cmd:*"), "WORKFLOW") is None
    assert creation_refusal(dep, person(roles=("Admin",)), "WORKFLOW") is None


def test_create_grants_a_modules_types(dep):
    assert creation_refusal(dep, person("cmd:create"), "ITEM") is None
    assert creation_refusal(dep, person("cmd:create"), "SUB") is None


def test_a_typed_grant_allows_that_type_only(dep):
    assert creation_refusal(dep, person("create:ITEM"), "ITEM") is None
    assert "no grant allows it" in (creation_refusal(dep, person("create:ITEM"), "SUB") or "")


def test_no_grant_no_creation(dep):
    assert "`cmd:create`, or `create:ITEM`" in (creation_refusal(dep, person("cmd:status"), "ITEM") or "")


def test_the_kernels_types_are_an_admins(dep):
    assert "the kernel's" in (creation_refusal(dep, person("cmd:create", "create:WORKFLOW"), "WORKFLOW") or "")


def test_a_module_may_keep_a_type_to_admins(dep):
    module = next(m for m in dep.installed() if "SUB" in m.entity_types)
    module.entity_types["SUB"].contributors_create = False
    assert "contributors_create: false" in (creation_refusal(dep, person("cmd:create"), "SUB") or "")
    assert creation_refusal(dep, person("cmd:*"), "SUB") is None


def test_module_yaml_keeps_a_type_to_admins():
    from module_loader import v3_entity

    assert v3_entity("NOTE", {"name": "Note"}).contributors_create is True
    assert v3_entity("NOTE", {"name": "Note", "contributors_create": False}).contributors_create is False
