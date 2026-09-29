"""A small, fully valid deployment for the `catalyst` CLI tests, governed by a
fictional `example-process` module with two entity types:

- ITEM (folder items/): grounded on rules via Targets, with a Domain, a
  Status enum and an optional Subs ref-list back-referenced by SUB.Item;
- SUB (folder subs/): grounding inherited through its Item.

Tests start from this known-good baseline and break one thing each.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

USERID = "Ab3xR9pQ"
USER = "Ada Lovelace"

ITEM_SCHEMA = """id_prefix: ITEM
name: Item
plural_name: Items
folder: items
grounding: required
grounding_field: Targets

fields:
  - name: ID
    kind: text
    required: true
  - name: Status
    kind: enum
    required: true
    allowed_values:
      - Open
      - Done
  - name: Targets
    kind: ref-list
    required: true
    target_type: rule
  - name: Domain
    kind: ref
    required: true
    target_type: domain
  - name: Subs
    kind: ref-list
    required: false
    target_type: SUB

workflow:
  initial: Open
  states:
    - Open
    - Done
  closed_states:
    - Done
"""

SUB_SCHEMA = """id_prefix: SUB
name: Sub
plural_name: Subs
folder: subs
grounding: inherited
grounding_field: Item

fields:
  - name: ID
    kind: text
    required: true
  - name: Status
    kind: enum
    required: true
    allowed_values:
      - Open
      - Done
  - name: Item
    kind: ref
    required: true
    target_type: ITEM
    backref: Subs
"""

MODULE_YAML = """id: example-process
name: Example Process Module
version: 0.2.0
description: A fictional module for tests.
grounding_type: rule

entity_types:
  - id: ITEM
    schema: schemas/item.yaml
  - id: SUB
    schema: schemas/sub.yaml
"""


def artifact(art_id: str, title: str, fields: dict[str, str]) -> str:
    rows = "\n".join(f"| **{k}** | {v} |" for k, v in fields.items())
    return f"# `{art_id}` — {title}\n\n| Field | Value |\n|---|---|\n{rows}\n\n## Description\n\nText.\n"


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_project(tmp: Path, git: bool = False) -> Path:
    """Project root at tmp/app with its working copy at tmp/app/.criterion."""
    project = tmp / "app"
    root = project / ".criterion"
    write(project / "app.catalyst", json.dumps(
        {"project_name": "app", "kernel_version": "0.38.0", "module": "example-process"}))
    write(root / "version.txt", "0.38.0\n")
    mod = root / "modules" / "example-process"
    write(mod / "module.yaml", MODULE_YAML)
    write(mod / "schemas" / "item.yaml", ITEM_SCHEMA)
    write(mod / "schemas" / "sub.yaml", SUB_SCHEMA)
    write(root / "IAM" / "users" / "users.json", json.dumps({"users": [
        {"name": USER, "git_username": "ada", "roles": ["Admin"], "active": True,
         "userid": USERID}]}))
    rule = f"br-AUTH-000001-{USERID}"
    write(root / "rules" / "rules.md", f"# Rules index\n\n- `{rule}` — Login flow\n")
    write(root / "rules" / "business" / "br-business-rules.md",
          f"# Business rules\n\n## Contents\n\n### `{rule}` Login flow\n\n"
          "**Status:** ✅\n\n## Linked Artifacts — Quick Index\n")
    write(root / "rules" / "domains" / "domains.md",
          "# Domains index\n\n| Code | Document | Defined |\n|---|---|---|\n"
          "| [`AUTH`](br-AUTH-authentication.md) | rules/business/br-business-rules.md | 2026-01-01 |\n")
    item_id, sub_id = f"ITEM-000001-{USERID}", f"SUB-000001-{USERID}"
    write(root / "items" / "ITEM-000001-first-item.md", artifact(item_id, "First item", {
        "ID": f"`{item_id}`", "Status": "Open", "Targets": f"`{rule}`",
        "Domain": "`AUTH`", "Subs": f"`{sub_id}`", "Signed-off-by": USER}))
    write(root / "items" / "items.md",
          "# Items index\n\n| ID | Title | Status |\n|---|---|---|\n"
          f"| [{item_id}](ITEM-000001-first-item.md) | First item | Open |\n")
    write(root / "subs" / "SUB-000001-first-sub.md", artifact(sub_id, "First sub", {
        "ID": f"`{sub_id}`", "Status": "Open", "Item": f"`{item_id}`", "Signed-off-by": USER}))
    write(root / "subs" / "subs.md",
          "# Subs index\n\n| ID | Title | Item | Status |\n|---|---|---|---|\n"
          f"| [{sub_id}](SUB-000001-first-sub.md) | First sub | {item_id} | Open |\n")
    write(root / "development" / "journal.jsonl", "")
    if git:
        for repo in (project, root):
            git_init(repo)
    return project


def git_init(repo: Path) -> None:
    run = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)
    run("init", "-q")
    run("config", "user.name", USER)
    run("config", "user.email", "ada@example.com")
    if repo.name != ".criterion":
        write(repo / ".gitignore", "/.criterion\n")
    run("add", "-A")
    run("commit", "-q", "-m", "init")
