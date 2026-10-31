"""The kernel catalyst.pyz carries (REQ-000106).

`package_release.build_cli` bundles `framework/kernel` into the zipapp under
`catalyst_kernel/`, with a `manifest.json` naming its version, so `catalyst
init` runs from the installed launcher (whose runtime holds that pyz) with no
catalyst checkout and no `--kernel`. Run from source, the checkout's own
`framework/kernel` is the default instead.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

PREFIX = "catalyst_kernel/"


def running_pyz() -> Path | None:
    """The catalyst.pyz this process runs from: `python catalyst.pyz`, or a
    runtime's `python -m catalyst` (its site-packages' catalyst.pth names it)."""
    for candidate in (Path(sys.argv[0]), *Path(__file__).resolve().parents):
        if candidate.suffix == ".pyz" and candidate.is_file():
            return candidate
    return None


def checkout_kernel() -> Path | None:
    """`framework/kernel` of the catalyst checkout this runs from, if any."""
    kernel = Path(__file__).resolve().parent.parent.parent / "framework" / "kernel"
    return kernel if (kernel / "rules-of-rules.template.md").is_file() else None


def extract_kernel(pyz: Path, dest: Path) -> Path | None:
    """The kernel bundled in `pyz`, extracted under `dest`; None if it holds none."""
    with zipfile.ZipFile(pyz) as zf:
        names = [n for n in zf.namelist() if n.startswith(PREFIX) and not n.endswith("/")]
        if f"{PREFIX}rules-of-rules.template.md" not in names:
            return None
        kernel = dest / "kernel"
        for name in names:
            target = kernel / name[len(PREFIX) :]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(name))
    return kernel


def default_kernel(tmp: Path) -> Path | None:
    """The kernel a command uses when `--kernel` is not given: this checkout's,
    else the one bundled in the running catalyst.pyz (extracted under `tmp`)."""
    kernel = checkout_kernel()
    if kernel is not None:
        return kernel
    pyz = running_pyz()
    return extract_kernel(pyz, tmp) if pyz is not None else None
