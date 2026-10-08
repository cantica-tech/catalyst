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

# On-disk format versions this CLI reads (framework/kernel/FORMAT.md). A
# deployment declares its own in the pointer's `format` field.
FORMAT = "1.0-rc"
SUPPORTED_FORMATS = {"1.0-rc"}

# Files operating systems drop into any directory: never product work, so never
# an unrecorded change (anything else is opted out with .catalystignore).
NOISE = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})


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
    if not dep.standalone:
        declared = dep.pointer.get("format")
        if declared is None:
            report.warnings.append(f"format: the pointer declares no `format` (pre-{FORMAT} deployment; "
                                   "migration 0.41.0 adds it)")
        elif declared not in SUPPORTED_FORMATS:
            report.errors.append(f"format: the deployment is format {declared}; this catalyst reads "
                                 f"{', '.join(sorted(SUPPORTED_FORMATS))} — sync the CLI or the deployment")
    if not dep.standalone:
        from catalyst.scope import IGNORE_FILE, opted_out
        if opted_out(dep.project_root):
            report.errors.append(f"scope: {dep.project_root.name} has a pointer but is opted out of catalyst "
                                 f"by a {IGNORE_FILE} — remove one or the other")
    structure, report.scope = structural_errors(
        dep.root, None if dep.standalone else dep.project_root, dep.module)
    report.errors += [f"structure: {e}" for e in structure]
    corpus = load_corpus(dep)
    for f in validate(dep, corpus):
        (report.errors if f.level == ERROR else report.warnings).append(
            f"chain {f.code}: {f.where}: {f.message}")
    from catalyst import unrecorded
    manual = unrecorded.since_baseline(dep) if not dep.standalone and unrecorded.baseline(dep) is not None else []
    # a journaled file whose committed state is an unrecorded change: reported once, below, at the
    # beta's level — not also as an `unjournaled` error
    committed_by_hand = {path for c in manual for path, _, _ in c.changes}
    legacy = 0
    for i in journal.verify(dep):
        if i.code == "unjournaled" and i.path in committed_by_hand and _matches_head(dep, i.path):
            continue
        if i.level == "note":
            continue                         # history (e.g. merged concurrent edits), not a problem
        if i.legacy and i.level != "error":
            legacy += 1
            continue
        (report.errors if i.level == "error" else report.warnings).append(
            f"journal {i.code}: line {i.line}: {i.message}")
    if legacy:
        report.warnings.append(f"journal: {legacy} warning(s) on pre-CLI entries "
                               "(`catalyst journal verify --legacy`)")
    for path in unrecorded_changes(dep):
        report.warnings.append(f"journal unrecorded-change: {path} is changed in git but not recorded "
                               "in the journal (`catalyst journal append`)")
    if not dep.standalone:
        if unrecorded.baseline_missing(dep):
            report.warnings.append(f"unrecorded-change: {unrecorded.MISSING_BASELINE}")
        elif unrecorded.baseline(dep) is None:
            report.warnings.append(f"unrecorded-change: the pointer declares no `{unrecorded.BASELINE_KEY}`, so "
                                   "changes committed outside catalyst are not checked (migration 0.42.0)")
        else:
            sink = report.errors if unrecorded.level(dep) == "error" else report.warnings
            for c in manual:
                sink.append(f"unrecorded-change: {unrecorded.describe(c)}")
    from catalyst import analysis
    for art in corpus.by_prefix.get(analysis.PREFIX, []):
        for problem in analysis.problems(analysis.Context(dep, corpus, art, analysis.reports(dep, art.id))):
            report.errors.append(f"analysis: {art.id}: {problem}")
    for c in regenerate(dep, corpus, write=False):
        report.warnings.append(f"index: .criterion/{c.path.relative_to(dep.root)} is out of date "
                               "(`catalyst index regen`)")
    return report


def _matches_head(dep: Deployment, path: str) -> bool:
    """The file's working-tree content is what HEAD commits (edited, then committed as is)."""
    where = journal.locate(dep, path)
    if where is None:
        return False
    repo, rel = where
    current = journal.current_hashes(repo, [rel]).get(rel)
    return current is not None and current == journal.head_blob(repo, rel)


def unrecorded_changes(dep: Deployment) -> list[str]:
    """Product files git sees as changed or new whose current content is not
    what the journal last recorded — work that has not been journaled yet
    (edits to already-journaled files are journal-verify errors instead)."""
    import subprocess
    from catalyst.scope import governs
    if dep.standalone:
        return []
    root = str(dep.project_root)
    prefix = subprocess.run(["git", "-C", root, "rev-parse", "--show-prefix"],
                            capture_output=True, text=True, encoding="utf-8")
    # porcelain paths are relative to the repository top: keep the project's own
    # (`-- .`) and make them relative to the project, as the journal records them
    res = subprocess.run(["git", "-C", root, "status", "--porcelain", "-uall", "-z", "--", "."],
                         capture_output=True, text=True, encoding="utf-8")
    if prefix.returncode != 0 or res.returncode != 0:
        return []
    top = prefix.stdout.strip()
    paths = []
    items = iter(res.stdout.split("\0"))
    for item in items:
        if len(item) <= 3:
            continue
        if item[0] in "RC":
            next(items, None)                 # `-z` rename/copy: the source path follows
        path = item[3:]
        if top and path.startswith(top):
            path = path[len(top):]
        if path.rsplit("/", 1)[-1] in NOISE or not governs(dep.project_root, path):
            continue
        paths.append(path)
    if not paths:
        return []
    last = journal.last_after(dep)
    present = [p for p in paths if (dep.project_root / p).is_file()]
    # paths already in the journal are reported by `journal verify` (unjournaled)
    return sorted(p for p in present if p not in last)


def hook_stop(dep: Deployment, stdin=None, strict: bool = False) -> int:
    """Exit 2 with the failures on stderr so the agent keeps working; let
    the stop through when a Stop hook already blocked this stop, so an
    unfixable failure can't loop the session. A check that crashes is a
    failure too (fail closed): Claude Code ignores any exit but 2."""
    try:
        hook_input = json.loads((stdin or sys.stdin).read() or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        hook_input = {}
    try:
        report = run(dep)
    except Exception as exc:  # noqa: BLE001 — any crash must block, not switch enforcement off
        report = Report(errors=[f"check crashed: {type(exc).__name__}: {exc}"])
    if not report.failing(strict):
        return 0
    body = report.text() if strict else "\n".join(f"ERROR   {e}" for e in report.errors)
    if isinstance(hook_input, dict) and hook_input.get("stop_hook_active"):
        print(f"catalyst checks still failing (not blocking again):\n{body}", file=sys.stderr)
        return 0
    print(f"catalyst checks failed — fix these before stopping:\n{body}", file=sys.stderr)
    return 2
