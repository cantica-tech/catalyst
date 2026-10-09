"""`catalyst move` (roadmap R2 W5, R3.1 stage E): move a legacy deployment
into catalyst's home store, or rename a project.

`--to-home` takes any legacy shape — a `.criterion` symlink into agent space,
an in-project `.criterion` directory, a `.criterion` git submodule (a shared
deployment), or a pre-0.37.0 `agent-source` — and moves the criterion to
`$CATALYST_HOME/projects/<name>/criterion` with its whole git history,
branches and remote. The project keeps one file: `<name>.catalyst` becomes
`catalyst.toml`. Product-side changes are staged, never committed (INV-4).

`--name <new>` renames a home-store project: its criterion directory and
the name in `catalyst.toml`.
"""
from __future__ import annotations

import datetime
import shutil
import subprocess
from pathlib import Path

import project_file

from catalyst import journal
from catalyst.deployment import load


class MoveError(Exception):
    pass


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    res = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    if check and res.returncode != 0:
        raise MoveError(f"git {' '.join(args)} failed in {repo}: {res.stderr.strip()}")
    return res


def _is_repo(path: Path) -> bool:
    return _git(path, "rev-parse", "--git-dir", check=False).returncode == 0


def _drop_gitignore_line(project: Path) -> Path | None:
    ignore = project / ".gitignore"
    if not ignore.is_file():
        return None
    lines = ignore.read_text(encoding="utf-8").splitlines()
    kept = [l for l in lines if l.strip() not in ("/.criterion", ".criterion", "/.criterion/", ".criterion/")
            and not l.startswith("# catalyst working copy:")]
    if kept == lines:
        return None
    ignore.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return ignore


def _move_submodule(project: Path, link: Path, target: Path) -> list[Path]:
    """A shared deployment: the criterion becomes a standalone repository at
    `target` (its git data from the product's .git/modules, so branches,
    remote and unpushed work travel), and the product drops the submodule."""
    gitdir = Path(_git(link, "rev-parse", "--absolute-git-dir").stdout.strip())
    target.mkdir(parents=True)
    for item in link.iterdir():
        if item.name == ".git":
            continue
        dest = target / item.name
        if item.is_dir() and not item.is_symlink():
            shutil.copytree(item, dest, symlinks=True)
        else:
            shutil.copy2(item, dest, follow_symlinks=False)
    shutil.copytree(gitdir, target / ".git", symlinks=True)
    # the submodule's git data names its old worktree; edit the file itself
    # (any git command run on the repository would first try to enter it)
    subprocess.run(["git", "config", "--file", str(target / ".git" / "config"), "--unset", "core.worktree"],
                   capture_output=True)
    _git(target, "status", "--porcelain")                       # the moved repository works
    _git(project, "submodule", "deinit", "-q", "-f", ".criterion")
    _git(project, "rm", "-q", "-f", ".criterion")
    shutil.rmtree(gitdir, ignore_errors=True)
    touched = []
    gitmodules = project / ".gitmodules"
    if gitmodules.is_file():
        if not gitmodules.read_text(encoding="utf-8").strip():
            _git(project, "rm", "-q", "-f", ".gitmodules")
        else:
            _git(project, "add", ".gitmodules")
        touched.append(gitmodules)
    return touched


