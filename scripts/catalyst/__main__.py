"""`catalyst` command line. Every subcommand works on the deployment found at
or above the current directory (or `--project`), prints human-readable
output, or JSON with `--json`, and exits non-zero on failure."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from catalyst import proc, version_string
from catalyst.analysis import AnalysisError
from catalyst.criterion import CriterionError
from catalyst.deployment import DeploymentNotFound, WorkingCopyMissing, load, logical_cwd
from catalyst.ids import IdError
from catalyst.journal import JournalError, check_tier as journal_check_tier
from catalyst.store import ShareError


def open_deployment(args):
    if getattr(args, "working_copy", None):
        from catalyst.deployment import load_working_copy

        return load_working_copy(args.working_copy)
    return load(args.project)


def cmd_validate(args) -> int:
    from catalyst.corpus import load_corpus
    from catalyst.validate import ERROR, validate

    dep = open_deployment(args)
    findings = validate(dep, load_corpus(dep))
    errors = [f for f in findings if f.level == ERROR]
    failing = findings if args.strict else errors
    if args.json:
        json.dump({"ok": not failing, "findings": [f.as_dict() for f in findings]}, sys.stdout, indent=2)
        print()
    else:
        for f in findings:
            print(f)
        warnings = len(findings) - len(errors)
        verdict = "FAILED" if failing else "passed"
        print(
            f"catalyst validate {verdict}: {len(errors)} error(s), {warnings} warning(s)"
            + (" (strict)" if args.strict else "")
        )
    return 1 if failing else 0


def cmd_id(args) -> int:
    from catalyst.corpus import load_corpus
    from catalyst.ids import next_entity_id, next_rule_id, resolve_signer

    dep = open_deployment(args)
    corpus = load_corpus(dep)
    signer = resolve_signer(dep, corpus, args.as_user)
    # reserved under the ID lock: parallel callers never get the same ID
    if args.id_command == "next":
        if args.count < 1:
            print("catalyst: --count must be at least 1", file=sys.stderr)
            return 2
        for _ in range(args.count):  # consecutive IDs, each reserved: a batch of rows, never guessed
            print(next_entity_id(dep, corpus, args.prefix, signer, reserve=True))
    else:
        print(next_rule_id(dep, corpus, args.doc_prefix, args.domain, signer, reserve=True))
    return 0


def cmd_userid(args) -> int:
    from catalyst.corpus import load_corpus
    from catalyst.ids import generate_userid

    dep = open_deployment(args)
    existing = {str(u["userid"]) for u in load_corpus(dep).users if u.get("userid")}
    print(generate_userid(existing))
    return 0


def cmd_journal(args) -> int:
    from catalyst import journal as j

    dep = open_deployment(args)
    if args.journal_command == "redact":
        from catalyst import tiers
        from catalyst.corpus import load_corpus
        from catalyst.ids import resolve_signer

        try:
            signer = resolve_signer(dep, load_corpus(dep), args.as_user)
            chore = args.tier or next((t.id for t in tiers.tiers_for(dep) if not t.needs_artifact), None)
            entry = j.redact(
                dep, args.blobs, args.intent or [], str(signer.get("git_username") or signer.get("name")), chore
            )
        except (j.JournalError, IdError) as exc:
            print(f"catalyst: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(entry, indent=2))
            return 0
        print(f"redacted {len(entry['redacted'])} blob(s) of {', '.join(entry['paths'])}; journaled")
        print(f"unpinned in: {', '.join(entry['unpinned_in']) or 'nothing (not pinned)'}")
        print(
            "Not done, and not catalyst's to do: a commit that holds the file still holds the blob, here and on "
            "every clone. Rotate the secret; purging history (`git filter-repo`) is the owner's call. The pins "
            "change on the shared copy at the next publish."
        )
        return 0
    if args.journal_command == "append":
        from catalyst.corpus import load_corpus
        from catalyst.ids import resolve_signer

        signer = resolve_signer(dep, load_corpus(dep), args.as_user)
        entry = j.append(
            dep,
            j.AppendRequest(
                command=args.cmd,
                action=args.action,
                artifact=args.artifact,
                targets=args.target or [],
                intent=args.intent or [],
                files=args.file or [],
                actor=str(signer.get("git_username") or signer.get("name")),
                allow_unchanged=args.allow_unchanged,
                tier=args.tier,
            ),
        )
        print(
            json.dumps(entry, ensure_ascii=False)
            if args.json
            else f"journaled {len(entry['files'])} file(s) at {entry['timestamp']}"
        )
        return 0
    if args.journal_command == "adopt":
        from catalyst import unrecorded

        try:
            entries = unrecorded.adopt(
                dep,
                args.revs,
                args.intent or [],
                tier=args.tier,
                targets=args.target or [],
                artifact=args.artifact,
                actor=args.as_user,
            )
        except ValueError as exc:
            print(f"catalyst: {exc}", file=sys.stderr)
            return 1
        for e in entries:
            print(
                json.dumps(e, ensure_ascii=False)
                if args.json
                else f"adopted {e['commit'][:10]} ({e['actor']}): {len(e['files'])} file(s)"
            )
        if not entries:
            print("nothing to adopt: every change in those commits is already in the journal")
        return 0
    if args.journal_command == "verify":
        issues = j.verify(dep)
        notes = [i for i in issues if i.level == "note"]
        issues = [i for i in issues if i.level != "note"]
        errors = [i for i in issues if i.level == "error"]
        failing = issues if args.strict else errors
        if args.json:
            json.dump({"ok": not failing, "issues": [vars(i) for i in issues]}, sys.stdout, indent=2)
            print()
        else:
            hidden = [i for i in issues if i.legacy and i.level != "error" and not args.legacy]
            for i in issues:
                if i not in hidden:
                    print(i)
            if hidden:
                print(f"({len(hidden)} warning(s) on entries written before the catalyst CLI; --legacy lists them)")
            print(
                f"catalyst journal verify {'FAILED' if failing else 'passed'}: "
                f"{len(errors)} error(s), {len(issues) - len(errors)} warning(s)"
                + (f", {len(notes)} note(s) (merged concurrent edits)" if notes else "")
            )
        return 1 if failing else 0
    if args.journal_command == "restore":
        import tempfile

        # outside the project by default, never over the working tree
        out = args.out or Path(tempfile.gettempdir()) / f"journal-restore-{re.sub(r'[^0-9A-Za-z]', '', args.timestamp)}"
        restored, missing = j.restore(dep, args.timestamp, out)
        print(f"restored {len(restored)} file(s) as of {args.timestamp} into {out}")
        for path in missing:
            print(f"  missing blob: {path}")
        return 1 if missing else 0
    counts = j.pin_all(dep)
    for repo, n in counts.items():
        print(f"{repo}: pinned {n} new blob(s) under {j.PIN_REF}")
    if args.share:
        from catalyst.criterion import CriterionError, share_pins

        repos = [dep.root] + ([] if dep.standalone else [dep.project_root])
        for repo in repos:
            if proc.git(repo, "remote", "get-url", "origin").returncode != 0:
                continue
            try:
                print(f"{repo.name}: {share_pins(repo)} blob(s) pinned on the remote")
            except CriterionError as exc:
                print(f"catalyst: {exc}", file=sys.stderr)
                return 1
    return 0


def cmd_index(args) -> int:
    import difflib

    from catalyst.corpus import load_corpus
    from catalyst.indexes import regenerate

    dep = open_deployment(args)
    changes = regenerate(dep, load_corpus(dep), write=not args.check)
    for c in changes:
        rel = f".criterion/{c.path.relative_to(dep.root)}"
        if args.check:
            print(f"out of date: {rel}")
            if args.diff:
                sys.stdout.writelines(
                    difflib.unified_diff(c.old.splitlines(True), c.new.splitlines(True), rel, rel + " (regenerated)")
                )
        else:
            print(f"regenerated: {rel}")
    if not changes:
        print("all indexes are up to date")
    return 1 if (args.check and changes) else 0


def cmd_check(args) -> int:
    from catalyst.check import run

    try:
        dep = open_deployment(args)
    except WorkingCopyMissing as exc:
        print(f"catalyst check FAILED: {exc}")
        return 1
    except DeploymentNotFound as exc:
        print(f"catalyst check skipped: {exc}")  # not a catalyst project at all
        return 0
    report = run(dep)
    failing = report.failing(args.strict)
    if args.json:
        from catalyst.check import as_json

        json.dump(as_json(report, dep, failing), sys.stdout, indent=2)
        print()
    else:
        if report.errors or report.warnings:
            print(report.text())
        print(
            f"catalyst check {'FAILED' if failing else 'passed'} ({report.scope}): "
            f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)"
        )
    return 1 if failing else 0


def cmd_view(args) -> int:
    """Read-only views (R2 W1): list, journal show, view, backlog."""
    from catalyst import views as v
    from catalyst.corpus import load_corpus

    dep = open_deployment(args)
    data: Any  # each view's own shape, printed by its own renderer
    try:
        if args.view == "journal" and getattr(args, "content", False):
            from catalyst import history

            if not args.artifact:
                raise v.ViewError("--content shows one entity's history: name it with --artifact <id>")
            data, text = history.history(dep, load_corpus(dep), args.artifact), history.render
        elif args.view == "journal":
            data = v.journal_entries(dep, args.since, args.artifact, args.actor, args.rule)
            text = v.render_journal
        else:
            corpus = load_corpus(dep)
            if args.view == "list":
                data = v.list_items(dep, corpus, args.type, v.parse_filters(args.filter), args.template_type)
                text = v.render_list
            elif args.view == "view":
                data, text = v.view(dep, corpus, args.id), v.render_view
            elif args.view == "graph":
                data, text = v.graph(dep, corpus), v.render_graph
            else:
                data, text = v.backlog(dep, corpus), v.render_backlog
    except (v.ViewError, JournalError) as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    if args.json:
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False, default=str)
        print()
    else:
        sys.stdout.write(text(data))
    return 0


def cmd_repair(args) -> int:
    """`catalyst repair derived` (module v3 M2): rewrite every derived field
    from its sources, journaled."""
    from catalyst import derived, tiers
    from catalyst.corpus import load_corpus
    from catalyst.ids import resolve_signer

    dep = open_deployment(args)
    corpus = load_corpus(dep)
    try:
        signer = resolve_signer(dep, corpus, args.as_user)
        chore = next((t.id for t in tiers.tiers_for(dep) if not t.needs_artifact), None)
        changed = derived.repair(dep, corpus, signer, args.tier or chore)
    except (IdError, JournalError, ValueError) as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(
            json.dumps(
                [{"id": d.art.id, "field": d.field, "added": d.missing, "removed": d.extra} for d in changed], indent=2
            )
        )
    elif not changed:
        print("every derived field agrees with its sources")
    else:
        for d in changed:
            print(f"{d.art.id} `{d.field}`: added {', '.join(d.missing) or '—'}; removed {', '.join(d.extra) or '—'}")
        print(f"{len(changed)} derived field(s) rewritten, journaled")
    return 0


def cmd_approve(args) -> int:
    """`catalyst approve <ID> --gate <gate>` (decision G, design 25 A2): one
    approval of the entity's current version, journaled."""
    from catalyst import gates
    from catalyst.corpus import load_corpus
    from catalyst.ids import resolve_signer
    from catalyst.views import ViewError

    dep = open_deployment(args)
    corpus = load_corpus(dep)
    try:
        signer = resolve_signer(dep, corpus, args.as_user)
        entry = gates.approve(dep, corpus, args.id, args.gate, signer, args.intent or [], args.tier)
        left = next(
            g for g in gates.report(dep, load_corpus(dep), entry["artifact"])["gates"] if g["gate"] == args.gate
        )
    except (IdError, JournalError, gates.GateError, ViewError) as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({**entry, "missing": left["missing"]}, indent=2))
    else:
        print(
            f"{entry['artifact']} approved under gate {args.gate} by {entry['actor']}, journaled; "
            + (f"{left['missing']} approval(s) still missing" if left["missing"] else "the gate is passed")
        )
    return 0


