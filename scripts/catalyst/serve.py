"""`catalyst serve` and its share driver (roadmap R3.9).

The server is a remote that understands catalyst. It keeps every version of
a criterion's files as git blobs and takes pushes one batch at a time; each
person's criterion stays in catalyst's home and works offline
(`what-is-going-on/19-server-design.md`, decisions of 2026-10-10).

Server side (`Server`, SQLite from the standard library):

- the truth is `batches` (who pushed, when), `changes` (each file's
  `before` and `after` in a batch) and `blobs` (every version, by its git
  hash, checked on arrival); `files` (each path's current version) and
  `ids` (which file holds which artifact ID) are derived, and `rebuild`
  recomputes them;
- a push is applied all or nothing. It is refused, with nothing applied,
  when a file moved on the server since the client's version (409), when a
  journal shard is not appended to, when a change to a file the server
  already has is not journaled, when a new entry names a signer other than
  the token's user, when an artifact ID is already another file's, or when
  a `RECON-` case changes beyond the signer's `reconciliation` level;
- the first push is an import: it brings the whole history, signed by
  whoever made it, so only its signers are not checked;
- every request carries a bearer token; the server stores only its hash.
  Tokens are issued and revoked on the server's host (`catalyst serve
  token`).

Client side (`ServeShare`, the `serve` share driver): `catalyst.toml` has
`share = "serve"` and `share_url = "<url>"`; the token is in
`$CATALYST_HOME/credentials` (`catalyst share login`), never in a criterion
or a project. The client remembers the server's state it last saw (batch
number, each file's version) in the criterion's git directory: a file that
differs from it is a local change, and a pull that would overwrite one
stops with nothing written.

JSON over HTTP, `/v1`: `GET head`, `GET changes?since=<batch>`,
`GET blobs/<sha>`, `POST have` (which blobs the server lacks), `POST push`.
The read side (R3.9 S3) answers what the CLI's read commands
answer, with their own code over the server's current files:
`GET list?type=&filter=`, `GET view/<id>`, `GET backlog`,
`GET journal?since=&artifact=&actor=&rule=`, `GET graph` (header
`X-Catalyst-Batch`: the batch the answer is for), and `GET events`, a
server-sent event stream of batch numbers.

Local mode (`catalyst serve --local`, `LocalReader`): the same read
endpoints over one project's own criterion, read-only, on loopback, with a
token made for the run; `GET check` returns `catalyst check --json`. A
client reads every criterion the same way, served or not.
"""

from __future__ import annotations

import base64
import contextlib
import datetime
import hashlib
import http.server
import json
import os
import re
import secrets
import sqlite3
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

API = "/v1"
WC = ".criterion/"
LEVELS = {"none": 0, "propose": 1, "full": 2}
USERS = "IAM/users/users.json"
ROLES = "IAM/roles/roles.json"
MAX_BODY = 512 * 1024 * 1024
ID_FIELD = re.compile(r"^\| \*\*ID\*\* \| `([^`]+)` \|", re.M)
STATUS_FIELD = re.compile(r"^\| \*\*Status\*\* \| ([^|]+?) \|", re.M)

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches(seq INTEGER PRIMARY KEY, userid TEXT NOT NULL, time TEXT NOT NULL, message TEXT);
CREATE TABLE IF NOT EXISTS changes(seq INTEGER NOT NULL, path TEXT NOT NULL, before TEXT, after TEXT,
                                   PRIMARY KEY (seq, path));