def to_home(project: Path, runtime: bool = True, actor: str | None = None) -> tuple[Path, list[str]]:
    project = project.resolve()
    pointer = project_file.find(project)
    if pointer is None:
        raise MoveError(f"{project} has no catalyst.toml or *.catalyst pointer")
    data = project_file.read(pointer)
    name = project_file.project_name(data)
    if not name:
        raise MoveError(f"{pointer.name} names no project (project_name)")
    target = project_file.home_criterion(name)
    link = project / project_file.LEGACY_DIRNAME
    source = data.get("agent-source")
    current = (link if (link.is_symlink() or link.is_dir()) else
               Path(str(source)).expanduser() if source and Path(str(source)).expanduser().is_dir() else None)
    if current is None:
        if target.is_dir():
            raise MoveError(f"{name} is already in the home store ({target})")
        raise MoveError(f"{project}'s criterion is not reachable: nothing to move")
    if target.exists() and any(target.iterdir()):
        raise MoveError(f"{target} already exists — another project is named '{name}'")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.rmdir()
    steps, touched = [], []
    if link.is_symlink():
        real = link.resolve()
        shutil.move(str(real), str(target))
        link.unlink()
        steps.append(f"moved the criterion from agent space ({real}) to {target}; removed the .criterion symlink")
    elif link.is_dir() and (link / ".git").is_file():
        touched += _move_submodule(project, link, target)
        steps.append(f"made the shared criterion a standalone repository at {target} (branches, remote and "
                     "unpushed work kept); removed the .criterion submodule from the product (staged)")
    elif link.is_dir():
        shutil.move(str(link), str(target))
        steps.append(f"moved the in-project .criterion to {target}")
    else:                                                        # pre-0.37.0 agent-source
        shutil.move(str(current), str(target))
        data.pop("agent-source", None)
        steps.append(f"moved the criterion from its agent-source ({current}) to {target}")
    ignore = _drop_gitignore_line(project)
    if ignore is not None:
        touched.append(ignore)
        steps.append("removed /.criterion from .gitignore")
    data["updated"] = datetime.date.today().isoformat()
    toml = project / project_file.NAME
    project_file.write(toml, data)
    if pointer != toml:
        pointer.unlink()
        steps.append(f"{pointer.name} is now catalyst.toml")
    touched += [toml, pointer]
    if _is_repo(project):
        for path in dict.fromkeys(touched):          # one by one: a path git never knew must not stop the rest
            _git(project, "add", "-A", "--", str(path.relative_to(project)), check=False)
        steps.append("product changes staged, not committed")
    if runtime:
        # the catalyst doing the move knows the home store; a legacy deployment's
        # vendored CLI may predate it, so the runtime comes from this one
        import tempfile

        from catalyst import runtime as rt
        with tempfile.TemporaryDirectory() as tmp:
            pyz = rt.own_pyz(Path(tmp))
            version = rt.pyz_version(pyz)
            venv, _ = rt.install_into(target, version, pyz)
        steps.append(f"filled the criterion's runtime {venv} (catalyst {version})")
    dep = load(project)
    journal.append(dep, journal.AppendRequest(
        command="catalyst move", action="update", artifact=f"criterion of {name}", targets=[],
        intent=[f"Move the criterion into catalyst's home store ({target}): nothing of it stays in the "
                "project but catalyst.toml (ADR-010)."],
        files=[str(p) for p in dict.fromkeys(touched)] if _is_repo(project) else [str(target / "version.txt")],
        actor=actor or str(data.get("created_by") or "catalyst"),
        allow_unchanged=True, tier="chore"))
    steps.append("journaled the move")
    return target, steps


def rename(project: Path, new: str, actor: str | None = None) -> tuple[Path, list[str]]:
    from catalyst.init import NAME_RE
    project = project.resolve()
    if not NAME_RE.match(new):
        raise MoveError(f"'{new}' must be letters, digits, '.', '_' or '-'")
    toml = project / project_file.NAME
    if not toml.is_file():
        raise MoveError(f"{project} has no catalyst.toml — `catalyst move --to-home` first")
    data = project_file.read(toml)
    old = project_file.project_name(data)
    source, target = project_file.home_criterion(old), project_file.home_criterion(new)
    if not source.is_dir():
        raise MoveError(f"no criterion at {source}")
    if target.exists():
        raise MoveError(f"{target} already exists")
    shutil.move(str(source.parent), str(target.parent))
    data["project_name"] = new
    data["updated"] = datetime.date.today().isoformat()
    project_file.write(toml, data)
    if _is_repo(project):
        _git(project, "add", "--", project_file.NAME, check=False)
    dep = load(project)
    journal.append(dep, journal.AppendRequest(
        command="catalyst move", action="update", artifact=f"project {old} -> {new}", targets=[],
        intent=[f"Rename the project {old} to {new}: its criterion moves to {target}."],
        files=[str(toml)] if _is_repo(project) else [str(target / "version.txt")],
        actor=actor or str(data.get("created_by") or "catalyst"),
        allow_unchanged=True, tier="chore"))
    return target, [f"renamed {old} to {new}; the criterion is {target}", "catalyst.toml staged, not committed"]
