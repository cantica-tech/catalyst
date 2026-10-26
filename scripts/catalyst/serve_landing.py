"""Landing, phase 2 (design `docs/design/33` §3, fw-STRUCTURE-000024): the
server lands what it accepted in the criterion's repository.

Every batch `catalyst serve` accepts is held (`held`), with its signer and
roles. A tick (`catalyst serve landing tick`, and a thread while the server
runs, once connected):

1. takes in the shared branch: a file whose tip differs from the server's,
   and that no pending landing holds, becomes a server batch;
2. matches each held batch to the landing policy's first rule
   (fw-STRUCTURE-000023) and groups them (`change`, `session`, `window`);
3. lands a group: one commit on a topic branch from the shared branch's tip,
   built in a bare workspace beside the database (author the server,
   `Signed-off-by` per signer), pushed, and a pull request opened. A file the
   shared branch changed since the batch's base is a conflict: nothing is
   pushed, the landing is `conflict`, for a human (L4);
4. follows each open landing: it merges when its rule says `review: none` and
   `merge: auto` and the check passes, else waits, until merged or closed on
   the host.

The target and the credential's command are the server's meta (`serve landing
connect`); the token is read from its command at each tick, never stored.
Forges: `github` (REST) and `git` (any remote: the server runs `catalyst
check` on the merge result, then merges itself).
"""

from __future__ import annotations

import base64
import datetime
import json
import os
import re
import shlex
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

TABLES = """
CREATE TABLE IF NOT EXISTS held(seq INTEGER PRIMARY KEY, signer TEXT NOT NULL, roles TEXT NOT NULL,
                                landing INTEGER);
CREATE TABLE IF NOT EXISTS landings(id INTEGER PRIMARY KEY, rule TEXT NOT NULL, branch TEXT NOT NULL,
                                    base TEXT NOT NULL, head TEXT, number TEXT, url TEXT, state TEXT NOT NULL,
                                    review TEXT NOT NULL, merge TEXT NOT NULL, created TEXT NOT NULL,
                                    updated TEXT NOT NULL, note TEXT);
"""
TAKEN_IN = -1  # a held batch that came from the shared branch (or the first push's import): never landed
FOLLOWED = ("open", "waiting-review", "waiting-admin", "check-failed")
PENDING = (*FOLLOWED, "conflict")  # a landing whose files the shared branch does not hold yet (5: the SQL's ?s)
FORGES = ("github", "git")
SERVER_NAME, SERVER_EMAIL = "catalyst serve", "serve@catalyst.invalid"
ID_FIELD = re.compile(r"^\| \*\*ID\*\* \| `([^`]+)` \|", re.M)
GITHUB = re.compile(r"github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?/?$")


class LandingError(Exception):
    pass


def hold(c, seq: int, user: dict, importing: bool = False) -> None:
    """Hold a batch the server accepted: its signer and roles, for the policy's `who` (call inside the push's
    transaction)."""
    c.execute(
        "INSERT OR REPLACE INTO held(seq, signer, roles, landing) VALUES (?, ?, ?, ?)",
        (
            seq,
            str(user.get("name") or user.get("git_username") or user.get("userid") or ""),
            json.dumps(sorted({str(r) for r in user.get("roles") or []})),
            TAKEN_IN if importing else None,
        ),
    )


def now() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _epoch(stamp: str) -> float:
    return datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.UTC).timestamp()


# --- git -----------------------------------------------------------------------------------------------------
def _auth(url: str, token: str | None) -> list[str]:
    """git's `-c` for an HTTPS remote with a token (GitHub's `x-access-token` form); none for SSH or no token."""
    if not token or not url.startswith("https://"):
        return []
    basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    return ["-c", f"http.extraHeader=Authorization: Basic {basic}"]


def git(
    ws: Path, *args: str, input: bytes | None = None, env: dict | None = None, auth: list[str] | tuple[str, ...] = ()
) -> bytes:
    done = subprocess.run(
        ["git", *auth, "-C", str(ws), *args],
        input=input,
        capture_output=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", **(env or {})},
        check=False,
    )
    if done.returncode != 0:
        raise LandingError(f"git {args[0]}: {done.stderr.decode('utf-8', 'replace').strip()}")
    return done.stdout


