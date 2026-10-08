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

import contextlib
import hashlib
import json
import os
import re
import secrets
import string
import subprocess
import tempfile
import time
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


def next_entity_id(dep: Deployment, corpus: Corpus, prefix: str, signer: dict,
                   reserve: bool = False) -> str:
    """The next ID of an entity type. With `reserve`, the number is handed
    out once under the working copy's ID lock, so parallel callers (several
    sub-agents in one session) never get the same one."""
    if prefix not in dep.etds:
        known = ", ".join(sorted(dep.etds))
        raise IdError(f"unknown entity type '{prefix}' (known: {known})")
    userid = _signer_userid(signer)
    if not reserve:
        return f"{prefix}-{highest_number(dep, corpus, prefix) + 1:06d}-{userid}"
    with id_lock(dep):
        number = _reserve(dep, prefix, highest_number(dep, corpus, prefix))
    return f"{prefix}-{number:06d}-{userid}"


def highest_rule_number(dep: Deployment, corpus: Corpus, domain: str) -> int:
    """The highest rule number ever used in `domain`, under any document
    prefix: defined, indexed, cited anywhere in a rule document (a retired
    or removed rule keeps its number) or remembered by the journal."""
    pattern = re.compile(rf"^[a-z]+-{re.escape(domain)}-(\d{{3,6}})")
    ever = set(corpus.rules) | corpus.indexed_rules      # defined or merely indexed
    numbers = [0] + [int(m.group(1)) for r in ever if (m := pattern.match(r))]
    cited = re.compile(rf"(?<![A-Za-z0-9-])[a-z]+-{re.escape(domain)}-(\d{{3,6}})(?![0-9])")
    rules_dir = dep.root / "rules"
    texts = [f for f in rules_dir.rglob("*.md") if "templates" not in f.relative_to(rules_dir).parts] \
        if rules_dir.is_dir() else []
    journal = dep.root / "development" / "journal.jsonl"
    for f in texts + ([journal] if journal.is_file() else []):
        numbers += [int(n) for n in cited.findall(f.read_text(encoding="utf-8", errors="ignore"))]
    return max(numbers)


def next_rule_id(dep: Deployment, corpus: Corpus, doc_prefix: str, domain: str,
                 signer: dict, reserve: bool = False) -> str:
    """The next rule ID in `domain` (numbers are unique within the DOMAIN,
    never reused). `reserve` as for next_entity_id."""
    if domain not in corpus.domains and domain != "META":
        raise IdError(f"domain '{domain}' is not registered in rules/domains/domains.md")
    userid = _signer_userid(signer)
    if not reserve:
        return f"{doc_prefix}-{domain}-{highest_rule_number(dep, corpus, domain) + 1:06d}-{userid}"
    with id_lock(dep):
        number = _reserve(dep, f"rule:{domain}", highest_rule_number(dep, corpus, domain))
    return f"{doc_prefix}-{domain}-{number:06d}-{userid}"


# --- allocation across processes ---------------------------------------------
# Reservations and their lock live outside the tracked tree: in the working
# copy's git directory (never committed, never pushed), else in the system's
# temporary directory. The lock is a file created with O_CREAT|O_EXCL, which
# is atomic on every OS (no fcntl, so it works on Windows too); a lock older
# than LOCK_STALE seconds belongs to a crashed caller and is broken.
LOCK_STALE = 30.0
LOCK_WAIT = 60.0


def state_dir(dep: Deployment) -> Path:
    res = subprocess.run(["git", "-C", str(dep.root), "rev-parse", "--git-path", "catalyst"],
                         capture_output=True, text=True, encoding="utf-8")
    if res.returncode == 0 and res.stdout.strip():
        path = Path(res.stdout.strip())
        return path if path.is_absolute() else (dep.root / path).resolve()
    digest = hashlib.sha256(str(dep.root.resolve()).encode()).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"catalyst-{digest}"


@contextlib.contextmanager
def id_lock(dep: Deployment, wait: float = LOCK_WAIT, stale: float = LOCK_STALE):
    folder = state_dir(dep)
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / "ids.lock"
    deadline = time.monotonic() + wait
    while True:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > stale:
                    lock.unlink()            # a crashed holder: break its lock
                    continue
            except FileNotFoundError:
                continue                     # released meanwhile
            if time.monotonic() > deadline:
                raise IdError(f"the ID lock {lock} is held by another process — retry, or remove it "
                              "if no catalyst command is running") from None
            time.sleep(0.02)
            continue
        try:
            os.write(fd, f"{os.getpid()}\n".encode())
        finally:
            os.close(fd)
        break
    try:
        yield
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def _reserve(dep: Deployment, key: str, highest_seen: int) -> int:
    """One above everything seen or already handed out for `key`; records it.
    Call with the ID lock held."""
    store = state_dir(dep) / "ids.json"
    try:
        reserved = json.loads(store.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        reserved = {}
    if not isinstance(reserved, dict):
        reserved = {}
    number = max(highest_seen, int(reserved.get(key, 0) or 0)) + 1
    reserved[key] = number
    tmp = store.with_name(f"ids.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(reserved, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, store)
    return number
