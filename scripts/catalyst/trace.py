"""Every commit traces to the chain (INV-5 at commit granularity).

A product commit's message must cite an artifact or rule ID that resolves in
the deployment — in full (`<PREFIX>-NNNNNN-<userid>`, `<doc>-<DOMAIN>-NNNNNN-
<userid>`) or short (`<PREFIX>-NNNNNN`, matching a full ID) — or be marked as
a chore (a subject starting `chore:` or `chore(...)`: no rule's behaviour
changes, the chore tier). Merge commits are not checked.

`catalyst hook commit-msg` applies it as a git commit-msg hook;
`catalyst trace <range>` checks a range of commits (CI). Without a working
copy (a CI checkout of a local-only deployment), `--pattern-only` accepts any
well-formed ID.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from catalyst.corpus import Corpus
from catalyst.journal import revisions

# an entity ID (ITEM-000001[-userid]) or a rule ID (br-AUTH-000001[-userid]);
# nothing else that merely looks like word-digits (paths, versions)
TOKEN_RE = re.compile(
    r"\b([A-Z][A-Z0-9]*-\d{6}(?:-[A-Za-z0-9]{8})?|[a-z]+-[A-Z][A-Z0-9]*(?:\.[A-Z][A-Z0-9]*)?-\d{3,6}(?:-[A-Za-z0-9]{8})?)\b"
)
FULL_SHAPE = re.compile(
    r"^(?:[A-Z][A-Z0-9]*-\d{6}(?:-[A-Za-z0-9]{8})?|[a-z]+-[A-Z][A-Z0-9]*(?:\.[A-Z][A-Z0-9]*)?-\d{6}(?:-[A-Za-z0-9]{8})?)$"
)
HOOK = """#!/usr/bin/env python3
# Installed by `catalyst hook install`: every commit cites an artifact or rule ID,
# or is marked `chore:` (catalyst trace) — checked by each deployment whose files
# it changes. Bypass once with `git commit --no-verify`.
import os
import subprocess
import sys

git = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True, encoding="utf-8").stdout
top = git("rev-parse", "--show-toplevel").strip()
staged = [p for p in git("-C", top, "diff", "--cached", "--name-only", "-z").split("\\0") if p]
ROUTER = "{router}"  # the launcher, or a legacy vendored CLI relative to the repository top


def cli_near(rel):
    d = os.path.dirname(rel)
    while True:
        cli = os.path.join(top, d, ".criterion", "bin", "catalyst.pyz")
        if os.path.isfile(cli):
            return cli
        if not d:
            return None
        d = os.path.dirname(d)


# the launcher runs each project's own catalyst (its criterion's .venv); a
# legacy deployment's vendored CLI otherwise
home = os.environ.get("CATALYST_HOME") or os.path.join(os.path.expanduser("~"), ".catalyst")
launcher = os.path.join(home, "bin", "catalyst")
router = os.path.join(top, ROUTER)


def criterion_cli():  # the CLI of the criterion catalyst.toml names, in catalyst's home: no launcher yet
    import re

    try:
        text = open(os.path.join(top, "catalyst.toml"), encoding="utf-8").read()
    except OSError:
        return None
    name = re.search(r'^project_name\\s*=\\s*"([^"]+)"', text, re.M)
    for kind in ("projects", "workspaces"):
        cli = name and os.path.join(home, kind, name.group(1), "criterion", "bin", "catalyst.pyz")
        if cli and os.path.isfile(cli):
            return cli
    return None


cli = (launcher if os.path.isfile(launcher) else router if os.path.isfile(router)
       else criterion_cli() or next((c for c in map(cli_near, staged + [""]) if c), None))
if cli is None:
    if os.path.isfile(os.path.join(top, "catalyst.toml")):  # governed, but no CLI here: say so, never pass silently
        print("catalyst: commit message not checked: no catalyst CLI found for this project "
              "(`catalyst runtime install`, or `catalyst open`)", file=sys.stderr)
    sys.exit(0)
sys.exit(subprocess.run([sys.executable, cli, "--project", top, "hook", "commit-msg", "--route",
                         os.path.abspath(sys.argv[1])], cwd=top).returncode)
"""


@dataclass
class Failure:
    sha: str
    subject: str
    reason: str


def cited(message: str) -> list[str]:
    body = "\n".join(l for l in message.splitlines() if not l.startswith("#"))
    return TOKEN_RE.findall(body)


def resolves(corpus: Corpus, token: str, all_ids: set[str]) -> bool:
    if token in all_ids:
        return True
    return any(i.startswith(token + "-") for i in all_ids)  # short form of a full ID


def check_message(message: str, corpus: Corpus | None, prefixes: tuple[str, ...] = ("chore:",)) -> str | None:
    """None when the message traces; else why not. `prefixes`: the subject
    prefixes of the active module's tiers that need no artifact (rr-META-006)."""
    from catalyst.tiers import prefix_re

    lines = [l for l in message.splitlines() if l.strip() and not l.startswith("#")]
    if not lines:
        return "empty message"
    if prefix_re(prefixes).match(lines[0]):
        return None
    mark = f" (or mark it `{prefixes[0]}`)" if prefixes else ""
    tokens = cited(message)
    if corpus is None:
        if any(FULL_SHAPE.match(t) for t in tokens):
            return None
        return f"cites no artifact or rule ID{mark}"
    all_ids = corpus.all_ids()
    for t in tokens:
        if t in all_ids:
            return None
        matches = sorted(i for i in all_ids if i.startswith(t + "-"))
        if len(matches) == 1:
            return None
        if len(matches) > 1:
            return f"{t} is ambiguous ({', '.join(matches[:3])}): cite the full ID"
    if tokens:
        return f"cites {', '.join(sorted(set(tokens))[:3])}, which resolve to nothing in the deployment"
    return f"cites no artifact or rule ID{mark}"