def tree_of(ws: Path, rev: str) -> dict[str, tuple[str, str]]:
    """{path: (mode, blob)} of a revision's tree."""
    out = {}
    for line in git(ws, "ls-tree", "-r", "-z", rev).split(b"\0"):
        if not line:
            continue
        meta, path = line.split(b"\t", 1)
        mode, kind, sha = meta.decode().split()
        if kind == "blob":
            out[path.decode("utf-8")] = (mode, sha)
    return out


# --- forges --------------------------------------------------------------------------------------------------
@dataclass
class Opened:
    number: str
    url: str


class GitForge:
    """Any git remote, no hosting service: a landing's "pull request" is its branch; the server runs `catalyst
    check` on the merge result and merges it itself."""

    def __init__(self, ws: Path, branch: str, auth: list[str], check=None):
        self.ws, self.branch, self.auth = ws, branch, auth
        self._check = check or catalyst_check  # (a checked-out tree) -> whether `catalyst check` passes

    def open(self, head_branch: str, title: str, body: str) -> Opened:
        return Opened(head_branch, head_branch)

    def _merged(self, head: str) -> str:
        """The merge commit of the shared branch's tip and `head` (or `head` when it is a fast-forward)."""
        tip = git(self.ws, "rev-parse", f"refs/remotes/origin/{self.branch}").decode().strip()
        if git(self.ws, "merge-base", tip, head).decode().strip() == tip:
            return head
        tree = git(self.ws, "merge-tree", "--write-tree", tip, head).decode().split()[0]
        env = _committer()
        message = f"Merge landing {head[:12]} into {self.branch}"
        return git(self.ws, "commit-tree", tree, "-p", tip, "-p", head, "-m", message, env=env).decode().strip()

    def state(self, number: str, head: str) -> str:
        tip = git(self.ws, "rev-parse", f"refs/remotes/origin/{self.branch}").decode().strip()
        done = subprocess.run(["git", "-C", str(self.ws), "merge-base", "--is-ancestor", head, tip], check=False)
        return "merged" if done.returncode == 0 else "open"

    def checks(self, number: str, head: str) -> str:
        try:
            merged = self._merged(head)
        except LandingError:
            return "failure"  # a conflict the merge cannot settle
        with tempfile.TemporaryDirectory(prefix="catalyst-landing-") as tmp:
            work = Path(tmp) / "merged"
            git(self.ws, "worktree", "add", "-q", "--detach", str(work), merged)
            try:
                return "success" if self._check(work) else "failure"
            finally:
                subprocess.run(["git", "-C", str(self.ws), "worktree", "remove", "--force", str(work)], check=False)

    def merge(self, number: str, head: str) -> None:
        merged = self._merged(head)
        git(self.ws, "push", "-q", "origin", f"{merged}:refs/heads/{self.branch}", auth=self.auth)


def catalyst_check(work: Path) -> bool:
    """Whether `catalyst check` passes on a checked-out criterion (the merge result a landing would make)."""
    from catalyst import check
    from catalyst.deployment import load_working_copy

    try:
        return not check.run(load_working_copy(work)).errors
    except Exception:
        return False


class GitHubForge:
    """GitHub's REST API: pull requests, their check runs, merging (a token with `contents` and `pull requests`
    write, a GitHub App's installation token being the recommended one, decision 33.4)."""

    def __init__(self, url: str, branch: str, token: str | None, transport=None, api: str | None = None):
        m = GITHUB.search(url)
        if not m:
            raise LandingError(f"{url} is not a GitHub repository")
        if not token:
            raise LandingError("the github forge needs a token: `serve landing connect --token-command`")
        self.owner, self.repo, self.branch, self.token = m.group(1), m.group(2), branch, token
        self.api = (api or os.environ.get("CATALYST_GITHUB_API") or "https://api.github.com").rstrip("/")
        self.transport = transport or _http

    def _call(self, method: str, path: str, body: dict | None = None) -> object:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        status, data = self.transport(method, f"{self.api}/repos/{self.owner}/{self.repo}{path}", headers, body)
        if status >= 400:
            message = data.get("message") if isinstance(data, dict) else data
            raise LandingError(f"GitHub {method} {path}: {status} {message}")
        return data

    def open(self, head_branch: str, title: str, body: str) -> Opened:
        data = self._call("POST", "/pulls", {"title": title, "head": head_branch, "base": self.branch, "body": body})
        return Opened(str(data["number"]), str(data["html_url"]))  # type: ignore[index]

    def state(self, number: str, head: str) -> str:
        data = self._call("GET", f"/pulls/{number}")
        if data.get("merged"):  # type: ignore[union-attr]
            return "merged"
        return "closed" if data.get("state") == "closed" else "open"  # type: ignore[union-attr]

    def checks(self, number: str, head: str) -> str:
        runs = self._call("GET", f"/commits/{head}/check-runs").get("check_runs") or []  # type: ignore[union-attr]
        if not runs:
            return "pending"  # not registered yet: never taken for a pass
        if any(r.get("conclusion") in ("failure", "cancelled", "timed_out", "action_required") for r in runs):
            return "failure"
        done = all(
            r.get("status") == "completed" and r.get("conclusion") in ("success", "neutral", "skipped") for r in runs
        )
        return "success" if done else "pending"

    def merge(self, number: str, head: str) -> None:
        self._call("PUT", f"/pulls/{number}/merge", {"merge_method": "merge", "sha": head})


