"""What a deployment governs (fw-STRUCTURE-000017).

A deployment — the directory holding its `*.catalyst` pointer — governs
the files under it, except:

- those under a nested directory that has its own pointer: that is another
  deployment, isolated from this one (the inner one wins);
- those a `.catalystignore` opts out. An empty one (blank lines and `#`
  comments aside) opts its directory and everything below out of catalyst.
  One with lines opts out those paths, relative to its directory: a line
  names a file or a directory (everything below it), `/`-separated, no
  wildcards; a leading `/` or `./` is ignored.

Everything that reads the product's files applies `governs()`: changes
outside catalyst, `trace`, the commit-msg hook, an analysis's inventory.
The topology is the working tree's as it is now — a file deleted from the
tree is judged by the directories that would hold it.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path, PurePosixPath

IGNORE_FILE = ".catalystignore"


@lru_cache(maxsize=4096)
def _ignore_lines(directory: str) -> tuple[str, ...] | None:
    """The opted-out paths a directory's `.catalystignore` lists, `()` for
    an empty one (the whole directory), None when it has none."""
    f = Path(directory) / IGNORE_FILE
    if not f.is_file():
        return None
    lines = []
    for raw in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        while line.startswith("./"):
            line = line[2:]
        line = line.strip("/")
        if line and line != ".":
            lines.append(line)
        elif line in ("", "."):
            return ()  # "." or "/" alone: the whole directory
    return tuple(lines)


@lru_cache(maxsize=4096)
def _has_pointer(directory: str) -> bool:
    d = Path(directory)
    import project_file

    return d.is_dir() and project_file.is_project(d)


def opted_out(directory: Path) -> bool:
    """The directory is outside catalyst: an empty `.catalystignore` in it
    or an ancestor, or an ancestor's line naming it."""
    directory = Path(directory).absolute()
    for d in (directory, *directory.parents):
        lines = _ignore_lines(str(d))
        if lines is None:
            continue
        if lines == ():
            return True
        rel = directory.relative_to(d).as_posix() if directory != d else ""
        if rel and any(rel == l or rel.startswith(l + "/") for l in lines):
            return True
    return False


def governs(project_root: Path, path: str) -> bool:
    """`path` (relative to the project root, `/`-separated) belongs to the
    deployment at `project_root`."""
    rel = PurePosixPath(path)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        return False
    if rel.parts[0] == ".criterion":
        return False
    root = Path(project_root).absolute()
    parts = rel.parts
    # walk the directories from the root down to the file's own directory
    for depth in range(len(parts)):
        here = root.joinpath(*parts[:depth])
        if depth > 0 and _has_pointer(str(here)):
            return False  # a nested deployment owns it
        lines = _ignore_lines(str(here))
        if lines is not None:
            if lines == ():
                return False
            rest = "/".join(parts[depth:])
            if any(rest == l or rest.startswith(l + "/") for l in lines):
                return False
    return True


def owner(repo_top: Path, path: str) -> Path | None:
    """The deployment that owns `path` (relative to the repository top):
    the nearest directory above it with a pointer, unless the path is
    opted out on the way. None when no deployment owns it."""
    top = Path(repo_top).absolute()
    parts = PurePosixPath(path).parts
    for depth in range(len(parts) - 1, -1, -1):
        here = top.joinpath(*parts[:depth])
        if _has_pointer(str(here)):
            return here if governs(here, "/".join(parts[depth:])) else None
    return None


def clear_cache() -> None:
    """Forget what was read from disk (tests; a long-lived process after
    the tree changed)."""
    _ignore_lines.cache_clear()
    _has_pointer.cache_clear()
