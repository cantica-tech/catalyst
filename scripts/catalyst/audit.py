"""`catalyst audit` (roadmap R6.27): the audit pack — for each rule, the
chain of everything that rests on it, with the record's integrity: who
signed, whether the journal verifies, what `check` reports, which gated
rules lack their approvals. Read from the views the CLI already computes;
nothing is written but the file asked for. It names no module type: the
chain is `impact`'s, downstream from each rule."""

from __future__ import annotations

import datetime
import html
import subprocess
from collections import Counter

from catalyst import impact, views
from catalyst.corpus import Corpus
from catalyst.deployment import Deployment


def _criterion_commit(dep: Deployment) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(dep.root), "rev-parse", "HEAD"], capture_output=True, text=True, check=False, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None


def _integrity(dep: Deployment, corpus: Corpus) -> dict:
    from catalyst import check, gates, journal

    issues = journal.verify(dep)
    report = check.run(dep)
    # a malformed gates file gives none here: `check` reports it
    unapproved = {str(w.get("id")) for w in gates.unapproved_rules(dep, corpus)}
    return {
        "journal": {
            "entries": sum(1 for _, e, _ in journal.read(dep) if e),
            "errors": sum(1 for i in issues if i.level == "error"),
            "warnings": sum(1 for i in issues if i.level != "error"),
        },
        "check": {"errors": len(report.errors), "warnings": len(report.warnings), "first": report.errors[:20]},
        "unapproved_rules": sorted(unapproved),
    }


def build(dep: Deployment, corpus: Corpus) -> dict:
    """The pack as data (`catalyst audit --json`, `spec/audit.schema.json`)."""
    from catalyst import __version__

    g = views.graph(dep, corpus)
    nodes = impact._nodes(g)
    rested_on: dict[str, list[tuple[str, str]]] = {}
    for source, field, target in impact.links(dep, g, nodes):
        rested_on.setdefault(target, []).append((field, source))
    signers: Counter = Counter()
    for a in g["artifacts"]:
        who = (a.get("fields") or {}).get("Signed-off-by") or a.get("Signed-off-by")
        if isinstance(who, str) and who.strip():
            signers[who.strip()] += 1
    rules = []
    for r in g["rules"]:
        chain = impact._closure(r["id"], rested_on, nodes, None, carried_by_reached=True)
        rules.append(
            {
                "id": r["id"],
                "title": r.get("title") or "",
                "status": r.get("status"),
                "strength": r.get("strength", "must"),
                "domain": r.get("domain"),
                "retired": bool(r.get("retired")),
                # a meta-rule governs the rule system itself: work does not rest on it
                "meta": str(r.get("file") or "").endswith(META_DOC),
                "chain": [
                    {
                        "id": c["id"],
                        "type": c["type"],
                        "title": c["title"],
                        "status": c["status"],
                        "depth": c["depth"],
                        "via": c["via"],
                    }
                    for c in chain
                ],
            }
        )
    version = dep.root / "version.txt"
    return {
        "project": dep.pointer.get("project_name") if not dep.standalone else None,
        "generated": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "catalyst": __version__,
        "kernel": version.read_text(encoding="utf-8").strip() if version.is_file() else None,
        "modules": [{"id": m.id, "version": m.version} for m in dep.installed()],
        "criterion_commit": _criterion_commit(dep),
        "integrity": _integrity(dep, corpus),
        "signers": [{"name": n, "signed": c} for n, c in sorted(signers.items(), key=lambda x: (-x[1], x[0]))],
        "rules": rules,
    }


META_DOC = "Rules-of-Rules.md"


def live(pack: dict) -> list[dict]:
    """The rules work can rest on: neither retired nor meta-rules."""
    return [r for r in pack["rules"] if not r["retired"] and not r["meta"]]


_CSS = """
body{font:14px/1.45 system-ui,sans-serif;margin:2em auto;max-width:60em;padding:0 1em;color:#1b1f24;background:#fff}
h1{font-size:1.6em}h2{font-size:1.25em;border-bottom:1px solid #ccc;padding-bottom:.2em;margin-top:2em}
h3{font-size:1.05em;margin:1.4em 0 .3em}code{font-family:ui-monospace,monospace;font-size:.92em}
table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:.2em .5em;border-bottom:1px solid #e3e3e3;vertical-align:top}
.muted{color:#555}.ok{color:#17663a}.bad{color:#a4161a}.rule{break-inside:avoid}
@media print{body{margin:0;max-width:none}a{color:inherit;text-decoration:none}}
"""