CREATE TABLE IF NOT EXISTS blobs(sha TEXT PRIMARY KEY, bytes BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, sha TEXT NOT NULL, seq INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS ids(id TEXT PRIMARY KEY, path TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tokens(id INTEGER PRIMARY KEY, hash TEXT UNIQUE NOT NULL, userid TEXT NOT NULL,
                                  created TEXT NOT NULL, revoked TEXT);
"""


class ServeError(Exception):
    """A refusal, with the HTTP status that carries it and its details."""

    def __init__(self, status: int, message: str, **details):
        super().__init__(message)
        self.status, self.details = status, details

    def payload(self) -> dict:
        return {"error": str(self), **self.details}


def now() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def blob_sha(data: bytes, length: int = 40) -> str:
    """A git blob's object id (SHA-1, or SHA-256 for a 64-hex id)."""
    h = hashlib.sha256() if length == 64 else hashlib.sha1(usedforsecurity=False)  # git's object id
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


EMPTY = {blob_sha(b""), blob_sha(b"", 64)}  # an empty file: known everywhere, stored nowhere


def safe_path(path: object) -> str:
    """A criterion-relative path, refused when it could leave the criterion."""
    p = str(path)
    parts = p.split("/")
    if not p or p.startswith("/") or "\\" in p or "\0" in p or ".." in parts or parts[0] in (".git", ""):
        raise ServeError(422, f"'{p}' is not a criterion-relative path")
    return p


def is_journal(path: str) -> bool:
    return path == "development/journal.jsonl" or (path.startswith("development/journal/") and path.endswith(".jsonl"))


def slug(value: object) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", str(value or "").strip().lower()).strip("-.")


def field_of(pattern: re.Pattern, data: bytes | None) -> str | None:
    if data is None:
        return None
    found = pattern.search(data.decode("utf-8", "replace"))
    return found.group(1).strip() if found else None


def entries_in(old: bytes | None, new: bytes | None) -> list[dict]:
    """The entries a push appends to a journal shard (ServeError when it
    does anything but append)."""
    old = old or b""
    if new is None or not new.startswith(old):
        raise ServeError(422, "a journal shard is append-only: a push may only add lines to it")
    out = []
    for line in new[len(old) :].decode("utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            raise ServeError(422, "a pushed journal line is not JSON") from None
        if not isinstance(entry, dict):
            raise ServeError(422, "a pushed journal line is not an entry")
        out.append(entry)
    return out


def entry_shas(entry: dict) -> list[tuple[str, str]]:
    """(criterion path, blob) for every criterion version an entry names."""
    out = []
    for f in entry.get("files") or []:
        if isinstance(f, dict) and str(f.get("path", "")).startswith(WC):
            for key in ("before", "after"):
                if f.get(key):
                    out.append((str(f["path"])[len(WC) :], str(f[key])))
    return out


# --- the server -------------------------------------------------------------
class Reads:
    """The read side, over whatever `loaded()` gives: the CLI's own views."""

    def loaded(self) -> tuple:  # (batch, deployment, corpus)
        raise NotImplementedError

    def check(self) -> dict:
        raise ServeError(501, "check runs where the criterion's git history is: `catalyst serve --local`, or the CLI")

    def read(self, what: str, query: dict[str, list[str]], item: str = "") -> tuple[int, object]:
        """(batch, what `catalyst <what> --json` prints) for list, view,
        backlog and journal."""
        from catalyst import views
        from catalyst.journal import JournalError

        seq, dep, corpus = self.loaded()
        one = lambda key: (query.get(key) or [None])[0]  # noqa: E731
        try:
            if what == "list":
                data = views.list_items(
                    dep, corpus, one("type") or "all", views.parse_filters(query.get("filter")), one("template_type")
                )
            elif what == "view":
                data = views.view(dep, corpus, item)
            elif what == "graph":
                data = views.graph(dep, corpus)
            elif what == "inbox":
                from catalyst import inbox

                data = inbox.inbox(dep, corpus)
            elif what == "history":
                from catalyst import history

                # a served criterion has no git of its own: its blobs are the server's
                held = getattr(self, "blob", None)
                has_git = (dep.root / ".git").exists()
                data = history.history(dep, corpus, item, None if has_git or held is None else held)
            elif what == "impact":
                from catalyst import impact

                depth = one("depth")
                data = impact.impact(dep, corpus, item, one("direction") or "both", int(depth) if depth else None)
            elif what == "backlog":
                data = views.backlog(dep, corpus)
            else:
                data = views.journal_entries(dep, one("since"), one("artifact"), one("actor"), one("rule"))
        except views.ViewError as e:
            raise ServeError(404, str(e)) from None
        except JournalError as e:
            raise ServeError(400, str(e)) from None
        return seq, data


class Server(Reads):
    def __init__(self, db: Path):
        self.db = Path(db)
        self.db.parent.mkdir(parents=True, exist_ok=True)
        self._write = threading.Lock()
        self._loading = threading.Lock()
        self._loaded: tuple | None = None  # (batch, deployment, corpus) the reads answer from
        self.changed = threading.Condition()  # notified when a batch lands (the events stream)
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextlib.contextmanager
    def _conn(self):
        c = sqlite3.connect(self.db, timeout=30, isolation_level=None)
        try:
            yield c
        finally:
            c.close()

    # tokens (the host's commands)
    def issue(self, userid: str) -> tuple[int, str]:
        token = "cst_" + secrets.token_urlsafe(32)  # never starts with "-" (an option), and scanners can spot it
        with self._conn() as c:
            cur = c.execute("INSERT INTO tokens(hash, userid, created) VALUES (?, ?, ?)", (_hash(token), userid, now()))
            return int(cur.lastrowid or 0), token

    def revoke(self, token_id: int) -> bool:
        with self._conn() as c:
            cur = c.execute("UPDATE tokens SET revoked = ? WHERE id = ? AND revoked IS NULL", (now(), token_id))
            return cur.rowcount == 1

    def tokens(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("SELECT id, userid, created, revoked FROM tokens ORDER BY id").fetchall()
        return [{"id": r[0], "userid": r[1], "created": r[2], "revoked": r[3]} for r in rows]

    def user_for(self, token: str) -> str | None:
        with self._conn() as c:
            row = c.execute("SELECT userid FROM tokens WHERE hash = ? AND revoked IS NULL", (_hash(token),)).fetchone()
        return row[0] if row else None

    # reads
    def head(self) -> dict:
        with self._conn() as c:
            seq = c.execute("SELECT COALESCE(MAX(seq), 0) FROM batches").fetchone()[0]
            count = c.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        return {"seq": seq, "files": count}

    def changes_since(self, since: int) -> dict:
        """Each path changed after batch `since`, at its current version
        (None: deleted), and the batch that is current."""
        with self._conn() as c:
            c.execute("BEGIN")
            seq = c.execute("SELECT COALESCE(MAX(seq), 0) FROM batches").fetchone()[0]
            paths = [r[0] for r in c.execute("SELECT DISTINCT path FROM changes WHERE seq > ?", (since,))]
            files = {p: _current(c, p) for p in paths}
            c.execute("COMMIT")
        return {"seq": seq, "files": files}

    def blob(self, sha: str) -> bytes | None:
        with self._conn() as c:
            row = c.execute("SELECT bytes FROM blobs WHERE sha = ?", (sha,)).fetchone()
        return bytes(row[0]) if row else None

    def missing(self, shas: list[str]) -> list[str]:
        with self._conn() as c:
            return [
                s
                for s in dict.fromkeys(shas)
                if s not in EMPTY and not c.execute("SELECT 1 FROM blobs WHERE sha = ?", (s,)).fetchone()
            ]

    # the one write
    def push(self, userid: str, base: int, changes: list[dict], blobs: dict[str, bytes], message: str = "") -> dict:
        with self._write, self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                out = self._apply(c, userid, base, changes, blobs, message)
            except BaseException:
                c.execute("ROLLBACK")
                raise
            c.execute("COMMIT")
        with self.changed:
            self.changed.notify_all()
        return out

    def _apply(self, c, userid: str, base: int, changes: list[dict], blobs: dict[str, bytes], message: str) -> dict:
        for sha, data in blobs.items():
            if blob_sha(data, len(sha)) != sha:
                raise ServeError(422, f"blob {sha[:10]} does not match its content")
        rows = []
        for ch in changes:
            rows.append((safe_path(ch.get("path")), ch.get("before") or None, ch.get("after") or None))
        if not rows:
            raise ServeError(422, "nothing to push")
        if len({p for p, _, _ in rows}) != len(rows):
            raise ServeError(422, "a path is named twice in one push")
        conflicts = [
            {"path": p, "from": before, "server": cur} for p, before, _ in rows if (cur := _current(c, p)) != before
        ]
        if conflicts:
            raise ServeError(
                409,
                "files moved on the server since your version: pull, then settle each with a human",
                conflicts=conflicts,
            )

        def content(sha: str | None) -> bytes | None:
            if sha is None:
                return None
            if sha in blobs:
                return blobs[sha]
            if sha in EMPTY:
                return b""
            row = c.execute("SELECT bytes FROM blobs WHERE sha = ?", (sha,)).fetchone()
            if row is None:
                raise ServeError(422, f"blob {sha[:10]} is neither in the push nor on the server")
            return bytes(row[0])

        after_of = {p: after for p, _, after in rows}

        def pre(path: str) -> bytes | None:  # the server's version, else the pushed one (a first push)
            cur = _current(c, path)
            return content(cur) if cur else content(after_of.get(path))

        user = _user(pre(USERS), userid)
        entries = []
        for p, before, after in rows:
            if is_journal(p):
                entries += entries_in(content(before), content(after))
            elif after is not None:
                content(after)
        names = {slug(user.get("name")), slug(user.get("git_username"))} - {""}
        importing = c.execute("SELECT COUNT(*) FROM batches").fetchone()[0] == 0
        journaled = set()
        for entry in entries:
            if not importing and slug(entry.get("actor")) not in names:
                raise ServeError(
                    403, f"an entry is signed by '{entry.get('actor')}', but this token is {user.get('name')}'s"
                )
            cli = str(entry.get("writer", "")).startswith("catalyst/")
            for path, sha in entry_shas(entry):
                journaled.add((path, sha))
                if cli:
                    content(sha)  # every version a new entry names stays verifiable
        for p, before, after in rows:
            if not is_journal(p) and before is not None and (p, after) not in journaled:
                raise ServeError(422, f"{p} changed without a journal entry (`catalyst unrecorded`)")

        roles = _levels(pre(ROLES))
        level = max((LEVELS.get(roles.get(str(r), "none"), 0) for r in user.get("roles") or []), default=0)
        deleted = {p for p, _, after in rows if after is None}
        for p, before, after in rows:
            if not p.endswith(".md"):
                continue
            new = content(after)
            if p.startswith("reconciliations/") and "/templates/" not in p:
                if level < LEVELS["propose"]:
                    raise ServeError(403, f"{p}: {user.get('name')} has no reconciliation rights")
                old_status, new_status = field_of(STATUS_FIELD, content(before)), field_of(STATUS_FIELD, new)
                decided = new_status is not None and (new_status.startswith("Resolved-") or new_status == "Closed")
                if decided and new_status != old_status and level < LEVELS["full"]:
                    raise ServeError(403, f"{p}: deciding a case needs a `full` reconciliation role")
            art = field_of(ID_FIELD, new)
            if art:
                owner = c.execute("SELECT path FROM ids WHERE id = ?", (art,)).fetchone()
                if owner and owner[0] != p and owner[0] not in deleted:
                    raise ServeError(
                        409, f"{art} is already {owner[0]} on the server", conflicts=[{"path": p, "id": art}]
                    )

        previous = c.execute("SELECT COALESCE(MAX(seq), 0) FROM batches").fetchone()[0]
        seq = previous + 1
        c.execute("INSERT INTO batches(seq, userid, time, message) VALUES (?, ?, ?, ?)", (seq, userid, now(), message))
        for sha, data in blobs.items():
            c.execute("INSERT OR IGNORE INTO blobs(sha, bytes) VALUES (?, ?)", (sha, data))
        for p, before, after in rows:
            c.execute("INSERT INTO changes(seq, path, before, after) VALUES (?, ?, ?, ?)", (seq, p, before, after))
            _project(c, seq, p, after, content(after))
        return {"seq": seq, "previous": previous, "base": base, "files": len(rows)}

    def rebuild(self) -> None:
        """Recompute the derived tables from the batches and the blobs."""
        with self._write, self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            c.execute("DELETE FROM files")
            c.execute("DELETE FROM ids")
            for seq, p, after in c.execute("SELECT seq, path, after FROM changes ORDER BY seq, path").fetchall():
                row = c.execute("SELECT bytes FROM blobs WHERE sha = ?", (after,)).fetchone() if after else None
                _project(c, seq, p, after, bytes(row[0]) if row else None)
            c.execute("COMMIT")

    # the read side: the CLI's own views over the current files
    def tree(self) -> Path:
        """The current files, as a directory beside the database: a
        projection of the `files` table, rebuilt whenever the batch moves,
        never the truth."""
        return self.db.with_name(self.db.stem + ".tree")

    def loaded(self) -> tuple:
        """(batch, deployment, corpus) for the latest batch, loaded once per
        batch."""
        from catalyst.corpus import load_corpus
        from catalyst.deployment import DeploymentNotFound, load_working_copy

        with self._loading:
            with self._conn() as c:
                c.execute("BEGIN")
                seq = c.execute("SELECT COALESCE(MAX(seq), 0) FROM batches").fetchone()[0]
                if self._loaded and self._loaded[0] == seq:
                    c.execute("COMMIT")
                    return self._loaded
                files = dict(c.execute("SELECT path, sha FROM files").fetchall())
                manifest = self.tree().with_suffix(".json")
                try:
                    have = json.loads(manifest.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    have = {}
                root = self.tree()
                for path in set(have) - set(files):
                    (root / path).unlink(missing_ok=True)
                for path, sha in files.items():
                    if have.get(path) != sha or not (root / path).is_file():
                        data = (
                            b""
                            if sha in EMPTY
                            else c.execute("SELECT bytes FROM blobs WHERE sha = ?", (sha,)).fetchone()[0]
                        )
                        (root / path).parent.mkdir(parents=True, exist_ok=True)
                        (root / path).write_bytes(bytes(data))
                c.execute("COMMIT")
            manifest.write_text(json.dumps(files, sort_keys=True), encoding="utf-8")
            try:
                dep = load_working_copy(root)
            except DeploymentNotFound:
                raise ServeError(
                    404, "the server holds no criterion yet (`catalyst share create --driver serve`)"
                ) from None
            self._loaded = (seq, dep, load_corpus(dep))
            return self._loaded

    def batch(self) -> int:
        with self._conn() as c:
            return c.execute("SELECT COALESCE(MAX(seq), 0) FROM batches").fetchone()[0]

    def derived(self) -> tuple[list, list]:
        with self._conn() as c:
            return (
                c.execute("SELECT path, sha, seq FROM files ORDER BY path").fetchall(),
                c.execute("SELECT id, path FROM ids ORDER BY id").fetchall(),
            )


class LocalReader(Reads):
    """`catalyst serve --local`: one project's own criterion, read-only, for
    a client on this machine. Its batch is a change counter: it moves when a
    criterion file changes (polled every second), and `events` sends it."""

    read_only = True

    def __init__(self, project: Path, token: str, poll: float = 1.0):
        self.project = Path(project)
        self._token = _hash(token)
        self._stamp_lock, self._loading = threading.Lock(), threading.Lock()
        self._stamp: tuple | None = None
        self._batch = 0
        self._loaded: tuple | None = None
        self._checked: tuple | None = None
        self.changed = threading.Condition()
        self.root = self._load()[0].root
        self.refresh()
        if poll:
            threading.Thread(target=self._poll, args=(poll,), daemon=True).start()

    def _load(self) -> tuple:
        from catalyst.corpus import load_corpus
        from catalyst.deployment import load

        dep = load(self.project)
        return dep, load_corpus(dep)

    def _poll(self, every: float) -> None:
        import time

        while True:
            time.sleep(every)
            self.refresh()

    def user_for(self, token: str) -> str | None:
        return "local" if secrets.compare_digest(_hash(token), self._token) else None

    def _fingerprint(self) -> tuple:
        out = []
        for base, dirs, files in os.walk(self.root):
            dirs[:] = sorted(d for d in dirs if d not in (".git", ".venv", "__pycache__"))
            for name in sorted(files):
                path = Path(base) / name
                try:
                    st = path.stat()
                except OSError:
                    continue
                out.append((path.relative_to(self.root).as_posix(), st.st_size, st.st_mtime_ns))
        return tuple(out)

    def refresh(self) -> int:
        """The batch, moved on when a criterion file changed since last seen."""
        stamp = self._fingerprint()
        with self._stamp_lock:
            moved = stamp != self._stamp
            if moved:
                self._stamp, self._batch = stamp, self._batch + 1
            batch = self._batch
        if moved:
            with self.changed:
                self.changed.notify_all()
        return batch

    def batch(self) -> int:
        return self.refresh()

    def head(self) -> dict:
        return {"seq": self.batch(), "files": len(self._stamp or ())}

    def loaded(self) -> tuple:
        batch = self.refresh()
        with self._loading:
            if not self._loaded or self._loaded[0] != batch:
                self._loaded = (batch, *self._load())
            return self._loaded

    def check(self) -> dict:
        """What `catalyst check --json` prints, once per change."""
        from catalyst.check import run

        batch, dep, _ = self.loaded()
        with self._loading:
            if not self._checked or self._checked[0] != batch:
                report = run(dep)
                self._checked = (
                    batch,
                    {"ok": not report.failing(False), "errors": report.errors, "warnings": report.warnings},
                )
            return self._checked[1]


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _current(c, path: str) -> str | None:
    row = c.execute("SELECT sha FROM files WHERE path = ?", (path,)).fetchone()
    return row[0] if row else None


def _project(c, seq: int, path: str, after: str | None, data: bytes | None) -> None:
    c.execute("DELETE FROM ids WHERE path = ?", (path,))
    if after is None:
        c.execute("DELETE FROM files WHERE path = ?", (path,))
        return
    c.execute("INSERT OR REPLACE INTO files(path, sha, seq) VALUES (?, ?, ?)", (path, after, seq))
    art = field_of(ID_FIELD, data) if path.endswith(".md") else None
    if art:
        c.execute("INSERT OR REPLACE INTO ids(id, path) VALUES (?, ?)", (art, path))


def _json(data: bytes | None, key: str) -> list:
    try:
        value = json.loads(data or b"{}").get(key, [])
    except (ValueError, AttributeError):
        return []
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _user(users: bytes | None, userid: str) -> dict:
    for user in _json(users, "users"):
        if user.get("userid") == userid:
            if user.get("active") is False:
                raise ServeError(403, f"{user.get('name')} is deactivated")
            return user
    raise ServeError(403, "this token's user is not a registered user of the criterion")


def _levels(roles: bytes | None) -> dict[str, str]:
    return {str(r.get("name")): str(r.get("reconciliation") or "none") for r in _json(roles, "roles")}


# --- HTTP ---------------------------------------------------------------------
class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "catalyst-serve/1"
    app: Server

    def log_message(self, format, *args):  # quiet: a server for a few people, not a web log
        pass

    def _send(self, status: int, payload: object = None, raw: bytes | None = None, batch: int | None = None) -> None:
        if raw is None:
            payload = {} if payload is None else payload
            raw = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
            kind = "application/json"
        else:
            kind = "application/octet-stream"
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(raw)))
        if batch is not None:
            self.send_header("X-Catalyst-Batch", str(batch))
        self.end_headers()
        self.wfile.write(raw)

    def _events(self) -> None:
        """Server-sent events: the current batch on connect, then each new
        one as it lands; a comment every 15 s keeps proxies from closing."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        last = None
        try:
            while True:
                seq = self.app.batch()
                if seq != last:
                    self.wfile.write(f"event: batch\ndata: {seq}\n\n".encode())
                    last = seq
                else:
                    self.wfile.write(b": still here\n\n")
                self.wfile.flush()
                with self.app.changed:
                    self.app.changed.wait(timeout=15)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return  # the client left

    def _route(self, method: str) -> None:
        try:
            auth = self.headers.get("Authorization", "")
            userid = self.app.user_for(auth[7:]) if auth.startswith("Bearer ") else None
            if userid is None:
                raise ServeError(401, "a valid token is required (`catalyst share login`)")
            url = urllib.parse.urlparse(self.path)
            path = url.path.removeprefix(API)
            if getattr(self.app, "read_only", False) and (
                path in ("/changes", "/have", "/push") or path.startswith("/blobs/")
            ):
                raise ServeError(405, "this is a local, read-only view of one criterion")
            if method == "GET" and path == "/head":
                return self._send(200, self.app.head())
            if method == "GET" and path == "/changes":
                since = urllib.parse.parse_qs(url.query).get("since", ["0"])[0]
                return self._send(200, self.app.changes_since(int(since) if since.isdigit() else 0))
            if method == "GET" and path.startswith("/blobs/"):
                data = self.app.blob(path[len("/blobs/") :])
                return self._send(200, raw=data) if data is not None else self._send(404, {"error": "no such blob"})
            if method == "GET" and path == "/events":
                return self._events()
            if method == "GET" and path == "/check":
                return self._send(200, self.app.check(), batch=self.app.batch())
            if method == "GET" and (
                path in ("/list", "/backlog", "/journal", "/graph", "/inbox")
                or path.startswith(("/view/", "/impact/", "/history/"))
            ):
                what, _, item = path.strip("/").partition("/")
                seq, data = self.app.read(what, urllib.parse.parse_qs(url.query), urllib.parse.unquote(item))
                return self._send(200, data, batch=seq)
            if method == "POST" and path in ("/have", "/push"):
                length = int(self.headers.get("Content-Length") or 0)
                if length > MAX_BODY:
                    raise ServeError(413, "the push is too large")
                body = json.loads(self.rfile.read(length) or b"{}")
                if path == "/have":
                    return self._send(200, {"missing": self.app.missing([str(s) for s in body.get("shas", [])])})
                blobs = {str(k): base64.b64decode(v) for k, v in (body.get("blobs") or {}).items()}
                res = self.app.push(
                    userid, int(body.get("base") or 0), body.get("changes") or [], blobs, str(body.get("message") or "")
                )
                return self._send(200, res)
            raise ServeError(404, f"no such endpoint: {method} {url.path}")
        except ServeError as e:
            self._send(e.status, e.payload())
        except (ValueError, TypeError) as e:
            self._send(400, {"error": f"bad request: {e}"})

    def do_GET(self):  # http.server's name
        self._route("GET")

    def do_POST(self):
        self._route("POST")


def make_server(db: Path, host: str = "127.0.0.1", port: int = 8765) -> http.server.ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"app": Server(db)})
    return http.server.ThreadingHTTPServer((host, port), handler)


def make_local(project: Path, port: int = 0, poll: float = 1.0) -> tuple[http.server.ThreadingHTTPServer, str]:
    """A read-only server over one project's criterion, on loopback only, and
    its token (fresh per run, never stored)."""
    token = "cst_" + secrets.token_urlsafe(32)
    handler = type("LocalHandler", (Handler,), {"app": LocalReader(project, token, poll)})
    return http.server.ThreadingHTTPServer(("127.0.0.1", port), handler), token


def default_db() -> Path:
    import project_file

    return project_file.home() / "serve" / "serve.db"


# --- the client ----------------------------------------------------------------
def credentials_file() -> Path:
    import project_file

    return project_file.home() / "credentials"


def _norm(url: str) -> str:
    return url.rstrip("/")


def token_for(url: str) -> str | None:
    if os.environ.get("CATALYST_TOKEN"):
        return os.environ["CATALYST_TOKEN"]
    try:
        return json.loads(credentials_file().read_text(encoding="utf-8")).get(_norm(url))
    except (OSError, ValueError, AttributeError):
        return None


def save_token(url: str, token: str) -> Path:
    path = credentials_file()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data[_norm(url)] = token
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return path


@dataclass
class Client:
    url: str
    token: str | None

    def call(self, method: str, path: str, body: dict | None = None, raw: bool = False):
        from catalyst.store import ShareError

        if not self.token:
            raise ShareError(
                f"no token for {self.url}: `catalyst share login {self.url}` (the server's host issues one)"
            )
        data = json.dumps(body).encode("utf-8") if body is not None else None
        target = _norm(self.url) + API + path
        if urllib.parse.urlparse(target).scheme not in ("http", "https"):
            raise ShareError(f"{self.url} is not an http(s) URL")
        req = urllib.request.Request(target, data=data, method=method)  # noqa: S310 (scheme checked above)
        req.add_header("Authorization", f"Bearer {self.token}")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=120) as res:  # noqa: S310 (scheme checked above)
                out = res.read()
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read() or b"{}")
            except ValueError:
                payload = {}
            raise ServeError(
                e.code, str(payload.get("error") or e.reason), **{k: v for k, v in payload.items() if k != "error"}
            ) from None
        except urllib.error.URLError as e:
            raise ShareError(f"cannot reach {self.url}: {e.reason}") from None
        return out if raw else json.loads(out or b"{}")


def _git(root: Path, *args: str, input: bytes | None = None) -> bytes:
    res = subprocess.run(["git", "-C", str(root), *args], input=input, capture_output=True, check=False)
    if res.returncode != 0:
        from catalyst.store import ShareError

        raise ShareError(f"git {args[0]} failed in {root}: {res.stderr.decode('utf-8', 'replace').strip()}")
    return res.stdout


def tracked(root: Path) -> dict[str, str]:
    """Every file the criterion shares (what git would track), with the blob
    id of its content; the blobs are written to the criterion's git."""
    paths = [
        p
        for p in _git(root, "ls-files", "-z", "-co", "--exclude-standard").decode("utf-8").split("\0")
        if p and "\n" not in p and (root / p).is_file()
    ]
    paths = sorted(set(paths))
    if not paths:
        return {}
    shas = _git(root, "hash-object", "-w", "--stdin-paths", input="\n".join(paths).encode("utf-8") + b"\n").split()
    return dict(zip(paths, (s.decode() for s in shas), strict=True))


def read_blobs(root: Path, shas: list[str]) -> dict[str, bytes]:
    """The blobs the criterion's git has, among `shas` (an empty file's
    always)."""
    found = {s: b"" for s in shas if s in EMPTY}
    shas = [s for s in shas if s not in EMPTY]
    if not shas:
        return found
    out = _git(root, "cat-file", "--batch", input="".join(f"{s}\n" for s in shas).encode())
    i = 0
    while i < len(out):
        nl = out.index(b"\n", i)
        header = out[i:nl].split()
        i = nl + 1
        if len(header) == 3 and header[1] == b"blob":
            size = int(header[2])
            found[header[0].decode()] = out[i : i + size]
            i += size + 1
    return found


def store_blobs(root: Path, blobs: dict[str, bytes]) -> None:
    """Write blobs into the criterion's git, checking each one's id."""
    if not blobs:
        return
    with tempfile.TemporaryDirectory() as tmp:
        names = []
        for sha, data in blobs.items():
            (Path(tmp) / sha).write_bytes(data)
            names.append(str(Path(tmp) / sha))
        got = _git(root, "hash-object", "-w", "--no-filters", "--stdin-paths", input="\n".join(names).encode() + b"\n")
    if [s.decode() for s in got.split()] != list(blobs):
        raise ServeError(422, "a blob from the server does not match its id")


@dataclass
class ServePreview:
    url: str
    changes: list[dict] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.changes

    def describe(self) -> str:
        if self.empty:
            return "nothing to publish: the criterion matches its shared copy"
        lines = [f"publish to {self.url} ({len(self.changes)} file(s)):"]
        for ch in self.changes:
            mark = "A" if ch["before"] is None else "D" if ch["after"] is None else "M"
            lines.append(f"  {mark} {ch['path']}")
        return "\n".join(lines)


@dataclass
class ServeShare:
    """The `serve` share driver: a `catalyst serve` server."""

    dep: object
    driver: str = "serve"

    @property
    def root(self) -> Path:
        return self.dep.root  # type: ignore[attr-defined]

    @property
    def url(self) -> str:
        from catalyst.store import ShareError

        url = self.dep.pointer.get("share_url")  # type: ignore[attr-defined]
        if not url:
            raise ShareError('catalyst.toml has share = "serve" but no share_url')
        return str(url)

    def client(self) -> Client:
        return Client(self.url, token_for(self.url))

    # what this criterion last saw of the server
    def _state_file(self) -> Path:
        from catalyst.lock import state_dir

        return state_dir(self.root) / "serve.json"

    def base(self) -> dict:
        try:
            data = json.loads(self._state_file().read_text(encoding="utf-8"))
            if data.get("url") == _norm(self.url):
                return {"seq": int(data.get("seq", 0)), "files": dict(data.get("files") or {})}
        except (OSError, ValueError, AttributeError):
            pass
        return {"seq": 0, "files": {}}

    def _save(self, base: dict) -> None:
        path = self._state_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"url": _norm(self.url), **base}, indent=1, sort_keys=True), encoding="utf-8")

    def changes(self) -> list[dict]:
        base, local = self.base()["files"], tracked(self.root)
        return [
            {"path": p, "before": base.get(p), "after": local.get(p)}
            for p in sorted(set(base) | set(local))
            if base.get(p) != local.get(p)
        ]

    # the Share protocol
    def info(self) -> dict:
        return {"driver": self.driver, "location": self.url, "capabilities": ["pull", "push", "verified-signers"]}

    def status(self, fetch: bool = False):
        from catalyst.store import ShareStatus

        base = self.base()
        behind = None
        if fetch:
            behind = int(self.client().call("GET", "/head")["seq"]) - base["seq"]
        return ShareStatus(self.driver, self.url, None, [c["path"] for c in self.changes()], None, behind, "serve")

    def head(self) -> str | None:
        seq = self.base()["seq"]
        return f"batch {seq}" if seq else None

    def preview(self, fetch: bool = True) -> ServePreview:
        return ServePreview(self.url, self.changes())

    def push(self, signer: dict, message: str, open_pr: bool = True) -> dict:
        from catalyst.store import ShareError

        changes = self.changes()
        if not changes:
            return {"branch": None, "commits": 0, "pull_request": None, "regenerated": [], "seq": self.base()["seq"]}
        shas = {c["after"] for c in changes if c["after"]}
        old = read_blobs(self.root, [c["before"] for c in changes if c["before"] and is_journal(c["path"])])
        new = read_blobs(self.root, [c["after"] for c in changes if c["after"] and is_journal(c["path"])])
        for c in changes:
            if is_journal(c["path"]) and c["after"]:
                try:
                    found = entries_in(old.get(c["before"] or ""), new.get(c["after"]))
                except ServeError as e:
                    raise ShareError(f"{c['path']}: {e}") from None
                shas |= {sha for e in found for _, sha in entry_shas(e)}
        client = self.client()
        missing = client.call("POST", "/have", {"shas": sorted(shas)})["missing"]
        blobs = read_blobs(self.root, missing)
        try:
            res = client.call(
                "POST",
                "/push",
                {
                    "base": self.base()["seq"],
                    "message": message,
                    "changes": changes,
                    "blobs": {k: base64.b64encode(v).decode() for k, v in blobs.items()},
                },
            )
        except ServeError as e:
            detail = "".join(f"\n  {c.get('path')}" for c in e.details.get("conflicts", []))
            raise ShareError(f"push refused, nothing published: {e}{detail}") from None
        base = self.base()
        for c in changes:
            if c["after"] is None:
                base["files"].pop(c["path"], None)
            else:
                base["files"][c["path"]] = c["after"]
        if res["previous"] == base["seq"]:
            base["seq"] = res["seq"]  # nothing of anyone else's in between
        self._save(base)
        return {"branch": None, "commits": res["files"], "pull_request": None, "regenerated": [], "seq": res["seq"]}

    def pull(self) -> str:
        from catalyst import journal
        from catalyst.store import ShareError

        client, base = self.client(), self.base()
        data = client.call("GET", f"/changes?since={base['seq']}")
        incoming = {safe_path(p): sha for p, sha in data["files"].items()}
        local = tracked(self.root) if incoming else {}
        clashes = sorted(
            p for p, sha in incoming.items() if local.get(p) != base["files"].get(p) and local.get(p) != sha
        )
        if clashes:
            raise ShareError(
                "pull stopped, nothing written: changed here and on the server — publish or set aside your "
                "version, then pull; a human settles the difference (a RECON- case):\n  " + "\n  ".join(clashes)
            )

        def fetch(shas: set[str]) -> dict[str, bytes]:
            have = read_blobs(self.root, sorted(shas))
            got = {}
            for sha in sorted(shas - set(have)):
                try:
                    body = client.call("GET", f"/blobs/{sha}", raw=True)
                except ServeError as e:
                    if e.status == 404:
                        continue  # a pre-CLI entry's version nobody kept
                    raise
                if blob_sha(body, len(sha)) != sha:
                    raise ShareError(f"blob {sha[:10]} from the server does not match its id")
                got[sha] = body
            store_blobs(self.root, got)
            return {**have, **got}

        contents = fetch({sha for sha in incoming.values() if sha})
        lost = sorted(p for p, sha in incoming.items() if sha and sha not in contents)
        if lost:
            raise ShareError("the server lacks the current version of: " + ", ".join(lost))
        named = set()
        for p, sha in incoming.items():
            if is_journal(p) and sha:
                mine = (self.root / p).read_bytes() if (self.root / p).is_file() else b""
                try:
                    named |= {s for e in entries_in(mine, contents[sha]) for _, s in entry_shas(e)}
                except ServeError:
                    raise ShareError(f"{p}: the server's shard does not extend this one") from None
        fetch(named)
        for p, sha in incoming.items():
            target = self.root / p
            if sha is None:
                target.unlink(missing_ok=True)
            elif local.get(p) != sha:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(contents[sha])
        journal.pin(self.root, named | {s for s in incoming.values() if s})
        for p, sha in incoming.items():
            if sha is None:
                base["files"].pop(p, None)
            else:
                base["files"][p] = sha
        base["seq"] = int(data["seq"])
        self._save(base)
        return f"batch {base['seq']}"


