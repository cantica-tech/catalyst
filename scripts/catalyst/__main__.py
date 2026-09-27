"""`catalyst` command line. Every subcommand works on the deployment found at
or above the current directory (or `--project`), prints human-readable
output, or JSON with `--json`, and exits non-zero on failure."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from catalyst import __version__
from catalyst.deployment import DeploymentNotFound, WorkingCopyMissing, load
from catalyst.ids import IdError
from catalyst.journal import JournalError


def cmd_validate(args) -> int:
    from catalyst.corpus import load_corpus
    from catalyst.validate import ERROR, validate

    dep = load(args.project)
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

    dep = load(args.project)
    corpus = load_corpus(dep)
    signer = resolve_signer(dep, corpus, args.as_user)
    if args.id_command == "next":
        print(next_entity_id(dep, corpus, args.prefix, signer))
    else:
        print(next_rule_id(dep, corpus, args.doc_prefix, args.domain, signer))
    return 0


def cmd_userid(args) -> int:
    from catalyst.corpus import load_corpus
    from catalyst.ids import generate_userid

    dep = load(args.project)
    existing = {str(u["userid"]) for u in load_corpus(dep).users if u.get("userid")}
    print(generate_userid(existing))
    return 0


def cmd_journal(args) -> int:
    from catalyst import journal as j

    dep = load(args.project)
    if args.journal_command == "append":
        from catalyst.corpus import load_corpus
        from catalyst.ids import resolve_signer

        signer = resolve_signer(dep, load_corpus(dep), args.as_user)
        entry = j.append(dep, j.AppendRequest(
            command=args.cmd, action=args.action, artifact=args.artifact,
            targets=args.target or [], intent=args.intent or [], files=args.file or [],
            actor=str(signer.get("git_username") or signer.get("name")),
            allow_unchanged=args.allow_unchanged))
        print(json.dumps(entry, ensure_ascii=False) if args.json else
              f"journaled {len(entry['files'])} file(s) at {entry['timestamp']}")
        return 0
    if args.journal_command == "verify":
        issues = j.verify(dep)
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
                  f"{len(errors)} error(s), {len(issues) - len(errors)} warning(s)")
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
    return 0


def cmd_index(args) -> int:
    import difflib

    from catalyst.corpus import load_corpus
    from catalyst.indexes import regenerate

    dep = load(args.project)
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
        dep = load(args.project)
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


def cmd_hook(args) -> int:
    from catalyst.check import hook_stop

    try:
        dep = load(args.project)
    except WorkingCopyMissing as exc:
        print(f"catalyst: {exc}", file=sys.stderr)
        return 2
    except DeploymentNotFound:
        return 0
    return hook_stop(dep, strict=args.strict)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="catalyst", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"catalyst {__version__}")
    parser.add_argument("--project", type=Path, default=None,
                        help="a directory inside the project (default: current directory)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="validate the traceability chain against the ETDs")
    p.add_argument("--strict", action="store_true", help="treat warnings as errors")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("check", help="run every check: structure, chain, journal, indexes")
    p.add_argument("--strict", action="store_true", help="treat warnings as errors")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("hook", help="entry points for agent hooks")
    hk = p.add_subparsers(dest="hook_command", required=True)
    q = hk.add_parser("stop", help="end-of-turn hook: exit 2 with failures on stderr")
    q.add_argument("--strict", action="store_true")
    q.set_defaults(func=cmd_hook)

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
    q.set_defaults(func=cmd_journal)

    p = sub.add_parser("index", help="regenerate entity indexes from the artifact files")
    ix = p.add_subparsers(dest="index_command", required=True)
    q = ix.add_parser("regen", help="rewrite every <folder>/<folder>.md index")
    q.add_argument("--check", action="store_true", help="change nothing; exit 1 if any index is stale")
    q.add_argument("--diff", action="store_true", help="with --check, show what would change")
    q.set_defaults(func=cmd_index)

    p = sub.add_parser("userid", help="userid operations")
    uid = p.add_subparsers(dest="userid_command", required=True)
    q = uid.add_parser("gen", help="draw a new unique userid (INV-26)")
    q.set_defaults(func=cmd_userid)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (IdError, JournalError) as exc:
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
