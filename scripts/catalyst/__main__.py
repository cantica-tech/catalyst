"""`catalyst` command line. Every subcommand works on the deployment found at
or above the current directory (or `--project`), prints human-readable
output, or JSON with `--json`, and exits non-zero on failure."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from catalyst import version_string
from catalyst.deployment import DeploymentNotFound, WorkingCopyMissing, load
from catalyst.ids import IdError
from catalyst.journal import JournalError
from catalyst.analysis import AnalysisError
from catalyst.criterion import CriterionError


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
        json.dump({"ok": not failing, "findings": [f.as_dict() for f in findings]},
                  sys.stdout, indent=2)
        print()
    else:
        for f in findings:
            print(f)
        warnings = len(findings) - len(errors)
        verdict = "FAILED" if failing else "passed"
        print(f"catalyst validate {verdict}: {len(errors)} error(s), {warnings} warning(s)"
              + (" (strict)" if args.strict else ""))
    return 1 if failing else 0


def cmd_id(args) -> int:
    from catalyst.corpus import load_corpus
    from catalyst.ids import next_entity_id, next_rule_id, resolve_signer

    dep = open_deployment(args)
    corpus = load_corpus(dep)
    signer = resolve_signer(dep, corpus, args.as_user)
    # reserved under the ID lock: parallel callers never get the same ID
    if args.id_command == "next":
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
    if args.journal_command == "append":
        from catalyst.corpus import load_corpus
        from catalyst.ids import resolve_signer

        signer = resolve_signer(dep, load_corpus(dep), args.as_user)
        entry = j.append(dep, j.AppendRequest(
            command=args.cmd, action=args.action, artifact=args.artifact,
            targets=args.target or [], intent=args.intent or [], files=args.file or [],
            actor=str(signer.get("git_username") or signer.get("name")),
            allow_unchanged=args.allow_unchanged, tier=args.tier))
        print(json.dumps(entry, ensure_ascii=False) if args.json else
              f"journaled {len(entry['files'])} file(s) at {entry['timestamp']}")
        return 0
    if args.journal_command == "adopt":
        from catalyst import unrecorded
        try:
            entries = unrecorded.adopt(dep, args.revs, args.intent or [], tier=args.tier,
                                       targets=args.target or [], artifact=args.artifact, actor=args.as_user)
        except ValueError as exc:
            print(f"catalyst: {exc}", file=sys.stderr)
            return 1
        for e in entries:
            print(json.dumps(e, ensure_ascii=False) if args.json else
                  f"adopted {e['commit'][:10]} ({e['actor']}): {len(e['files'])} file(s)")
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
                print(f"({len(hidden)} warning(s) on entries written before the catalyst CLI; "
                      "--legacy lists them)")
            print(f"catalyst journal verify {'FAILED' if failing else 'passed'}: "
                  f"{len(errors)} error(s), {len(issues) - len(errors)} warning(s)"
                  + (f", {len(notes)} note(s) (merged concurrent edits)" if notes else ""))
        return 1 if failing else 0
    if args.journal_command == "restore":
        restored, missing = j.restore(dep, args.timestamp, args.out)
        print(f"restored {len(restored)} file(s) as of {args.timestamp} into {args.out}")
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
            if subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"],
                              check=False, capture_output=True).returncode != 0:
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
                sys.stdout.writelines(difflib.unified_diff(
                    c.old.splitlines(True), c.new.splitlines(True), rel, rel + " (regenerated)"))
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
        print(f"catalyst check skipped: {exc}")     # not a catalyst project at all
        return 0
    report = run(dep)
    failing = report.failing(args.strict)
    if args.json:
        json.dump({"ok": not failing, "errors": report.errors, "warnings": report.warnings},
                  sys.stdout, indent=2)
        print()
    else:
        if report.errors or report.warnings:
            print(report.text())
        print(f"catalyst check {'FAILED' if failing else 'passed'} ({report.scope}): "
              f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    return 1 if failing else 0


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
        checked, failures = trace(repo, args.range, corpus, scoped=dep is not None and not dep.standalone)
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
    print(f"catalyst trace {'FAILED' if failed else 'passed'}: {checked} commit(s) checked, "
          f"{len(failures)} without a trace" + (" (pattern only)" if corpus is None else
                                                 f", {len(manual)} with unrecorded changes"))
    return 1 if failed else 0


def cmd_unrecorded(args) -> int:
    from catalyst import unrecorded

    dep = open_deployment(args)
    if dep.standalone:
        print("catalyst: a standalone working copy has no product history", file=sys.stderr)
        return 1
    if unrecorded.baseline(dep) is None and not args.range:
        print(f"catalyst: the pointer declares no `{unrecorded.BASELINE_KEY}` (migration 0.42.0); "
              "pass a range to check one", file=sys.stderr)
        return 1
    if unrecorded.baseline_missing(dep):
        print(f"catalyst: {unrecorded.MISSING_BASELINE}", file=sys.stderr)
        return 1
    try:
        pairs = unrecorded.recorded(dep)
        revs = unrecorded.scoped(dep, [args.range or "HEAD"])
        found = [unrecorded.Commit(c.sha, c.author, c.subject, m)
                 for c in unrecorded.commits(dep.project_root, revs)
                 if (m := unrecorded.unrecorded_in(c, pairs))]
    except ValueError as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    if args.json:
        json.dump([{"commit": c.sha, "author": c.author, "subject": c.subject,
                    "files": [{"path": p, "before": b, "after": a} for p, b, a in c.changes]}
                   for c in found], sys.stdout, indent=2)
        print()
    else:
        for c in found:
            print(unrecorded.describe(c))
        print(f"{len(found)} commit(s) with changes not in the journal "
              f"(checked as {unrecorded.level(dep)}s)")
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
            corpus = load_corpus(open_deployment(args))
        except DeploymentNotFound:
            return 0
        git_dir = subprocess.run(["git", "rev-parse", "--absolute-git-dir"], check=False, capture_output=True, text=True, encoding="utf-8")
        if git_dir.returncode == 0 and (Path(git_dir.stdout.strip()) / "MERGE_HEAD").exists():
            return 0                         # a merge carries its parents' trace (as in `trace`)
        reason = check_message(Path(args.message_file).read_text(encoding="utf-8"), corpus)
        if not reason:
            from catalyst import unrecorded
            dep = open_deployment(args)
            missing = unrecorded.staged(dep) if unrecorded.baseline(dep) is not None else []
            if missing:
                paths = ", ".join(p for p, _, _ in missing[:5]) + (" ..." if len(missing) > 5 else "")
                advice = ("Journal them first (`catalyst journal append --file <path>`), or record the "
                          "commit afterwards with `catalyst journal adopt HEAD`.")
                if unrecorded.level(dep) == "error":
                    print(f"catalyst: commit refused — {len(missing)} staged file(s) not recorded in the "
                          f"journal: {paths}.\n{advice} Bypass once: git commit --no-verify.", file=sys.stderr)
                    return 1
                print(f"catalyst: warning — {len(missing)} staged file(s) not recorded in the journal: "
                      f"{paths}.\n{advice} (A warning during the beta; from format 1.0 this refuses "
                      "the commit.)", file=sys.stderr)
        if reason:
            print(f"catalyst: commit refused — {reason}.\nCite the artifact or rule this commit serves "
                  "(e.g. <PREFIX>-000012 or its full ID), or start the subject with `chore:` "
                  "if no rule's behaviour changes. Bypass once: git commit --no-verify.", file=sys.stderr)
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
    try:
        try:
            dep = open_deployment(args)
        except WorkingCopyMissing as exc:
            print(f"catalyst: {exc}", file=sys.stderr)
            return 2
        except DeploymentNotFound:
            return 0
        return hook_stop(dep, strict=args.strict)
    except Exception as exc:  # noqa: BLE001
        print(f"catalyst hook stop crashed — {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


def _ask_url(exc) -> str:
    """Ask for the criterion repository's URL on an interactive terminal;
    elsewhere (an agent, CI) the error stands and names --url."""
    if not sys.stdin.isatty():
        raise exc
    print(f"catalyst: {exc}", file=sys.stderr)
    url = input("criterion repository URL (empty to stay local): ").strip()
    if not url:
        from catalyst.criterion import CriterionError
        raise CriterionError("no URL given: nothing changed, the deployment stays local")
    return url


def cmd_analysis(args) -> int:
    from catalyst import analysis as an
    from catalyst import journal
    from catalyst.corpus import load_corpus
    from catalyst.ids import resolve_signer

    dep = open_deployment(args)
    corpus = load_corpus(dep)
    sub = args.analysis_command

    def signer():
        return resolve_signer(dep, corpus, getattr(args, "as_user", None))

    def journaled(ctx, action: str, intent: str, who: dict) -> None:
        journal.append(dep, journal.AppendRequest(
            command=f"catalyst analysis {sub}", action=action, artifact=ctx.art.id,
            targets=[], intent=[intent], files=[str(f) for f in an.files_of(ctx)],
            actor=str(who.get("git_username") or who.get("name")), allow_unchanged=True))

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
        print(f"{ctx.art.id}: {len(inv['files'])} file(s) at {inv['code_state'][:10]}; "
              f"record two independent passes with `catalyst analysis record {ctx.art.id} --pass A|B <file>`")
        return 0
    ctx = an.context(dep, args.id, corpus)
    if sub == "status":
        d, r = ctx.load("diff.json"), ctx.load("reconciled.json")
        decided = (ctx.load("decisions.json") or {}).get("decisions", {})
        print(f"{ctx.art.id}: {an.phase(ctx.art)} ({ctx.art.get('Mode')}; {ctx.art.get('Scope')})")
        print(f"passes:    A {'recorded' if ctx.load('A.json') else '—'}, B {'recorded' if ctx.load('B.json') else '—'}")
        if d:
            print(f"diff:      {len(d['agreed'])} agreed, {len(d['conflicting'])} conflicting, "
                  f"{len(d['a_only'])} A-only, {len(d['b_only'])} B-only")
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
        print(f"{len(d['agreed'])} agreed, {len(d['conflicting'])} conflicting, {len(d['a_only'])} A-only, "
              f"{len(d['b_only'])} B-only — reconcile every one (`catalyst analysis reconcile`)")
        return 0
    if sub == "reconcile":
        an.reconcile(ctx, read_json(args.file))
        journaled(an.context(dep, ctx.art.id), "update", "reconciled list accepted: every finding accounted for", who)
        n = len(an.context(dep, ctx.art.id).load("reconciled.json")["findings"])
        print(f"{n} reconciled finding(s): each needs the user's decision (`catalyst analysis decide`)")
        return 0
    if sub == "decide":
        an.decide(ctx, args.finding, args.verdict, who, args.artifact, args.reason)
        journaled(ctx, "update", f"finding {args.finding}: {args.verdict}"
                  + (f" as {args.artifact}" if args.artifact else ""), who)
        print(f"{args.finding}: {args.verdict}" + (f" → {args.artifact}" if args.artifact else ""))
        return 0
    if sub == "close":
        counts = an.close(ctx)
        journaled(an.context(dep, ctx.art.id), "close", "every finding decided; accepted ones exist", who)
        print(f"{ctx.art.id} closed: " + (", ".join(f"{k} {c['accept']}/{c['accept'] + c['reject']} accepted"
                                                   for k, c in sorted(counts.items())) or "no findings"))
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
        project = next((d for d in (start, *start.parents) if any(d.glob("*.catalyst"))), None)
        if project is None:
            raise DeploymentNotFound(f"no *.catalyst pointer at or above {start}")
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
        print(f"mode:     {st.mode}\nremote:   {st.remote or '(none)'}\nshared:   {st.branch}\n"
              f"branch:   {st.current or '(detached)'}\nchanges:  {len(st.dirty)} uncommitted")
        if st.ahead is not None:
            print(f"vs shared: {st.ahead} ahead, {st.behind} behind")
        return 0
    if sub == "create":
        for note in cr.create(dep, args.url, args.branch, cr.CI_TEMPLATE):
            print(f"- {note}")
        print("Commit the product repository's staged changes when ready.")
        return 0
    if sub in ("push", "sync"):
        # a local-only deployment is published first, to the URL given or asked for
        url = args.url
        while True:
            try:
                dep, published = cr.ensure_remote(dep, url)
                break
            except cr.NeedsURL as exc:
                url = _ask_url(exc)
        for note in published:
            print(f"- {note}")
        if published:
            print("Published: commit the product repository's staged changes when ready.")
    if sub == "push":
        from catalyst.corpus import load_corpus
        from catalyst.ids import resolve_signer
        signer = resolve_signer(dep, load_corpus(dep), args.as_user)
        res = cr.push(dep, signer, args.message, open_pr=not args.no_pr)
        if res.commits == 0:
            print("nothing to push: the working copy matches the shared branch")
            return 0
        print(f"pushed {res.commits} commit(s) to {res.branch}"
              + (f" (regenerated {', '.join(res.regenerated)})" if res.regenerated else ""))
        print(f"pull request: {res.pr}" if res.pr else
              f"open a pull request from {res.branch} into {cr.shared_branch(dep)}")
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
        print(f"catalyst criterion integrity {'FAILED' if problems else 'passed'}: "
              f"{len(problems)} missing")
        return 1 if problems else 0
    print(cr.protect(dep, apply=args.yes))
    return 0


def cmd_init(args) -> int:
    from module_loader import REPO_ROOT

    from catalyst.init import (InitError, InitRequest, default_commands_dir, git_user_name, init,
                               local_modules)

    kernel = args.kernel or (REPO_ROOT / "framework" / "kernel")
    if not (kernel / "rules-of-rules.template.md").is_file():
        print("catalyst: pass --kernel <framework/kernel of a catalyst checkout or release>", file=sys.stderr)
        return 2
    project = Path(os.path.abspath(args.project)) if args.project else Path.cwd()
    if not args.module:                      # never chosen for the user: list what is here
        found = local_modules(project)
        listing = "; ".join(f"{m} ({d})" for m, d in found.items()) or "none next to the project or catalyst"
        print(f"catalyst: pass --module <id> (and --module-dir if it is elsewhere). Found: {listing}",
              file=sys.stderr)
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
        steps = init(InitRequest(
            project=project, name=args.name, module_id=args.module, user=user, kernel=kernel,
            module=args.module_dir, git_username=args.git_username or user, rule_docs=docs,
            test_locations=args.test_locations, at=args.at, agent=args.agent,
            commands_dir=args.commands_dir or default_commands_dir(args.agent), userid=args.userid))
    except InitError as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    for step in steps:
        print(f"- {step}")
    print("Next: write the first rules (catalyst id next-rule), then `catalyst check`. Nothing was committed "
          "in the project repository.")
    return 0


def cmd_hook_start(args) -> int:
    """SessionStart hook: print the deployment's invariants (kernel, then
    module) so every session starts grounded. Never blocks a session."""
    try:
        dep = open_deployment(args)
    except WorkingCopyMissing as exc:
        print(f"catalyst: {exc}")
        return 0
    except DeploymentNotFound:
        return 0
    for name in ("INVARIANTS.md", "INVARIANTS.module.md"):
        path = dep.root / name
        if path.is_file():
            print(path.read_text(encoding="utf-8", errors="replace"))
    return 0


def cmd_spec(args) -> int:
    from catalyst.spec import SpecError, commands, general, spec

    dep = open_deployment(args)
    try:
        if args.budget is not None:
            over = [(len(spec(dep, c).split()), c) for c in commands(dep)]
            over = sorted(o for o in over if o[0] > args.budget)
            for words, c in over:
                print(f"ERROR   /{c}: {words} words (budget {args.budget})")
            print(f"catalyst spec budget {'FAILED' if over else 'passed'}: "
                  f"{len(commands(dep))} commands, budget {args.budget} words each")
            return 1 if over else 0
        if args.general:
            sys.stdout.write(general(dep))
            return 0
        if not args.command:
            print("\n".join(f"/{c}" for c in commands(dep)))
            return 0
        sys.stdout.write(spec(dep, args.command))
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
    new_module = args.module_dir or dep.module.path
    try:
        results = recompose(dep.root, params, (args.base_kernel, args.base_module),
                            (args.kernel, new_module), write=not args.check, force=args.force)
    except RuntimeError as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    for r in results:
        state = ("frozen, skipped" if r.frozen else f"{r.conflicts} conflict(s)" if r.conflicts
                 else ("merged" if r.changed else "unchanged"))
        print(f"{'would update' if args.check and r.changed else state:>14}  .criterion/{r.path}")
    conflicts = sum(r.conflicts for r in results)
    if conflicts:
        print(f"{conflicts} conflict(s) left marked (<<<<<<<) for a human or agent to resolve")
    return 1 if conflicts or (args.check and any(r.changed for r in results)) else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="catalyst", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"catalyst {version_string()}")
    parser.add_argument("--project", type=Path, default=None,
                        help="a directory inside the project (default: current directory)")
    parser.add_argument("--working-copy", type=Path, default=None,
                        help="check a bare working copy (e.g. the criterion repository in CI)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="validate the traceability chain against the ETDs")
    p.add_argument("--strict", action="store_true", help="treat warnings as errors")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("init", help="install catalyst into this project (explicit only, INV-2)")
    p.add_argument("--name", required=True, help="the project name (the pointer is <name>.catalyst)")
    p.add_argument("--module", help="the active process module id (no default: without it, init lists "
                   "the modules it finds)")
    p.add_argument("--user", help="the first user's name, who becomes Admin (default: git config user.name)")
    p.add_argument("--git-username", help="the first user's git username (default: --user)")
    p.add_argument("--rule-doc", action="append", metavar="FILE:PREFIX",
                   help="a rule document and its ID prefix, e.g. business-rules:br (repeatable)")
    p.add_argument("--test-locations", help="where the project's tests live (Rules-of-Rules §2)")
    p.add_argument("--at", type=Path, help="agent-owned location for the working copy "
                   "(the agent's shim says where); default: .criterion in the project")
    p.add_argument("--agent", default="unknown", help="the running agent's id, e.g. claude-code")
    p.add_argument("--commands-dir", type=Path, help="write command files here (default: the agent's, "
                   "e.g. .claude/commands for claude-code)")
    p.add_argument("--kernel", type=Path, help="framework/kernel of a catalyst checkout or release "
                   "(default: this checkout's)")
    p.add_argument("--module-dir", type=Path, help="the module's directory (default: searched)")
    p.add_argument("--userid", help=argparse.SUPPRESS)       # fixed first userid: reproducible examples
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("check", help="run every check: structure, chain, journal, indexes")
    p.add_argument("--strict", action="store_true", help="treat warnings as errors")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("hook", help="entry points for agent hooks")
    hk = p.add_subparsers(dest="hook_command", required=True)
    q = hk.add_parser("stop", help="end-of-turn hook: exit 2 with failures on stderr")
    q.add_argument("--strict", action="store_true")
    q.set_defaults(func=cmd_hook)
    q = hk.add_parser("commit-msg", help="git commit-msg hook: the message must trace to the chain")
    q.add_argument("message_file")
    q.add_argument("--route", action="store_true",
                   help="from the repository top: hand the message to each deployment owning a staged file")
    q.set_defaults(func=cmd_hook)
    q = hk.add_parser("install", help="install the commit-msg hook in the project's git repository")
    q.set_defaults(func=cmd_hook)
    q = hk.add_parser("start", help="session-start hook: print the deployment's invariants")
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
    p.add_argument("--pattern-only", action="store_true",
                   help="no working copy (e.g. CI of a local-only deployment): accept any well-formed ID")
    p.set_defaults(func=cmd_trace)

    p = sub.add_parser("recompose", help="merge kernel/module template changes into the deployed "
                       "documents, keeping local edits (three-way)")
    p.add_argument("--base-kernel", type=Path, required=True,
                   help="framework/kernel the deployment was composed from (the old version)")
    p.add_argument("--base-module", type=Path, required=True, help="the module directory it was composed from")
    p.add_argument("--kernel", type=Path, required=True, help="the new framework/kernel")
    p.add_argument("--module-dir", type=Path, help="the new module directory (default: the deployed one)")
    p.add_argument("--check", action="store_true", help="change nothing; exit 1 if anything would change")
    p.add_argument("--force", action="store_true", help="also merge documents listed in .frozen")
    p.set_defaults(func=cmd_recompose)

    p = sub.add_parser("spec", help="print only what one command needs from CODE-OF-CONDUCT §4")
    p.add_argument("command", nargs="?", help="e.g. status or /check-rules (none: list commands)")
    p.add_argument("--general", action="store_true", help="the §4 rules that apply to every command")
    p.add_argument("--budget", type=int, metavar="WORDS",
                   help="check every command's spec against a word budget (exit 1 if over)")
    p.set_defaults(func=cmd_spec)

    p = sub.add_parser("id", help="allocate the next ID (never reused)")
    ids = p.add_subparsers(dest="id_command", required=True)
    q = ids.add_parser("next", help="next <PREFIX>-NNNNNN-<userid> for an entity type")
    q.add_argument("prefix", help="entity type prefix, e.g. RECON or a module's type")
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
    q.add_argument("--tier", choices=["chore", "fix", "feature"],
                   help="the change's ceremony tier (a chore needs no artifact)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_journal)
    q = js.add_parser("adopt", help="record commits made outside catalyst in the journal (origin manual)")
    q.add_argument("revs", nargs="+", help="a commit, several, or a range (A..B)")
    q.add_argument("--intent", action="append", help="why the change was made (repeatable, required)")
    q.add_argument("--target", action="append", help="a rule/artifact ID this serves (repeatable)")
    q.add_argument("--artifact", help="the artifact ID or a short description (default: commit <sha>)")
    q.add_argument("--tier", choices=["chore", "fix", "feature"], help="the change's ceremony tier")
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
    q.add_argument("out", type=Path, help="side directory (must be empty or absent)")
    q.set_defaults(func=cmd_journal)
    q = js.add_parser("pin", help="pin every referenced blob so git gc keeps it")
    q.add_argument("--share", action="store_true",
                   help="also merge with and push the remote's pins (working copy and product repository)")
    q.set_defaults(func=cmd_journal)

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
    q.add_argument("--mode", choices=["bootstrap", "incremental"], default="incremental",
                   help="bootstrap: no rules yet; incremental: find what the rules miss (default)")
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

    p = sub.add_parser("criterion", help="shared deployments on git: submodule, pull requests")
    cs = p.add_subparsers(dest="criterion_command", required=True)
    q = cs.add_parser("status", help="the working copy against the shared branch")
    q.add_argument("--fetch", action="store_true")
    q.set_defaults(func=cmd_criterion)
    q = cs.add_parser("create", help="version the working copy for sharing; with a URL, publish it as the .criterion submodule")
    q.add_argument("url", nargs="?", default=None,
                   help="the criterion repository (empty, or already holding this history); without it "
                        "the working copy is versioned strictly locally, and push/sync/join ask for it")
    q.add_argument("--branch", default="criterion", help="the shared branch (default: criterion)")
    q.set_defaults(func=cmd_criterion)
    q = cs.add_parser("join", help="check out a shared deployment in a clone of the product")
    q.add_argument("--url", help="the criterion repository, when the product has no .criterion submodule yet")
    q.set_defaults(func=cmd_criterion)
    q = cs.add_parser("push", help="commit, rebase, check, push a topic branch, open a pull request")
    q.add_argument("-m", "--message", required=True, help="commit message / pull request title")
    q.add_argument("--as", dest="as_user", help="signer (name or git_username)")
    q.add_argument("--no-pr", action="store_true", help="push the branch without opening a pull request")
    q.add_argument("--url", help="the criterion repository, when the deployment is still local only")
    q.set_defaults(func=cmd_criterion)
    q = cs.add_parser("sync", help="fast-forward to the shared branch (refuses with local work)")
    q.add_argument("--url", help="the criterion repository, when the deployment is still local only")
    q.set_defaults(func=cmd_criterion)
    q = cs.add_parser("integrity", help="fail if a merge lost any ID, index row or journal line")
    q.add_argument("--head", default="HEAD")
    q.add_argument("--parent", action="append", help="compare against this revision (repeatable; "
                   "default: the head's own parents)")
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
    for stream in (sys.stdout, sys.stderr):       # UTF-8 out, whatever the code page (cp1252), so
        if hasattr(stream, "reconfigure"):        # git and hooks read it back; degrade, never crash
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (IdError, JournalError, CriterionError, AnalysisError) as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1
    except DeploymentNotFound as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:        # e.g. git missing, unreadable file
        print(f"catalyst: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
