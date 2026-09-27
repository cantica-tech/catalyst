"""`catalyst check`: every check a deployment can run on itself, in one pass
— structure (check_deployment), the traceability chain (validate), the
journal (verify) and index freshness — and `catalyst hook stop`, the same
pass shaped for an agent's end-of-turn hook."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field

from check_deployment import structural_errors

from catalyst import journal
from catalyst.corpus import load_corpus
from catalyst.deployment import Deployment
from catalyst.indexes import regenerate
from catalyst.validate import ERROR, validate


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    scope: str = ""

    def failing(self, strict: bool) -> bool:
        return bool(self.errors or (strict and self.warnings))

    def text(self) -> str:
        lines = [f"ERROR   {e}" for e in self.errors] + [f"WARNING {w}" for w in self.warnings]
        return "\n".join(lines)


def run(dep: Deployment) -> Report:
    report = Report()
    structure, report.scope = structural_errors(dep.root, dep.project_root)
    report.errors += [f"structure: {e}" for e in structure]
    corpus = load_corpus(dep)
    for f in validate(dep, corpus):
        (report.errors if f.level == ERROR else report.warnings).append(
            f"chain {f.code}: {f.where}: {f.message}")
    legacy = 0
    for i in journal.verify(dep):
        if i.legacy and i.level != "error":
            legacy += 1
            continue
        (report.errors if i.level == "error" else report.warnings).append(
            f"journal {i.code}: line {i.line}: {i.message}")
    if legacy:
        report.warnings.append(f"journal: {legacy} warning(s) on pre-CLI entries "
                               "(`catalyst journal verify --legacy`)")
    for c in regenerate(dep, corpus, write=False):
        report.warnings.append(f"index: .criterion/{c.path.relative_to(dep.root)} is out of date "
                               "(`catalyst index regen`)")
    return report


def hook_stop(dep: Deployment, stdin=None, strict: bool = False) -> int:
    """Exit 2 with the failures on stderr so the agent keeps working; let
    the stop through when a Stop hook already blocked this stop, so an
    unfixable failure can't loop the session."""
    try:
        hook_input = json.loads((stdin or sys.stdin).read() or "{}")
    except json.JSONDecodeError:
        hook_input = {}
    report = run(dep)
    if not report.failing(strict):
        return 0
    body = report.text() if strict else "\n".join(f"ERROR   {e}" for e in report.errors)
    if isinstance(hook_input, dict) and hook_input.get("stop_hook_active"):
        print(f"catalyst checks still failing (not blocking again):\n{body}", file=sys.stderr)
        return 0
    print(f"catalyst checks failed — fix these before stopping:\n{body}", file=sys.stderr)
    return 2
