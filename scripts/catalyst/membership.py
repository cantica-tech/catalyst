"""Project membership on the server (design 32): who belongs to a served criterion, kept safe and confidential.

The provider decides who is a member, reached only through catalyst-users (`members`, `is_member`, `add_member`,
`remove_member`, the system account's rights). `catalyst serve` keeps the record: a ledger per criterion, in its
own database, never in the criterion or a clone.

- An entry says who was added or removed, by whom, when and why. People hold no signing keys: the server verified
  the actor's token, records a hash of it, and signs the entry (HMAC-SHA-256, its own key).
- Entries are chained: `head = SHA-256(previous head | salt | ciphertext)`, a random salt each, so every entry seals
  the ones before it.
- Entries are encrypted at rest (ChaCha20-Poly1305) with the criterion's data key, wrapped by the master key; the
  master key is never in the database (the OS keychain, or a key-management service through a command printing it).
- The criterion holds only fingerprints, written once a day whatever changed (`IAM/membership.fingerprints.jsonl`,
  journaled), so they reveal neither who, nor how many, nor when.
- Access fails closed: a person who is not an admin of the criterion reaches it only when the provider and the
  ledger both name them.
- Break-glass: the master key split among other admins (Shamir's secret sharing); its use is written to the ledger
  and the journal, and the key replaced.

Standard library only, but for the cryptography: pycryptodome, imported when a ledger is used, on the server's host
only (the CLI stays stdlib-only).
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FINGERPRINTS = "IAM/membership.fingerprints.jsonl"  # criterion-relative: fingerprints only, never a name
KINDS = ("members", "user-groups")
FINGERPRINT_EVERY = 24 * 3600.0
PROVIDER_TTL = 10.0  # seconds a provider's answer is kept: a removal takes effect within it
KEY_SERVICE = "catalyst-serve"
OPS = ("open", "add", "remove", "adopt", "break-glass", "rotate")

SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger(kind TEXT NOT NULL, seq INTEGER NOT NULL, salt TEXT NOT NULL, nonce TEXT NOT NULL,
                                  ct TEXT NOT NULL, sig TEXT NOT NULL, head TEXT NOT NULL, PRIMARY KEY (kind, seq));
"""


class MembershipError(Exception):
    """A refusal, with the HTTP status a server answers it with."""

    def __init__(self, message: str, status: int = 403):
        super().__init__(message)
        self.status = status


# --- cryptography: pycryptodome, never our own ---------------------------------------------------------------
def _crypto():
    try:
        from Crypto.Cipher import ChaCha20_Poly1305
        from Crypto.Protocol.SecretSharing import Shamir
    except ImportError:
        raise MembershipError(
            "membership needs pycryptodome on the server's host: `pip install pycryptodome` in the Python that runs "
            "`catalyst serve` (the CLI itself stays standard-library only)",
            503,
        ) from None
    return ChaCha20_Poly1305, Shamir


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def seal(key: bytes, plain: bytes, aad: bytes = b"") -> tuple[bytes, bytes]:
    """(nonce, ciphertext with its tag)."""
    cipher_cls, _ = _crypto()
    nonce = secrets.token_bytes(12)
    cipher = cipher_cls.new(key=key, nonce=nonce)
    cipher.update(aad)
    ct, tag = cipher.encrypt_and_digest(plain)
    return nonce, ct + tag


def unseal(key: bytes, nonce: bytes, sealed: bytes, aad: bytes = b"") -> bytes:
    cipher_cls, _ = _crypto()
    cipher = cipher_cls.new(key=key, nonce=nonce)
    cipher.update(aad)
    try:
        return cipher.decrypt_and_verify(sealed[:-16], sealed[-16:])
    except ValueError:
        raise MembershipError("a ledger entry or key does not decrypt: wrong key, or tampered with", 500) from None


def wrap(master: bytes, key: bytes, what: str) -> str:
    nonce, sealed = seal(master, key, what.encode())
    return _b64(nonce + sealed)


def unwrap(master: bytes, wrapped: str, what: str) -> bytes:
    raw = _unb64(wrapped)
    return unseal(master, raw[:12], raw[12:], what.encode())


