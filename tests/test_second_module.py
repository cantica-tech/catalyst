"""The second module as a fixture (roadmap R7, owner decision B1, revised
2026-10-22): the published knowledge-base module, checked out beside
the kernel, installed into a scratch project and driven through every verb a
person would use. It shows the kernel needs nothing of the
software-engineering module.

The module is found at `$CATALYST_KB_MODULE`, else as the sibling checkout
`../catalyst-knowledge-base`; the test is skipped without it, except
where `CATALYST_REQUIRE_FIXTURES` is set (CI checks the module out at a
release tag).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from catalyst.__main__ import main

ROOT = Path(__file__).resolve().parent.parent
KERNEL = ROOT / "framework" / "kernel"
MODULE = Path(os.environ.get("CATALYST_KB_MODULE") or ROOT.parent / "catalyst-knowledge-base")

if os.environ.get("CATALYST_REQUIRE_FIXTURES") and not (MODULE / "module.yaml").is_file():
    raise RuntimeError(f"CATALYST_REQUIRE_FIXTURES is set but there is no knowledge-base module at {MODULE}")

pytestmark = [
    pytest.mark.skipif(not (MODULE / "module.yaml").is_file(), reason=f"no knowledge-base module at {MODULE}"),
    pytest.mark.skipif(sys.version_info < (3, 11), reason="catalyst.toml needs Python 3.11+"),
]


@pytest.fixture
def project(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    app = tmp_path / "app"
    subprocess.run(["git", "init", "-q", str(app)], check=True)
    assert (
        main(
            [
                "--project",
                str(app),
                "init",
                "--kernel",
                str(KERNEL),
                "--name",
                "app",
                "--module",
                "knowledge-base",
                "--module-dir",
                str(MODULE),
                "--git-username",
                "ada",
                "--rule-doc",
                "knowledge-rules.md:kr",
                "--agent",
                "claude-code",
                "--no-runtime",
            ]
        )
        == 0
    ), capsys.readouterr().err
    monkeypatch.chdir(app)
    capsys.readouterr()
    return app


def _cli(capsys, *argv: str) -> str:
    capsys.readouterr()
    code = main(list(argv))
    out = capsys.readouterr()
    assert code == 0, out.err + out.out
    return out.out


def _id(capsys, *argv: str) -> str:
    return json.loads(_cli(capsys, *argv, "--json"))["id"]


def _criterion(capsys) -> Path:
    where = _cli(capsys, "where")
    return Path(re.search(r"criterion\s+(\S+)", where).group(1))  # type: ignore[union-attr]


def _write_section(capsys, path: Path, heading: str, text: str, artifact: str) -> None:
    """A person writes a section, then journals it (L1)."""
    body = path.read_text(encoding="utf-8")
    start = body.index(f"## {heading}")
    end = body.find("\n## ", start + 3)
    path.write_text(body[:start] + f"## {heading}\n\n{text}\n" + (body[end:] if end >= 0 else ""), encoding="utf-8")
    _cli(
        capsys,
        "journal",
        "append",
        "--command",
        "/create",
        "--action",
        "update",
        "--artifact",
        artifact,
        "--file",
        str(path),
        "--intent",
        f"the {heading.lower()} written down",
    )


def test_the_knowledge_base_module_runs_end_to_end(project, capsys):
    root = _criterion(capsys)
    rules = root / "rules"
    # a domain and a rule, the way a person adds them: files, then the journal
    domains = rules / "domains" / "domains.md"
    domains.write_text(
        domains.read_text(encoding="utf-8")
        + "| [`KNOW`](kr-KNOW-shared-knowledge.md) | rules/knowledge-rules.md | 2026-10-22 |\n",
        encoding="utf-8",
    )
    (rules / "domains" / "kr-KNOW-shared-knowledge.md").write_text(
        "# `KNOW` — Shared knowledge\n\n## Scope\n\nWhat the team must be able to find.\n", encoding="utf-8"
    )
    _cli(
        capsys,
        "journal",
        "append",
        "--command",
        "chore",
        "--action",
        "create",
        "--artifact",
        "domain KNOW",
        "--file",
        str(domains),
        "--file",
        str(rules / "domains" / "kr-KNOW-shared-knowledge.md"),
        "--intent",
        "the shared-knowledge domain the first rule belongs to",
        "--tier",
        "chore",
    )
    rule = _cli(capsys, "id", "next-rule", "kr", "KNOW", "--as", "ada").strip()
    doc, index = rules / "knowledge-rules.md", rules / "rules.md"
    doc.write_text(
        doc.read_text(encoding="utf-8").replace(
            "## Contents\n\n*(no rules yet)*",
            f"## Contents\n\n### `{rule}` Support answers from the product's documentation\n\n**Status:** ✅\n\n"
            "Support finds every answer in one knowledge base.",
        ),
        encoding="utf-8",
    )
    index.write_text(
        index.read_text(encoding="utf-8").replace(
            "## Rule IDs\n\n*(none yet)*",
            f"## Rule IDs\n\n- `{rule}` — Support answers from the product's documentation",
        ),
        encoding="utf-8",
    )
    _cli(
        capsys,
        "journal",
        "append",
        "--command",
        "chore",
        "--action",
        "create",
        "--artifact",
        rule,
        "--file",
        str(doc),
        "--file",
        str(index),
        "--intent",
        "the first rule the knowledge base serves",
        "--tier",
        "chore",
    )

    kb = _id(
        capsys,
        "new",
        "KB",
        "--title",
        "Support knowledge base",
        "--field",
        f"Serves={rule}",
        "--field",
        "Kind=Project",
        "--field",
        "Classification=Internal",
        "--field",
        "Default classification=Confidential",
        "--field",
        "Hosted embedding up to=Internal",
        "--field",
        "Repository=git@example.com:support/kb.git",
        "--field",
        "Freshness=30 days",
        "--field",
        "Curator=ada",
        "--intent",
        "support needs one place to find the product's answers",
    )
    source = _id(
        capsys,
        "new",
        "KSOURCE",
        "--title",
        "The support wiki",
        "--field",
        f"Knowledge base={kb}",
        "--field",
        "Location=https://wiki.example.com/support",
        "--field",
        "Classification=Internal",
        "--field",
        "Next check=2026-01-01",
        "--intent",
        "the wiki holds most of the answers",
    )
    assert source in json.loads(_cli(capsys, "view", kb, "--json"))["Sources"]  # the back-reference

    # each state's guard holds until its section is written
    kb_file = root / json.loads(_cli(capsys, "view", kb, "--json"))["file"]
    assert main(["status", "set", kb, "Established", "--intent", "the repository is laid out"]) == 1
    assert "`## Structure` is not written" in capsys.readouterr().err
    _write_section(capsys, kb_file, "Structure", "docs/ by product area; pointers/ mirrors it.", kb)
    _cli(capsys, "status", "set", kb, "Established", "--intent", "the repository is laid out")
    assert main(["status", "set", kb, "Active", "--intent", "its policy is decided"]) == 1
    _write_section(capsys, kb_file, "Policy", "Internal; new and unmarked documents Confidential.", kb)
    _write_section(capsys, kb_file, "Maintenance", "Pointers checked monthly; rebuilt at each release.", kb)
    _cli(capsys, "status", "set", kb, "Active", "--intent", "its policy and its maintenance are decided")

    build = _id(
        capsys,
        "new",
        "KBUILD",
        "--title",
        "Support knowledge base 1.0.0",
        "--field",
        f"Knowledge base={kb}",
        "--field",
        "Version=1.0.0",
        "--field",
        "Ceiling=Internal",
        "--field",
        "Embedding model=nomic-embed-text-v1.5, local",
        "--field",
        "Classification=Internal",
        "--intent",
        "the first vector database support's assistant ingests",
    )
    assert build in json.loads(_cli(capsys, "view", kb, "--json"))["Builds"]
    _cli(capsys, "status", "set", build, "Built", "--intent", "the vectors are written")
    assert main(["status", "set", build, "Published", "--intent", "support's assistant may use it"]) == 1
    build_file = root / json.loads(_cli(capsys, "view", build, "--json"))["file"]
    _write_section(capsys, build_file, "Verification", "Checksums match; nothing above Internal in it.", build)
    _cli(capsys, "status", "set", build, "Published", "--intent", "support's assistant may use it")

    # a source past its next check waits in the inbox (kernel 0.104.0, `due`)
    overdue = [i["id"] for i in json.loads(_cli(capsys, "inbox", "--json"))["items"] if i["kind"] == "overdue"]
    assert overdue == [source]

    # what a person reads: the list, the graph, the audit, and a clean check
    assert {r["id"] for r in json.loads(_cli(capsys, "list", "KB", "--json"))} == {kb}
    graph = json.loads(_cli(capsys, "graph", "--json"))
    assert {"KB", "KSOURCE", "KBUILD"} <= set(graph["types"])
    assert json.loads(_cli(capsys, "audit", "--json"))["rules"]
    entries = [
        json.loads(line)
        for f in (root / "development" / "journal").rglob("*.jsonl")
        for line in f.read_text(encoding="utf-8").splitlines()
        if line.startswith("{")
    ]
    tiers = {e.get("artifact"): e.get("tier") for e in entries if e.get("action") == "create"}
    assert tiers[kb] == "kb" and tiers[build] == "build"  # the module's tiers, inferred
    report = _cli(capsys, "check")
    assert "0 error(s)" in report and "legacy:" not in report  # catalyst.toml, the criterion in catalyst's home
    assert "software-engineering" not in json.dumps(graph)  # nothing of the other module


# --- modules compose (INV-30, fw-STRUCTURE-000018, REQ-000088) ------------------------------
def _install(capsys, source: Path) -> None:
    _cli(capsys, "module", "install", str(source), "--kernel", str(KERNEL), "--intent", "a module beside the other")


def _both_checked(capsys, order: list[str]) -> None:
    """Both modules loaded, in install order, and the deployment passes `check` with both in scope."""
    report = _cli(capsys, "check")
    assert "0 error(s)" in report and f"modules {', '.join(order)}" in report, report
    assert [
        m["id"] for m in json.loads((_criterion(capsys) / "modules" / "modules.json").read_text())["modules"]
    ] == order


def test_another_module_is_installed_beside_the_knowledge_base_module(project, capsys, tmp_path):
    from test_catalyst_several_modules import notes_module

    _install(capsys, notes_module(tmp_path / "modules"))
    _both_checked(capsys, ["knowledge-base", "notes-process"])
    assert {"KB", "KSOURCE", "KBUILD", "NOTE"} <= set(json.loads(_cli(capsys, "graph", "--json"))["types"])


def test_the_knowledge_base_module_is_installed_beside_another_module(tmp_path, monkeypatch, capsys):
    from test_catalyst_several_modules import notes_module

    monkeypatch.setenv("CATALYST_HOME", str(tmp_path / "home"))
    app = tmp_path / "app"
    subprocess.run(["git", "init", "-q", str(app)], check=True)
    init = ["--project", str(app), "init", "--kernel", str(KERNEL), "--name", "app", "--no-module"]
    assert main([*init, "--git-username", "ada", "--agent", "claude-code", "--no-runtime"]) == 0
    monkeypatch.chdir(app)
    _install(capsys, notes_module(tmp_path / "modules"))  # the module that governs the project
    _install(capsys, MODULE)  # then the knowledge bases, built off it
    _both_checked(capsys, ["notes-process", "knowledge-base"])
    assert {"KB", "KSOURCE", "KBUILD", "NOTE"} <= set(json.loads(_cli(capsys, "graph", "--json"))["types"])
