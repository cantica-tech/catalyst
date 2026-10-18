"""`catalyst badge` (roadmap R6.28): a README badge — one small SVG of
`check`'s result, or of how many rules have something resting on them — for
a CI job to publish beside the code. A file, so no server ever answers an
anonymous request for it."""

from __future__ import annotations

import html

from catalyst.corpus import Corpus
from catalyst.deployment import Deployment

METRICS = ("check", "chain")
GOOD, WARN, BAD = "#2e7d32", "#9a6700", "#b42318"


def _width(text: str) -> int:
    """The text's width in the badge's 11px font, near enough: no font is loaded to measure it."""
    narrow = sum(1 for c in text if c in "iIl1.,:;|' ")
    return int((len(text) - narrow) * 6.6 + narrow * 3.4) + 12


def svg(label: str, value: str, colour: str) -> str:
    """A flat two-part badge, `label | value`, readable without its colour (the text says it all)."""
    lw, vw = _width(label), _width(value)
    e = html.escape
    title = f"{label}: {value}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{lw + vw}" height="20" role="img" aria-label="{e(title)}">'
        f"<title>{e(title)}</title>"
        f'<rect width="{lw}" height="20" fill="#555"/>'
        f'<rect x="{lw}" width="{vw}" height="20" fill="{colour}"/>'
        '<g fill="#fff" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">'
        f'<text x="{lw / 2:.1f}" y="14">{e(label)}</text>'
        f'<text x="{lw + vw / 2:.1f}" y="14">{e(value)}</text>'
        "</g></svg>\n"
    )


def measure(dep: Deployment, corpus: Corpus, metric: str) -> tuple[str, str, str]:
    """(label, value, colour) for a metric: `check` (passing, or its errors)
    or `chain` (live rules with something resting on them, of all)."""
    if metric not in METRICS:
        raise ValueError(f"metric is one of {', '.join(METRICS)}")
    if metric == "check":
        from catalyst import check

        report = check.run(dep)
        if report.errors:
            return "catalyst", f"{len(report.errors)} error{'s' if len(report.errors) != 1 else ''}", BAD
        return "catalyst", "passing", WARN if report.warnings else GOOD
    from catalyst import impact, views

    g = views.graph(dep, corpus)
    nodes = impact._nodes(g)
    rested = {target for _, _, target in impact.links(dep, g, nodes)}
    # meta-rules govern the rule system: no work rests on them
    live = [
        r["id"]
        for r in g["rules"]
        if not r.get("retired") and not str(r.get("file") or "").endswith("Rules-of-Rules.md")
    ]
    held = sum(1 for r in live if r in rested)
    share = held / len(live) if live else 1.0
    colour = GOOD if share >= 0.8 else WARN if share >= 0.5 else BAD
    return "rules in use", f"{held}/{len(live)}", colour
