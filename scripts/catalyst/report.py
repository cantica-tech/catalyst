"""`catalyst report`: what a deployment's history says about how it is used —
the measurement side of a trial (who works in it, at which tier, how much is
traced, what is still open) — from the journal, the artifacts and git."""

from __future__ import annotations

import collections

from catalyst import journal
from catalyst.corpus import load_corpus
from catalyst.deployment import Deployment
from catalyst.validate import ERROR, validate


def build(dep: Deployment, since: str | None = None) -> dict:
    entries = [e for _, e, _ in journal.read(dep) if e]
    if since:
        cutoff = journal.parse_time(since)
        entries = [e for e in entries if (t := journal._entry_time(e)) and t >= cutoff]
    corpus = load_corpus(dep)
    findings = validate(dep, corpus)
    by_type: dict[str, collections.Counter] = {}
    for prefix, arts in corpus.by_prefix.items():
        by_type[prefix] = collections.Counter((a.get("Status") or "?").strip("` *") for a in arts)
    weeks = collections.Counter(str(e.get("timestamp", ""))[:10] for e in entries)
    commits = traced = 0
    if not dep.standalone:
        from catalyst.trace import check_message, commits as git_commits

        window = [f"--since={since}"] if since else ["-200"]
        try:
            history = git_commits(dep.project_root, ["HEAD"], options=tuple(window))
        except ValueError:
            history = []  # no commits yet
        for sha, parents, body in history:
            if len(parents) > 1:
                continue
            commits += 1
            traced += check_message(body, corpus) is None
    from catalyst import unrecorded

    manual = unrecorded.since_baseline(dep) if not dep.standalone else []
    adopted = sum(e.get("origin") == "manual" for e in entries)
    return {
        "entries": len(entries),
        "actors": dict(collections.Counter(str(e.get("actor")) for e in entries).most_common()),
        "tiers": dict(collections.Counter(str(e.get("tier", "untiered")) for e in entries).most_common()),
        "commands": dict(collections.Counter(str(e.get("command")) for e in entries).most_common(10)),
        "active_days": len(weeks),
        "artifacts": {p: dict(c) for p, c in sorted(by_type.items()) if c},
        "reconciliations": len(corpus.by_prefix.get("RECON", [])),
        "errors": sum(f.level == ERROR for f in findings),
        "warnings": sum(f.level != ERROR for f in findings),
        "commits": commits,
        "commits_traced": traced,
        "unrecorded_commits": len(manual),
        "adopted_commits": adopted,
    }


def render(r: dict) -> str:
    lines = [
        "# catalyst report",
        "",
        f"- journal entries: {r['entries']} over {r['active_days']} active day(s)",
        "- actors: " + (", ".join(f"{a} ({n})" for a, n in r["actors"].items()) or "none"),
        "- tiers: " + (", ".join(f"{t} ({n})" for t, n in r["tiers"].items()) or "none"),
        f"- commits traced: {r['commits_traced']}/{r['commits']}",
        f"- commits with changes outside catalyst: {r['unrecorded_commits']} unrecorded, "
        f"{r['adopted_commits']} adopted",
        f"- reconciliation cases: {r['reconciliations']}",
        f"- validate: {r['errors']} error(s), {r['warnings']} warning(s)",
        "",
        "## Artifacts",
        "",
    ]
    for prefix, statuses in r["artifacts"].items():
        lines.append(f"- {prefix}: " + ", ".join(f"{s} {n}" for s, n in sorted(statuses.items())))
    lines += ["", "## Most used commands", ""] + [f"- {c}: {n}" for c, n in r["commands"].items()]
    return "\n".join(lines) + "\n"