def cmd_approvals(args) -> int:
    """`catalyst approvals <ID>`: each gate covering the entity, what counts and what is missing."""
    from catalyst import gates
    from catalyst.corpus import load_corpus
    from catalyst.views import ViewError

    dep = open_deployment(args)
    try:
        data = gates.report(dep, load_corpus(dep), args.id)
    except (gates.GateError, ViewError) as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    if not data["gates"]:
        print(f"{data['id']}: no gate covers it")
    for g in data["gates"]:
        what = (
            f"rules of {g['covers']['rules']['domain']}"
            if "rules" in g["covers"]
            else (f"{g['covers']['type']} entering {g['covers']['to']}")
        )
        said = ", ".join(g["counted"]) or "none"
        print(
            f"{data['id']} gate {g['gate']} ({what}): {len(g['counted'])}/{g['approvals']} from {g['role']} "
            f"({said})" + (f"; {g['missing']} missing" if g["missing"] else "; passed")
        )
    return 0


def cmd_edit(args) -> int:
    """Writing verbs (R2 W2): new, rename, restore, status set, link."""
    from catalyst import edit
    from catalyst.corpus import load_corpus
    from catalyst.ids import resolve_signer

    dep = open_deployment(args)
    corpus = load_corpus(dep)
    try:
        if getattr(args, "tier", None) is not None:
            journal_check_tier(dep, args.tier)  # before anything is written (rr-META-006)
        signer = resolve_signer(dep, corpus, args.as_user)
        if args.edit == "new":
            values = {}
            for spec in args.field or []:
                key, sep, value = spec.partition("=")
                if not sep:
                    raise edit.EditError(f"--field '{spec}' is not NAME=VALUE")
                values[key.strip()] = value.strip()
            res = edit.new(
                dep,
                corpus,
                args.type,
                args.title,
                values,
                signer,
                args.intent or [],
                command=args.cmd or "catalyst new",
                tier=args.tier,
            )
        elif args.edit == "rename":
            res = edit.rename(
                dep,
                corpus,
                args.id,
                args.title,
                signer,
                args.intent or [],
                command=args.cmd or "catalyst rename",
                tier=args.tier,
            )
        elif args.edit == "restore":
            res = edit.restore(
                dep,
                corpus,
                args.id,
                args.to,
                signer,
                args.intent or [],
                command=args.cmd or "catalyst restore",
                tier=args.tier,
            )
        elif args.edit == "status":
            res = edit.set_status(
                dep,
                corpus,
                args.id,
                args.status,
                signer,
                args.intent or [],
                force=args.force,
                command=args.cmd or "/status",
                tier=args.tier,
            )
        else:
            res = edit.link(
                dep,
                corpus,
                args.id,
                args.field_name,
                args.ids,
                signer,
                args.intent or [],
                command=args.cmd or "catalyst link",
                tier=args.tier,
            )
    except (edit.EditError, IdError, JournalError) as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"id": res.id, "file": str(res.file), "touched": [str(p) for p in res.touched]}))
    else:
        print(f"{res.id}  {res.file}")
        for p in res.touched[1:]:
            print(f"  also updated {p}")
    return 0


def cmd_admin(args) -> int:
    """Administration verbs (R2 W3): users, roles, freeze/unfreeze, definitions."""
    from catalyst import admin
    from catalyst.corpus import load_corpus
    from catalyst.ids import resolve_signer
    from module_loader import REPO_ROOT

    dep = open_deployment(args)
    intent = args.intent or []
    try:
        signer = resolve_signer(dep, load_corpus(dep), args.as_user)
        if args.admin == "user":
            sub_cmd = args.user_command
            if sub_cmd == "add":
                out = admin.user_add(dep, args.name, args.role, signer, intent, git_username=args.git_username)
            elif sub_cmd == "remove":
                out = admin.user_remove(dep, args.name, signer, intent)
            elif sub_cmd == "modify":
                out = admin.user_modify(dep, args.name, args.field, args.value, signer, intent)
            else:
                out = admin.user_assign_role(dep, args.name, args.role, signer, intent)
        elif args.admin == "role":
            if args.role_command == "add":
                out = admin.role_add(dep, args.name, args.action or [], signer, intent, args.reconciliation)
            else:
                out = admin.role_modify(dep, args.name, args.action or [], signer, intent)
        elif args.admin in ("freeze", "unfreeze"):
            out = {
                "frozen" if args.admin == "freeze" else "unfrozen": admin.freeze(
                    dep, args.item, signer, intent, unfreeze=args.admin == "unfreeze"
                )
            }
        else:
            kernel = args.kernel or (REPO_ROOT / "framework" / "kernel")
            entity, old = admin.migrate_definition(dep, args.entity, args.version, kernel, signer, intent)
            out = {"definition": entity, "from": old, "to": args.version}
    except (admin.AdminError, IdError, JournalError) as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(out, ensure_ascii=False)
        if args.json
        else "; ".join(f"{k}: {v}" for k, v in out.items() if k != "notes")
    )
    return 0


def cmd_sync(args) -> int:
    """`sync plan|apply` (R2 W4): the mechanical half of /sync-framework."""

    dep = open_deployment(args)
    return _sync(args, dep, args.module, args.sync_command == "plan")


def _sync(args, dep, module_spec: str | None, plan_only: bool) -> int:
    """Plan or apply a sync; `module_spec` is a directory, a release zip or
    a git URL[@ref], fetched for the time of the sync."""
    import tempfile

    from catalyst import modules, sync

    with tempfile.TemporaryDirectory(prefix="catalyst-fetch-") as tmp:
        try:
            module = modules.fetch(module_spec, Path(tmp))[0] if module_spec else None
            src = sync.Sources(dep, args.kernel, module, args.base_kernel, args.cli)
        except (sync.SyncError, modules.ModuleError) as exc:
            print(f"catalyst: {exc}", file=sys.stderr)
            return 1
        return _sync_run(args, dep, src, plan_only)


def _sync_run(args, dep, src, plan_only: bool) -> int:
    from catalyst import sync
    from catalyst.corpus import load_corpus
    from catalyst.ids import resolve_signer

    try:
        commands = sync.commands_dir(dep, args.commands_dir)
        if plan_only:
            p = sync.plan(dep, src, commands)
            print(json.dumps(p.as_dict(), indent=2) if args.json else sync.render(p), end="" if not args.json else "\n")
            return 0
        signer = resolve_signer(dep, load_corpus(dep), args.as_user)
        p, touched = sync.apply(
            dep, src, commands, str(signer.get("git_username") or signer.get("name")), args.intent or []
        )
    except (sync.SyncError, IdError, JournalError) as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    finally:
        src.close()
    from catalyst import runtime as rt

    try:
        runtime, runtime_note = sync.refresh_runtime(dep), None
    except (rt.RuntimeError_, OSError, subprocess.CalledProcessError) as exc:
        runtime, runtime_note = None, f"the criterion's runtime was not refreshed ({exc}): run `catalyst open`"
    if args.json:
        print(json.dumps({**p.as_dict(), "touched": [str(t) for t in touched], "runtime": runtime}, indent=2))
    else:
        sys.stdout.write(sync.render(p, applied=True))
        if runtime:
            print(f"    update  runtime    .criterion/.venv  (catalyst {runtime})")
        print("Next: the migrations' judgment steps above, a DEPLOYMENT.md history line, then `catalyst check`.")
    if runtime_note:
        print(f"catalyst: {runtime_note}", file=sys.stderr)
    return 0


def cmd_module(args) -> int:
    """`module list|verify` (roadmap R4.9, N1): the criterion's record of its
    modules, and each module's tree against it."""
    from catalyst import modules

    dep = open_deployment(args)
    if args.module_command in ("install", "upgrade"):
        from module_loader import REPO_ROOT

        args.kernel = args.kernel or (REPO_ROOT / "framework" / "kernel")
        if not (args.kernel / "rules-of-rules.template.md").is_file() and args.kernel.suffix != ".zip":
            print("catalyst: pass --kernel <framework/kernel of a catalyst checkout or release>", file=sys.stderr)
            return 2
    if args.module_command == "install":
        from catalyst.corpus import load_corpus
        from catalyst.ids import resolve_signer

        try:
            signer = resolve_signer(dep, load_corpus(dep), args.as_user)
            done = modules.install(
                dep, args.kernel, args.source, str(signer.get("git_username") or signer.get("name")), args.intent or []
            )
        except (modules.ModuleError, IdError, JournalError) as exc:
            print(f"catalyst: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(done, indent=2))
        else:
            where = f" from {done['source']}" if done["source"] else ""
            print(f"installed module {done['id']} {done['version']}{where} ({done['files']} file(s), journaled)")
            print("Next: a DEPLOYMENT.md history line, then `catalyst check`.")
        return 0
    if args.module_command == "upgrade":
        installed = [m.id for m in dep.installed()]
        if args.id not in installed:
            print(
                f"catalyst: no module '{args.id}' here"
                + (f" (installed: {', '.join(installed)})" if installed else ": `catalyst module install` adds one"),
                file=sys.stderr,
            )
            return 1
        source = args.source
        if not source:
            recorded = next((e.get("source") for e in modules.read_record(dep.root) if e["id"] == args.id), None)
            if not recorded or not modules.is_url(recorded):
                print(
                    f"catalyst: pass the release to upgrade {args.id} to (a directory, a release zip or a git "
                    "URL[@ref]): its record names no repository to fetch from",
                    file=sys.stderr,
                )
                return 1
            source = recorded
        args.base_kernel = args.base_kernel or args.kernel  # the kernel stays: only the module moves
        return _sync(args, dep, source, args.plan)
    try:
        findings = modules.verify(dep.root, getattr(args, "id", None))
    except modules.ModuleError as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    bad = [f for f in findings if f.state in ("changed", "missing")]
    if args.json:
        print(json.dumps([f.as_dict() for f in findings], indent=2))
    elif not findings:
        print("no module installed")
    elif args.module_command == "list":
        for f in findings:
            where = f.source or ("not recorded: the next `catalyst sync apply` records it" if not f.sha256 else "?")
            print(f"{f.id} {f.version or '?'}  {where}" + (f" @ {f.commit[:12]}" if f.commit else ""))
            if f.sha256:
                print(f"    sha256 {f.sha256}")
    else:
        said = {
            "ok": "matches its record",
            "changed": "differs from its record: a file under its folder changed outside `catalyst sync`",
            "unrecorded": "not recorded (installed before the record existed): the next `catalyst sync apply` records it",
            "missing": "recorded, but its folder is gone",
        }
        for f in findings:
            print(f"{f.id} {f.version or '?'}: {said[f.state]}")
    return 1 if args.module_command == "verify" and bad else 0


def cmd_inbox(args) -> int:
    """`inbox` (roadmap R5.7): what waits for a person, read-only."""
    from catalyst import inbox
    from catalyst.corpus import load_corpus

    dep = open_deployment(args)
    found = inbox.inbox(dep, load_corpus(dep))
    print(json.dumps(found, indent=2) if args.json else inbox.render(found), end="\n" if args.json else "")
    return 0


def cmd_impact(args) -> int:
    """`impact <id>` (roadmap R5.6): what an entity rests on and what rests
    on it, read-only."""
    from catalyst import impact, views
    from catalyst.corpus import load_corpus

    dep = open_deployment(args)
    direction = "up" if args.up else "down" if args.down else "both"
    try:
        found = impact.impact(dep, load_corpus(dep), args.id, direction, args.depth)
    except views.ViewError as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(found, indent=2) if args.json else impact.render(found), end="\n" if args.json else "")
    return 0


def cmd_where(args) -> int:
    """Where the project's criterion is (roadmap R3.1): the project file, its
    name, and the criterion it resolves to — the home store, or legacy."""
    import project_file

    start = Path(os.path.abspath(args.project)) if args.project else logical_cwd()
    project = project_file.find_up(start)
    if project is None:
        print(f"catalyst: no catalyst.toml (or legacy *.catalyst pointer) at or above {start}", file=sys.stderr)
        return 1
    data = project_file.read_dir(project)
    name = project_file.project_name(data)
    criterion = project_file.resolve(project)
    home = project_file.home_criterion(name) if name else None
    kind = "home" if criterion is not None and criterion == home else "legacy" if criterion is not None else "missing"
    out = {
        "project": str(project),
        "file": project_file.find(project).name,
        "name": name,
        "criterion": str(criterion) if criterion else None,
        "kind": kind,
        "expected": str(home) if home else None,
        "workspace": project_file.workspace_of(data),
    }
    if out["workspace"]:
        out["workspace_criterion"] = str(project_file.workspace_criterion(out["workspace"]))
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"project    {out['project']} ({out['file']}, name {name})")
        print(
            f"criterion  {out['criterion'] or 'not found'} ({kind})"
            + (f" — expected {out['expected']}" if kind != "home" and out["expected"] else "")
        )
        if out["workspace"]:
            print(f"workspace  {out['workspace']} ({out['workspace_criterion']})")
    return 0 if criterion is not None else 1