def create(dep, url: str, signer: dict) -> list[str]:
    """Share a criterion through a server for the first time: name it in
    catalyst.toml (journaled, signed by `signer`), then push every file.
    Call only with the user's assent."""
    import subprocess as sp

    import project_file
    from catalyst import journal
    from catalyst.deployment import load
    from catalyst.store import ShareError

    toml = project_file.find(dep.project_root)
    if toml is None or toml.name != project_file.NAME:
        raise ShareError("sharing through a server needs a catalyst.toml (`catalyst move --to-home` first)")
    data = project_file.read(toml)
    data.update({"share": "serve", "share_url": _norm(url)})
    project_file.write(toml, data)
    in_repo = (
        sp.run(
            ["git", "-C", str(dep.project_root), "rev-parse", "--git-dir"], capture_output=True, check=False
        ).returncode
        == 0
    )
    if in_repo:
        sp.run(["git", "-C", str(dep.project_root), "add", "--", toml.name], capture_output=True, check=False)
    shared = load(dep.project_root)
    journal.append(
        shared,
        journal.AppendRequest(
            command="catalyst share create",
            action="update",
            artifact="deployment shared",
            targets=[],
            intent=[
                f"The criterion is shared through the server {_norm(url)}; a collaborator joins with `catalyst open`."
            ],
            files=[str(toml)] if in_repo else [str(shared.root / "version.txt")],
            actor=str(signer.get("git_username") or signer.get("name")),
            allow_unchanged=True,
            tier="chore",
        ),
    )
    res = ServeShare(shared).push(signer, "share create")
    return [
        f'catalyst.toml: share = "serve", share_url = "{_norm(url)}" (staged, not committed)',
        f"published {res['commits']} file(s) as batch {res['seq']}",
    ]


