"""ID allocation (Rules-of-Rules.md §3, §6, §11, §20; INV-26).

- Entity IDs: `<PREFIX>-NNNNNN-<userid>`, NNNNNN global within the type,
  in creation order, never reused — the next number is one above the highest
  ever seen for the prefix, in files, index rows and table rows alike.
- Rule IDs: `<doc prefix>-<DOMAIN>-NNNNNN-<userid>`, NNNNNN unique within
  the DOMAIN.
- userids: 8 characters drawn uniformly from [A-Za-z0-9] with a CSPRNG,
  redrawn from scratch if there is no uppercase letter or on any collision.
"""
from __future__ import annotations

import re
import secrets
import string
from pathlib import Path

from catalyst.corpus import Corpus
from catalyst.deployment import Deployment

USERID_ALPHABET = string.ascii_letters + string.digits
USERID_LENGTH = 8


class IdError(Exception):
    pass


def generate_userid(existing: set[str], rng=secrets.choice) -> str:
    while True:
        candidate = "".join(rng(USERID_ALPHABET) for _ in range(USERID_LENGTH))
        if any(c.isupper() for c in candidate) and candidate not in existing:
            return candidate


def resolve_signer(dep: Deployment, corpus: Corpus, as_user: str | None = None) -> dict:
    """The registered user signing this operation (CODE-OF-CONDUCT.md §2):
    `--as` when given, else the only active user. Never guessed from git
    config — with several users and no `--as`, the caller must ask."""
    if as_user:
        user = corpus.user(as_user)
        if user is None:
            raise IdError(f"'{as_user}' is not a registered user — /user-add first")
        return user
    active = [u for u in corpus.users if u.get("active", True)]
    if len(active) == 1:
        return active[0]
    raise IdError("cannot tell who is signing — pass --as <name|git_username>")


def _signer_userid(user: dict) -> str:
    userid = user.get("userid")
    if not userid:
        raise IdError(f"user '{user.get('name')}' has no userid — register one first (INV-26)")
    return str(userid)


def highest_number(dep: Deployment, corpus: Corpus, prefix: str) -> int:
    pattern = re.compile(rf"\b{re.escape(prefix)}-(\d{{3,6}})\b")
    numbers = [0]
    etd = dep.etds.get(prefix)
    folder = dep.folder(etd) if etd else None
    if folder is not None:
        for f in folder.rglob("*.md"):
            numbers += [int(n) for n in pattern.findall(f.name)]
            if etd.naming == "free-form" or f.name == f"{folder.name}.md":
                numbers += [int(n) for n in pattern.findall(f.read_text(encoding="utf-8", errors="ignore"))]
    numbers += [int(m.group(1)) for i in corpus.artifacts if (m := pattern.match(i))]
    # the journal remembers every ID ever touched, even if its file is gone
    journal = dep.root / "development" / "journal.jsonl"
    if journal.is_file():
        numbers += [int(n) for n in pattern.findall(journal.read_text(encoding="utf-8", errors="ignore"))]
    return max(numbers)


def next_entity_id(dep: Deployment, corpus: Corpus, prefix: str, signer: dict) -> str:
    if prefix not in dep.etds:
        known = ", ".join(sorted(dep.etds))
        raise IdError(f"unknown entity type '{prefix}' (known: {known})")
    return f"{prefix}-{highest_number(dep, corpus, prefix) + 1:06d}-{_signer_userid(signer)}"


def next_rule_id(dep: Deployment, corpus: Corpus, doc_prefix: str, domain: str,
                 signer: dict) -> str:
    if domain not in corpus.domains and domain != "META":
        raise IdError(f"domain '{domain}' is not registered in rules/domains/domains.md")
    pattern = re.compile(rf"^[a-z]+-{re.escape(domain)}-(\d{{3,6}})")
    ever = set(corpus.rules) | corpus.indexed_rules      # defined or merely indexed
    numbers = [0] + [int(m.group(1)) for r in ever if (m := pattern.match(r))]
    return f"{doc_prefix}-{domain}-{max(numbers) + 1:06d}-{_signer_userid(signer)}"
