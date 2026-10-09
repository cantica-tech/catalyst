"""Per-criterion runtime (roadmap R3.1a, ADR-010 §6).

One runtime per catalyst version, built once per machine in
`$CATALYST_HOME/runtimes/<version>/`: a virtual environment (uv's
`--relocatable` when uv is installed, else Python's own `venv`) whose
site-packages holds `catalyst.pyz` and a `catalyst.pth` naming it, so
`python -m catalyst` runs it — nothing is installed, nothing is activated.
Creating or loading a criterion copies that runtime into `<criterion>/.venv`;
several criteria pinned to different versions run side by side.

The launcher (`$CATALYST_HOME/bin/catalyst`, plus `catalyst.cmd` on Windows)
is a stdlib script any `python3` can run: it finds the project above the
current directory and runs its criterion's `.venv`, or a legacy deployment's
vendored `.criterion/bin/catalyst.pyz`.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import project_file

MARKER = "catalyst-version"
MIN_PYTHON = (3, 11)


class RuntimeError_(Exception):
    pass


def runtimes() -> Path:
    return project_file.home() / "runtimes"


def venv_python(venv: Path) -> Path:
    win = venv / "Scripts" / "python.exe"
    return win if win.exists() or os.name == "nt" else venv / "bin" / "python"


def site_packages(venv: Path) -> Path:
    if (venv / "Lib" / "site-packages").is_dir():
        return venv / "Lib" / "site-packages"
    found = sorted(venv.glob("lib/python3*/site-packages"))
    if not found:
        raise RuntimeError_(f"{venv} has no site-packages")
    return found[-1]


def _create_venv(target: Path) -> None:
    uv = shutil.which("uv")
    if uv:
        res = subprocess.run([uv, "venv", "--quiet", "--relocatable", "--python",
                              f">={MIN_PYTHON[0]}.{MIN_PYTHON[1]}", str(target)],
                             capture_output=True, text=True, encoding="utf-8")
        if res.returncode == 0:
            return
        shutil.rmtree(target, ignore_errors=True)
    if sys.version_info < MIN_PYTHON:
        raise RuntimeError_(f"building a runtime needs uv, or Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ "
                            f"(this is {sys.version.split()[0]})")
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(target)], check=True,
                   capture_output=True)


def ensure_runtime(version: str, pyz: Path) -> Path:
    """The runtime for `version`, built from `pyz` when missing."""
    target = runtimes() / version
    if (target / MARKER).is_file() and venv_python(target).exists():
        return target
    staging = target.with_name(f".{version}.building")
    shutil.rmtree(staging, ignore_errors=True)
    staging.parent.mkdir(parents=True, exist_ok=True)
    _create_venv(staging)
    site = site_packages(staging)
    shutil.copyfile(pyz, site / "catalyst.pyz")
    (site / "catalyst.pth").write_text("catalyst.pyz\n", encoding="utf-8")
    (staging / MARKER).write_text(version + "\n", encoding="utf-8")
    shutil.rmtree(target, ignore_errors=True)
    staging.rename(target)
    return target


def installed_version(venv: Path) -> str | None:
    marker = venv / MARKER
    return marker.read_text(encoding="utf-8").strip() if marker.is_file() else None


def install_into(criterion: Path, version: str, pyz: Path) -> tuple[Path, bool]:
    """Copy the runtime for `version` into `<criterion>/.venv` unless it is
    already there; keep `.venv` out of the criterion's git repository."""
    venv = criterion / ".venv"
    changed = False
    if installed_version(venv) != version or not venv_python(venv).exists():
        source = ensure_runtime(version, pyz)
        shutil.rmtree(venv, ignore_errors=True)
        shutil.copytree(source, venv, symlinks=True)
        changed = True
    ignore = criterion / ".gitignore"
    lines = ignore.read_text(encoding="utf-8").splitlines() if ignore.is_file() else []
    if "/.venv" not in lines:
        ignore.write_text("\n".join([*lines, "/.venv"]) + "\n", encoding="utf-8")
    return venv, changed