def split_key(master: bytes, holders: list[str], threshold: int) -> list[dict]:
    """The master key's break-glass shares, one per holder: any `threshold` of them recover it."""
    _, shamir = _crypto()
    if len(master) != 32:
        raise MembershipError("a master key is 32 bytes", 500)
    if not 2 <= threshold <= len(holders):
        raise MembershipError(f"a threshold of {threshold} needs at least that many holders, and at least 2", 422)
    if len(set(holders)) != len(holders):
        raise MembershipError("a holder is named twice", 422)
    halves = [shamir.split(threshold, len(holders), master[i : i + 16], ssss=False) for i in (0, 16)]
    return [
        {
            "holder": h,
            "index": halves[0][n][0],
            "threshold": threshold,
            "share": _b64(halves[0][n][1] + halves[1][n][1]),
        }
        for n, h in enumerate(holders)
    ]


def join_key(shares: list[dict]) -> bytes:
    _, shamir = _crypto()
    if not shares:
        raise MembershipError("no share given", 422)
    threshold = int(shares[0]["threshold"])
    if len({int(s["index"]) for s in shares}) < threshold:
        raise MembershipError(f"{threshold} different holders' shares are needed", 422)
    parts = [(int(s["index"]), _unb64(s["share"])) for s in shares]
    return b"".join(shamir.combine([(i, raw[o : o + 16]) for i, raw in parts], ssss=False) for o in (0, 16))


# --- the master key ------------------------------------------------------------------------------------------
def key_account(db: Path) -> str:
    """The keychain account a server database's master key is stored under."""
    return f"{KEY_SERVICE}:{hashlib.sha256(str(Path(db).resolve()).encode()).hexdigest()[:16]}"


def read_master(command: str, windows: bool | None = None) -> bytes:
    """The master key, printed (base64) by `command`: the keychain's read command, or a key-management service's;
    the command split by this platform's rules (BUG-000062: a Windows path keeps its backslashes)."""
    from catalyst.identity.provider import split_command

    try:
        argv = split_command(command, windows=windows)
    except ValueError:
        raise MembershipError("the master key cannot be read: its command cannot be split", 503) from None
    if not argv:
        raise MembershipError("the master key cannot be read: its command is empty", 503)
    try:
        done = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MembershipError(f"the master key cannot be read ({type(exc).__name__})", 503) from None
    if done.returncode != 0:
        raise MembershipError("the master key cannot be read: its command failed", 503)
    try:
        key = base64.b64decode(done.stdout.strip(), validate=True)
    except ValueError:
        raise MembershipError("the master key's command prints no base64 key", 503) from None
    if len(key) != 32:
        raise MembershipError("the master key's command prints no 32-byte key", 503)
    return key


def store_master(db: Path, key: bytes) -> str:
    """Keep a master key in the OS keychain; the command that reads it back."""
    from catalyst.identity import keychain

    try:
        return keychain.store(key_account(db), _b64(key))
    except Exception as exc:  # the keychain's own error: never the key
        raise MembershipError(f"the keychain refused the master key: {exc}", 503) from None


# --- the ledger ----------------------------------------------------------------------------------------------
@dataclass
class Keys:
    data: bytes
    sign: bytes


def _token_hash(token: str | None) -> str | None:
    return "sha256:" + hashlib.sha256(token.encode()).hexdigest()[:16] if token else None


