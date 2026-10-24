"""Guards on entering a state (rr-META-021, module v3 M2): a type's
`workflow.guards` maps a state to conditions — `children_closed: <field>`
(every artifact the field cites is closed), `nonempty: <field>`,
`section_written: <heading>` (the section's text differs from the type's
template's), `holds: <condition>` (a field condition, `catalyst.conditions`:
`Classification at least Confidential`). `status set` refuses to enter a
guarded state while one fails; `check` warns about an artifact already in
one."""

from __future__ import annotations

import re

from catalyst.corpus import Artifact, Corpus, is_unset, norm_field, ref_values
from catalyst.deployment import Deployment


def _section(text: str, heading: str) -> str:
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return ""
    return "\n".join(line.strip() for line in m.group(1).strip().splitlines() if line.strip())


def _template_section(dep: Deployment, prefix: str, heading: str) -> str:
    from catalyst.edit import EditError, latest_template

    try:
        return _section(latest_template(dep, dep.etds[prefix]).read_text(encoding="utf-8"), heading)
    except (EditError, OSError, KeyError):
        return ""


def _status(art: Artifact) -> str:
    return (art.get("Status") or "").strip().strip("`")


def failures(dep: Deployment, corpus: Corpus, art: Artifact, state: str) -> list[str]:
    """Why `art` may not enter `state` (empty: it may)."""
    etd = dep.etds.get(art.prefix)
    if etd is None:
        return []
    out = []
    for cond, arg in etd.workflow.guards.get(state, []):
        if cond == "nonempty":
            fd = next((f for f in etd.fields if norm_field(f.name) == norm_field(arg)), None)
            if is_unset(art.get(arg), fd.allowed_values if fd is not None and fd.kind == "enum" else ()):
                out.append(f"`{arg}` is empty")
        elif cond == "children_closed":
            for token in ref_values(art.get(arg) or ""):
                for child in (
                    corpus.artifacts.get(token, [])
                    or [a for i, defs in corpus.artifacts.items() if i.startswith(token + "-") for a in defs][:1]
                ):
                    child_etd = dep.etds.get(child.prefix)
                    closed = set(child_etd.workflow.closed_states) if child_etd else set()
                    if _status(child) not in closed:
                        out.append(f"{child.id} (in `{arg}`) is {_status(child) or 'without a status'}, not closed")
        elif cond == "section_written":
            text = _section(art.file.read_text(encoding="utf-8"), arg)
            if not text or text == _template_section(dep, art.prefix, arg):
                out.append(f"`## {arg}` is not written")
        elif cond == "holds":
            from catalyst import conditions

            try:
                c = conditions.parse(arg)
            except conditions.ConditionError as exc:
                out.append(str(exc))
                continue
            wrong = conditions.problems(c, etd)
            if wrong:
                out.extend(wrong)
            elif not conditions.holds(c, art, etd):
                out.append(f"`{c}` does not hold (`{c.field}` is {conditions.value_of(art, c.field, etd) or 'empty'})")
        else:
            out.append(f"unknown guard `{cond}` (children_closed, nonempty, section_written, holds)")
    return out