def cmd_reconcile(args) -> int:
    """`reconcile <RECON-id> <verb>` (rr-META-016, INV-21): the role-gated
    decision on a reconciliation case."""
    from catalyst import edit
    from catalyst.corpus import load_corpus
    from catalyst.ids import resolve_signer

    dep = open_deployment(args)
    corpus = load_corpus(dep)
    try:
        res = edit.reconcile(
            dep,
            corpus,
            args.case,
            args.verb,
            resolve_signer(dep, corpus, args.as_user),
            args.text or "",
            args.intent or [],
        )
    except edit.EditError as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    status = (load_corpus(dep).artifacts[res.id][0].get("Status") or "").strip()
    print(f"{res.id}: {args.verb} -> {status}")
    return 0


def cmd_why(args) -> int:
    """`why <law|INV-n|meta-rule|ID>` (R4.1): a law with the invariants it
    absorbs, an invariant with its law and what enforces it, a meta-rule's
    section, or an artifact or rule (`view`)."""
    from catalyst.laws import why

    dep = open_deployment(args)
    found = why(dep.root, args.item)
    if found is not None:
        print(found)
        return 0
    from catalyst import views as v
    from catalyst.corpus import load_corpus

    try:
        sys.stdout.write(v.render_view(v.view(dep, load_corpus(dep), args.item)))
    except v.ViewError:
        print(f"catalyst: '{args.item}' is not a law, an invariant, a meta-rule or an ID here", file=sys.stderr)
        return 1
    return 0


def cmd_open(args) -> int:
    """`open` (R3.5): make the project ready on this machine and report it."""
    import project_file
    from catalyst.open import open_project

    start = Path(os.path.abspath(args.project)) if args.project else logical_cwd()
    project = project_file.find_up(start)
    if project is None:
        print(f"catalyst: no catalyst.toml (or legacy *.catalyst pointer) at or above {start}", file=sys.stderr)
        return 2
    o = open_project(project, act=True, fetch=args.fetch, agent=args.agent)
    print(json.dumps(o.as_dict(), indent=2) if args.json else o.render())
    return 0 if o.ready else 1


def cmd_mcp(args) -> int:
    """`mcp`: the stdio MCP server agents register at user level (R3.1c)."""
    from catalyst import mcp

    start = Path(os.path.abspath(args.project)) if args.project else logical_cwd()
    return mcp.run(start)


def cmd_agent(args) -> int:
    """`agent install|uninstall|status`: catalyst in an agent, at user level (R3.1c)."""
    from catalyst import agents

    try:
        if args.agent_command == "status":
            rows = agents.status()
            if args.json:
                print(json.dumps(rows, indent=2))
            else:
                for row in rows:
                    parts = ", ".join(
                        f"{k} {'yes' if v else 'unknown' if v is None else 'no'}" for k, v in row["parts"].items()
                    )
                    print(f"{row['agent']:<12} {'installed' if row['installed'] else '-':<10} {parts}")
            return 0
        print("\n".join(agents.run(args.agent, install=args.agent_command == "install")))
        return 0
    except agents.AgentError as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1


def cmd_agent_run(args) -> int:
    """`agent run <command> [args]` (R5.5): the command's procedure sent to the
    project's agent from the project's root; its events streamed, then what
    it cost. Exit 0 when the agent says it succeeded, 1 when not, 2 when it
    could not start."""
    import project_file
    from catalyst import run as runs
    from catalyst.spec import SpecError, load_section4, procedure

    dep = open_deployment(args)
    agent = args.agent or project_file.agent_of(project_file.read_dir(dep.project_root))
    rest = list(args.arguments)
    if "--json" in rest:  # given after the arguments: still catalyst's own flag
        rest.remove("--json")
        args.json = True
    arguments = " ".join(rest)
    try:
        prompt = procedure(load_section4(dep), args.command, arguments, dep.project_root)
        adapter = runs.adapter_for(agent)
    except (SpecError, runs.RunError) as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 2

    def show(event: dict) -> None:
        if args.json:
            print(json.dumps(event, ensure_ascii=False), flush=True)
        elif (line := runs.render(event)) is not None:
            print(line, flush=True)

    end = runs.run(adapter, agent, args.command, arguments, prompt, dep.project_root, show)
    runs.record(dep.project_root, git_actor(dep.project_root), agent, args.command, arguments, end)
    return 0 if end["ok"] else 1


def git_actor(project: Path) -> str:
    """Who runs: the project's `git config user.name`, else the system user."""
    import getpass

    name = proc.git(str(project), "config", "user.name").stdout.strip()
    return name or getpass.getuser()


def cmd_agent_runs(args) -> int:
    """`agent runs [--limit N] [--json]`: this user's logged runs for the
    project, with what each cost (`agent run` writes them)."""
    from catalyst import run as runs

    dep = open_deployment(args)
    items = runs.runs(dep.project_root, args.limit)
    if args.json:
        print(json.dumps(items, indent=2, ensure_ascii=False))
        return 0
    total = 0.0
    for r in items:
        cost = r.get("cost_usd")
        total += cost if isinstance(cost, (int, float)) else 0.0
        u = r.get("usage") or {}
        print(
            f"{r.get('timestamp')}  {'ok    ' if r.get('ok') else 'FAILED'}  /{r.get('command')} {r.get('arguments') or ''}".rstrip()
            + f"  ({u.get('input', 0)} in, {u.get('output', 0)} out"
            + (f", ${cost:.4f})" if isinstance(cost, (int, float)) else ")")
        )
    print(f"catalyst: {len(items)} run(s), ${total:.4f} in all")
    return 0


AGENT_BINARIES = {"claude-code": "claude"}  # an agent id whose CLI binary has another name


def cmd_task(args) -> int:
    """`task <name> [-- args]`: run one of the criterion's Taskfile.common.yml
    tasks from the project's root. catalyst never touches the project's own
    Taskfile; its tasks are reached through this verb (or `task -t`)."""
    import shutil

    import project_file

    start = Path(os.path.abspath(args.project)) if args.project else logical_cwd()
    project = project_file.find_up(start)
    criterion = project_file.resolve(project) if project else None
    taskfile = criterion / "Taskfile.common.yml" if criterion else None
    if taskfile is None or not taskfile.is_file():
        print(f"catalyst: no criterion Taskfile.common.yml for {start}", file=sys.stderr)
        return 1
    binary = shutil.which("task")
    if binary is None:
        print("catalyst: Task (https://taskfile.dev) is not on PATH", file=sys.stderr)
        return 1
    agent = project_file.agent_of(project_file.read_dir(project))
    agent_cmd = os.environ.get("AGENT_CMD") or f"{AGENT_BINARIES.get(agent, agent)} -p"
    rest = args.task_args[1:] if args.task_args[:1] == ["--"] else args.task_args
    command = [binary, "-t", str(taskfile)]
    command += [args.name, f"AGENT_CMD={agent_cmd}", *(["--", *rest] if rest else [])] if args.name else ["--list"]
    return subprocess.run(command, cwd=project, check=False).returncode


def cmd_runtime(args) -> int:
    """`runtime install|status` (R3.1a): the per-version runtime, the
    launcher, and the project's criterion .venv."""
    import tempfile

    import project_file
    from catalyst import runtime as rt, version_string

    version = version_string()
    start = Path(os.path.abspath(args.project)) if args.project else logical_cwd()
    project = project_file.find_up(start)
    criterion = project_file.resolve(project) if project else None
    name = project_file.project_name(project_file.read_dir(project)) if project else None
    home_store = criterion is not None and name is not None and criterion == project_file.home_criterion(name)
    if args.runtime_command == "status":
        out = {
            "version": version,
            "home": str(project_file.home()),
            "runtimes": sorted(p.name for p in rt.runtimes().glob("*") if (p / rt.MARKER).is_file()),
            "launcher": str(project_file.home() / "bin" / "catalyst"),
            "launcher_installed": (project_file.home() / "bin" / "catalyst").is_file(),
            "criterion": str(criterion) if criterion else None,
            "criterion_runtime": rt.installed_version(criterion / ".venv") if criterion else None,
        }
        print(json.dumps(out, indent=2) if args.json else "\n".join(f"{k:<20}{v}" for k, v in out.items()))
        return 0
    try:
        with tempfile.TemporaryDirectory() as tmp:
            pyz = rt.own_pyz(Path(tmp))
            version = rt.pyz_version(pyz)  # a build from source is not its release
            runtime_dir = rt.ensure_runtime(version, pyz)
            launcher = rt.install_launcher()
            lines = [f"runtime {version}: {runtime_dir}", f"launcher: {launcher} (put {launcher.parent} on PATH)"]
            if home_store:
                venv, changed = rt.install_into(criterion, version, pyz)
                lines.append(f"criterion runtime: {venv} ({'installed' if changed else 'already ' + version})")
            elif criterion is not None:
                lines.append("legacy deployment (.criterion in the project): no .venv; `catalyst move --to-home` first")
    except (rt.RuntimeError_, OSError, subprocess.CalledProcessError) as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    print("\n".join(lines))
    return 0


def cmd_move(args) -> int:
    """`move --to-home | --name <new>` (R2 W5): legacy deployment to the home
    store, or rename a project."""
    import project_file
    from catalyst import move

    start = Path(os.path.abspath(args.project)) if args.project else logical_cwd()
    project = project_file.find_up(start)
    if project is None:
        print(f"catalyst: no catalyst.toml (or legacy *.catalyst pointer) at or above {start}", file=sys.stderr)
        return 1
    try:
        if args.name:
            _, steps = move.rename(project, args.name, actor=args.as_user)
        else:
            _, steps = move.to_home(project, runtime=not args.no_runtime, actor=args.as_user)
    except (move.MoveError, JournalError, OSError) as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    for step in steps:
        print(f"- {step}")
    return 0


def cmd_workspace(args) -> int:
    """`workspace init|status` (R3.1b): a VS Code workspace's meta criterion."""
    from catalyst import workspace as ws
    from catalyst.init import git_user_name
    from module_loader import REPO_ROOT

    path = Path(os.path.abspath(args.file))
    try:
        if args.workspace_command == "init":
            kernel = args.kernel or (REPO_ROOT / "framework" / "kernel")
            user = args.user or git_user_name(path.parent)
            if not user:
                print("catalyst: pass --user <name> (git config user.name is not set)", file=sys.stderr)
                return 2
            _, steps = ws.init(path, kernel, user, args.git_username)
            for step in steps:
                print(f"- {step}")
            return 0
        out = ws.status(path)
    except (ws.WorkspaceError, JournalError) as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"workspace  {out['workspace']}  ({out['criterion'] or 'no criterion yet: catalyst workspace init'})")
        for row in out["folders"]:
            mark = "member" if row["member"] else ("project, not a member" if row["project"] else "no catalyst")
            print(f"  {row['folder']}  {row['project'] or ''}  [{mark}]")
    return 0


def cmd_report(args) -> int:
    from catalyst.report import build, render

    r = build(open_deployment(args), args.since)
    if args.json:
        json.dump(r, sys.stdout, indent=2)
        print()
    else:
        sys.stdout.write(render(r))
    return 0


