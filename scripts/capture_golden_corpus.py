#!/usr/bin/env python3
"""Capture a deployment as a golden-corpus fixture (roadmap R1.4).

A corpus is a read-only snapshot of a real deployment: its working copy
(`.criterion`, whether a symlink, a directory or a submodule) and its
`*.catalyst` pointer, packed as `<name>-golden-corpus.tar.gz` with a
`<name>-golden-corpus.json` summary beside it. R3's migration tests and R5's
UI parity tests run against these.

A corpus holds a deployment's private governance data: both files are
gitignored and never committed. The working copy's own git repository (its
private history), the deployment ledger and journal restore points are never
captured. The archive is deterministic: the same working copy gives the same
bytes.

    python3 scripts/capture_golden_corpus.py --project <root> --name <name>
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
EXCLUDED = {".git", ".ledger", ".journal-restore", ".DS_Store"}


def _members(project: Path) -> list[tuple[str, Path]]:
    """(archive name, source file) for the pointer(s) and every working-copy file."""
    criterion = project / ".criterion"
    if not criterion.is_dir():
        raise SystemExit(f"capture: no .criterion working copy under {project}")
    files = [(p.name, p) for p in sorted(project.glob("*.catalyst")) if p.is_file()]
    base = criterion.resolve()
    for path in sorted(base.rglob("*")):
        rel = path.relative_to(base)
        if path.is_file() and not any(part in EXCLUDED or part.startswith("._") for part in rel.parts):
            files.append((f".criterion/{rel.as_posix()}", path))
    return files


def _summary(project: Path, files: list[tuple[str, Path]]) -> dict:
    names = [n for n, _ in files]
    wc = project / ".criterion"
    read = lambda rel: (wc / rel).read_text(encoding="utf-8") if (wc / rel).is_file() else ""
    count = lambda rel, key: len(json.loads(read(rel) or "{}").get(key, []))
    pointer = next((json.loads(p.read_text(encoding="utf-8")) for n, p in files if n.endswith(".catalyst")), {})
    head = subprocess.run(
        ["git", "-C", str(wc), "rev-parse", "--show-toplevel", "HEAD"], capture_output=True, text=True, encoding="utf-8"
    )
    top, _, sha = head.stdout.strip().partition("\n")
    own_repo = head.returncode == 0 and Path(top).resolve() == wc.resolve()  # not an enclosing repo's
    folders: dict[str, int] = {}
    for n in names:
        parts = n.split("/")
        if len(parts) > 2 and n.endswith(".md"):
            folders[parts[1]] = folders.get(parts[1], 0) + 1
    return {
        "project": pointer.get("project_name", project.name),
        "kernel_version": read("version.txt").strip() or pointer.get("kernel_version", ""),
        "module": pointer.get("module", ""),
        "format": pointer.get("format", ""),
        "working_copy_head": sha if own_repo else None,
        "files": len(names),
        "journal_entries": sum(
            len([l for l in read(n).splitlines() if l.strip()])
            for n in names
            if n == "development/journal.jsonl" or (n.startswith("development/journal/") and n.endswith(".jsonl"))
        ),
        "users": count("IAM/users/users.json", "users"),
        "roles": count("IAM/roles/roles.json", "roles"),
        "markdown_per_folder": dict(sorted(folders.items())),
    }


def capture(project: Path, name: str, out: Path = FIXTURES) -> tuple[Path, Path]:
    project = project.resolve()
    files = _members(project)
    out.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for arcname, path in files:
            info = tarfile.TarInfo(arcname)
            data = path.read_bytes()
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            tar.addfile(info, io.BytesIO(data))
    archive = out / f"{name}-golden-corpus.tar.gz"
    with archive.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as gz:
        gz.write(buf.getvalue())
    summary = out / f"{name}-golden-corpus.json"
    summary.write_text(json.dumps(_summary(project, files), indent=2) + "\n", encoding="utf-8")
    return archive, summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=Path, required=True, help="the deployed project's root")
    ap.add_argument("--name", required=True, help="corpus name, e.g. catalyst, ui, example")
    ap.add_argument("--out", type=Path, default=FIXTURES)
    args = ap.parse_args(argv)
    archive, summary = capture(args.project, args.name, args.out)
    print(f"captured {archive} ({archive.stat().st_size:,} bytes)")
    print(summary.read_text(encoding="utf-8"), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
