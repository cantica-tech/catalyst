"""Run a command with UTF-8 text in and out, the same on every platform.

`subprocess.run(..., text=True)` decodes with the locale's code page and, on
Windows, turns every "\n" written to stdin into "\r\n" — which git reads as
part of the data (`mktree`, `hash-object --stdin-paths`, `cat-file --batch`).
This runs the process in binary mode and does the encoding itself.
"""

from __future__ import annotations

import subprocess


def run(cmd: list[str], *, input: str | None = None, **kwargs) -> subprocess.CompletedProcess:
    res = subprocess.run(cmd, input=None if input is None else input.encode("utf-8"), capture_output=True, **kwargs)
    decode = lambda b: b.decode("utf-8", "replace").replace("\r\n", "\n") if b is not None else ""
    return subprocess.CompletedProcess(res.args, res.returncode, decode(res.stdout), decode(res.stderr))