def join(project: Path, runtime: bool = True) -> str:
    """Bring a served criterion to this machine: an empty criterion in
    catalyst's home, filled by a pull, with its runtime."""
    import types

    import project_file
    from catalyst.store import ShareError

    data = project_file.read_dir(project)
    name = project_file.project_name(data)
    if not name:
        raise ShareError("catalyst.toml names no project")
    target = project_file.home_criterion(name)
    probe = ServeShare(types.SimpleNamespace(root=target, pointer=data, project_root=project))
    try:
        probe.client().call("GET", "/head")  # nothing is created on this machine before the server says yes
    except ServeError as e:
        raise ShareError(f"{probe.url}: {e}") from None
    if not (target / ".git").exists():
        target.mkdir(parents=True, exist_ok=True)
        _git(target, "init", "-q")
    exclude = Path(_git(target, "rev-parse", "--git-path", "info/exclude").decode().strip())
    exclude = exclude if exclude.is_absolute() else target / exclude
    if "/.venv" not in (exclude.read_text(encoding="utf-8") if exclude.is_file() else ""):
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open("a", encoding="utf-8") as fh:
            fh.write("/.venv\n")  # the runtime is this machine's, never shared
    dep = types.SimpleNamespace(root=target, pointer=data, project_root=project)
    out = ServeShare(dep).pull()
    if runtime:
        from catalyst import runtime as rt

        with tempfile.TemporaryDirectory() as tmp:
            pyz = rt.own_pyz(Path(tmp))
            rt.install_into(target, rt.pyz_version(pyz), pyz)
    return out