def commits(repo: Path, rev_range: str | list[str], options: tuple[str, ...] = ()) -> list[tuple[str, list[str], str]]:
    """`rev_range`: user-supplied revisions, never options (`revisions`);
    `options`: the caller's own `git log` options (e.g. `--since=`)."""
    revs = revisions([rev_range] if isinstance(rev_range, str) else rev_range)
    res = subprocess.run(
        ["git", "-C", str(repo), "log", "--format=%H%x00%P%x00%B%x1e", *options, *revs],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if res.returncode != 0:
        raise ValueError(res.stderr.strip() or f"bad range {rev_range}")
    out = []
    for record in res.stdout.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        sha, parents, body = record.split("\x00", 2)
        out.append((sha, parents.split(), body))
    return out


def changed_files(repo: Path, rev_range: str | list[str]) -> dict[str, list[str]]:
    """Each commit's changed files, relative to the repository top."""
    revs = revisions([rev_range] if isinstance(rev_range, str) else rev_range)
    res = subprocess.run(
        ["git", "-C", str(repo), "log", "--no-renames", "--name-only", "-z", "--format=%x1e%H", *revs],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if res.returncode != 0:
        raise ValueError(res.stderr.strip() or f"bad range {rev_range}")
    out: dict[str, list[str]] = {}
    for record in res.stdout.split("\x1e"):
        fields = [f.strip("\n") for f in record.split("\x00")]
        fields = [f for f in fields if f]
        if fields:
            out[fields[0]] = fields[1:]
    return out


def trace(
    repo: Path, rev_range: str, corpus: Corpus | None, scoped: bool = False, prefixes: tuple[str, ...] = ("chore:",)
) -> tuple[int, list[Failure]]:
    """Check each non-merge commit's message. `scoped`: only commits that
    change a file this deployment governs, or no file at all
    (fw-STRUCTURE-000017) — another project's commits in a shared
    repository are that project's to check."""
    checked, failures = 0, []
    files: dict[str, list[str]] = {}
    prefix = ""
    from catalyst.scope import governs

    if scoped:
        files = changed_files(repo, rev_range)
        prefix = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--show-prefix"], capture_output=True, text=True, encoding="utf-8"
        ).stdout.strip()
    for sha, parents, body in commits(repo, rev_range):
        if len(parents) > 1:
            continue  # merges carry their parents' trace
        if scoped and files.get(sha):
            mine = [f[len(prefix) :] for f in files[sha] if f.startswith(prefix)]
            if not any(governs(repo, f) for f in mine):
                continue  # changes only other projects' files
        checked += 1
        reason = check_message(body, corpus, prefixes)
        if reason:
            failures.append(Failure(sha[:10], body.splitlines()[0] if body else "", reason))
    return checked, failures


def hook_path(project_root: Path) -> Path:
    """The commit-msg hook `install_hook` writes; refused when it is not a git repository, or the hook there is
    someone else's."""
    git_dir = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "--absolute-git-dir"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if git_dir.returncode != 0:
        raise ValueError(f"{project_root} is not a git repository")
    hook = Path(git_dir.stdout.strip()) / "hooks" / "commit-msg"
    if hook.exists() and "catalyst hook install" not in hook.read_text(encoding="utf-8", errors="ignore"):
        raise ValueError(f"{hook} exists and was not written by catalyst — merge it by hand")
    return hook


def install_hook(project_root: Path, router: str | None = None) -> Path:
    """Write the commit-msg hook. `router` is the CLI it falls back to: the launcher's path for a deployment whose
    criterion is in catalyst's home; by default a legacy deployment's vendored `.criterion/bin/catalyst.pyz`,
    relative to the repository top."""
    hook = hook_path(project_root)
    if router is None:
        prefix = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "--show-prefix"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        router = f"{prefix}.criterion/bin/catalyst.pyz"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(HOOK.replace("{router}", Path(router).as_posix()), encoding="utf-8")
    hook.chmod(0o755)
    return hook


def route(top: Path, message_file: Path, cli: list[str]) -> int:
    """The commit-msg hook's router (fw-STRUCTURE-000017): every deployment
    owning a staged file checks the message and its own staged files with
    its own vendored CLI; with no owned file staged, the repository top's
    deployment does, if there is one. Fails if any of them refuses."""
    import sys

    from catalyst.scope import owner

    res = subprocess.run(
        ["git", "-C", str(top), "diff", "--cached", "--name-only", "-z"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    staged = [p for p in res.stdout.split("\0") if p]
    owners = sorted({o for o in (owner(top, p) for p in staged) if o is not None})
    import project_file

    if not owners and project_file.is_project(Path(top)):
        owners = [Path(top).absolute()]
    status = 0
    for o in owners:
        command = cli
        criterion = project_file.resolve(o)
        if criterion is not None:
            from catalyst.runtime import venv_python

            python, vendored = venv_python(criterion / ".venv"), criterion / "bin" / "catalyst.pyz"
            if python.exists():  # the project's own runtime
                command = [str(python), "-m", "catalyst"]
            elif vendored.is_file():
                command = [sys.executable, str(vendored)]
        done = subprocess.run([*command, "--project", str(o), "hook", "commit-msg", str(message_file)])
        status = max(status, done.returncode)
    return status