class Ledger:
    """The membership ledgers of one server database (one criterion): encrypted, chained, signed."""

    def __init__(self, connect: Callable[[], Any], master: bytes):
        self.connect = connect
        with self._conn() as c:
            c.executescript(SCHEMA)
            meta = dict(c.execute("SELECT key, value FROM meta WHERE key LIKE 'members.%'").fetchall())
        if "members.data_key" not in meta:
            raise MembershipError("no ledger is open here: `catalyst serve members open`", 409)
        self.master = master
        self.keys = Keys(
            unwrap(master, meta["members.data_key"], "data"), unwrap(master, meta["members.sign_key"], "sign")
        )
        self._lock = threading.Lock()
        self._members: set[str] | None = None

    @contextlib.contextmanager
    def _conn(self) -> Iterator[Any]:
        with self.connect() as c:
            yield c

    @staticmethod
    def is_open(connect: Callable[[], Any]) -> bool:
        with connect() as c:
            row = c.execute("SELECT value FROM meta WHERE key = 'members.data_key'").fetchone()
        return row is not None

    @staticmethod
    def create(connect: Callable[[], Any], master: bytes, command: str) -> None:
        """Make the criterion's data and signing keys, wrapped by the master key, and record the key's command."""
        with connect() as c:
            c.executescript(SCHEMA)
            if c.execute("SELECT 1 FROM meta WHERE key = 'members.data_key'").fetchone():
                raise MembershipError("a ledger is already open here", 409)
            rows = {
                "members.data_key": wrap(master, secrets.token_bytes(32), "data"),
                "members.sign_key": wrap(master, secrets.token_bytes(32), "sign"),
                "members.key_command": command,
            }
            c.executemany("INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)", list(rows.items()))

    def _sign(self, head: str) -> str:
        return hmac.new(self.keys.sign, head.encode(), hashlib.sha256).hexdigest()

    def head(self, kind: str = "members") -> str:
        with self._conn() as c:
            row = c.execute("SELECT head FROM ledger WHERE kind = ? ORDER BY seq DESC LIMIT 1", (kind,)).fetchone()
        return row[0] if row else ""

    def append(self, record: dict, kind: str = "members") -> dict:
        """Seal one entry at the chain's head; the entry as written (seq, head)."""
        if kind not in KINDS or record.get("op") not in OPS:
            raise MembershipError(f"not a ledger entry: {kind} {record.get('op')}", 422)
        with self._lock, self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            last = c.execute(
                "SELECT seq, head FROM ledger WHERE kind = ? ORDER BY seq DESC LIMIT 1", (kind,)
            ).fetchone()
            seq, prev = (last[0] + 1, last[1]) if last else (0, "")
            entry = {**record, "seq": seq, "prev": prev}
            nonce, ct = seal(self.keys.data, json.dumps(entry, sort_keys=True).encode(), f"{kind}:{seq}".encode())
            salt = secrets.token_bytes(16)
            head = "sha256:" + hashlib.sha256(prev.encode() + salt + ct).hexdigest()
            c.execute(
                "INSERT INTO ledger(kind, seq, salt, nonce, ct, sig, head) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (kind, seq, _b64(salt), _b64(nonce), _b64(ct), self._sign(head), head),
            )
            c.execute("COMMIT")
        self._members = None
        return {"seq": seq, "head": head}

    def entries(self, kind: str = "members") -> list[dict]:
        """Every entry, decrypted; MembershipError on the first that is not intact."""
        found, problems = self.verify(kind)
        if problems:
            raise MembershipError(f"the {kind} ledger is not intact: {problems[0]}", 500)
        return found

    def verify(self, kind: str = "members") -> tuple[list[dict], list[str]]:
        """(the entries that verify, the problems): the chain, each signature, each decryption."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT seq, salt, nonce, ct, sig, head FROM ledger WHERE kind = ? ORDER BY seq", (kind,)
            ).fetchall()
        out, problems, prev = [], [], ""
        for n, (seq, salt, nonce, ct, sig, head) in enumerate(rows):
            if seq != n:
                problems.append(f"entry {n} is missing (the next is {seq})")
                break
            expect = "sha256:" + hashlib.sha256(prev.encode() + _unb64(salt) + _unb64(ct)).hexdigest()
            if head != expect:
                problems.append(f"entry {seq} does not chain to the one before it")
                break
            if not hmac.compare_digest(sig, self._sign(head)):
                problems.append(f"entry {seq}'s signature does not verify")
                break
            try:
                entry = json.loads(unseal(self.keys.data, _unb64(nonce), _unb64(ct), f"{kind}:{seq}".encode()))
            except MembershipError as exc:
                problems.append(f"entry {seq}: {exc}")
                break
            if entry.get("prev") != prev or entry.get("seq") != seq:
                problems.append(f"entry {seq}'s content does not match its place in the chain")
                break
            out.append(entry)
            prev = head
        return out, problems

    def members(self) -> set[str]:
        """The members the ledger names now, replayed from its entries (kept in memory until the next entry)."""
        if self._members is None:
            names: set[str] = set()
            for entry in self.entries():
                if entry.get("op") in ("add", "adopt"):
                    names.add(str(entry["member"]))
                elif entry.get("op") == "open":
                    names |= {str(m) for m in entry.get("members") or ()}
                elif entry.get("op") == "remove":
                    names.discard(str(entry["member"]))
            self._members = names
        return set(self._members)

    def rewrap(self, master: bytes, command: str) -> None:
        """A new master key: the data and signing keys wrapped again (the entries are not re-encrypted)."""
        with self._conn() as c:
            c.executemany(
                "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                [
                    ("members.data_key", wrap(master, self.keys.data, "data")),
                    ("members.sign_key", wrap(master, self.keys.sign, "sign")),
                    ("members.key_command", command),
                ],
            )
        self.master = master


def record(op: str, by: str, reason: str, token: str | None = None, **more: Any) -> dict:
    """A ledger entry's content: what, by whom (a verified identity), when, why."""
    if not str(reason or "").strip():
        raise MembershipError("a membership change says why: give a reason", 422)
    import datetime

    at = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = {"op": op, "by": by, "at": at, "reason": reason.strip(), "by_token": _token_hash(token)}
    out.update(more)
    return out


