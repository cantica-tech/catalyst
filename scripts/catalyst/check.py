"""`catalyst check`: every check a deployment can run on itself, in one pass
— structure (check_deployment), the traceability chain (validate), the
journal (verify) and index freshness — and `catalyst hook stop`, the same
pass shaped for an agent's end-of-turn hook."""

from __future__ import annotations

import datetime
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from catalyst import journal, proc
from catalyst.corpus import load_corpus
from catalyst.deployment import Deployment
from catalyst.indexes import regenerate
from catalyst.validate import ERROR, validate
from check_deployment import structural_errors

# On-disk format versions this CLI reads (framework/kernel/FORMAT.md). A
# deployment declares its own in the pointer's `format` field.
FORMAT = "1.0-rc"
# `1.0` is read too, ahead of the release: a deployment that declares it gets the release's strictness
# (unrecorded changes are errors, a legacy deployment is read-only); new ones still get FORMAT
SUPPORTED_FORMATS = {"1.0-rc", "1.0"}

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


# An entity ID inside a finding's text: an artifact's (`REQ-000004`) or a rule's (`br-AUTH-000001`), signed or not.
ENTITY_IN_TEXT = re.compile(r"\b[A-Za-z][A-Za-z0-9]*-(?:[A-Z][A-Z0-9.]*-)?\d{3,6}(?:-[A-Za-z0-9]{8})?\b")
FILE_IN_TEXT = re.compile(r"[\w./-]+\.md\b")


def as_json(report: Report, dep: Deployment, failing: bool) -> dict:
    """What `check --json` prints and `GET /v1/check` returns: `ok`, the
    `errors` and `warnings` as lines, and the same as `findings`, each with
    the entity it is about — the one whose file it names, else the first
    known entity ID in it — so a UI can mark drift where it shows the entity."""
    from catalyst import views

    corpus = load_corpus(dep)
    by_file: dict[str, str] = {}
    for defs in corpus.artifacts.values():
        for art in defs:
            by_file[art.file.relative_to(dep.root).as_posix()] = art.id
    for rid, defs in corpus.rules.items():
        if defs[0].file.name.startswith(rid):  # a one-file rule; a shared document names several
            by_file[defs[0].file.relative_to(dep.root).as_posix()] = rid

    def entity(text: str) -> str | None:
        for m in FILE_IN_TEXT.finditer(text):
            path = m.group(0)
            found = next((i for f, i in by_file.items() if path == f or path.endswith("/" + f)), None)
            if found:
                return found
        for m in ENTITY_IN_TEXT.finditer(text):
            try:
                found = views.resolve(corpus, m.group(0))
            except views.ViewError:  # a short ID two artifacts share: not this one's to guess
                continue
            if found:
                return found
        return None

    findings = [{"level": "error", "text": e, "entity": entity(e)} for e in report.errors]
    findings += [{"level": "warning", "text": w, "entity": entity(w)} for w in report.warnings]
    return {"ok": not failing, "errors": report.errors, "warnings": report.warnings, "findings": findings}