def cmd_trace(args) -> int:
    from catalyst import unrecorded
    from catalyst.corpus import load_corpus
    from catalyst.trace import trace

    dep, corpus, repo = None, None, Path(os.path.abspath(args.project)) if args.project else Path.cwd()
    if not args.pattern_only:
        dep = open_deployment(args)
        corpus, repo = load_corpus(dep), dep.project_root
    try:
        from catalyst.tiers import commit_prefixes

        checked, failures = trace(
            repo, args.range, corpus, scoped=dep is not None and not dep.standalone, prefixes=commit_prefixes(dep)
        )
        manual, lvl = [], "warning"
        if corpus is not None and not dep.standalone and unrecorded.baseline_missing(dep):
            print(f"WARNING unrecorded-change: {unrecorded.MISSING_BASELINE}")
        elif corpus is not None and not dep.standalone and unrecorded.baseline(dep) is not None:
            pairs, lvl = unrecorded.recorded(dep), unrecorded.level(dep)
            for c in unrecorded.commits(repo, unrecorded.scoped(dep, [args.range])):
                missing = unrecorded.unrecorded_in(c, pairs)
                if missing:
                    manual.append(unrecorded.Commit(c.sha, c.author, c.subject, missing))
    except ValueError as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    for f in failures:
        print(f"ERROR   {f.sha} {f.subject[:60]!r}: {f.reason}")
    for c in manual:
        print(f"{'ERROR  ' if lvl == 'error' else 'WARNING'} unrecorded-change: {unrecorded.describe(c)}")
    failed = bool(failures) or (lvl == "error" and bool(manual))
    print(
        f"catalyst trace {'FAILED' if failed else 'passed'}: {checked} commit(s) checked, "
        f"{len(failures)} without a trace"
        + (" (pattern only)" if corpus is None else f", {len(manual)} with unrecorded changes")
    )
    return 1 if failed else 0


def cmd_unrecorded(args) -> int:
    from catalyst import unrecorded

    dep = open_deployment(args)
    if dep.standalone:
        print("catalyst: a standalone working copy has no product history", file=sys.stderr)
        return 1
    if unrecorded.baseline(dep) is None and not args.range:
        print(
            f"catalyst: the pointer declares no `{unrecorded.BASELINE_KEY}` (migration 0.42.0); "
            "pass a range to check one",
            file=sys.stderr,
        )
        return 1
    if unrecorded.baseline_missing(dep):
        print(f"catalyst: {unrecorded.MISSING_BASELINE}", file=sys.stderr)
        return 1
    try:
        pairs = unrecorded.recorded(dep)
        revs = unrecorded.scoped(dep, [args.range or "HEAD"])
        found = [
            unrecorded.Commit(c.sha, c.author, c.subject, m)
            for c in unrecorded.commits(dep.project_root, revs)
            if (m := unrecorded.unrecorded_in(c, pairs))
        ]
    except ValueError as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    if args.json:
        json.dump(
            [
                {
                    "commit": c.sha,
                    "author": c.author,
                    "subject": c.subject,
                    "files": [{"path": p, "before": b, "after": a} for p, b, a in c.changes],
                }
                for c in found
            ],
            sys.stdout,
            indent=2,
        )
        print()
    else:
        for c in found:
            print(unrecorded.describe(c))
        print(f"{len(found)} commit(s) with changes not in the journal (checked as {unrecorded.level(dep)}s)")
    return 1 if found and unrecorded.level(dep) == "error" else 0


def cmd_hook(args) -> int:
    from catalyst.check import hook_stop

    if args.hook_command == "commit-msg" and args.route:
        from catalyst.trace import route

        top = Path(os.path.abspath(args.project)) if args.project else Path.cwd()
        return route(top, Path(os.path.abspath(args.message_file)), [sys.executable, sys.argv[0]])
    if args.hook_command == "commit-msg":
        from catalyst.corpus import load_corpus
        from catalyst.trace import check_message

        try:
            hook_dep = open_deployment(args)
            corpus = load_corpus(hook_dep)
        except DeploymentNotFound:
            return 0
        git_dir = subprocess.run(
            ["git", "rev-parse", "--absolute-git-dir"], check=False, capture_output=True, text=True, encoding="utf-8"
        )
        if git_dir.returncode == 0 and (Path(git_dir.stdout.strip()) / "MERGE_HEAD").exists():
            return 0  # a merge carries its parents' trace (as in `trace`)
        from catalyst.tiers import commit_prefixes

        reason = check_message(Path(args.message_file).read_text(encoding="utf-8"), corpus, commit_prefixes(hook_dep))
        if not reason:
            from catalyst import unrecorded

            dep = open_deployment(args)
            missing = unrecorded.staged(dep) if unrecorded.baseline(dep) is not None else []
            if missing:
                paths = ", ".join(p for p, _, _ in missing[:5]) + (" ..." if len(missing) > 5 else "")
                advice = (
                    "Journal them first (`catalyst journal append --file <path>`), or record the "
                    "commit afterwards with `catalyst journal adopt HEAD`."
                )
                if unrecorded.level(dep) == "error":
                    print(
                        f"catalyst: commit refused — {len(missing)} staged file(s) not recorded in the "
                        f"journal: {paths}.\n{advice} Bypass once: git commit --no-verify.",
                        file=sys.stderr,
                    )
                    return 1
                print(
                    f"catalyst: warning — {len(missing)} staged file(s) not recorded in the journal: "
                    f"{paths}.\n{advice} (A warning during the beta; from format 1.0 this refuses "
                    "the commit.)",
                    file=sys.stderr,
                )
        if reason:
            print(
                f"catalyst: commit refused — {reason}.\nCite the artifact or rule this commit serves "
                "(e.g. <PREFIX>-000012 or its full ID), or start the subject with `chore:` "
                "if no rule's behaviour changes. Bypass once: git commit --no-verify.",
                file=sys.stderr,
            )
            return 1
        return 0
    if args.hook_command == "install":
        from catalyst.trace import install_hook

        try:
            print(f"installed {install_hook(open_deployment(args).project_root)}")
        except ValueError as exc:
            print(f"catalyst: {exc}", file=sys.stderr)
            return 1
        return 0

    # Fail closed: Claude Code ignores every exit but 2, so a crash here must
    # block the stop (with its reason) instead of switching enforcement off.
    from catalyst.check import hook_block, hook_input

    try:
        data = hook_input()
        try:
            dep = open_deployment(_hook_project(args, data))
        except WorkingCopyMissing as exc:
            return hook_block(f"catalyst: {exc}", args.format)
        except DeploymentNotFound:
            return 0
        return hook_stop(dep, data, strict=args.strict, fmt=args.format)
    except Exception as exc:
        return hook_block(f"catalyst hook stop crashed — {type(exc).__name__}: {exc}", args.format)


def _hook_project(args, data: dict):
    """The project a hook runs for: --project, else the directory the agent
    names in the hook's input (`cwd`; Cursor's `workspace_roots`), else ours."""
    if args.project or getattr(args, "working_copy", None):
        return args
    roots = data.get("workspace_roots")
    named = data.get("cwd") or (roots[0] if isinstance(roots, list) and roots else None)
    if isinstance(named, str) and named:
        args.project = Path(named)
    return args


NEEDS_ASSENT = 3  # exit code: nothing done, the user's assent is needed (INV-4)


def _assented(args, what: str) -> bool:
    """INV-4: never push without the user's assent. `--yes` carries it; an
    interactive terminal asks; anywhere else (an agent, CI) the preview is
    printed and nothing happens — the agent shows it to the user and re-runs
    with --yes once they agree."""
    if getattr(args, "yes", False):
        return True
    print(what)
    if sys.stdin.isatty():
        return input("Publish? [y/N] ").strip().lower() in ("y", "yes")
    print(
        "catalyst: publishing needs the user's assent (INV-4): show them the above, then re-run with --yes",
        file=sys.stderr,
    )
    return False


def _ask_url(exc) -> str:
    """Ask for the criterion repository's URL on an interactive terminal;
    elsewhere (an agent, CI) the error stands and names --url."""
    if not sys.stdin.isatty():
        raise exc
    print(f"catalyst: {exc}", file=sys.stderr)
    url = input("publish the criterion to which repository URL? (empty to stay local): ").strip()
    if not url:
        from catalyst.criterion import CriterionError

        raise CriterionError("no URL given: nothing changed, the deployment stays local")
    return url


def cmd_analysis(args) -> int:
    from catalyst import analysis as an, journal
    from catalyst.corpus import load_corpus
    from catalyst.ids import resolve_signer

    dep = open_deployment(args)
    corpus = load_corpus(dep)
    sub = args.analysis_command

    def signer():
        return resolve_signer(dep, corpus, getattr(args, "as_user", None))

    def journaled(ctx, action: str, intent: str, who: dict) -> None:
        journal.append(
            dep,
            journal.AppendRequest(
                command=f"catalyst analysis {sub}",
                action=action,
                artifact=ctx.art.id,
                targets=[],
                intent=[intent],
                files=[str(f) for f in an.files_of(ctx)],
                actor=str(who.get("git_username") or who.get("name")),
                allow_unchanged=True,
            ),
        )

    def read_json(path: str):
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise an.AnalysisError(f"cannot read {path}: {exc}") from exc

    if sub == "start":
        who = signer()
        ctx = an.start(dep, args.scope, args.mode, who, args.name)
        journaled(ctx, "create", f"{args.mode} analysis of {' '.join(ctx.load('inventory.json')['scope'])}", who)
        inv = ctx.load("inventory.json")
        print(
            f"{ctx.art.id}: {len(inv['files'])} file(s) at {inv['code_state'][:10]}; "
            f"record two independent passes with `catalyst analysis record {ctx.art.id} --pass A|B <file>`"
        )
        return 0
    ctx = an.context(dep, args.id, corpus)
    if sub == "status":
        d, r = ctx.load("diff.json"), ctx.load("reconciled.json")
        decided = (ctx.load("decisions.json") or {}).get("decisions", {})
        print(f"{ctx.art.id}: {an.phase(ctx.art)} ({ctx.art.get('Mode')}; {ctx.art.get('Scope')})")
        print(
            f"passes:    A {'recorded' if ctx.load('A.json') else '—'}, B {'recorded' if ctx.load('B.json') else '—'}"
        )
        if d:
            print(
                f"diff:      {len(d['agreed'])} agreed, {len(d['conflicting'])} conflicting, "
                f"{len(d['a_only'])} A-only, {len(d['b_only'])} B-only"
            )
        if r:
            print(f"decisions: {len(decided)}/{len(r['findings'])} findings decided")
        for problem in an.problems(ctx):
            print(f"PROBLEM   {problem}")
        return 0
    who = signer()
    if sub == "record":
        for w in an.record(ctx, args.which, read_json(args.file), replace=args.replace):
            print(f"WARNING   {w}")
        journaled(ctx, "update", f"pass {args.which.upper()} recorded", who)
        print(f"pass {args.which.upper()} recorded for {ctx.art.id}")
        return 0
    if sub == "diff":
        d = an.run_diff(ctx)
        journaled(an.context(dep, ctx.art.id), "update", "passes matched for reconciliation", who)
        print(
            f"{len(d['agreed'])} agreed, {len(d['conflicting'])} conflicting, {len(d['a_only'])} A-only, "
            f"{len(d['b_only'])} B-only — reconcile every one (`catalyst analysis reconcile`)"
        )
        return 0
    if sub == "reconcile":
        an.reconcile(ctx, read_json(args.file))
        journaled(an.context(dep, ctx.art.id), "update", "reconciled list accepted: every finding accounted for", who)
        n = len(an.context(dep, ctx.art.id).load("reconciled.json")["findings"])
        print(f"{n} reconciled finding(s): each needs the user's decision (`catalyst analysis decide`)")
        return 0
    if sub == "decide":
        an.decide(ctx, args.finding, args.verdict, who, args.artifact, args.reason)
        journaled(
            ctx,
            "update",
            f"finding {args.finding}: {args.verdict}" + (f" as {args.artifact}" if args.artifact else ""),
            who,
        )
        print(f"{args.finding}: {args.verdict}" + (f" → {args.artifact}" if args.artifact else ""))
        return 0
    if sub == "close":
        counts = an.close(ctx)
        journaled(an.context(dep, ctx.art.id), "close", "every finding decided; accepted ones exist", who)
        print(
            f"{ctx.art.id} closed: "
            + (
                ", ".join(f"{k} {c['accept']}/{c['accept'] + c['reject']} accepted" for k, c in sorted(counts.items()))
                or "no findings"
            )
        )
        return 0
    an.abandon(ctx, args.reason)
    journaled(an.context(dep, ctx.art.id), "close", f"abandoned: {args.reason}", who)
    print(f"{ctx.art.id} abandoned")
    return 0