def render_html(pack: dict) -> str:
    """A self-contained page: no script, no remote file, printable to PDF."""
    e = html.escape
    integ = pack["integrity"]
    ok = integ["journal"]["errors"] == 0 and integ["check"]["errors"] == 0 and not integ["unapproved_rules"]
    title = f"Audit pack — {pack.get('project') or 'criterion'}"
    out = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{e(title)}</title><style>{_CSS}</style></head><body>",
        f"<h1>{e(title)}</h1>",
        f'<p class="muted">Generated {e(pack["generated"])} by catalyst {e(pack["catalyst"])}; kernel '
        f"{e(str(pack.get('kernel') or '?'))}; "
        + ", ".join(f"{e(m['id'])} {e(str(m['version']))}" for m in pack["modules"])
        + (f"; criterion at <code>{e(pack['criterion_commit'])}</code>" if pack.get("criterion_commit") else "")
        + ".</p>",
        "<h2>Integrity</h2>",
        f'<p class="{"ok" if ok else "bad"}">' + ("The record holds." if ok else "The record has problems.") + "</p>",
        "<table><tbody>",
        f"<tr><th>Journal</th><td>{integ['journal']['entries']} entries; {integ['journal']['errors']} error(s), "
        f"{integ['journal']['warnings']} warning(s) in <code>catalyst journal verify</code></td></tr>",
        f"<tr><th>Check</th><td>{integ['check']['errors']} error(s), {integ['check']['warnings']} warning(s) in "
        "<code>catalyst check</code></td></tr>",
        "<tr><th>Approvals</th><td>"
        + (
            "every gated rule's text is approved"
            if not integ["unapproved_rules"]
            else "lacking for " + ", ".join(f"<code>{e(r)}</code>" for r in integ["unapproved_rules"])
        )
        + "</td></tr>",
        "</tbody></table>",
    ]
    if integ["check"]["first"]:
        out.append("<ul>" + "".join(f"<li>{e(x)}</li>" for x in integ["check"]["first"]) + "</ul>")
    out += ["<h2>Signers</h2>", "<table><thead><tr><th>Signer</th><th>Entities signed</th></tr></thead><tbody>"]
    out += [f"<tr><td>{e(s['name'])}</td><td>{s['signed']}</td></tr>" for s in pack["signers"]]
    out += ["</tbody></table>", "<h2>Rules and what rests on them</h2>"]
    for r in pack["rules"]:
        flag = " (retired)" if r["retired"] else " (meta-rule)" if r["meta"] else ""
        out.append('<section class="rule">')
        out.append(f"<h3><code>{e(r['id'])}</code> {e(r['title'])}{flag}</h3>")
        out.append(
            f'<p class="muted">{e(str(r.get("status") or "no status"))} · strength {e(r["strength"])}'
            + (f" · domain {e(r['domain'])}" if r.get("domain") else "")
            + "</p>"
        )
        if not r["chain"] and r["meta"]:
            out.append('<p class="muted">A meta-rule: it governs the rules, and no work rests on it.</p>')
        elif not r["chain"]:
            out.append('<p class="bad">Nothing rests on it.</p>')
        else:
            out.append("<table><thead><tr><th>Entity</th><th>Type</th><th>Status</th><th>By</th></tr></thead><tbody>")
            for c in r["chain"]:
                indent = "&nbsp;&nbsp;" * (c["depth"] - 1)
                via = c["via"]
                out.append(
                    f"<tr><td>{indent}<code>{e(c['id'])}</code> {e(c['title'])}</td><td>{e(c['type'])}</td>"
                    f"<td>{e(str(c.get('status') or ''))}</td>"
                    f'<td class="muted">{e(via["field"])} of <code>{e(via["on"])}</code></td></tr>'
                )
            out.append("</tbody></table>")
        out.append("</section>")
    out.append("</body></html>")
    return "\n".join(out) + "\n"


def render(pack: dict) -> str:
    """The pack in brief, for the terminal."""
    integ = pack["integrity"]
    alone = [r["id"] for r in live(pack) if not r["chain"]]
    lines = [
        f"audit pack of {pack.get('project') or 'the criterion'} (kernel {pack.get('kernel')})",
        f"  journal: {integ['journal']['entries']} entries, {integ['journal']['errors']} error(s)",
        f"  check:   {integ['check']['errors']} error(s), {integ['check']['warnings']} warning(s)",
        f"  gates:   {len(integ['unapproved_rules'])} gated rule(s) lacking approvals",
        f"  rules:   {len(live(pack))} in force (besides meta-rules and retired ones), {len(alone)} with nothing resting on them",
    ]
    return "\n".join(lines) + "\n"