def run(dep: Deployment) -> Report:
    report = Report()
    if not dep.standalone:
        declared = dep.pointer.get("format")
        if declared is None:
            report.warnings.append(
                f"format: the pointer declares no `format` (pre-{FORMAT} deployment; migration 0.41.0 adds it)"
            )
        elif declared not in SUPPORTED_FORMATS:
            report.errors.append(
                f"format: the deployment is format {declared}; this catalyst reads "
                f"{', '.join(sorted(SUPPORTED_FORMATS))} — sync the CLI or the deployment"
            )
    if not dep.standalone:
        from catalyst.scope import IGNORE_FILE, opted_out

        if opted_out(dep.project_root):
            report.errors.append(
                f"scope: {dep.project_root.name} has a pointer but is opted out of catalyst "
                f"by a {IGNORE_FILE} — remove one or the other"
            )
    for module in dep.installed() if (dep.root / "version.txt").is_file() else []:
        if not module.kernel_version:
            continue
        from catalyst.versions import VersionError, satisfies

        deployed = (dep.root / "version.txt").read_text(encoding="utf-8").strip()
        try:
            inside = satisfies(deployed, module.kernel_version)
        except VersionError:
            inside = True  # an unreadable version is the structure check's to report
        if not inside:
            report.errors.append(
                f"module: {module.id} {module.version} works with kernel {module.kernel_version}, "
                f"but this deployment is at {deployed} — sync a module release that matches (fw-STRUCTURE-000016)"
            )
    structure, report.scope = structural_errors(
        dep.root, None if dep.standalone else dep.project_root, dep.module, dep.installed()[1:]
    )
    report.errors += [f"structure: {e}" for e in structure]
    corpus = load_corpus(dep)
    for f in validate(dep, corpus):
        (report.errors if f.level == ERROR else report.warnings).append(f"chain {f.code}: {f.where}: {f.message}")
    from catalyst import gates

    report.errors += [f"gates: {p}" for p in gates.problems(dep, corpus)]
    from catalyst import workflows

    report.errors += [f"workflow: {p}" for p in workflows.problems(dep, corpus)]
    report.errors += [f"type: {p}" for p in workflows.definition_problems(dep)]
    for o in workflows.overdue(dep, corpus):
        to = f"; escalate to {o['escalate_to']}" if o["escalate_to"] else ""
        report.warnings.append(f"overdue: {o['id']} is {o['status']}, due {o['due']} ({o['days']} day(s) ago){to}")
    from catalyst import proposals

    report.errors += [f"proposal: {p}" for p in proposals.problems(dep, corpus)]
    for w in gates.unapproved_rules(dep, corpus):
        report.errors.append(
            f"gates unapproved: {w['id']}: its current text lacks {w['missing']} of {w['approvals']} approval(s) "
            f"from {w['role']} under gate {w['gate']} (`catalyst approve {w['id']} --gate {w['gate']}`)"
        )
    from catalyst import unrecorded

    legacy_note = unrecorded.legacy_message(dep)
    if legacy_note:
        report.warnings.append(f"legacy: {legacy_note}")

    manual = unrecorded.since_baseline(dep) if not dep.standalone and unrecorded.baseline(dep) is not None else []
    # a journaled file whose committed state is an unrecorded change: reported once, below, at the
    # beta's level — not also as an `unjournaled` error
    committed_by_hand = {path for c in manual for path, _, _ in c.changes}
    legacy = 0
    issues = journal.verify(dep)
    candidates = {i.path for i in issues if i.code == "unjournaled" and i.path in committed_by_hand}
    as_committed = _matching_head(dep, candidates)
    for i in issues:
        if i.code == "unjournaled" and i.path in as_committed:
            continue
        if i.level == "note":
            continue  # history (e.g. merged concurrent edits), not a problem
        if i.legacy and i.level != "error":
            legacy += 1
            continue
        (report.errors if i.level == "error" else report.warnings).append(f"journal {i.code}: {i.at}: {i.message}")
    if legacy:
        report.warnings.append(f"journal: {legacy} warning(s) on pre-CLI entries (`catalyst journal verify --legacy`)")
    for path in unrecorded_changes(dep):
        report.warnings.append(
            f"journal unrecorded-change: {path} is changed in git but not recorded "
            "in the journal (`catalyst journal append`)"
        )
    if not dep.standalone:
        if unrecorded.baseline_missing(dep):
            report.warnings.append(f"unrecorded-change: {unrecorded.MISSING_BASELINE}")
        elif unrecorded.baseline(dep) is None:
            report.warnings.append(
                f"unrecorded-change: the pointer declares no `{unrecorded.BASELINE_KEY}`, so "
                "changes committed outside catalyst are not checked (migration 0.42.0)"
            )
        else:
            sink = report.errors if unrecorded.level(dep) == "error" else report.warnings
            for c in manual:
                sink.append(f"unrecorded-change: {unrecorded.describe(c)}")
    from catalyst import analysis

    for art in corpus.by_prefix.get(analysis.PREFIX, []):
        for problem in analysis.problems(analysis.Context(dep, corpus, art, analysis.reports(dep, art.id))):
            report.errors.append(f"analysis: {art.id}: {problem}")
    for c in regenerate(dep, corpus, write=False):
        report.warnings.append(
            f"index: .criterion/{c.path.relative_to(dep.root)} is out of date (`catalyst index regen`)"
        )
    report.errors += [f"integrity: {p}" for p in merge_integrity(dep)]
    from catalyst import modules

    for f in modules.verify(dep.root):
        if f.state == "changed":
            report.errors.append(
                f"module: {f.id} differs from its record in {modules.RECORD}: a file under modules/{f.id}/ "
                "changed outside `catalyst sync` (`catalyst module verify`)"
            )
        elif f.state == "missing":
            report.errors.append(f"module: {f.id} is recorded in {modules.RECORD} but modules/{f.id}/ is gone")
    record_last(dep, report)
    return report


def _last_path(dep: Deployment) -> Path:
    from catalyst import lock

    return lock.state_dir(dep.root) / "last-check.json"


def record_last(dep: Deployment, report: Report) -> None:
    """The last check's result, for the CLI's status line (brand item 9): in
    the criterion's own git directory, never shared; best effort."""
    try:
        path = _last_path(dep)
        path.parent.mkdir(parents=True, exist_ok=True)
        at = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
        path.write_text(
            json.dumps({"at": at, "errors": len(report.errors), "warnings": len(report.warnings)}), encoding="utf-8"
        )
    except OSError:
        pass


