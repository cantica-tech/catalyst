"""The history of one entity (roadmap R5.9): every journal entry that
changed its file, in the journal's causal order, with the file's content
before and after.

The entries are found by the entity's file, not by their label, so a change
journaled under another artifact (a status change recorded with its parent)
is part of the history. The content comes from the blobs the journal names:
the criterion's own git, or the store a server keeps. A blob that is no
longer there gives `null` and keeps its hash. Nothing is written.
"""

from __future__ import annotations

import difflib
import subprocess
from collections.abc import Callable

from catalyst import journal, views
from catalyst.corpus import Corpus
from catalyst.deployment import Deployment

Blob = Callable[[str], bytes | None]


def git_blob(dep: Deployment) -> Blob:
    """Blobs from the criterion's own git."""

    def fetch(sha: str) -> bytes | None:
        res = subprocess.run(["git", "-C", str(dep.root), "cat-file", "blob", sha], capture_output=True, check=False)
        return res.stdout if res.returncode == 0 else None

    return fetch


def _subject(dep: Deployment, corpus: Corpus, item_id: str) -> tuple[str, str, str]:
    """(id, type, criterion-relative file) of an artifact or a rule."""
    found = views.resolve(corpus, item_id)
    if found in corpus.artifacts:
        art = corpus.artifacts[found][0]
        return art.id, art.prefix, art.file.relative_to(dep.root).as_posix()
    if found is None:
        raise views.ViewError(f"no artifact or rule '{item_id}' in this deployment")
    return found, "rule", corpus.rules[found][0].file.relative_to(dep.root).as_posix()


def history(dep: Deployment, corpus: Corpus, item_id: str, blob: Blob | None = None) -> dict:
    """The history of `item_id`: `{id, type, file, entries}`, each entry with
    who, when, why and the file's content `before` and `after`."""
    subject, kind, rel = _subject(dep, corpus, item_id)
    fetch = blob or git_blob(dep)
    gone = journal.redacted_in(dep.root)

    def text(sha: str | None) -> str | None:
        data = fetch(sha) if sha and sha not in gone else None  # a redacted content is never shown
        return data.decode("utf-8", errors="replace") if data is not None else None

    entries = []
    for _, entry, _ in journal.read(dep):
        if entry is None:
            continue
        touched = next(
            (f for f in entry.get("files") or [] if isinstance(f, dict) and f.get("path") == journal.WC + rel), None
        )
        if touched is None:
            continue
        intent = entry.get("intent")
        entries.append(
            {
                "timestamp": entry.get("timestamp"),
                "actor": entry.get("actor"),
                "command": entry.get("command"),
                "action": entry.get("action"),
                "artifact": entry.get("artifact"),
                "tier": entry.get("tier"),
                "intent": intent if isinstance(intent, list) else ([str(intent)] if intent else []),
                "before": touched.get("before"),
                "after": touched.get("after"),
                "content_before": text(touched.get("before")),
                "content_after": text(touched.get("after")),
                "redacted": bool({touched.get("before"), touched.get("after")} & gone),
            }
        )
    return {"id": subject, "type": kind, "file": rel, "entries": entries}


def render(h: dict) -> str:
    lines = [f"{h['id']} ({h['type']})  {h['file']}"]
    for e in h["entries"]:
        lines.append("")
        lines.append(f"{e['timestamp']}  {e['actor']}  {e['command']} {e['action']}  {e['artifact']}")
        lines += [f"    {why}" for why in e["intent"]]
        before, after = e["content_before"], e["content_after"]
        if e["redacted"]:
            lines.append("    (content redacted: `catalyst journal redact`)")
            continue
        if (e["before"] and before is None) or (e["after"] and after is None):
            lines.append("    (content no longer available: the journal names it, the store no longer has it)")
            continue
        diff = difflib.unified_diff(
            (before or "").splitlines(), (after or "").splitlines(), "before", "after", lineterm="", n=2
        )
        lines += [f"    {line}" for line in diff]
    count = len(h["entries"])
    lines += ["", f"{count} change{'' if count == 1 else 's'}"]
    return "\n".join(lines) + "\n"
