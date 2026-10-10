"""Both rule shapes real deployments use (0.52.1): a heading in a rule
document, or one file per rule (`<ID>-<slug>.md`), with sub-domain codes
(`CORE.INGEST`) and `<ID>-<slug>` citations."""

from __future__ import annotations

import json

from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst.trace import FULL_SHAPE, TOKEN_RE
from catalyst.validate import validate
from catalyst_fixtures import USERID, artifact, make_project, write
from check_deployment import check_journal_exists


def _per_file_rules(project):
    root = project / ".criterion"
    rule = f"cor-CORE.INGEST-000001-{USERID}"
    old = f"cor-CORE.INGEST-000002-{USERID}"
    write(
        root / "rules" / "core" / f"{rule}-log-pipeline.md",
        "## Rule metadata\n\n- **Domain**: `CORE.INGEST`\n- **Status**: ✅ implemented\n\n## Rule\n\nLogs flow.\n",
    )
    write(
        root / "rules" / "core" / f"{old}-old-pipeline.md",
        "## Rule metadata\n\n- **Status**: 🗑 retired — superseded\n\n## Rule\n\nOld.\n",
    )
    write(
        root / "rules" / "core" / "core-rules.md",
        "# Core rules\n\n## Contents\n\n| Rule | Status |\n|---|---|\n"
        f"| [`{rule}-log-pipeline`]({rule}-log-pipeline.md) | ✅ |\n\n## Linked Artifacts — Quick Index\n",
    )
    index = root / "rules" / "rules.md"
    index.write_text(
        index.read_text(encoding="utf-8") + f"- `{rule}-log-pipeline` — Logs\n- `{old}-old-pipeline` — Old\n",
        encoding="utf-8",
    )
    domains = root / "rules" / "domains" / "domains.md"
    domains.write_text(
        domains.read_text(encoding="utf-8") + "| [`CORE.INGEST`](cor-CORE.INGEST-ingest.md) | core | 2026-01-01 |\n",
        encoding="utf-8",
    )
    return rule, old


def test_one_file_per_rule_with_sub_domains_and_slug_citations(tmp_path):
    project = make_project(tmp_path, git=True)
    rule, old = _per_file_rules(project)
    item = f"ITEM-000002-{USERID}"
    write(
        project / ".criterion" / "items" / "ITEM-000002-ingest.md",
        artifact(
            item,
            "Ingest",
            {
                "ID": f"`{item}`",
                "Status": "Open",
                "Targets": f"`{rule}-log-pipeline`, `{old}`",
                "Domain": "`CORE.INGEST`",
                "Signed-off-by": "Ada Lovelace",
            },
        ),
    )
    corpus = load_corpus(load(project))
    assert corpus.rule_id(f"{rule}-log-pipeline") == rule and corpus.rule_id(rule) == rule
    assert corpus.rules[old][0].retired and not corpus.rules[rule][0].retired
    findings = {(f.code, f.message) for f in validate(load(project), corpus)}
    assert not [m for c, m in findings if c in ("dangling-ref", "ungrounded", "rule-unindexed")], findings
    assert any(c == "retired-target" and old in m for c, m in findings)
    found = TOKEN_RE.search(f"fix: ingest ({rule})")
    assert found is not None and found.group(1) == rule and FULL_SHAPE.match(rule)


def test_a_pre_cli_journal_entry_is_never_a_structure_error(tmp_path):
    project = make_project(tmp_path)
    root = project / ".criterion"
    entry = {
        "timestamp": "2026-09-20T21:45:00Z",
        "actor": "ada",
        "command": "/create-req",
        "action": "create",
        "artifact": "x",
        "targets": [],
        "intent": ["before hashes not recoverable, flagged"],
        "files": [{"path": "items/x.md", "before": "(unrecoverable)", "after": "1" * 40}],
    }
    write(root / "development" / "journal.jsonl", json.dumps(entry) + "\n")
    assert check_journal_exists(root) == []
    write(root / "development" / "journal.jsonl", json.dumps(dict(entry, writer="catalyst/0.52.1")) + "\n")
    assert any("is not a 40-hex git hash" in e for e in check_journal_exists(root))