def _http(method: str, url: str, headers: dict, body: dict | None) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(  # noqa: S310 (the forge's own API URL)
        url, data=data, method=method, headers={**headers, "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (the forge's own API URL)
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw) if raw else {}
        except ValueError:
            return exc.code, {"message": raw.decode("utf-8", "replace")}


def _committer() -> dict:
    return {
        "GIT_AUTHOR_NAME": SERVER_NAME,
        "GIT_AUTHOR_EMAIL": SERVER_EMAIL,
        "GIT_COMMITTER_NAME": SERVER_NAME,
        "GIT_COMMITTER_EMAIL": SERVER_EMAIL,
    }


# --- the policy, applied ---------------------------------------------------------------------------------------
@dataclass
class Batch:
    seq: int
    time: str
    signer: str
    roles: list[str]
    message: str
    rows: list[tuple[str, str | None, str | None]]  # (path, before, after)
    via: str = "person"
    change: str = "unlinked"
    types: list[str] = field(default_factory=list)


def _group(rule: dict) -> tuple[str, int]:
    """(kind, minutes) of a rule's `group`."""
    group = rule.get("group")
    if isinstance(group, str):
        kind, spec = group, {}
    else:
        kind, spec = str((group or {}).get("by") or "change"), group or {}
    if kind == "session":
        return kind, int(spec.get("idle_minutes") or 30)
    if kind == "window":
        return kind, int(spec.get("minutes") or 60)
    return "change", 0


def matches(match: dict, b: Batch) -> bool:
    if "via" in match and match["via"] != b.via:
        return False
    if "change" in match and match["change"] != b.change:
        return False
    if "who" in match and not set(match["who"]) & set(b.roles):
        return False
    return not ("types" in match and not set(match["types"]) & set(b.types))


def rule_for(policy: dict, b: Batch) -> dict:
    for rule in policy.get("rules") or []:
        if isinstance(rule, dict) and matches(rule.get("match") or {}, b):
            return rule
    return {"id": "default", **(policy.get("default") or {})}


def _review(rule: dict) -> str:
    review = rule.get("review")
    if not isinstance(review, dict):
        return "none"
    return f"{review.get('approvals', 1)}x {review.get('role')} ({review.get('where', 'catalyst')})"


# --- the lander ------------------------------------------------------------------------------------------------
class Lander:
    """One server's landing: its config from the server's meta, its workspace beside the database."""

    _ticking = threading.Lock()

    def __init__(self, app, forge=None, clock=time.time, transport=None, check=None):
        self.app, self.clock, self.transport, self.check = app, clock, transport, check
        self.url = app.meta("landing.url")
        if not self.url:
            raise LandingError("this server lands nowhere yet: `catalyst serve landing connect <repository>`")
        self.kind = app.meta("landing.forge") or "git"
        self.branch = app.meta("landing.branch") or "criterion"
        self.name = app.meta("landing.name") or "serve-landing"
        self.token_command = app.meta("landing.token_command")
        self.ws = app.db.with_name(app.db.stem + ".landing.git")
        self._forge = forge

    # config
    @staticmethod
    def connect(app, url: str, forge: str, token_command: str | None, name: str, branch: str) -> dict:
        if forge not in FORGES:
            raise LandingError(f"forge {forge!r}: one of {', '.join(FORGES)}")
        token = read_token(token_command) if token_command else None
        if forge == "github":
            GitHubForge(url, branch, token)  # the URL and token are usable
        done = subprocess.run(
            ["git", *_auth(url, token), "ls-remote", "--heads", url, branch],
            capture_output=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            check=False,
        )
        if done.returncode != 0:
            raise LandingError(f"{url} cannot be read: {done.stderr.decode('utf-8', 'replace').strip()}")
        if not done.stdout.strip():
            raise LandingError(f"{url} has no branch {branch}")
        for key, value in (("url", url), ("forge", forge), ("branch", branch), ("name", name)):
            app.set_meta(f"landing.{key}", value)
        app.set_meta("landing.token_command", token_command or "")
        return {"url": url, "forge": forge, "branch": branch, "credential": name}

    def token(self) -> str | None:
        return read_token(self.token_command) if self.token_command else None

    def forge(self, token: str | None):
        if self._forge is not None:
            return self._forge
        if self.kind == "github":
            return GitHubForge(self.url, self.branch, token, transport=self.transport)
        return GitForge(self.ws, self.branch, _auth(self.url, token), self.check)

    # the workspace
    def fetch(self, auth: list[str]) -> str:
        if not (self.ws / "HEAD").is_file():
            self.ws.mkdir(parents=True, exist_ok=True)
            git(self.ws, "init", "-q", "--bare")
            git(self.ws, "remote", "add", "origin", self.url)
        git(self.ws, "fetch", "-q", "origin", f"+refs/heads/{self.branch}:refs/remotes/origin/{self.branch}", auth=auth)
        return git(self.ws, "rev-parse", f"refs/remotes/origin/{self.branch}").decode().strip()

    # the tick
    def tick(self) -> dict:
        if not Lander._ticking.acquire(blocking=False):
            return {"busy": True}
        try:
            return self._tick()
        finally:
            Lander._ticking.release()

    def _tick(self) -> dict:
        token = self.token()
        auth = _auth(self.url, token)
        forge = self.forge(token)
        out: dict = {"taken_in": None, "landed": [], "merged": [], "waiting": [], "conflicts": [], "errors": []}
        tip = self.fetch(auth)
        out["taken_in"] = self.take_in(tip)
        policy, problems = self._policy()
        if problems:
            out["errors"] += problems
        else:
            for group in self._groups(policy):
                landed = self._land(group, tip, forge, auth)
                out["conflicts" if landed["state"] == "conflict" else "landed"].append(landed)
        for row in self._open():
            followed = self._follow(row, forge)
            if followed["state"] == "merged":
                out["merged"].append(followed)
            elif followed["state"] != "closed":
                out["waiting"].append(followed)
        return out

    def _policy(self) -> tuple[dict, list[str]]:
        from catalyst import landing

        _, dep, corpus = self.app.loaded()
        found = landing.problems(dep, corpus)
        if found:
            return {}, [f"landing policy: {p}" for p in found]
        policy, _ = landing.effective(dep)
        target = policy.get("target") or {}
        named = target.get("credential")
        if named and named != self.name:
            return {}, [f"the landing policy names credential {named!r}; this server's is {self.name!r}"]
        return policy, []

    # 1. the shared branch, taken in
    def _pending_paths(self, c) -> set[str]:
        rows = c.execute(
            "SELECT ch.path FROM changes ch JOIN held h ON h.seq = ch.seq LEFT JOIN landings l ON l.id = h.landing "
            "WHERE h.landing IS NULL OR (h.landing > 0 AND l.state IN (?, ?, ?, ?, ?))",
            PENDING,
        ).fetchall()
        return {r[0] for r in rows}

    def take_in(self, tip: str) -> int | None:
        """A server batch of what the shared branch holds and the server does not (an admin's push), leaving every
        file a pending landing holds; the batch's number, or None when nothing differs."""
        from catalyst import serve

        theirs = tree_of(self.ws, tip)
        with self.app._write, self.app._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                ours = dict(c.execute("SELECT path, sha FROM files").fetchall())
                if not ours:
                    c.execute("COMMIT")
                    return None  # nothing pushed yet: the first push is the import
                skip = self._pending_paths(c)
                rows = []
                for path in sorted(set(theirs) | set(ours)):
                    mine, git_sha = ours.get(path), theirs[path][1] if path in theirs else None
                    if mine != git_sha and path not in skip:
                        rows.append((path, mine, git_sha))
                if not rows:
                    c.execute("COMMIT")
                    return None
                seq = c.execute("SELECT COALESCE(MAX(seq), 0) FROM batches").fetchone()[0] + 1
                c.execute(
                    "INSERT INTO batches(seq, userid, time, message) VALUES (?, ?, ?, ?)",
                    (seq, "serve-landing", now(), f"the shared branch at {tip[:12]}"),
                )
                for path, before, after in rows:
                    data = git(self.ws, "cat-file", "blob", after) if after else None
                    if after:
                        c.execute("INSERT OR IGNORE INTO blobs(sha, bytes) VALUES (?, ?)", (after, data))
                    c.execute(
                        "INSERT INTO changes(seq, path, before, after) VALUES (?, ?, ?, ?)", (seq, path, before, after)
                    )
                    serve._project(c, seq, path, after, data)
                hold(c, seq, {"name": "the shared branch"}, importing=True)
            except BaseException:
                c.execute("ROLLBACK")
                raise
            c.execute("COMMIT")
        with self.app.changed:
            self.app.changed.notify_all()
        return seq

    # 2. held batches, matched and grouped
    def _held(self) -> list[Batch]:
        from catalyst import serve

        with self.app._conn() as c:
            rows = c.execute(
                "SELECT h.seq, b.time, h.signer, h.roles, b.message FROM held h JOIN batches b ON b.seq = h.seq "
                "WHERE h.landing IS NULL ORDER BY h.seq"
            ).fetchall()
            batches = []
            for seq, stamp, signer, roles, message in rows:
                changes = c.execute("SELECT path, before, after FROM changes WHERE seq = ? ORDER BY path", (seq,))
                b = Batch(seq, stamp, signer, json.loads(roles or "[]"), message or "", changes.fetchall())

                def content(sha, c=c):
                    if not sha:
                        return None
                    row = c.execute("SELECT bytes FROM blobs WHERE sha = ?", (sha,)).fetchone()
                    return bytes(row[0]) if row else b""

                entries = []
                ids = []
                for path, before, after in b.rows:
                    if serve.is_journal(path):
                        entries += serve.entries_in(content(before), content(after))
                    elif path.endswith(".md") and (
                        m := ID_FIELD.search((content(after) or content(before) or b"").decode("utf-8", "replace"))
                    ):
                        ids.append((m.group(1), path, after is None))
                self._classify(b, entries, ids)
                batches.append(b)
        return batches

    def _classify(self, b: Batch, entries: list[dict], ids: list[tuple[str, str, bool]]) -> None:
        vias = {str(e.get("via") or "person") for e in entries}
        b.via = "server" if vias == {"server"} else ("agent" if "agent" in vias else "person")
        b.types = sorted({i.split("-")[0] for i, _, _ in ids})
        if b.via == "server":
            b.change = "server"
        elif any(e.get("proposed_by") for e in entries):
            b.change = "proposal-accepted"
        elif self._linked(ids, b.rows):
            b.change = "linked"
        else:
            b.change = "unlinked"

    def _linked(self, ids: list[tuple[str, str, bool]], rows) -> bool:
        from catalyst.edit import is_linked

        if any(path.startswith("rules/") and path.endswith(".md") for path, _, _ in rows):
            return True  # rules are cited
        _, dep, corpus = self.app.loaded()
        for art_id, _, deleted in ids:
            arts = corpus.artifacts.get(art_id)
            if deleted or not arts:
                return True
            if arts[0].prefix in dep.etds and is_linked(dep, corpus, arts[0]):
                return True
        return False

    def _groups(self, policy: dict) -> list[tuple[dict, list[Batch]]]:
        groups: dict[tuple, tuple[dict, list[Batch]]] = {}
        for b in self._held():
            rule = rule_for(policy, b)
            kind, _ = _group(rule)
            key = (rule.get("id"), kind, b.seq if kind == "change" else (b.signer if kind == "session" else ""))
            groups.setdefault(key, (rule, []))[1].append(b)
        ready, clock = [], self.clock()
        for rule, batches in groups.values():
            kind, minutes = _group(rule)
            if kind == "session" and clock - _epoch(batches[-1].time) < minutes * 60:
                continue  # the session may go on
            if kind == "window" and clock - _epoch(batches[0].time) < minutes * 60:
                continue
            ready.append((rule, batches))
        return ready

    # 3. a group, landed
    def _land(self, group: tuple[dict, list[Batch]], tip: str, forge, auth: list[str]) -> dict:
        rule, batches = group
        net: dict[str, list] = {}
        for b in batches:
            for path, before, after in b.rows:
                if path in net:
                    net[path][1] = after
                else:
                    net[path] = [before, after]
        theirs = tree_of(self.ws, tip)
        conflicts = [p for p, (before, after) in net.items() if (theirs.get(p, (None, None))[1]) not in (before, after)]
        stamp = now()
        signers = list(dict.fromkeys(b.signer for b in batches))
        branch = f"landing/{_slug(signers[0])}/{stamp.replace(':', '').replace('-', '')}-{batches[0].seq}"
        with self.app._conn() as c:
            c.execute(
                "INSERT INTO landings(rule, branch, base, state, review, merge, created, updated) "
                "VALUES (?, ?, ?, 'new', ?, ?, ?, ?)",
                (str(rule.get("id")), branch, tip, _review(rule), str(rule.get("merge") or "admin"), stamp, stamp),
            )
            lid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            c.executemany("UPDATE held SET landing = ? WHERE seq = ?", [(lid, b.seq) for b in batches])
        seqs = [b.seq for b in batches]
        if conflicts:
            note = "the shared branch changed since these batches: " + ", ".join(sorted(conflicts))
            self._set(lid, state="conflict", note=note)
            return {"id": lid, "state": "conflict", "batches": seqs, "note": note}
        if all(theirs.get(p, (None, None))[1] == after for p, (_, after) in net.items()):
            self._set(lid, state="merged", head=tip, note="already on the shared branch")
            return {"id": lid, "state": "merged", "batches": seqs, "note": "already on the shared branch"}
        try:
            head = self._commit(lid, batches, net, tip, theirs, signers)
            git(self.ws, "push", "-q", "origin", f"{head}:refs/heads/{branch}", auth=auth)
            title = f"catalyst: {batches[0].message or 'a change'}" + (
                f" (+{len(batches) - 1} more)" if len(batches) > 1 else ""
            )
            opened = forge.open(branch, title[:200], self._body(rule, batches))
        except LandingError as exc:
            self._set(lid, state="failed", note=str(exc))
            return {"id": lid, "state": "failed", "batches": seqs, "note": str(exc)}
        self._set(lid, state="open", head=head, number=opened.number, url=opened.url)
        return {"id": lid, "state": "open", "batches": seqs, "url": opened.url, "rule": rule.get("id")}

    def _commit(self, lid: int, batches: list[Batch], net: dict, tip: str, theirs: dict, signers: list[str]) -> str:
        index = self.ws / f"landing-{lid}.index"
        env = {**_committer(), "GIT_INDEX_FILE": str(index)}
        try:
            git(self.ws, "read-tree", tip, env=env)
            with self.app._conn() as c:
                for path, (_, after) in sorted(net.items()):
                    if after is None:
                        git(self.ws, "update-index", "--force-remove", "--", path, env=env)
                        continue
                    row = c.execute("SELECT bytes FROM blobs WHERE sha = ?", (after,)).fetchone()
                    data = bytes(row[0]) if row else b""
                    sha = git(self.ws, "hash-object", "-w", "--stdin", input=data).decode().strip()
                    mode = theirs.get(path, ("100644", ""))[0]
                    git(self.ws, "update-index", "--add", "--cacheinfo", f"{mode},{sha},{path}", env=env)
            tree = git(self.ws, "write-tree", env=env).decode().strip()
        finally:
            index.unlink(missing_ok=True)
        lines = [f"catalyst: landing {lid} ({len(batches)} batch(es) from catalyst serve)", ""]
        lines += [f"- batch {b.seq} by {b.signer} ({b.via}, {b.change}): {b.message}" for b in batches]
        lines += ["", *[f"Signed-off-by: {s}" for s in signers]]
        message = "\n".join(lines) + "\n"
        return git(self.ws, "commit-tree", tree, "-p", tip, input=message.encode(), env=_committer()).decode().strip()

    @staticmethod
    def _body(rule: dict, batches: list[Batch]) -> str:
        lines = [
            f"Landed by `catalyst serve` under the landing rule `{rule.get('id')}` "
            f"(review: {_review(rule)}; merge: {rule.get('merge')}).",
            "",
        ]
        lines += [f"- batch {b.seq} by {b.signer} ({b.via}, {b.change}): {b.message}" for b in batches]
        return "\n".join(lines)

    # 4. open landings, followed
    def _open(self) -> list[dict]:
        with self.app._conn() as c:
            c.row_factory = _rows
            return c.execute("SELECT * FROM landings WHERE state IN (?, ?, ?, ?) ORDER BY id", FOLLOWED).fetchall()

    def _follow(self, row: dict, forge) -> dict:
        out = {"id": row["id"], "url": row["url"], "rule": row["rule"]}
        try:
            state = forge.state(row["number"], row["head"])
            if state in ("merged", "closed"):
                self._set(row["id"], state=state)
                return {**out, "state": state}
            if row["review"] != "none":
                self._set(row["id"], state="waiting-review")
                return {**out, "state": "waiting-review"}
            if row["merge"] != "auto":
                self._set(row["id"], state="waiting-admin")
                return {**out, "state": "waiting-admin"}
            checks = forge.checks(row["number"], row["head"])
            if checks == "failure":
                self._set(row["id"], state="check-failed", note="the catalyst check failed: a human decides")
                return {**out, "state": "check-failed"}
            if checks != "success":
                return {**out, "state": row["state"]}
            forge.merge(row["number"], row["head"])
        except LandingError as exc:
            self._set(row["id"], note=str(exc))
            return {**out, "state": row["state"], "note": str(exc)}
        self._set(row["id"], state="merged")
        return {**out, "state": "merged"}

    def _set(
        self,
        lid: int,
        state: str | None = None,
        head: str | None = None,
        number: str | None = None,
        url: str | None = None,
        note: str | None = None,
    ) -> None:
        with self.app._conn() as c:
            c.execute(
                "UPDATE landings SET state = COALESCE(?, state), head = COALESCE(?, head), number = COALESCE(?, number), "
                "url = COALESCE(?, url), note = COALESCE(?, note), updated = ? WHERE id = ?",
                (state, head, number, url, note, now(), lid),
            )

    # the host's view
    def list(self) -> list[dict]:
        with self.app._conn() as c:
            c.row_factory = _rows
            rows = c.execute("SELECT * FROM landings ORDER BY id").fetchall()
            for row in rows:
                row["batches"] = [s for (s,) in c.execute("SELECT seq FROM held WHERE landing = ?", (row["id"],))]
            held = [s for (s,) in c.execute("SELECT seq FROM held WHERE landing IS NULL ORDER BY seq")]
        return [*rows, *([{"id": None, "state": "held", "batches": held}] if held else [])]

    def retry(self, lid: int) -> list[int]:
        """Hold a conflicted (or failed) landing's batches again, once a human settled the shared branch."""
        with self.app._conn() as c:
            row = c.execute("SELECT state FROM landings WHERE id = ?", (lid,)).fetchone()
            if row is None:
                raise LandingError(f"no landing {lid}")
            if row[0] not in ("conflict", "failed", "check-failed", "closed"):
                raise LandingError(f"landing {lid} is {row[0]}: only a conflicted, failed or closed one is retried")
            seqs = [s for (s,) in c.execute("SELECT seq FROM held WHERE landing = ?", (lid,))]
            c.execute("UPDATE held SET landing = NULL WHERE landing = ?", (lid,))
            c.execute("UPDATE landings SET state = 'retried', updated = ? WHERE id = ?", (now(), lid))
        return seqs


def _rows(cursor, row) -> dict:
    return {d[0]: v for d, v in zip(cursor.description, row, strict=True)}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "someone"


def read_token(command: str) -> str:
    done = subprocess.run(shlex.split(command), capture_output=True, text=True, check=False)
    token = done.stdout.strip()
    if done.returncode != 0 or not token:
        raise LandingError(f"the token command failed: {done.stderr.strip() or 'it printed nothing'}")
    return token


def start(app, every: float = 60.0) -> threading.Thread | None:
    """While the server runs, a tick every minute, once it is connected (`serve landing connect`)."""
    if not app.meta("landing.url"):
        return None

    def loop() -> None:
        import sys

        while True:
            try:
                result = Lander(app).tick()
                for err in result.get("errors") or []:
                    print(f"catalyst serve: landing: {err}", file=sys.stderr)
            except Exception as exc:  # never the server's end: said, and tried again
                print(f"catalyst serve: landing could not run: {exc}", file=sys.stderr)
            time.sleep(every)

    thread = threading.Thread(target=loop, name="landing", daemon=True)
    thread.start()
    return thread