# --- admission: fail closed ------------------------------------------------------------------------------------
class Admission:
    """Who a served criterion admits (design 32 §2.5): its admins, and anyone the provider and the ledger both name
    as a member. The provider is asked through catalyst-users, with the system account's rights, its answer kept a
    few seconds."""

    def __init__(self, ledger: Ledger, criterion: str, backend: Any, clock: Callable[[], float] = time.monotonic):
        self.ledger, self.criterion, self.backend, self.clock = ledger, criterion, backend, clock
        self._cache: dict[str, tuple[float, bool]] = {}
        self._lock = threading.Lock()

    def provider_says(self, username: str) -> bool:
        now = self.clock()
        with self._lock:
            hit = self._cache.get(username)
        if hit and hit[0] > now:
            return hit[1]
        try:
            yes = bool(self.backend.is_member(self.criterion, username, system=True))
        except Exception:  # the provider unreachable or refusing: nobody is admitted on its word
            raise MembershipError("the identity provider cannot be asked about membership", 503) from None
        with self._lock:
            self._cache[username] = (now + PROVIDER_TTL, yes)
        return yes

    def forget(self, username: str) -> None:
        with self._lock:
            self._cache.pop(username, None)

    def admit(self, username: str, is_admin: bool) -> None:
        if is_admin:
            return
        if username not in self.ledger.members():
            raise MembershipError(f"{username} is not a member of {self.criterion}")
        if not self.provider_says(username):
            raise MembershipError(f"{username} is not a member of {self.criterion} at the identity provider")


def is_admin(claims: dict, criterion: str | None) -> bool:
    """The Admin (every grant) or an admin of this criterion, as catalyst-users reads the token."""
    from catalyst.identity.provider import whoami_from_claims

    who = whoami_from_claims(claims, str(claims.get("iss") or ""), "catalyst")
    return "cmd:*" in who.grants or bool(criterion and criterion in who.administers)


def username_of(claims: dict) -> str:
    name = str(claims.get("preferred_username") or claims.get("username") or "").strip()
    if not name:
        raise MembershipError("the token names no username")
    return name


# --- fingerprints --------------------------------------------------------------------------------------------
def fingerprint_line(heads: dict[str, str]) -> bytes:
    """One fingerprint: the heads of the criterion's ledgers, and nothing that says who, how many or when beyond
    the day it was written."""
    import datetime

    day = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
    return (json.dumps({"day": day, "heads": heads}, sort_keys=True) + "\n").encode()


def last_fingerprint(data: bytes | None) -> dict | None:
    lines = [line for line in (data or b"").decode("utf-8", "replace").splitlines() if line.strip()]
    try:
        return json.loads(lines[-1]) if lines else None
    except ValueError:
        return None


def drift(ledger_members: set[str], provider_members: set[str]) -> list[str]:
    """Where the provider and the ledger disagree: each a finding the Admin settles (adopt or remove)."""
    out = [
        f"{name} is a member at the provider, but no ledger entry added them (adopt or remove)"
        for name in sorted(provider_members - ledger_members)
    ]
    out += [
        f"{name} is a member in the ledger, but not at the provider (re-add or remove)"
        for name in sorted(ledger_members - provider_members)
    ]
    return out


def env_key_command() -> str | None:
    """A master key's command named by the environment (`CATALYST_SERVE_KEY_COMMAND`): a key-management service."""
    return os.environ.get("CATALYST_SERVE_KEY_COMMAND") or None