def cmd_criterion(args) -> int:
    from catalyst import criterion as cr

    sub = args.criterion_command
    if sub == "join":
        start = Path(os.path.abspath(args.project)) if args.project else Path.cwd()
        import project_file

        project = project_file.find_up(start)
        if project is None:
            raise DeploymentNotFound(f"no catalyst.toml (or legacy *.catalyst pointer) at or above {start}")
        try:
            head = cr.join(project, args.url)
        except cr.NeedsURL as exc:
            head = cr.join(project, _ask_url(exc))
        print(f"joined: .criterion at {head}")
        if cr.is_submodule(project):
            print("Commit the product repository's staged changes (if any) when ready.")
        return 0
    dep = open_deployment(args)
    if sub == "status":
        st = cr.status(dep, fetch=args.fetch)
        print(
            f"mode:     {st.mode}\nremote:   {st.remote or '(none)'}\nshared:   {st.branch}\n"
            f"branch:   {st.current or '(detached)'}\nchanges:  {len(st.dirty)} uncommitted"
        )
        if st.ahead is not None:
            print(f"vs shared: {st.ahead} ahead, {st.behind} behind")
        return 0
    if sub == "create":
        if args.url and not _assented(args, f"publish this criterion to {args.url} (shared branch {args.branch})"):
            return NEEDS_ASSENT
        for note in cr.create(dep, args.url, args.branch, cr.CI_TEMPLATE):
            print(f"- {note}")
        print("Commit the product repository's staged changes when ready.")
        return 0
    if sub in ("push", "sync"):
        # a local-only deployment is published first, to the URL given or asked for
        url, typed = args.url, False
        while True:
            try:
                publishing = url and not cr.remote_url(dep.root)
                if publishing and not typed and not _assented(args, f"publish this criterion to {url}"):
                    return NEEDS_ASSENT
                dep, published = cr.ensure_remote(dep, url)
                break
            except cr.NeedsURL as exc:
                url, typed = _ask_url(exc), True  # typed at the prompt: the user's assent
        for note in published:
            print(f"- {note}")
        if published:
            print("Published: commit the product repository's staged changes when ready.")
    if sub == "push":
        from catalyst.corpus import load_corpus
        from catalyst.ids import resolve_signer

        signer = resolve_signer(dep, load_corpus(dep), args.as_user)
        pv = cr.preview(dep)
        if pv.empty:
            print(pv.describe())
            return 0
        if not _assented(args, pv.describe()):
            return NEEDS_ASSENT
        res = cr.push(dep, signer, args.message, open_pr=not args.no_pr)
        if res.commits == 0:
            print("nothing to push: the working copy matches the shared branch")
            return 0
        print(
            f"pushed {res.commits} commit(s) to {res.branch}"
            + (f" (regenerated {', '.join(res.regenerated)})" if res.regenerated else "")
        )
        print(
            f"pull request: {res.pr}"
            if res.pr
            else f"open a pull request from {res.branch} into {cr.shared_branch(dep)}"
            + (f" ({res.pr_note})" if res.pr_note else "")
        )
        return 0
    if sub == "sync":
        print(f"working copy at {cr.sync(dep)} (shared branch {cr.shared_branch(dep)})")
        if not dep.standalone and cr.is_submodule(dep.project_root):
            print("the product repository's .criterion pointer moved: commit it to pin these rules")
        return 0
    if sub == "integrity":
        problems = cr.integrity(dep.root, args.head, args.parent or None)
        for p in problems:
            print(f"ERROR   {p}")
        print(f"catalyst criterion integrity {'FAILED' if problems else 'passed'}: {len(problems)} missing")
        return 1 if problems else 0
    print(cr.protect(dep, apply=args.yes))
    return 0


def cmd_share(args) -> int:
    """The criterion's sharing driver, whichever it is (roadmaps R3.2, R3.6)."""
    from catalyst import store

    if args.share_command == "join":
        import project_file

        start = Path(os.path.abspath(args.project)) if args.project else Path.cwd()
        project = project_file.find_up(start)
        if project is None:
            raise DeploymentNotFound(f"no catalyst.toml (or legacy *.catalyst pointer) at or above {start}")
        print(f"joined: the criterion is at {store.join(project, args.url)} (catalyst where)")
        return 0
    if args.share_command == "login":
        from catalyst import serve

        token = args.token or sys.stdin.readline().strip()
        if not token:
            raise SystemExit("catalyst: no token given (--token, or one line on stdin)")
        print(f"token for {args.url} saved in {serve.save_token(args.url, token)}")
        return 0
    dep = open_deployment(args)
    if args.share_command == "create":
        where = args.url if args.driver == "serve" else f"{args.url} (shared branch {args.branch})"
        if not _assented(args, f"publish this criterion to {where}"):
            return NEEDS_ASSENT
        if args.driver == "serve":
            from catalyst import serve
            from catalyst.corpus import load_corpus
            from catalyst.ids import resolve_signer

            notes = serve.create(dep, args.url, resolve_signer(dep, load_corpus(dep), args.as_user))
        else:
            notes = store.create(dep, args.url, args.branch, protect=args.protect)
        for note in notes:
            print(f"- {note}")
        return 0
    share = store.share_for(dep)
    if args.share_command == "info":
        info = share.info()
        if args.json:
            print(json.dumps(info, indent=2))
        else:
            print(f"driver:   {info['driver']}\nlocation: {info.get('location') or '(not shared)'}")
            if info.get("branch"):
                print(f"branch:   {info['branch']}")
            print(f"can:      {', '.join(info['capabilities']) or '(nothing: local only)'}")
        return 0
    if args.share_command == "status":
        st = share.status(fetch=args.fetch)
        if args.json:
            print(json.dumps(st.as_dict(), indent=2))
            return 0
        print(f"driver:   {st.driver}" + (f" ({st.mode})" if st.mode else ""))
        print(f"location: {st.location or '(not shared)'}")
        if st.branch:
            print(f"branch:   {st.branch}")
        print(f"changes:  {len(st.dirty)} not published")
        if st.ahead is not None:
            print(f"vs shared: {st.ahead} ahead, {st.behind} behind")
        return 0
    if args.share_command == "pull":
        print(f"criterion at {share.pull()} ({share.driver})")
        return 0
    from catalyst.corpus import load_corpus
    from catalyst.ids import resolve_signer

    signer = resolve_signer(dep, load_corpus(dep), args.as_user)
    pv = share.preview()
    if pv.empty:
        print(pv.describe())
        return 0
    if not _assented(args, pv.describe()):
        return NEEDS_ASSENT
    res = share.push(signer, args.message, open_pr=not args.no_pr)
    if args.json:
        print(json.dumps(res, indent=2))
    elif not res["commits"]:
        print("nothing to publish: the criterion matches its shared copy")
    elif res.get("seq") is not None:
        print(f"published {res['commits']} file(s) as batch {res['seq']} ({share.driver})")
    else:
        print(f"published {res['commits']} commit(s) on {res['branch']} ({share.driver})")
        if res.get("pull_request"):
            print(f"pull request: {res['pull_request']}")
        elif not args.no_pr:
            why = res.get("pull_request_note")
            print(
                f"no pull request was opened{f' ({why})' if why else ''}: open one from {res['branch']} into "
                f"{share.info().get('branch')}, or run `catalyst share push` again"
            )
    return 0


def cmd_serve(args) -> int:
    """`catalyst serve` (roadmap R3.9): run the server, or manage its tokens
    on the server's host."""
    from catalyst import serve

    db = Path(args.db) if args.db else serve.default_db()
    if args.serve_command == "token":
        app = serve.Server(db)
        if args.action == "list":
            for t in app.tokens():
                print(
                    f"{t['id']:>4}  {t['userid']}  issued {t['created']}"
                    + (f"  revoked {t['revoked']}" if t["revoked"] else "")
                )
            return 0
        if not args.who:
            raise SystemExit(
                f"catalyst: serve token {args.action} needs {'a userid' if args.action == 'issue' else 'a token number'}"
            )
        if args.action == "issue":
            number, token = app.issue(args.who)
            print(f"token {number} for {args.who} (shown once; give it to them for `catalyst share login`):\n{token}")
            return 0
        if not args.who.isdigit() or not app.revoke(int(args.who)):
            raise SystemExit(f"catalyst: no active token {args.who}")
        print(f"token {args.who} revoked")
        return 0
    if args.static and not args.local:
        raise SystemExit("catalyst: --static goes with --local: a page is served beside one project's criterion")
    if args.local:
        if args.host != "127.0.0.1":
            raise SystemExit("catalyst: serve --local listens on 127.0.0.1 only")
        project = Path(os.path.abspath(args.project)) if args.project else Path.cwd()
        try:
            server, token = serve.make_local(project, args.port or 0, static=args.static)
        except serve.ServeError as exc:
            raise SystemExit(f"catalyst: {exc}") from None
        url = f"http://127.0.0.1:{server.server_address[1]}"
        line = serve.start_line(url, token, os.getpid(), args.static is not None)
        print(json.dumps(line), flush=True)  # the client reads this line
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    server = serve.make_server(db, args.host, args.port or 8765)
    print(f"catalyst serve: {db} on http://{args.host}:{server.server_address[1]} (Ctrl-C stops it)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def cmd_init(args) -> int:
    from catalyst.init import InitError, InitRequest, git_user_name, init, local_modules
    from module_loader import REPO_ROOT

    kernel = args.kernel or (REPO_ROOT / "framework" / "kernel")
    if not (kernel / "rules-of-rules.template.md").is_file():
        print("catalyst: pass --kernel <framework/kernel of a catalyst checkout or release>", file=sys.stderr)
        return 2
    project = Path(os.path.abspath(args.project)) if args.project else Path.cwd()
    if args.module and args.no_module:
        print("catalyst: --module and --no-module exclude each other", file=sys.stderr)
        return 2
    if not args.module and not args.no_module:  # never chosen for the user: list what is here
        found = local_modules(project)
        listing = "; ".join(f"{m} ({d})" for m, d in found.items()) or "none next to the project or catalyst"
        print(
            f"catalyst: pass --module <id> (and --module-dir if it is elsewhere), or --no-module to install one "
            f"later with `catalyst module install`. Found: {listing}",
            file=sys.stderr,
        )
        return 2
    user = args.user or git_user_name(project)
    if not user:
        print("catalyst: pass --user <name> (git config user.name is not set)", file=sys.stderr)
        return 2
    docs = []
    for spec in args.rule_doc or []:
        doc, _, prefix = spec.partition(":")
        docs.append((doc if doc.endswith(".md") else doc + ".md", prefix or "br"))
    try:
        steps = init(
            InitRequest(
                project=project,
                name=args.name,
                module_id=args.module or None,
                user=user,
                kernel=kernel,
                module=args.module_dir,
                git_username=args.git_username or user,
                rule_docs=docs,
                test_locations=args.test_locations,
                at=args.at,
                agent=args.agent,
                userid=args.userid,
                runtime=not args.no_runtime,
            )
        )
    except InitError as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    for step in steps:
        print(f"- {step}")
    print(
        "Next: `catalyst agent install <agent>` once per machine, then the first rules (catalyst id next-rule) "
        "and `catalyst check`. Nothing was committed in the project repository."
    )
    return 0


def cmd_hook_start(args) -> int:
    """SessionStart hook: where the project stands (`catalyst open`, changing
    nothing), then the deployment's invariants (kernel, then module), so
    every session starts grounded. Never blocks a session."""
    import project_file
    from catalyst.check import hook_input
    from catalyst.open import open_project

    data = hook_input() if args.format != "text" or args.quiet else {}
    args = _hook_project(args, data)
    start = Path(os.path.abspath(args.project)) if args.project else logical_cwd()
    project = project_file.find_up(start)
    if project is None:
        return 0
    try:
        report = open_project(project, act=False).render()
    except Exception as exc:  # a session must start whatever happens here
        report = f"catalyst: could not read the project's state ({exc})"
    try:
        dep = open_deployment(args)
    except (WorkingCopyMissing, DeploymentNotFound):
        text = report
    else:
        from catalyst.check import record_baseline, run, session_of
        from catalyst.laws import session_brief

        text = "\n".join([report, session_brief(dep.root)])
        session = session_of(data)
        if session is not None:  # ADR-002: the Stop hook blocks on what this session breaks
            try:
                record_baseline(dep, session, run(dep))
            except Exception as exc:  # a session must start whatever happens here
                print(f"catalyst: no baseline recorded for this session ({exc})", file=sys.stderr)
    if args.quiet:
        return 0
    if args.format == "text":
        print(text)
    elif args.format == "cursor":
        print(json.dumps({"additional_context": text}))
    else:  # Codex, Copilot (CLI and VS Code), Gemini CLI, Claude Code
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}))
    return 0


