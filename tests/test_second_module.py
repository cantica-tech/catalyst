"""The second module as a fixture (roadmap R7, owner decision B1): the
published risk-management module, checked out beside the kernel, installed
into a scratch project and driven through every verb a person would use. It
shows the kernel needs nothing of the software-engineering module.

The module is found at `$CATALYST_RISK_MODULE`, else as the sibling checkout
`../catalyst-risk-management`; the test is skipped without it, except where
`CATALYST_REQUIRE_FIXTURES` is set (CI checks the module out at a release
tag).
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
MODULE = Path(os.environ.get("CATALYST_RISK_MODULE") or ROOT.parent / "catalyst-risk-management")

if os.environ.get("CATALYST_REQUIRE_FIXTURES") and not (MODULE / "module.yaml").is_file():
    raise RuntimeError(f"CATALYST_REQUIRE_FIXTURES is set but there is no risk-management module at {MODULE}")

pytestmark = [
    pytest.mark.skipif(not (MODULE / "module.yaml").is_file(), reason=f"no risk-management module at {MODULE}"),
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
                "risk-management",
                "--module-dir",
                str(MODULE),
                "--git-username",
                "ada",
                "--rule-doc",
                "controls-rules.md:cr",
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


def test_the_risk_module_runs_end_to_end(project, capsys):
    root = _criterion(capsys)
    rules = root / "rules"
    # a domain and a rule, the way a person adds them: files, then the journal
    domains = rules / "domains" / "domains.md"
    domains.write_text(
        domains.read_text(encoding="utf-8")
        + "| [`ACCESS`](cr-ACCESS-access-control.md) | rules/controls-rules.md | 2026-10-19 |\n",
        encoding="utf-8",
    )
    (rules / "domains" / "cr-ACCESS-access-control.md").write_text(
        "# `ACCESS` — Access control\n\n## Scope\n\nWho may reach what.\n", encoding="utf-8"
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
        "domain ACCESS",
        "--file",
        str(domains),
        "--file",
        str(rules / "domains" / "cr-ACCESS-access-control.md"),
        "--intent",
        "the access-control domain the first rule belongs to",
        "--tier",
        "chore",
    )
    rule = _cli(capsys, "id", "next-rule", "cr", "ACCESS", "--as", "ada").strip()
    doc, index = rules / "controls-rules.md", rules / "rules.md"
    doc.write_text(
        doc.read_text(encoding="utf-8").replace(
            "## Contents\n\n*(no rules yet)*",
            f"## Contents\n\n### `{rule}` Only staff reach the admin console\n\n**Status:** ✅\n\n"
            "The admin console answers staff accounts only.",
        ),
        encoding="utf-8",
    )
    index.write_text(
        index.read_text(encoding="utf-8").replace(
            "## Rule IDs\n\n*(none yet)*", f"## Rule IDs\n\n- `{rule}` — Only staff reach the admin console"
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
        "the first rule the risks are grounded in",
        "--tier",
        "chore",
    )

    risk = _id(
        capsys,
        "new",
        "RISK",
        "--title",
        "A leaked staff password opens the admin console",
        "--field",
        f"Threatens={rule}",
        "--field",
        "Domain=ACCESS",
        "--field",
        "Likelihood=Possible",
        "--field",
        "Impact=Major",
        "--intent",
        "an attacker reaches the console with a staff password",
    )
    control = _id(
        capsys,
        "new",
        "CONTROL",
        "--title",
        "Second factor on staff accounts",
        "--field",
        f"Implements={rule}",
        "--field",
        f"Treats={risk}",
        "--field",
        "Kind=Preventive",
        "--intent",
        "a second factor stops a leaked password alone",
    )
    assert control in json.loads(_cli(capsys, "view", risk, "--json"))["Controls"]  # the back-reference

    # each closing state's guard holds until its section is written
    assert main(["status", "set", control, "Effective", "--intent", "the second factor is enforced"]) == 1
    assert "`## Evidence` is not written" in capsys.readouterr().err
    control_file = root / json.loads(_cli(capsys, "view", control, "--json"))["file"]
    _write_section(
        capsys, control_file, "Evidence", "Every staff login asks for a second factor since 2026-10-19.", control
    )
    _cli(capsys, "status", "set", control, "Effective", "--intent", "the second factor is enforced for staff")

    incident = _id(
        capsys,
        "new",
        "INCIDENT",
        "--title",
        "A contractor's account reached the console",
        "--field",
        f"Breaks={rule}",
        "--field",
        f"Risks={risk}",
        "--field",
        "Severity=High",
        "--intent",
        "an incident shows the risk materialised",
    )
    assert main(["status", "set", incident, "Closed", "--intent", "the incident is over and reviewed"]) == 1
    incident_file = root / json.loads(_cli(capsys, "view", incident, "--json"))["file"]
    _write_section(capsys, incident_file, "Lessons", "Contractor accounts are staff accounts no longer.", incident)
    _cli(capsys, "status", "set", incident, "Closed", "--intent", "the incident is over and its lessons drawn")
    assert main(["status", "set", risk, "Treated", "--intent", "the second factor treats the risk"]) == 1
    risk_file = root / json.loads(_cli(capsys, "view", risk, "--json"))["file"]
    _write_section(capsys, risk_file, "Treatment", f"Treated by {control}: a second factor on staff accounts.", risk)
    _cli(capsys, "status", "set", risk, "Treated", "--intent", "the second factor treats the risk")

    # what a person reads: the list, the graph, the backlog, the audit, and a clean check
    listed = {r["id"] for r in json.loads(_cli(capsys, "list", "RISK", "--json"))}
    assert listed == {risk}
    graph = json.loads(_cli(capsys, "graph", "--json"))
    assert {"RISK", "CONTROL", "INCIDENT"} <= set(graph["types"])
    assert json.loads(_cli(capsys, "audit", "--json"))["rules"]
    entries = [
        json.loads(line)
        for f in (root / "development" / "journal").rglob("*.jsonl")
        for line in f.read_text(encoding="utf-8").splitlines()
        if line.startswith("{")
    ]
    tiers = {e.get("artifact"): e.get("tier") for e in entries if e.get("action") == "create"}
    assert tiers[risk] == "risk" and tiers[incident] == "incident"  # the module's tiers, inferred
    report = _cli(capsys, "check")
    assert "0 error(s)" in report and "legacy:" not in report  # catalyst.toml, the criterion in catalyst's home
    assert "software-engineering" not in json.dumps(graph)  # nothing of the other module