# --- launcher --------------------------------------------------------------
LAUNCHER = r'''#!/usr/bin/env python3
"""catalyst launcher (installed by `catalyst runtime install`): runs the
catalyst of the project you are in — its criterion's .venv, or a legacy
deployment's .criterion/bin/catalyst.pyz. Stdlib only, any Python 3."""
import json, os, re, sys
from pathlib import Path

home = Path(os.environ.get("CATALYST_HOME") or Path.home() / ".catalyst").expanduser()


def project_name(directory):
    toml = directory / "catalyst.toml"
    if toml.is_file():
        m = re.search(r'^(?:project_name|name)\s*=\s*"((?:[^"\\]|\\.)*)"', toml.read_text(encoding="utf-8"), re.M)
        return (m.group(1) if m else None), True
    for pointer in sorted(directory.glob("*.catalyst")):
        try:
            return json.loads(pointer.read_text(encoding="utf-8")).get("project_name"), True
        except ValueError:
            pass
    return None, False


def python_of(venv):
    for p in (venv / "bin" / "python", venv / "Scripts" / "python.exe"):
        if p.exists():
            return p
    return None


def main():
    cwd, pwd = os.getcwd(), os.environ.get("PWD")
    # PWD keeps the path as the shell sees it (through symlinks), but only when it is this directory
    start = Path(pwd if pwd and os.path.realpath(pwd) == os.path.realpath(cwd) else cwd)
    for d in (start, *start.parents):
        name, found = project_name(d)
        if not found:
            continue
        criterion = home / "projects" / name / "criterion" if name else None
        py = python_of(criterion / ".venv") if criterion and criterion.is_dir() else None
        if py:
            os.execv(str(py), [str(py), "-m", "catalyst", *sys.argv[1:]])
        legacy = d / ".criterion" / "bin" / "catalyst.pyz"
        if legacy.is_file():
            os.execv(sys.executable, [sys.executable, str(legacy), *sys.argv[1:]])
        sys.exit(f"catalyst: {d} has no reachable criterion (expected {criterion})")
    runtimes = sorted((home / "runtimes").glob("*/"), key=lambda p: [int(n) for n in re.findall(r"\d+", p.name)])
    py = python_of(runtimes[-1]) if runtimes else None
    if py:                               # outside any project (e.g. `catalyst init`): the newest runtime
        os.execv(str(py), [str(py), "-m", "catalyst", *sys.argv[1:]])
    sys.exit("catalyst: no project here and no runtime installed (`catalyst runtime install`)")


main()
'''

LAUNCHER_CMD = '@echo off\r\npy -3 "%~dp0catalyst" %*\r\n'


def install_launcher() -> Path:
    bin_dir = project_file.home() / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    launcher = bin_dir / "catalyst"
    launcher.write_text(LAUNCHER, encoding="utf-8")
    launcher.chmod(0o755)
    (bin_dir / "catalyst.cmd").write_text(LAUNCHER_CMD, encoding="utf-8")
    return launcher


def own_pyz(tmp: Path) -> Path:
    """The catalyst.pyz this process runs from, or one built from this checkout."""
    for candidate in (Path(sys.argv[0]), *Path(__file__).parents):
        if candidate.suffix == ".pyz" and candidate.is_file():     # run as a zipapp, or from a runtime's .pth
            return candidate
    import package_release
    return package_release.build_cli(Path(package_release.ROOT), tmp / "catalyst.pyz")


def pyz_version(pyz: Path) -> str:
    """The version a catalyst.pyz reports (`X.Y.Z[+g<sha>[.dirty]]`): the
    runtime's label, so a development build never shares a release's runtime."""
    res = subprocess.run([sys.executable, str(pyz), "--version"], capture_output=True, text=True,
                         encoding="utf-8", env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"})
    if res.returncode != 0 or not res.stdout.startswith("catalyst "):
        raise RuntimeError_(f"{pyz} does not run: {res.stderr.strip()}")
    return res.stdout.split()[1]
