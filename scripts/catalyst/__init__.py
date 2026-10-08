"""catalyst — the executable half of the catalyst framework.

Everything mechanical that the framework's prose used to ask an agent to do
by hand (allocating IDs, writing and verifying the journal, regenerating
indexes, validating the traceability chain) lives here, so the agent calls a
tested tool instead of re-deriving the procedure each time.

Stdlib only. Runs from catalyst's own repository (`python3 -m catalyst` with
`scripts/` on the path) or as the single-file zipapp `catalyst.pyz` vendored
into a deployment's `.criterion/bin/`.
"""
from __future__ import annotations

from pathlib import Path

try:  # written into the zipapp by scripts/package_release.py
    from catalyst._build import VERSION as __version__  # type: ignore
except ImportError:  # running from catalyst's own repository
    _version_file = Path(__file__).resolve().parents[2] / "version.txt"
    __version__ = (_version_file.read_text(encoding="utf-8").strip()
                   if _version_file.is_file() else "0.0.0")
try:  # the commit a zipapp was built from (`g<sha>[.dirty]`), "" outside git
    from catalyst._build import BUILD as __build__  # type: ignore
except ImportError:  # from source, or a zipapp built before builds carried it
    __build__ = ""


def version_string() -> str:
    """`catalyst --version`: the kernel version, plus the build's commit
    when it has one, so two builds of one version can be told apart."""
    return f"{__version__}+{__build__}" if __build__ else __version__