def cmd_spec(args) -> int:
    from catalyst.spec import SpecError, catalogue, commands, general, load_section4, parts, spec

    dep = open_deployment(args)
    try:
        if getattr(args, "json", False) and args.budget is None and not args.general:
            if not args.command:
                print(json.dumps({"commands": catalogue(load_section4(dep))}, indent=2))
            else:
                text = spec(dep, args.command, args.part)
                print(json.dumps({"command": args.command.lstrip("/"), "part": args.part, "text": text}, indent=2))
            return 0
        if args.budget is not None:
            measured = [*commands(dep), *parts(dep)]  # a command with parts is read one part at a time
            over = [(len(spec(dep, c).split()), c) for c in measured]
            over = sorted(o for o in over if o[0] > args.budget)
            for words, c in over:
                print(f"ERROR   /{c}: {words} words (budget {args.budget})")
            print(
                f"catalyst spec budget {'FAILED' if over else 'passed'}: "
                f"{len(measured)} commands and parts, budget {args.budget} words each"
            )
            return 1 if over else 0
        if args.general:
            sys.stdout.write(general(dep))
            return 0
        if not args.command:
            print("\n".join(f"/{c}" for c in commands(dep)))
            return 0
        sys.stdout.write(spec(dep, args.command, args.part))
        return 0
    except SpecError as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1


