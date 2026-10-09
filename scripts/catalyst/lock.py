"""Cross-process locks on a criterion (ID allocation, journal appends).

Locks and other local state live outside the tracked tree: in the working
copy's git directory (never committed, never pushed), else in the system's
temporary directory. A lock is a file created with O_CREAT|O_EXCL, which is
atomic on every OS (no fcntl, so it works on Windows too); a lock older than
`stale` seconds belongs to a crashed caller and is broken.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import subprocess
import tempfile
import time
from pathlib import Path

STALE = 30.0
WAIT = 60.0
# On Windows a lock file being deleted by its holder is "delete pending": opening
# or stat-ing it fails with PermissionError, which means busy, not forbidden.
BUSY = (FileExistsError, PermissionError) if os.name == "nt" else (FileExistsError,)


class LockError(Exception):
    pass


def state_dir(root: Path) -> Path:
    res = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-path", "catalyst"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if res.returncode == 0 and res.stdout.strip():
        path = Path(res.stdout.strip())
        return path if path.is_absolute() else (root / path).resolve()
    digest = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"catalyst-{digest}"


@contextlib.contextmanager
def held(root: Path, name: str, wait: float = WAIT, stale: float = STALE, error: type[Exception] = LockError):
    """Hold the criterion's `<name>.lock` for the duration of the block."""
    folder = state_dir(root)
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / f"{name}.lock"
    deadline = time.monotonic() + wait
    while True:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except BUSY:
            try:
                if time.time() - lock.stat().st_mtime > stale:
                    lock.unlink()  # a crashed holder: break its lock
                    continue
            except FileNotFoundError:
                continue  # released meanwhile
            except BUSY:
                pass  # being released (Windows): wait
            if time.monotonic() > deadline:
                raise error(
                    f"the {name} lock {lock} is held by another process — retry, or remove it "
                    "if no catalyst command is running"
                ) from None
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
        with contextlib.suppress(FileNotFoundError):
            lock.unlink()