def last(dep: Deployment) -> dict | None:
    """The last check's result recorded here, or None."""
    try:
        data = json.loads(_last_path(dep).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and "at" in data else None


def status_line(dep: Deployment, now: datetime.datetime | None = None) -> str:
    """`catalyst · <project> · checked 14:08 · 0 error(s), 3 warning(s)` (`09`
    §5.4): the last recorded check, never a new one."""
    name = str(dep.pointer.get("project_name") or dep.pointer.get("name") or dep.project_root.name)
    result = last(dep)
    if result is None:
        return f"catalyst · {name} · not checked yet (catalyst check)"
    try:
        at = datetime.datetime.fromisoformat(str(result["at"])).astimezone()
    except ValueError:
        return f"catalyst · {name} · not checked yet (catalyst check)"
    now = (now or datetime.datetime.now(datetime.UTC)).astimezone()
    when = at.strftime("%H:%M") if at.date() == now.date() else at.strftime("%Y-%m-%d %H:%M")
    return (
        f"catalyst · {name} · checked {when} · {int(result.get('errors', 0))} error(s), "
        f"{int(result.get('warnings', 0))} warning(s)"
    )


def merge_integrity(dep: Deployment) -> list[str]:
    """When the criterion's own HEAD is a merge (a pull, a pull request's
    merge ref in CI), nothing either side recorded — IDs, index rows,
    journal lines — may be missing from it (`criterion integrity`). The
    result is kept per HEAD, so the end-of-turn check stays cheap."""

    from catalyst import criterion as cr, lock

    def git(*args: str) -> str:
        res = proc.git(dep.root, *args)
        return res.stdout.strip() if res.returncode == 0 else ""

    top = git("rev-parse", "--show-toplevel")
    if not top or Path(top).resolve() != dep.root.resolve():
        return []  # not its own repository (a legacy in-project working copy)
    head, *parents = git("rev-list", "--parents", "-n", "1", "HEAD").split() or [""]
    if len(parents) < 2:
        return []
    cache = lock.state_dir(dep.root) / "integrity" / head
    try:
        return [line for line in cache.read_text(encoding="utf-8").splitlines() if line]
    except OSError:
        pass
    problems = cr.integrity(dep.root, head, parents)
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text("".join(f"{p}\n" for p in problems), encoding="utf-8")
    except OSError:
        pass  # a read-only checkout: checked again next time
    return problems


def _matching_head(dep: Deployment, paths) -> set[str]:
    """Of these journal paths, those whose working-tree content is what HEAD
    commits (edited, then committed as is): one `hash-object` and one
    `cat-file --batch-check` per repository, whatever the number of files."""

    by_repo: dict[Path, dict[str, str]] = {}
    for path in paths:
        where = journal.locate(dep, path) if path else None
        if where is not None:
            by_repo.setdefault(where[0], {})[where[1]] = path
    found = set()
    for repo, rels in by_repo.items():
        current = journal.current_hashes(repo, list(rels))
        names = list(rels)
        prefix = proc.git(repo, "rev-parse", "--show-prefix").stdout.strip()  # a project below the top level
        res = proc.git(  # stdin as bytes: a text pipe on Windows would send "\r\n", which git reads as data
            repo, "cat-file", "--batch-check=%(objectname)", input="".join(f"HEAD:{prefix}{rel}\n" for rel in names)
        )
        lines = res.stdout.splitlines() if res.returncode == 0 else []
        for rel, line in zip(names, lines, strict=False):  # no lines when git failed
            head = line.strip() if not line.endswith("missing") else None
            if current.get(rel) is not None and current.get(rel) == head:
                found.add(rels[rel])
    return found


def unrecorded_changes(dep: Deployment) -> list[str]:
    """Product files git sees as changed or new whose current content is not
    what the journal last recorded — work that has not been journaled yet
    (edits to already-journaled files are journal-verify errors instead)."""

    from catalyst.scope import governs

    if dep.standalone:
        return []
    root = str(dep.project_root)
    prefix = proc.git(root, "rev-parse", "--show-prefix")
    # porcelain paths are relative to the repository top: keep the project's own
    # (`-- .`) and make them relative to the project, as the journal records them
    res = proc.git(root, "status", "--porcelain", "-uall", "-z", "--", ".")
    if prefix.returncode != 0 or res.returncode != 0:
        return []
    top = prefix.stdout.strip()
    paths = []
    items = iter(res.stdout.split("\0"))
    for item in items:
        if len(item) <= 3:
            continue
        if item[0] in "RC":
            next(items, None)  # `-z` rename/copy: the source path follows
        path = item[3:]
        if top and path.startswith(top):
            path = path[len(top) :]
        if path.rsplit("/", 1)[-1] in NOISE or not governs(dep.project_root, path):
            continue
        paths.append(path)
    if not paths:
        return []
    last = journal.last_after(dep)
    present = [p for p in paths if (dep.project_root / p).is_file()]
    # paths already in the journal are reported by `journal verify` (unjournaled)
    return sorted(p for p in present if p not in last)


HOOK_FORMATS = ("exit2", "json", "gemini", "cursor")


def hook_input(stdin=None) -> dict:
    """The JSON an agent hands its hooks on stdin ({} when none)."""
    try:
        data = json.loads((stdin or sys.stdin).read() or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def hook_block(reason: str, fmt: str = "exit2") -> int:
    """Keep the agent working, in the agent's own terms: Claude Code reads
    exit 2 and stderr; Codex, Copilot (CLI and VS Code) and Claude Code read
    `decision: block`; Gemini CLI `decision: deny`; Cursor a follow-up message."""
    if fmt == "exit2":
        print(reason, file=sys.stderr)
        return 2
    payload = (
        {"followup_message": reason}
        if fmt == "cursor"
        else {"decision": "deny" if fmt == "gemini" else "block", "reason": reason}
    )
    print(json.dumps(payload))
    return 0


SESSION_KEYS = ("session_id", "sessionId", "conversation_id", "conversationId")
BASELINE_DAYS = 7


def session_of(data: dict) -> str | None:
    """The agent's session id in its hook input, when it gives one."""
    for key in SESSION_KEYS:
        value = data.get(key)
        if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9._-]{1,128}", value):
            return value
    return None


def _baselines(dep: Deployment) -> Path:
    from catalyst import lock

    return lock.state_dir(dep.root) / "sessions"


def record_baseline(dep: Deployment, session: str, report: Report) -> Path:
    """What `check` fails on as a session starts (ADR-002), in the
    criterion's own git directory: never shared, never in the project.
    Baselines older than a week are removed."""
    import datetime
    import time

    folder = _baselines(dep)
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.json"):
        if time.time() - old.stat().st_mtime > BASELINE_DAYS * 86400:
            old.unlink(missing_ok=True)
    path = folder / f"{session}.json"
    at = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    path.write_text(json.dumps({"at": at, "errors": report.errors, "warnings": report.warnings}), encoding="utf-8")
    return path


def read_baseline(dep: Deployment, session: str | None) -> dict | None:
    if session is None:
        return None
    path = _baselines(dep) / f"{session}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def hook_stop(dep: Deployment, data: dict | None = None, strict: bool = False, fmt: str = "exit2") -> int:
    """Block the stop with the failures so the agent keeps working; let
    the stop through when a stop hook already blocked this stop, so an
    unfixable failure can't loop the session. A check that crashes is a
    failure too (fail closed): Claude Code ignores any exit but 2."""
    data = hook_input() if data is None else data
    if dep.pointer.get("governance") == "suspended":  # catalyst.toml: the owner suspended enforcement
        print(
            "catalyst: governance suspended in catalyst.toml — not checking (`catalyst check` still reports)",
            file=sys.stderr,
        )
        return 0
    try:
        report = run(dep)
    except Exception as exc:
        report = Report(errors=[f"check crashed: {type(exc).__name__}: {exc}"])
    if not report.failing(strict):
        return 0
    lines = [f"ERROR   {e}" for e in report.errors] + ([f"WARNING {w}" for w in report.warnings] if strict else [])
    if data.get("stop_hook_active"):
        print("catalyst checks still failing (not blocking again):\n" + "\n".join(lines), file=sys.stderr)
        return 0
    # ADR-002: a session blocks on what it broke, not on what it found
    session = session_of(data)
    base = read_baseline(dep, session)
    if base is None:
        why = (
            "no session id from the agent"
            if session is None
            else "no baseline for this session (`catalyst agent install <agent>` adds the session-start hook)"
        )
        return hook_block(
            "catalyst checks failed — fix these before stopping:\n"
            + "\n".join(lines)
            + f"\n({why}: every failure counts)",
            fmt,
        )
    known = {f"ERROR   {e}" for e in base.get("errors") or []} | {f"WARNING {w}" for w in base.get("warnings") or []}
    new = [line for line in lines if line not in known]
    found = [line for line in lines if line in known]
    if not new:
        print(
            f"catalyst: {len(found)} failure(s) were already there when this session started; not blocking:\n"
            + "\n".join(found),
            file=sys.stderr,
        )
        return 0
    tail = f"\n({len(found)} more were already there when this session started)" if found else ""
    return hook_block("catalyst checks failed — fix these before stopping:\n" + "\n".join(new) + tail, fmt)