def cmd_recompose(args) -> int:
    from catalyst.compose import deployed_params, recompose

    dep = open_deployment(args)
    if dep.module is None:
        print("catalyst: the deployment has no active module", file=sys.stderr)
        return 1
    params = deployed_params(dep.root, dep.module.id)
    new_module = args.module_dir or dep.module.path or dep.root / "modules" / dep.module.id
    base_modules, new_modules = args.base_module, new_module
    if len(dep.installed()) > 1:
        # several modules: the two directories stand for the one module they
        # name (the first when they name none); the others are as deployed
        from catalyst import modules

        try:
            named = modules.identity(args.base_module)["id"]
        except modules.ModuleError:
            named = dep.module.id
        if named not in [m.id for m in dep.installed()]:
            named = dep.module.id
        deployed = {m.id: dep.root / "modules" / m.id for m in dep.installed()}
        base_modules = [args.base_module if i == named else d for i, d in deployed.items()]
        new_modules = [new_module if i == named else d for i, d in deployed.items()]
    try:
        results = recompose(
            dep.root,
            params,
            (args.base_kernel, base_modules),
            (args.kernel, new_modules),
            write=not args.check,
            force=args.force,
        )
    except RuntimeError as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    for r in results:
        state = (
            "frozen, skipped"
            if r.frozen
            else f"{r.conflicts} conflict(s)"
            if r.conflicts
            else ("merged" if r.changed else "unchanged")
        )
        print(f"{'would update' if args.check and r.changed else state:>14}  .criterion/{r.path}")
    conflicts = sum(r.conflicts for r in results)
    if conflicts:
        print(f"{conflicts} conflict(s) left marked (<<<<<<<) for a human or agent to resolve")
    return 1 if conflicts or (args.check and any(r.changed for r in results)) else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="catalyst", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"catalyst {version_string()}")
    parser.add_argument(
        "--project", type=Path, default=None, help="a directory inside the project (default: current directory)"
    )
    parser.add_argument(
        "--working-copy",
        type=Path,
        default=None,
        help="check a bare working copy (e.g. the criterion repository in CI)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="validate the traceability chain against the ETDs")
    p.add_argument("--strict", action="store_true", help="treat warnings as errors")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("init", help="install catalyst into this project (explicit only, INV-2)")
    p.add_argument("--name", required=True, help="the project name (the pointer is <name>.catalyst)")
    p.add_argument(
        "--module", help="the active process module id (no default: without it, init lists the modules it finds)"
    )
    p.add_argument("--user", help="the first user's name, who becomes Admin (default: git config user.name)")
    p.add_argument("--git-username", help="the first user's git username (default: --user)")
    p.add_argument(
        "--rule-doc",
        action="append",
        metavar="FILE:PREFIX",
        help="a rule document and its ID prefix, e.g. business-rules:br (repeatable)",
    )
    p.add_argument("--test-locations", help="where the project's tests live (Rules-of-Rules §2)")
    p.add_argument(
        "--at",
        type=Path,
        help="legacy: an agent-owned location reached through a .criterion "
        "symlink (default, ADR-010: $HOME/.catalyst/projects/<name>/criterion, nothing in the project)",
    )
    p.add_argument(
        "--no-runtime",
        action="store_true",
        help="do not fill the criterion's .venv now (`catalyst runtime install` later)",
    )
    p.add_argument(
        "--agent",
        default="unknown",
        help="the running agent's id, e.g. claude-code (recorded in "
        "catalyst.toml; `catalyst agent install <agent>` wires the agent, at user level)",
    )
    p.add_argument(
        "--kernel", type=Path, help="framework/kernel of a catalyst checkout or release (default: this checkout's)"
    )
    p.add_argument("--module-dir", type=Path, help="the module's directory (default: searched)")
    p.add_argument(
        "--no-module",
        action="store_true",
        help="install the kernel only; `catalyst module install` adds a module later",
    )
    p.add_argument("--userid", help=argparse.SUPPRESS)  # fixed first userid: reproducible examples
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("check", help="run every check: structure, chain, journal, indexes")
    p.add_argument("--strict", action="store_true", help="treat warnings as errors")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("hook", help="entry points for agent hooks")
    hk = p.add_subparsers(dest="hook_command", required=True)
    q = hk.add_parser("stop", help="end-of-turn hook: block the stop with the failures")
    q.add_argument("--strict", action="store_true")
    q.add_argument(
        "--format",
        choices=("exit2", "json", "gemini", "cursor"),
        default="exit2",
        help="how to block: exit 2 + stderr (Claude Code), decision JSON (Codex, Copilot), "
        "Gemini CLI's, Cursor's follow-up message",
    )
    q.set_defaults(func=cmd_hook)
    q = hk.add_parser("commit-msg", help="git commit-msg hook: the message must trace to the chain")
    q.add_argument("message_file")
    q.add_argument(
        "--route",
        action="store_true",
        help="from the repository top: hand the message to each deployment owning a staged file",
    )
    q.set_defaults(func=cmd_hook)
    q = hk.add_parser("install", help="install the commit-msg hook in the project's git repository")
    q.set_defaults(func=cmd_hook)
    q = hk.add_parser("start", help="session-start hook: print the invariants, record the session's baseline")
    q.add_argument(
        "--format",
        choices=("text", "json", "cursor"),
        default="text",
        help="plain text (Claude Code), additionalContext JSON (Codex, Copilot, Gemini), Cursor's",
    )
    q.add_argument(
        "--quiet",
        action="store_true",
        help="record the session's baseline (from the hook input) and print nothing: for an agent "
        "whose session already carries the laws",
    )
    q.set_defaults(func=cmd_hook_start)

    p = sub.add_parser("report", help="usage report: actors, tiers, traced commits, open artifacts")
    p.add_argument("--since", help="only history from this date/time on (ISO 8601)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("unrecorded", help="commits whose product changes the journal does not record")
    p.add_argument("range", nargs="?", help="git revision range (default: every commit after the baseline)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_unrecorded)

    p = sub.add_parser("trace", help="check that every commit in a range cites an artifact or rule ID")
    p.add_argument("range", nargs="?", default="HEAD~1..HEAD", help="git revision range (default: HEAD~1..HEAD)")
    p.add_argument(
        "--pattern-only",
        action="store_true",
        help="no working copy (e.g. CI of a local-only deployment): accept any well-formed ID",
    )
    p.set_defaults(func=cmd_trace)

    p = sub.add_parser(
        "recompose",
        help="merge kernel/module template changes into the deployed documents, keeping local edits (three-way)",
    )
    p.add_argument(
        "--base-kernel",
        type=Path,
        required=True,
        help="framework/kernel the deployment was composed from (the old version)",
    )
    p.add_argument("--base-module", type=Path, required=True, help="the module directory it was composed from")
    p.add_argument("--kernel", type=Path, required=True, help="the new framework/kernel")
    p.add_argument("--module-dir", type=Path, help="the new module directory (default: the deployed one)")
    p.add_argument("--check", action="store_true", help="change nothing; exit 1 if anything would change")
    p.add_argument("--force", action="store_true", help="also merge documents listed in .frozen")
    p.set_defaults(func=cmd_recompose)

    p = sub.add_parser("spec", help="print only what one command needs from CODE-OF-CONDUCT §4")
    p.add_argument("command", nargs="?", help="e.g. status or /check-rules (none: list commands)")
    p.add_argument("part", nargs="?", help="one part of a command with parts, e.g. `create bug`")
    p.add_argument("--general", action="store_true", help="the §4 rules that apply to every command")
    p.add_argument(
        "--budget", type=int, metavar="WORDS", help="check every command's spec against a word budget (exit 1 if over)"
    )
    p.add_argument("--json", action="store_true", help="the commands, or one command's spec, as JSON")
    p.set_defaults(func=cmd_spec)

    p = sub.add_parser("id", help="allocate the next ID (never reused)")
    ids = p.add_subparsers(dest="id_command", required=True)
    q = ids.add_parser("next", help="next <PREFIX>-NNNNNN-<userid> for an entity type")
    q.add_argument("prefix", help="entity type prefix, e.g. RECON or a module's type")
    q.add_argument("--count", type=int, default=1, help="that many consecutive IDs, one per line")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.set_defaults(func=cmd_id)
    q = ids.add_parser("next-rule", help="next <doc-prefix>-<DOMAIN>-NNNNNN-<userid> rule ID")
    q.add_argument("doc_prefix", help="the rule document's prefix, e.g. br")
    q.add_argument("domain", help="a registered DOMAIN code")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.set_defaults(func=cmd_id)

    p = sub.add_parser("journal", help="append to, verify, restore from or pin the journal")
    js = p.add_subparsers(dest="journal_command", required=True)
    q = js.add_parser("append", help="append one entry with real hashes and time")
    q.add_argument("--command", dest="cmd", required=True, help="the catalyst command, e.g. /status")
    q.add_argument("--action", required=True, help="create|update|close|retire|status-change|sync")
    q.add_argument("--artifact", required=True, help="the artifact ID or a short description")
    q.add_argument("--target", action="append", help="a rule/artifact ID this serves (repeatable)")
    q.add_argument("--intent", action="append", help="the goal of the change (repeatable)")
    q.add_argument("--file", action="append", help="a touched file (repeatable)")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--allow-unchanged", action="store_true")
    q.add_argument(
        "--tier",
        help="the change's ceremony tier, one the active module declares (default: chore, fix, feature; a chore needs no artifact)",
    )
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_journal)
    q = js.add_parser("adopt", help="record commits made outside catalyst in the journal (origin manual)")
    q.add_argument("revs", nargs="+", help="a commit, several, or a range (A..B)")
    q.add_argument("--intent", action="append", help="why the change was made (repeatable, required)")
    q.add_argument("--target", action="append", help="a rule/artifact ID this serves (repeatable)")
    q.add_argument("--artifact", help="the artifact ID or a short description (default: commit <sha>)")
    q.add_argument("--tier", help="the change's ceremony tier, one the active module declares")
    q.add_argument("--as", dest="as_user", help="actor (default: the commit's git author)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_journal)
    q = js.add_parser("verify", help="check hash chains, blobs, pins and unjournaled edits")
    q.add_argument("--strict", action="store_true", help="treat warnings as errors")
    q.add_argument("--legacy", action="store_true", help="also list warnings on pre-CLI entries")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_journal)
    q = js.add_parser("restore", help="materialise journaled files as of a timestamp")
    q.add_argument("timestamp", help="ISO 8601 UTC, e.g. 2026-09-27T18:00:00Z")
    q.add_argument(
        "out",
        type=Path,
        nargs="?",
        help="side directory, empty or absent (default: journal-restore-<timestamp> in TMPDIR)",
    )
    q.set_defaults(func=cmd_journal)
    q = js.add_parser("show", help="read-only: journal entries, filtered, in time order")
    q.add_argument("--since", help="only entries from this date/time on (ISO 8601)")
    q.add_argument("--artifact", help="only entries for this artifact")
    q.add_argument("--actor", help="only entries by this actor (name or part of it)")
    q.add_argument("--rule", help="only entries targeting this rule or artifact ID")
    q.add_argument(
        "--content",
        action="store_true",
        help="with --artifact: the history of that entity, each change with its content before and after",
    )
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_view, view="journal")
    q = js.add_parser("redact", help="redact journaled content: a tombstone entry, the blobs out of the pins")
    q.add_argument("blobs", nargs="+", metavar="blob", help="a git blob the journal names (40 hex characters)")
    q.add_argument("--intent", action="append", help="why (repeatable; required)")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--tier", help="the change's ceremony tier (default: the module's tier with no artifact)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_journal)
    q = js.add_parser("pin", help="pin every referenced blob so git gc keeps it")
    q.add_argument(
        "--share",
        action="store_true",
        help="also merge with and push the remote's pins (working copy and product repository)",
    )
    q.set_defaults(func=cmd_journal)

    p = sub.add_parser("list", help="read-only: artifacts of a type, rules, users, roles or templates")
    p.add_argument("type", help="an entity type (prefix, name or folder), rule, user, role, template, or all")
    p.add_argument(
        "--filter",
        action="append",
        metavar="KEY=VALUE",
        help="keep items whose KEY matches VALUE (* and ? wildcards; repeatable)",
    )
    p.add_argument("--type", dest="template_type", help="with `template`: one template family")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_view, view="list")

    p = sub.add_parser("view", help="read-only: one artifact or rule, its links both ways and its history")
    p.add_argument("id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_view, view="view")

    p = sub.add_parser("backlog", help="read-only: open work by type and status, missing links, idle rules")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_view, view="backlog")

    p = sub.add_parser("repair", help="rewrite what catalyst derives when it disagrees with its sources")
    rs = p.add_subparsers(dest="repair_command", required=True)
    q = rs.add_parser("derived", help="every derived field (another type's back-reference) from its sources, journaled")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--tier", help="the change's ceremony tier (default: the module's tier with no artifact)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_repair)

    p = sub.add_parser("graph", help="read-only: every rule, domain and artifact with its links, and the entity types")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_view, view="graph")

    p = sub.add_parser("new", help="create an artifact from its type's latest template, signed, indexed, journaled")
    p.add_argument("type", help="an entity type (prefix, name or folder)")
    p.add_argument("--title", required=True)
    p.add_argument(
        "--field",
        action="append",
        metavar="NAME=VALUE",
        help="a field value; references as comma-separated IDs (repeatable)",
    )
    p.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    p.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    p.add_argument("--command", dest="cmd", help="the slash command this runs for, journaled")
    p.add_argument("--tier", help="the change's ceremony tier, one the active module declares")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_edit, edit="new")

    p = sub.add_parser("rename", help="a new title: heading, Name, Filename and file follow; the ID stays")
    p.add_argument("id")
    p.add_argument("--title", required=True)
    p.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    p.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    p.add_argument("--command", dest="cmd", help="the slash command this runs for, journaled")
    p.add_argument("--tier", help="the change's ceremony tier, one the active module declares")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_edit, edit="rename")

    p = sub.add_parser("approve", help="approve an entity's current version under a gate (IAM/gates.json), journaled")
    p.add_argument("id")
    p.add_argument("--gate", required=True, help="the gate's id in IAM/gates.json")
    p.add_argument("--as", dest="as_user", help="who approves (name or git_username): never the version's author")
    p.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    p.add_argument("--tier", help="the change's ceremony tier, one the active module declares")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_approve)

    p = sub.add_parser("approvals", help="the gates covering an entity: approvals counted and missing")
    p.add_argument("id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_approvals)

    p = sub.add_parser("restore", help="write an entity back as it stood at a time: a new journaled change")
    p.add_argument("id")
    p.add_argument(
        "--to",
        required=True,
        help="a journal timestamp (ISO; the version after the last entry at or before it), or #N (after its Nth change)",
    )
    p.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    p.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    p.add_argument("--command", dest="cmd", help="the slash command this runs for, journaled")
    p.add_argument("--tier", help="the change's ceremony tier, one the active module declares")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_edit, edit="restore")

    p = sub.add_parser("status", help="change an artifact's Status")
    st = p.add_subparsers(dest="status_command", required=True)
    q = st.add_parser("set", help="set Status, checked against the type's statuses and transitions")
    q.add_argument("id")
    q.add_argument("status")
    q.add_argument(
        "--force",
        action="store_true",
        help="write a status outside the type's statuses, or past a failing guard (journaled)",
    )
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    q.add_argument("--command", dest="cmd", help="the slash command this runs for, journaled")
    q.add_argument("--tier", help="the change's ceremony tier, one the active module declares")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_edit, edit="status")

    p = sub.add_parser("link", help="cite IDs in a reference field, keeping the back-reference")
    p.add_argument("id")
    p.add_argument("field_name", metavar="field")
    p.add_argument("ids", nargs="+")
    p.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    p.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    p.add_argument("--command", dest="cmd", help="the slash command this runs for, journaled")
    p.add_argument("--tier", help="the change's ceremony tier, one the active module declares")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_edit, edit="link")

    p = sub.add_parser("user", help="register, deactivate or change users (IAM/users/users.json)")
    us = p.add_subparsers(dest="user_command", required=True)
    q = us.add_parser("add", help="register a user with a fresh userid and one role")
    q.add_argument("name")
    q.add_argument("role")
    q.add_argument("--git-username", help="default: the name")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_admin, admin="user")
    q = us.add_parser("remove", help="deactivate a user (never deleted; never the last active one)")
    q.add_argument("name")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_admin, admin="user")
    q = us.add_parser("modify", help="change one field (not name, registered, userid or roles)")
    q.add_argument("name")
    q.add_argument("field")
    q.add_argument("value")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_admin, admin="user")
    q = us.add_parser("assign-role", help="add a role to a user")
    q.add_argument("name")
    q.add_argument("role")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_admin, admin="user")

    p = sub.add_parser("role", help="add or change roles (IAM/roles/roles.json)")
    rs = p.add_subparsers(dest="role_command", required=True)
    q = rs.add_parser("add", help="add a role with its actions and reconciliation level")
    q.add_argument("name")
    q.add_argument("--action", action="append", help="an action the role may take (repeatable)")
    q.add_argument("--reconciliation", choices=["full", "propose", "none"], default="propose")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_admin, admin="role")
    q = rs.add_parser("modify", help="replace a role's actions")
    q.add_argument("name")
    q.add_argument("--action", action="append", help="an action the role may take (repeatable)")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_admin, admin="role")

    for verb, text in (
        ("freeze", "protect an item from /sync-framework (.frozen)"),
        ("unfreeze", "remove an item from .frozen"),
    ):
        p = sub.add_parser(verb, help=text)
        p.add_argument("item", help="an artifact ID, entity type, template name or working-copy path")
        p.add_argument("--as", dest="as_user", help="signer (name or git_username)")
        p.add_argument("--intent", action="append", help="why (repeatable; journaled)")
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_admin, admin=verb)

    p = sub.add_parser("definition", help="deployed entity definitions")
    ds = p.add_subparsers(dest="definition_command", required=True)
    q = ds.add_parser("migrate", help="move definitions/<type>.md to a version that exists (INV-23)")
    q.add_argument("entity", help="the entity type's definitions folder name, e.g. role")
    q.add_argument("version", type=int)
    q.add_argument("--kernel", type=Path, help="framework/kernel of the catalyst release (default: this checkout's)")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_admin, admin="definition")

    p = sub.add_parser("sync", help="synchronize the deployment with a kernel (and module) release")
    sy = p.add_subparsers(dest="sync_command", required=True)
    for verb, text in (
        ("plan", "list what a sync would change, and the migrations to run"),
        ("apply", "do the mechanical half of /sync-framework, then journal it"),
    ):
        q = sy.add_parser(verb, help=text)
        q.add_argument(
            "--kernel",
            type=Path,
            required=True,
            help="the target kernel: framework/kernel of a catalyst checkout, or a kernel-vX.Y.Z.zip",
        )
        q.add_argument("--module", help="the target module: its directory, release zip, or git URL[@ref]")
        q.add_argument(
            "--base-kernel",
            type=Path,
            help="the kernel the deployment was composed from (default: found next to the zip, or the git tag)",
        )
        q.add_argument("--cli", type=Path, help="the catalyst.pyz to vendor (default: the release's, or built)")
        q.add_argument(
            "--commands-dir",
            type=Path,
            help="where an older catalyst wrote the project's command files, "
            "to retire them (default: .claude/commands)",
        )
        q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
        q.add_argument("--intent", action="append", help="why (repeatable; journaled)")
        q.add_argument("--json", action="store_true")
        q.set_defaults(func=cmd_sync)

    p = sub.add_parser("inbox", help="what waits for a person, with its evidence and what settles it (read-only)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_inbox)

    p = sub.add_parser("impact", help="what an entity rests on and what rests on it, transitively (read-only)")
    p.add_argument("id", help="an artifact, a rule or a domain")
    way = p.add_mutually_exclusive_group()
    way.add_argument("--up", action="store_true", help="only what it rests on")
    way.add_argument("--down", action="store_true", help="only what rests on it")
    p.add_argument("--depth", type=int, help="stop after this many links (default: all)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_impact)

    p = sub.add_parser("module", help="the modules this criterion holds: its record, and each tree against it")
    mods = p.add_subparsers(dest="module_command", required=True)
    q = mods.add_parser("list", help="each installed module: id, version, source, commit, hash (no network)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_module)
    q = mods.add_parser("install", help="install a module into a deployment that has none (seeded as init does)")
    q.add_argument("source", help="the module: its directory, release zip, or git URL[@ref]")
    q.add_argument("--kernel", type=Path, help="framework/kernel of the release this deployment is at")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_module)
    q = mods.add_parser("upgrade", help="move the installed module to another release, through `sync plan|apply`")
    q.add_argument("id", help="the installed module")
    q.add_argument("source", nargs="?", help="directory, release zip or git URL[@ref] (default: the recorded URL)")
    q.add_argument("--kernel", type=Path, help="framework/kernel of the release this deployment is at")
    q.add_argument("--base-kernel", type=Path, help="the kernel the deployment was composed from (default: --kernel)")
    q.add_argument("--cli", type=Path, help=argparse.SUPPRESS)
    q.add_argument("--commands-dir", type=Path, help=argparse.SUPPRESS)
    q.add_argument("--plan", action="store_true", help="list what would change, write nothing")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_module)
    q = mods.add_parser(
        "verify", help="recompute each module's hash and compare it with the record (exit 1 on a difference)"
    )
    q.add_argument("id", nargs="?", help="one module (default: all)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_module)

    p = sub.add_parser("where", help="the project's criterion: the home store, or a legacy working copy")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_where)

    p = sub.add_parser("agent", help="wire catalyst into an agent at user level (MCP server, hooks), never a project")
    ags = p.add_subparsers(dest="agent_command", required=True)
    for verb, text in (
        ("install", "add catalyst to the agent's user-level configuration"),
        ("uninstall", "remove catalyst's entries from it"),
    ):
        q = ags.add_parser(verb, help=text)
        q.add_argument("agent", choices=("claude-code", "copilot", "vscode", "cursor", "codex", "gemini"))
        q.set_defaults(func=cmd_agent)
    q = ags.add_parser("status", help="which agents have catalyst")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_agent)
    q = ags.add_parser("run", help="dispatch a command to the project's agent; stream what it does and what it cost")
    q.add_argument("command", help="a command of CODE-OF-CONDUCT.md §4, e.g. check-rules")
    q.add_argument("arguments", nargs=argparse.REMAINDER, help="its arguments, as typed after the slash command")
    q.add_argument("--agent", help="this run's agent (default: the one `catalyst open --agent` records)")
    q.add_argument("--json", action="store_true", help="the events as JSON lines (spec/run-event.schema.json)")
    q.set_defaults(func=cmd_agent_run)
    q = ags.add_parser("runs", help="this user's logged runs for the project, with what each cost")
    q.add_argument("--limit", type=int, help="only the last N")
    q.add_argument("--json", action="store_true", help="the log's lines (spec/runs.schema.json)")
    q.set_defaults(func=cmd_agent_runs)

    p = sub.add_parser("mcp", help="serve catalyst to an agent over MCP (stdio): its commands, CLI, invariants")
    p.set_defaults(func=cmd_mcp)

    p = sub.add_parser("task", help="run a criterion task (Taskfile.common.yml) from the project's root")
    p.add_argument("name", nargs="?", help="the task, i.e. the command name (none: list them)")
    p.add_argument("task_args", nargs=argparse.REMAINDER, help="-- <arguments> for the command")
    p.set_defaults(func=cmd_task)

    p = sub.add_parser("runtime", help="the per-version runtime, the launcher, the criterion's .venv")
    rs = p.add_subparsers(dest="runtime_command", required=True)
    q = rs.add_parser("install", help="build this version's runtime, install the launcher, fill the criterion's .venv")
    q.set_defaults(func=cmd_runtime)
    q = rs.add_parser("status", help="runtimes, launcher and the criterion's runtime version")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_runtime)

    p = sub.add_parser("move", help="move a legacy deployment into $HOME/.catalyst, or rename a project")
    mg = p.add_mutually_exclusive_group(required=True)
    mg.add_argument(
        "--to-home",
        action="store_true",
        help="symlink, in-project directory or submodule -> $CATALYST_HOME/projects/<name>/criterion",
    )
    mg.add_argument("--name", help="rename a home-store project")
    p.add_argument("--no-runtime", action="store_true", help="do not fill the criterion's .venv now")
    p.add_argument("--as", dest="as_user", help="actor recorded in the journal")
    p.set_defaults(func=cmd_move)

    p = sub.add_parser("workspace", help="a VS Code workspace's meta criterion: shared rules, users, roles")
    wss = p.add_subparsers(dest="workspace_command", required=True)
    q = wss.add_parser("init", help="create the meta criterion and make the folders with a catalyst.toml members")
    q.add_argument("file", help="the <name>.code-workspace file")
    q.add_argument("--user", help="the first user, Admin (default: git config user.name)")
    q.add_argument("--git-username")
    q.add_argument("--kernel", type=Path, help="framework/kernel (default: this checkout's)")
    q.set_defaults(func=cmd_workspace)
    q = wss.add_parser("status", help="the workspace's criterion and which folders are members")
    q.add_argument("file", help="the <name>.code-workspace file")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_workspace)

    p = sub.add_parser("index", help="regenerate entity indexes from the artifact files")
    ix = p.add_subparsers(dest="index_command", required=True)
    q = ix.add_parser("regen", help="rewrite every <folder>/<folder>.md index")
    q.add_argument("--check", action="store_true", help="change nothing; exit 1 if any index is stale")
    q.add_argument("--diff", action="store_true", help="with --check, show what would change")
    q.set_defaults(func=cmd_index)

    p = sub.add_parser("analysis", help="four-eyes analysis of existing code (ANALYSIS-PLAYBOOK.md)")
    an_sub = p.add_subparsers(dest="analysis_command", required=True)
    q = an_sub.add_parser("start", help="open an analysis: scope, mode, code state, inventory")
    q.add_argument("scope", nargs="*", default=["."], help="paths to analyse (default: the whole project)")
    q.add_argument(
        "--mode",
        choices=["bootstrap", "incremental"],
        default="incremental",
        help="bootstrap: no rules yet; incremental: find what the rules miss (default)",
    )
    q.add_argument("--name", help="a short name for the record")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.set_defaults(func=cmd_analysis)
    q = an_sub.add_parser("record", help="store one independent pass's findings (JSON)")
    q.add_argument("id")
    q.add_argument("--pass", dest="which", required=True, choices=["A", "B", "a", "b"])
    q.add_argument("file", help="the pass's findings file")
    q.add_argument("--replace", action="store_true", help="replace a pass recorded by mistake")
    q.add_argument("--as", dest="as_user")
    q.set_defaults(func=cmd_analysis)
    q = an_sub.add_parser("diff", help="match the two passes: agreed, conflicting, A-only, B-only")
    q.add_argument("id")
    q.add_argument("--as", dest="as_user")
    q.set_defaults(func=cmd_analysis)
    q = an_sub.add_parser("reconcile", help="store the reconciler's list (every finding accounted for)")
    q.add_argument("id")
    q.add_argument("file")
    q.add_argument("--as", dest="as_user")
    q.set_defaults(func=cmd_analysis)
    q = an_sub.add_parser("decide", help="record the user's decision on one reconciled finding")
    q.add_argument("id")
    q.add_argument("finding")
    q.add_argument("verdict", choices=["accept", "reject"])
    q.add_argument("--artifact", help="the domain code, rule ID or artifact ID an accepted finding became")
    q.add_argument("--reason")
    q.add_argument("--as", dest="as_user")
    q.set_defaults(func=cmd_analysis)
    q = an_sub.add_parser("close", help="close once every finding is decided and accepted ones exist")
    q.add_argument("id")
    q.add_argument("--as", dest="as_user")
    q.set_defaults(func=cmd_analysis)
    q = an_sub.add_parser("abandon", help="stop an analysis, with the reason")
    q.add_argument("id")
    q.add_argument("--reason", required=True)
    q.add_argument("--as", dest="as_user")
    q.set_defaults(func=cmd_analysis)
    q = an_sub.add_parser("status", help="an analysis's phase and what it still needs")
    q.add_argument("id")
    q.set_defaults(func=cmd_analysis)

    p = sub.add_parser("reconcile", help="decide a reconciliation case (role-gated: full, propose, none)")
    p.add_argument("case", help="the RECON- case ID")
    p.add_argument("verb", choices=["accept", "accept-with-edits", "reject", "propose", "close"])
    p.add_argument("--text", help="propose: the proposed resolution (a new Revisions row)")
    p.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    p.add_argument("--intent", action="append", help="why (repeatable; journaled)")
    p.set_defaults(func=cmd_reconcile)

    p = sub.add_parser("why", help="explain a law (L1…), an invariant (INV-n), a meta-rule or an ID")
    p.add_argument("item", help="L3, INV-17, rr-META-012, a rule or artifact ID")
    p.set_defaults(func=cmd_why)

    p = sub.add_parser("open", help="make the project ready on this machine (join, runtime) and say where it stands")
    p.add_argument("--fetch", action="store_true", help="fetch the shared copy first")
    p.add_argument("--agent", help="record the agent this user works with (catalyst task dispatches to it)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_open)

    p = sub.add_parser("share", help="the criterion's sharing driver: info, status, pull, push")
    ss = p.add_subparsers(dest="share_command", required=True)
    q = ss.add_parser("info", help="the driver, where the shared copy is, what it can do")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_share)
    q = ss.add_parser("status", help="this criterion against its shared copy")
    q.add_argument("--fetch", action="store_true", help="fetch the shared copy first")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_share)
    q = ss.add_parser("pull", help="bring in what the shared copy has (refuses with unpublished work)")
    q.set_defaults(func=cmd_share)
    q = ss.add_parser("push", help="publish this criterion's changes (git: a topic branch and a pull request)")
    q.add_argument("-m", "--message", required=True, help="what the change is (commit message, pull request title)")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--no-pr", action="store_true", help="git: push the branch without opening a pull request")
    q.add_argument("--yes", action="store_true", help="the user agreed to publish what the preview shows (INV-4)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_share)
    q = ss.add_parser("create", help="publish a local-only criterion for the first time (git, or a server)")
    q.add_argument("url", help="the criterion repository (empty, or holding this history), or a server's URL")
    q.add_argument("--driver", choices=("git", "serve"), default="git", help="git (default) or a catalyst serve server")
    q.add_argument("--as", dest="as_user", help="serve: the signer of the journal entry (name or git_username)")
    q.add_argument("--branch", default="criterion", help="the shared branch (default: criterion)")
    q.add_argument("--protect", action="store_true", help="also require pull requests and the check (GitHub)")
    q.add_argument("--yes", action="store_true", help="the user agreed to publish (INV-4)")
    q.set_defaults(func=cmd_share)
    q = ss.add_parser("join", help="bring a shared criterion to this machine (a project with catalyst.toml)")
    q.add_argument("url", nargs="?", default=None, help="the criterion repository, when catalyst.toml names none")
    q.set_defaults(func=cmd_share)
    q = ss.add_parser("login", help="keep this user's token for a catalyst serve server (in catalyst's home)")
    q.add_argument("url", help="the server's URL, as catalyst.toml's share_url names it")
    q.add_argument("--token", help="the token (default: read one line on stdin)")
    q.set_defaults(func=cmd_share)

    p = sub.add_parser("serve", help="run a server that shares criteria between people (and manage its tokens)")
    p.add_argument("--db", help="the server's database (default: $CATALYST_HOME/serve/serve.db)")
    p.add_argument("--host", default="127.0.0.1", help="the address to listen on (default: 127.0.0.1)")
    p.add_argument("--port", type=int, default=None, help="the port (default: 8765; --local: one the system picks)")
    p.add_argument(
        "--local",
        action="store_true",
        help="serve this project's own criterion read-only, on 127.0.0.1, for a client on this machine",
    )
    p.add_argument("--project", help="--local: the project (default: the current directory)")
    p.add_argument(
        "--static",
        type=Path,
        help="--local: also serve this directory's files outside /v1 (`/` is its index.html); "
        "the start line gives the page's URL with the token",
    )
    vs = p.add_subparsers(dest="serve_command")
    q = vs.add_parser("token", help="issue, list or revoke the tokens users sign with")
    q.add_argument("action", choices=("issue", "list", "revoke"))
    q.add_argument("who", nargs="?", help="issue: the user's userid; revoke: the token's number")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("criterion", help="shared deployments on git: submodule, pull requests")
    cs = p.add_subparsers(dest="criterion_command", required=True)
    q = cs.add_parser("status", help="the working copy against the shared branch")
    q.add_argument("--fetch", action="store_true")
    q.set_defaults(func=cmd_criterion)
    q = cs.add_parser(
        "create", help="version the working copy for sharing; with a URL, publish it as the .criterion submodule"
    )
    q.add_argument(
        "url",
        nargs="?",
        default=None,
        help="the criterion repository (empty, or already holding this history); without it "
        "the working copy is versioned strictly locally, and push/sync/join ask for it",
    )
    q.add_argument("--branch", default="criterion", help="the shared branch (default: criterion)")
    q.add_argument("--yes", action="store_true", help="with a URL: the user agreed to publish (INV-4)")
    q.set_defaults(func=cmd_criterion)
    q = cs.add_parser("join", help="check out a shared deployment in a clone of the product")
    q.add_argument("--url", help="the criterion repository, when the product has no .criterion submodule yet")
    q.set_defaults(func=cmd_criterion)
    q = cs.add_parser("push", help="commit, rebase, check, push a topic branch, open a pull request")
    q.add_argument("-m", "--message", required=True, help="commit message / pull request title")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--no-pr", action="store_true", help="push the branch without opening a pull request")
    q.add_argument("--url", help="the criterion repository, when the deployment is still local only")
    q.add_argument("--yes", action="store_true", help="the user agreed to publish what the preview shows (INV-4)")
    q.set_defaults(func=cmd_criterion)
    q = cs.add_parser("sync", help="fast-forward to the shared branch (refuses with local work)")
    q.add_argument("--url", help="the criterion repository, when the deployment is still local only")
    q.add_argument("--yes", action="store_true", help="with --url: the user agreed to publish (INV-4)")
    q.set_defaults(func=cmd_criterion)
    q = cs.add_parser("integrity", help="fail if a merge lost any ID, index row or journal line")
    q.add_argument("--head", default="HEAD")
    q.add_argument(
        "--parent", action="append", help="compare against this revision (repeatable; default: the head's own parents)"
    )
    q.set_defaults(func=cmd_criterion)
    q = cs.add_parser("protect", help="branch protection for the shared branch (GitHub)")
    q.add_argument("--yes", action="store_true", help="apply it (without: show what would be set)")
    q.set_defaults(func=cmd_criterion)

    p = sub.add_parser("userid", help="userid operations")
    uid = p.add_subparsers(dest="userid_command", required=True)
    q = uid.add_parser("gen", help="draw a new unique userid (INV-26)")
    q.set_defaults(func=cmd_userid)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # UTF-8 out, whatever the code page (cp1252), so
        if hasattr(stream, "reconfigure"):  # git and hooks read it back; degrade, never crash
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (IdError, JournalError, CriterionError, AnalysisError, ShareError) as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    except DeploymentNotFound as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:  # e.g. git missing, unreadable file
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
