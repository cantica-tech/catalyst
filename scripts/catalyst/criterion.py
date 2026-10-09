"""Shared deployments on plain git (Rules-of-Rules.md §13, INV-18).

A shared ("repoed") deployment's working copy is a git submodule of the
product repository at `.criterion`, pointing at the criterion repository:
every product commit pins the rules in force. Contributors land changes
through pull requests against the shared branch; CI runs `catalyst check`
and `catalyst criterion integrity` on the pull request, and branch
protection makes those gates real.

- create:    turn a local-only deployment into a submodule on a new remote.
- join:      check out a shared deployment in a fresh clone of the product.
- status:    where the working copy stands against the shared branch.
- push:      commit, rebase on the shared branch (the journal merges by
             union, indexes are regenerated), check, push with a lease and
             open a pull request. A real conflict stops the push; the agent
             may propose a resolution as a RECON case, a human decides.
- sync:      fast-forward to the shared branch; refuses while local work is
             uncommitted or unpushed.
- integrity: nothing either side of a merge had — entity IDs, rule IDs,
             index rows, journal lines — may be missing from the result.
- protect:   branch protection for the shared branch (GitHub, explicit --yes).
"""

from __future__ import annotations

import datetime
import json
import os
import re
import secrets
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import project_file
from catalyst import proc
from catalyst.deployment import Deployment

DEFAULT_BRANCH = "criterion"
ATTRIBUTES_HEADER = "# catalyst: append-only and regenerated files merge by union (catalyst criterion)"
CI_WORKFLOW = ".github/workflows/catalyst.yml"
ENTITY_ID_RE = re.compile(r"\b([A-Z][A-Z0-9]*-\d{6}-[A-Za-z0-9]{8})\b")
RULE_HEAD_RE = re.compile(r"^#{2,3}\s+(?:\d+\.\s+)?`([a-z]+-[A-Z][A-Z0-9]*-\d+(?:-[A-Za-z0-9]+)*)`", re.M)
ARTIFACT_NAME_RE = re.compile(r"(?:^|/)([A-Z][A-Z0-9]*-\d{6})-[^/]+\.md$")
INDEX_ROW_RE = re.compile(r"^\|\s*\[`?([A-Za-z]+-\d{3,6}(?:-[A-Za-z0-9]+)*)`?\]\(", re.M)


CI_TEMPLATE = """\
# Written by `catalyst criterion create` (rewritten by it while this line stays). Runs the catalyst gates on every
# pull request against the shared branch: branch protection
# (`catalyst criterion protect`) requires this check to pass.
# The change under review cannot change its own gate: this workflow runs as the base branch defines it
# (pull_request_target), and so does the checker, the base's bin/catalyst.pyz, verified against the hash the
# base records in bin/catalyst.pyz.sha256. The pull request is checked out as data only: nothing in it runs.
name: catalyst
on:
  pull_request_target:
    branches: [{{BRANCH}}]
  push:
    branches: [{{BRANCH}}]
permissions:
  contents: read
jobs:
  catalyst:
    runs-on: ubuntu-latest
    steps:
      - name: the checker, from the base branch
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.base.sha || github.sha }}
          path: gate
          persist-credentials: false
      - name: the change under review, merged into its base
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event_name == 'pull_request_target' && format('refs/pull/{0}/merge', github.event.pull_request.number) || github.sha }}
          path: change
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: verify the checker against the hash recorded on the base
        working-directory: gate
        run: sha256sum --check --strict bin/catalyst.pyz.sha256
      - name: fetch the journal's pinned blobs
        working-directory: change
        run: |
          # a brand-new repository has no pins yet; any other failure fails
          if git ls-remote --exit-code origin refs/catalyst/journal >/dev/null; then
            git fetch origin refs/catalyst/journal:refs/catalyst/journal
          fi
      - name: catalyst check
        working-directory: change
        run: python3 "$GITHUB_WORKSPACE/gate/bin/catalyst.pyz" --working-copy . check
      - name: nothing recorded was lost in the merge
        if: github.event_name == 'pull_request_target'
        working-directory: change
        run: python3 "$GITHUB_WORKSPACE/gate/bin/catalyst.pyz" --working-copy . criterion integrity
"""


class CriterionError(Exception):
    pass


class NeedsURL(CriterionError):
    """The deployment has no criterion repository yet (local only), and the
    command needs one: the caller asks for the URL, or passes --url."""

    def __init__(self, what: str = "this deployment is local only"):
        super().__init__(
            f"no criterion repository yet: {what} — pass --url <url> (the criterion "
            "repository: empty, or already holding this working copy's history)"
        )


class CriterionConflict(CriterionError):
    """A rebase hit a conflict git cannot resolve on its own."""

    def __init__(self, files: list[str]):
        self.files = files
        super().__init__(
            "rebasing onto the shared branch conflicts in: "
            + ", ".join(files)
            + ". Nothing was pushed. Resolve by hand, or record a proposed resolution "
            "as a RECON case for a human to accept (/reconcile) — never auto-apply one."
        )


# --- arguments that reach git ------------------------------------------------
# A URL or branch name is handed to git as an operand: one that starts with
# "-" would be read as an option (`--upload-pack=<command>` runs a command),
# and "<transport>::" selects a remote helper that can run one. Both are
# refused before git sees them; git calls also put "--" before operands.
BRANCH_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._/-]*$")


def check_url(url: str | None) -> str:
    if not url or url != url.strip() or any(ord(c) < 32 or ord(c) == 127 for c in url):
        raise CriterionError(f"{url!r} is not a usable criterion repository URL")
    if url.startswith("-"):
        raise CriterionError(f"{url!r} is not a repository URL (it starts with '-', which git reads as an option)")
    if "::" in url:
        raise CriterionError(f"{url!r} is not a repository URL ('<transport>::' remote helpers are refused)")
    return url


def check_branch(branch: str | None) -> str:
    if (
        not branch
        or not BRANCH_RE.match(branch)
        or ".." in branch
        or "//" in branch
        or branch.endswith((".", "/", ".lock"))
        or "/." in branch
    ):
        raise CriterionError(
            f"{branch!r} is not a usable shared branch name "
            "(letters, digits, '.', '_', '-', '/'; not starting with '-')"
        )
    return branch


def run(repo: Path, *args: str, check: bool = True, input: str | None = None) -> subprocess.CompletedProcess:
    res = proc.run(["git", "-C", str(repo), *args], input=input)
    if check and res.returncode != 0:
        raise CriterionError(f"git {' '.join(args)} failed in {repo}: {(res.stderr or res.stdout).strip()}")
    return res


def out(repo: Path, *args: str) -> str:
    return run(repo, *args).stdout.strip()


def remote_url(wc: Path) -> str | None:
    return run(wc, "remote", "get-url", "origin", check=False).stdout.strip() or None


def ensure_remote(dep: Deployment, url: str | None) -> tuple[Deployment, list[str]]:
    """The deployment, published to `url` first if it has no criterion
    repository yet (as `create <url>` does). Raises NeedsURL when it has
    none and no URL was given."""
    if remote_url(dep.root):
        return dep, []
    if not url:
        raise NeedsURL()
    check_url(url)
    if dep.standalone:
        raise CriterionError("a working copy opened on its own cannot be published — run from the product")
    notes = create(dep, url, shared_branch(dep), CI_TEMPLATE)
    from catalyst.deployment import load

    return load(dep.project_root), notes


def shared_branch(dep: Deployment) -> str:
    return check_branch(str(dep.pointer.get("criterion_branch") or DEFAULT_BRANCH))


def repo_place(project_root: Path) -> tuple[Path, str]:
    """The repository top holding the project, and the project's prefix in it
    (`""` at the top, else `sub/dir/`): `.gitmodules` lives at the top and
    names the working copy `<prefix>.criterion` (fw-STRUCTURE-000017)."""
    top = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    if not top:
        return Path(project_root), ""
    prefix = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "--show-prefix"], capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()
    return Path(top), prefix


def is_submodule(project_root: Path) -> bool:
    top, prefix = repo_place(project_root)
    gm = top / ".gitmodules"
    if not gm.is_file():
        return False
    res = subprocess.run(
        ["git", "config", "-f", str(gm), "--get-regexp", r"submodule\..*\.path"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return any(line.split()[-1] == f"{prefix}.criterion" for line in res.stdout.splitlines())


def in_home(dep: Deployment) -> bool:
    """The deployment's criterion is in catalyst's home store (ADR-010): its
    own repository, shared through a remote, with no submodule."""
    name = project_file.project_name(dep.pointer)
    return bool(name) and not dep.standalone and dep.root == project_file.home_criterion(name)


def dirty(wc: Path) -> list[str]:
    # not out(): stripping would eat the first line's leading status column
    return [line[3:] for line in run(wc, "status", "--porcelain").stdout.splitlines() if line.strip()]


# --- merge-safe storage -----------------------------------------
def attribute_paths(dep: Deployment) -> list[str]:
    """Files that merge by union: the append-only journal and every index
    catalyst regenerates (rows from both sides are kept, then regenerated)."""
    # rules/rules.md is hand-maintained (not regenerated): concurrent edits
    # there must surface as conflicts, not as silently duplicated rows.
    paths = ["development/journal.jsonl", "development/journal/**/*.jsonl"]
    for etd in dep.etds.values():
        folder = dep.folder(etd)
        if folder is not None and etd.naming != "free-form":
            paths.append(f"{folder.relative_to(dep.root).as_posix()}/{folder.name}.md")
    return sorted(set(paths))


def write_attributes(dep: Deployment) -> bool:
    """Write the working copy's .gitattributes; True if it changed."""
    target = dep.root / ".gitattributes"
    old = target.read_text(encoding="utf-8") if target.is_file() else ""
    generated = {f"{p} merge=union" for p in attribute_paths(dep)}
    lines, kept, in_block = old.splitlines(), [], False
    for line in lines:  # drop only the block catalyst wrote
        if line.startswith(ATTRIBUTES_HEADER):
            in_block = True
            continue
        if in_block and line.endswith(" merge=union"):
            continue
        in_block = False
        if line.strip() and line not in generated:
            kept.append(line)
    body = [ATTRIBUTES_HEADER] + [f"{p} merge=union" for p in attribute_paths(dep)]
    new = "\n".join(kept + ([""] if kept else []) + body) + "\n"
    if new != old:
        target.write_text(new, encoding="utf-8")
        return True
    return False


def write_ci(dep: Deployment, template: str) -> bool:
    """Write the CI workflow, or refresh one catalyst wrote (its first line
    says so); a workflow the team replaced is left alone."""
    target = dep.root / CI_WORKFLOW
    new = template.replace("{{BRANCH}}", shared_branch(dep))
    if target.is_file():
        old = target.read_text(encoding="utf-8")
        if not old.startswith("# Written by `catalyst criterion create`") or old == new:
            return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new, encoding="utf-8")
    return True


GATE_HASH = "bin/catalyst.pyz.sha256"


def write_gate_hash(dep: Deployment) -> bool:
    """Record the vendored CLI's SHA-256 (`sha256sum` format) next to it: CI
    verifies the base branch's checker against it before running it. True
    if it changed."""
    pyz = dep.root / "bin" / "catalyst.pyz"
    if not pyz.is_file():
        return False
    import hashlib

    target = dep.root / GATE_HASH
    new = f"{hashlib.sha256(pyz.read_bytes()).hexdigest()}  bin/catalyst.pyz\n"
    if target.is_file() and target.read_text(encoding="utf-8") == new:
        return False
    target.write_text(new, encoding="utf-8")
    return True


def fetch_product_pins(dep: Deployment) -> None:
    """The product repository's journal pins (the blobs of journaled product
    files), so a contributor's `catalyst check` sees what CI and the author
    saw. Best effort: a product without a remote, or without pins, is fine."""
    if dep.standalone:
        return
    project = dep.project_root
    if run(project, "remote", "get-url", "origin", check=False).returncode != 0:
        return
    try:
        share_pins(project, publish=False)
    except CriterionError:
        pass


# --- shared pins ------------------------------------------------------------
REMOTE_PINS = "refs/catalyst/remote-journal"


def share_pins(wc: Path, publish: bool = True) -> int:
    """Merge the remote's journal pins into ours and (with publish) push the
    result, so every clone holds every blob the journal references. Pin
    trees are unions: nobody's pins are lost when two contributors pin in
    parallel. Returns how many blobs the merged set holds."""
    for attempt in range(3):  # a concurrent pin push: fetch, merge, retry
        try:
            return _share_pins_once(wc, publish)
        except CriterionError:
            if attempt == 2:
                raise
    return 0


def _share_pins_once(wc: Path, publish: bool) -> int:
    from catalyst import journal

    has_remote = (
        run(wc, "fetch", "-q", "--", "origin", f"+{journal.PIN_REF}:{REMOTE_PINS}", check=False).returncode == 0
    )
    local = run(wc, "rev-parse", "-q", "--verify", journal.PIN_REF, check=False).stdout.strip()
    remote = run(wc, "rev-parse", "-q", "--verify", REMOTE_PINS, check=False).stdout.strip() if has_remote else ""
    if remote and local != remote:
        if not local or run(wc, "merge-base", "--is-ancestor", local, remote, check=False).returncode == 0:
            run(wc, "update-ref", journal.PIN_REF, remote, local or "0" * 40)  # fast-forward
        elif run(wc, "merge-base", "--is-ancestor", remote, local, check=False).returncode != 0:
            names = journal.pinned(wc) | {
                line.split("\t", 1)[1] for line in out(wc, "ls-tree", REMOTE_PINS).splitlines() if "\t" in line
            }
            tree = run(wc, "mktree", input="".join(f"100644 blob {n}\t{n}\n" for n in sorted(names))).stdout.strip()
            commit = out(
                wc,
                "-c",
                "user.name=catalyst",
                "-c",
                "user.email=catalyst@localhost",
                "commit-tree",
                tree,
                "-p",
                local,
                "-p",
                remote,
                "-m",
                "catalyst journal: merge pins",
            )
            run(wc, "update-ref", journal.PIN_REF, commit, local)
    if publish and run(wc, "rev-parse", "-q", "--verify", journal.PIN_REF, check=False).returncode == 0:
        run(wc, "push", "-q", "--", "origin", f"{journal.PIN_REF}:{journal.PIN_REF}")
    return len(journal.pinned(wc))


# --- integrity --------------------------------------------------
@dataclass
class Facts:
    journal: set[str] = field(default_factory=set)
    ids: set[str] = field(default_factory=set)  # defined: artifact files, rule headings
    rows: set[str] = field(default_factory=set)  # registered in an index


def _journal_source(name: str) -> bool:
    """The legacy journal file or one of its shards (journal.py)."""
    return name == "development/journal.jsonl" or (name.startswith("development/journal/") and name.endswith(".jsonl"))


def facts_at(wc: Path, rev: str) -> Facts:
    """What a revision of the working copy records, read straight from git."""
    listing = run(wc, "ls-tree", "-r", "-z", "--name-only", rev).stdout
    names = [n for n in listing.split("\0") if n]
    md = [n for n in names if n.endswith(".md") or _journal_source(n)]
    facts = Facts()
    if not md:
        return facts
    res = subprocess.run(
        ["git", "-C", str(wc), "cat-file", "--batch"],
        input="".join(f"{rev}:{n}\n" for n in md).encode(),
        capture_output=True,
    )
    if res.returncode != 0:
        raise CriterionError(f"git cat-file --batch failed in {wc}: {res.stderr.decode().strip()}")
    batch = res.stdout  # sizes are in bytes: parse bytes, decode each body
    contents: dict[str, str] = {}
    pos = 0
    for name in md:
        header_end = batch.index(b"\n", pos)
        header = batch[pos:header_end].split()
        if header and header[-1] == b"missing":
            pos = header_end + 1
            continue
        size = int(header[2])
        body_start = header_end + 1
        contents[name] = batch[body_start : body_start + size].decode("utf-8", errors="replace")
        pos = body_start + size + 1
    for name, text in contents.items():
        if _journal_source(name):
            facts.journal |= {line for line in text.splitlines() if line.strip()}
            continue
        m = ARTIFACT_NAME_RE.search(name)
        if m:
            ids = ENTITY_ID_RE.findall(text)
            facts.ids.add(next((i for i in ids if i.startswith(m.group(1) + "-")), m.group(1)))
        if name.startswith("rules/") and "/templates/" not in name:
            facts.ids.update(RULE_HEAD_RE.findall(text))
            if name == "rules/rules.md":
                facts.rows.update(re.findall(r"`([a-z]+-[A-Z][A-Z0-9]*-\d+(?:-[A-Za-z0-9]+)*)`", text))
        facts.rows.update(INDEX_ROW_RE.findall(text))
    return facts


def integrity(wc: Path, head: str = "HEAD", parents: list[str] | None = None) -> list[str]:
    """Everything any parent recorded must still be recorded at `head`.
    Without explicit parents, `head`'s own parents are used (a merge commit,
    such as a pull request's merge ref in CI)."""
    if parents is None:
        parents = out(wc, "rev-list", "--parents", "-n", "1", head).split()[1:]
    result = facts_at(wc, head)
    problems = []
    for p in parents:
        before = facts_at(wc, p)
        short = out(wc, "rev-parse", "--short", p)
        for line in sorted(before.journal - result.journal):
            problems.append(f"journal line from {short} is missing: {line[:100]}")
        for i in sorted(before.ids - result.ids):
            problems.append(f"{i} (defined in {short}) is missing")
        for i in sorted(before.rows - result.rows):
            problems.append(f"{i} (registered in {short}) is no longer registered")
    return problems


# --- status / sync ----------------------------------------------------------
@dataclass
class Status:
    mode: str
    remote: str | None
    branch: str
    current: str | None
    dirty: list[str]
    ahead: int | None
    behind: int | None


def status(dep: Deployment, fetch: bool = False) -> Status:
    wc = dep.root
    mode = "home" if in_home(dep) else "submodule" if is_submodule(dep.project_root) else "local"
    if run(wc, "rev-parse", "--git-dir", check=False).returncode != 0:
        return Status(mode, None, shared_branch(dep), None, [], None, None)
    remote = run(wc, "remote", "get-url", "origin", check=False).stdout.strip() or None
    branch = shared_branch(dep)
    if fetch and remote:
        run(wc, "fetch", "-q", "origin")
    current = run(wc, "symbolic-ref", "-q", "--short", "HEAD", check=False).stdout.strip() or None
    ahead = behind = None
    if remote and run(wc, "rev-parse", "-q", "--verify", f"origin/{branch}", check=False).returncode == 0:
        counts = out(wc, "rev-list", "--left-right", "--count", f"origin/{branch}...HEAD").split()
        behind, ahead = int(counts[0]), int(counts[1])
    return Status(mode, remote, branch, current, dirty(wc), ahead, behind)


def guard_branch_reset(wc: Path, branch: str) -> None:
    """Refuse to reset the local shared branch if it holds commits the
    remote does not (e.g. HEAD was detached by `git submodule update`)."""
    if run(wc, "rev-parse", "-q", "--verify", f"refs/heads/{branch}", check=False).returncode != 0:
        return
    extra = run(wc, "rev-list", f"refs/heads/{branch}", "--not", "--remotes=origin", check=False).stdout.split()
    if extra:
        raise CriterionError(
            f"local branch '{branch}' has {len(extra)} commit(s) not on the remote — "
            "push them (`catalyst criterion push`) before syncing"
        )


def unpushed(wc: Path, branch: str) -> list[str]:
    """Local commits that no remote branch contains."""
    res = run(wc, "rev-list", "HEAD", "--not", "--remotes=origin", check=False)
    return res.stdout.split() if res.returncode == 0 else []


def sync(dep: Deployment) -> str:
    """Fast-forward the working copy to the shared branch. Refuses while
    local work would be lost."""
    wc, branch = dep.root, shared_branch(dep)
    if not remote_url(wc):
        raise NeedsURL()
    changes = dirty(wc)
    if changes:
        raise CriterionError(
            f"{len(changes)} uncommitted change(s) in the working copy "
            f"({', '.join(changes[:5])}) — `catalyst criterion push` them first"
        )
    run(wc, "fetch", "-q", "--prune", "origin")
    local = unpushed(wc, branch)
    if local:
        raise CriterionError(
            f"{len(local)} local commit(s) are not on the remote — `catalyst criterion push` them first"
        )
    guard_branch_reset(wc, branch)
    run(wc, "checkout", "-q", "-B", branch, f"origin/{branch}")
    share_pins(wc, publish=False)
    fetch_product_pins(dep)
    # topic branches whose work is in the shared branch are done with
    for topic in run(wc, "branch", "--format=%(refname:short)", "--merged", f"origin/{branch}").stdout.split():
        if topic != branch and "/" in topic:
            run(wc, "branch", "-q", "-d", topic, check=False)
    return out(wc, "rev-parse", "--short", "HEAD")


# --- push -------------------------------------------
@dataclass
class PushResult:
    branch: str
    commits: int
    pr: str | None
    regenerated: list[str]


def _topic(user: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", user.lower()).strip("-") or "contributor"
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{slug}/{stamp}-{secrets.token_hex(2)}"  # unique even within one second


def _ident(wc: Path, user: str) -> list[str]:
    """Commit identity: the signer as author name, and an email only when
    git has none configured (a fresh CI runner, a new machine)."""
    args = ["-c", f"user.name={user}"]
    if not run(wc, "config", "user.email", check=False).stdout.strip():
        args += ["-c", f"user.email={re.sub(r'[^A-Za-z0-9._-]+', '-', user)}@catalyst.invalid"]
    return args


def push(dep: Deployment, signer: dict, message: str, open_pr: bool = True, checker=None) -> PushResult:
    from catalyst.corpus import load_corpus
    from catalyst.deployment import load, load_working_copy
    from catalyst.indexes import regenerate

    wc, branch = dep.root, shared_branch(dep)
    if not remote_url(wc):
        raise NeedsURL()
    user = str(signer.get("git_username") or signer.get("name"))
    run(wc, "fetch", "-q", "--prune", "origin")
    try:
        share_pins(wc, publish=False)  # others' journal blobs, before anything is checked
    except CriterionError:
        pass
    fetch_product_pins(dep)
    base = f"origin/{branch}"
    has_base = run(wc, "rev-parse", "-q", "--verify", base, check=False).returncode == 0
    current = run(wc, "symbolic-ref", "-q", "--short", "HEAD", check=False).stdout.strip()
    topic = current if current and current != branch else ""
    remote_topic = ""
    if topic:
        remote_topic = run(wc, "rev-parse", "-q", "--verify", f"origin/{topic}", check=False).stdout.strip()
        merged = (
            has_base
            and remote_topic
            and run(wc, "merge-base", "--is-ancestor", remote_topic, base, check=False).returncode == 0
        )
        if not remote_topic and run(wc, "config", f"branch.{topic}.remote", check=False).stdout.strip():
            topic = ""  # pushed before, branch now deleted: its PR was merged
        elif merged:
            topic = ""  # its pull request was merged: start a new one
        elif remote_topic and run(wc, "merge-base", "--is-ancestor", remote_topic, "HEAD", check=False).returncode != 0:
            raise CriterionError(
                f"origin/{topic} has commits this working copy does not have (a reviewer's?) — "
                f"`git -C {wc} pull --rebase origin {topic}` first; nothing was pushed"
            )
    if not topic:
        topic, remote_topic = _topic(user), ""
    if current != topic:
        run(wc, "checkout", "-q", "-B", topic)
    if write_attributes(dep):
        from catalyst import journal as _journal

        _journal.append(
            dep,
            _journal.AppendRequest(
                command="catalyst criterion push",
                action="update",
                artifact="merge attributes refreshed",
                targets=[],
                intent=[
                    "The files that merge by union changed with the deployment's entity types "
                    "or the kernel; .gitattributes now lists exactly those."
                ],
                files=[str(wc / ".gitattributes")],
                actor=user,
                allow_unchanged=True,
            ),
        )
    gate = [
        p for p, changed in ((CI_WORKFLOW, write_ci(dep, CI_TEMPLATE)), (GATE_HASH, write_gate_hash(dep))) if changed
    ]
    if gate:
        from catalyst import journal as _journal

        _journal.append(
            dep,
            _journal.AppendRequest(
                command="catalyst criterion push",
                action="update",
                artifact="CI gate refreshed",
                targets=[],
                intent=[
                    "The criterion repository's CI gate follows the vendored CLI: the workflow catalyst "
                    "wrote, and the checker's recorded hash, now match this working copy."
                ],
                files=[str(wc / p) for p in gate],
                actor=user,
                allow_unchanged=True,
            ),
        )
    if dirty(wc):
        run(wc, "add", "-A")
        run(wc, *_ident(wc, user), "commit", "-q", "-m", message)
    pre_rebase = (
        out(wc, "rev-parse", "HEAD")
        if run(wc, "rev-parse", "-q", "--verify", "HEAD", check=False).returncode == 0
        else None
    )
    if has_base:
        res = run(wc, *_ident(wc, user), "rebase", "-q", base, check=False)
        if res.returncode != 0:
            files = out(wc, "diff", "--name-only", "--diff-filter=U").splitlines()
            run(wc, "rebase", "--abort", check=False)
            raise CriterionConflict(files or ["(see git status)"])
    # Rows merged by union are regenerated in ID order.
    fresh = load_working_copy(wc) if dep.standalone else load(dep.project_root)
    from catalyst import journal

    changes = regenerate(fresh, load_corpus(fresh))
    regenerated = [str(c.path.relative_to(wc)) for c in changes]
    # Files the rebase merged (by union, or a clean three-way merge of both
    # sides' edits) match neither side's journaled version: record their
    # merged state, with the regeneration.
    rebased = set(out(wc, "diff", "--name-only", pre_rebase, "HEAD").splitlines()) if pre_rebase else set()
    merged = [
        p[len(journal.WC) :]
        for p in journal.unjournaled(fresh)
        if p.startswith(journal.WC) and p[len(journal.WC) :] in rebased
    ]
    touched = sorted(set(regenerated) | set(merged))
    if touched:
        journal.append(
            fresh,
            journal.AppendRequest(
                command="catalyst criterion push",
                action="update",
                artifact="files merged by rebasing onto the shared branch",
                targets=[],
                intent=[
                    "Rebasing onto the shared branch merged both sides' changes to these files "
                    "(append-only and index files by union, then indexes rewritten in ID order by "
                    "catalyst index regen); this records their merged state."
                ],
                files=[str(wc / p) for p in touched],
                actor=user,
                allow_unchanged=True,
            ),
        )
        run(wc, "add", "-A")
        run(wc, *_ident(wc, user), "commit", "-q", "-m", "Regenerate indexes after rebase")
    report = (checker or _check)(fresh)
    if report:
        raise CriterionError("catalyst check fails on the rebased work — nothing was pushed:\n" + report)
    if has_base:
        lost = integrity(wc, "HEAD", [base])
        if lost:
            raise CriterionError("the rebase lost recorded content — nothing was pushed:\n" + "\n".join(lost))
        commits = int(out(wc, "rev-list", "--count", f"{base}..HEAD"))
    else:
        commits = int(out(wc, "rev-list", "--count", "HEAD"))
    if commits == 0:
        return PushResult(topic, 0, None, regenerated)
    # An explicit lease: the remote branch must still be what we built on.
    run(
        wc,
        "push",
        "-q",
        f"--force-with-lease=refs/heads/{topic}:{remote_topic}",
        "-u",
        "--",
        "origin",
        f"HEAD:refs/heads/{topic}",
    )
    try:
        share_pins(wc)
    except CriterionError as exc:  # the pins go with the next push; the work is safe
        print(f"catalyst: journal pins not shared yet ({exc})")
    pr = open_pull_request(wc, branch, topic, message) if open_pr else None
    return PushResult(topic, commits, pr, regenerated)


def _check(dep: Deployment) -> str:
    from catalyst.check import run as run_checks

    report = run_checks(dep)
    return "\n".join(report.errors)


def open_pull_request(wc: Path, base: str, head: str, title: str) -> str | None:
    if shutil.which("gh") is None:
        return None
    existing = subprocess.run(
        ["gh", "pr", "view", head, "--json", "url", "--jq", ".url"],
        cwd=wc,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if existing.returncode == 0 and existing.stdout.strip():
        return existing.stdout.strip()
    res = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--base",
            base,
            "--head",
            head,
            "--title",
            title,
            "--body",
            "Opened by `catalyst criterion push`. CI runs `catalyst check` "
            "and `catalyst criterion integrity` on this pull request.",
        ],
        cwd=wc,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return res.stdout.strip().splitlines()[-1] if res.returncode == 0 and res.stdout.strip() else None


# --- create / join ----------------------------------------------
def create(
    dep: Deployment, url: str | None = None, branch: str = DEFAULT_BRANCH, ci_template: str | None = None
) -> list[str]:
    """Version a local-only working copy for sharing and, given `url`,
    publish it there and make it the product repository's `.criterion`
    submodule. Without a URL the deployment stays strictly local: the first
    `push`, `sync` or `join` asks for one. Stages the product changes; the
    caller commits them."""
    project, wc = dep.project_root, dep.root
    check_branch(branch)
    if url is not None:
        check_url(url)
    if in_home(dep):
        if url is None and run(wc, "rev-parse", "--git-dir", check=False).returncode == 0 and remote_url(wc):
            raise CriterionError(f"the criterion already has a repository ({remote_url(wc)})")
        notes = _prepare(dep, url, branch, ci_template)
        return notes + (_record_local(dep, branch) if url is None else _publish_home(dep, url, branch))
    link = project / ".criterion"
    if is_submodule(project):
        raise CriterionError(".criterion is already a submodule of this project")
    if not link.is_symlink():
        raise CriterionError(
            ".criterion is not a symlink to an agent-owned working copy; "
            "move an in-project working copy into agent-owned space first"
        )
    if url is None and run(wc, "rev-parse", "--git-dir", check=False).returncode == 0 and remote_url(wc):
        raise CriterionError(
            f"the working copy already has a criterion repository ({remote_url(wc)}) — "
            "`catalyst criterion create <url>` to make it the .criterion submodule"
        )
    notes = _prepare(dep, url, branch, ci_template)
    if url is None:
        return notes + _record_local(dep, branch)
    return notes + _publish(dep, url, branch)


def _actor(dep: Deployment) -> str:
    user = next((u for u in _users(dep) if u.get("active", True)), {})
    return str(user.get("git_username") or user.get("name") or "catalyst")


def _prepare(dep: Deployment, url: str | None, branch: str, ci_template: str | None) -> list[str]:
    """The local half of `create`: the working copy as a git repository on
    the shared branch, its merge attributes and CI workflow, committed."""
    wc = dep.root
    notes = []
    if run(wc, "rev-parse", "--git-dir", check=False).returncode != 0:
        run(wc, "init", "-q")  # not `init -b`: that needs git >= 2.28
        run(wc, "symbolic-ref", "HEAD", f"refs/heads/{branch}")
        notes.append(f"initialised the working copy as a git repository (branch {branch})")
    dep.pointer["criterion_branch"] = branch
    written = []
    if write_attributes(dep):
        written.append(".gitattributes")
        notes.append("wrote .gitattributes (journal and indexes merge by union)")
    if ci_template and write_ci(dep, ci_template):
        written.append(CI_WORKFLOW)
        notes.append(f"wrote {CI_WORKFLOW} (catalyst check + integrity on pull requests)")
    if ci_template and write_gate_hash(dep):
        written.append(GATE_HASH)
        notes.append(f"wrote {GATE_HASH} (CI runs the base branch's checker only if it matches)")
    if written:
        from catalyst import journal

        where = f"to {url}" if url else "locally, until a criterion repository is given"
        journal.append(
            dep,
            journal.AppendRequest(
                command="catalyst criterion create",
                action="create",
                artifact="shared deployment: merge attributes and CI",
                targets=[],
                intent=[
                    f"Versioning the working copy for sharing ({where}): the journal and "
                    "regenerated indexes merge by union, and the criterion repository's CI runs "
                    "catalyst check and the integrity check on every pull request."
                ],
                files=[str(wc / w) for w in written],
                actor=_actor(dep),
                allow_unchanged=True,
            ),
        )
    if dirty(wc):
        run(wc, "add", "-A")
        run(wc, *_ident(wc, _actor(dep)), "commit", "-q", "-m", "Publish the catalyst working copy")
    return notes


def _record_local(dep: Deployment, branch: str) -> list[str]:
    """A local-only create: the working copy sits on the shared branch, and
    the pointer names that branch for the publication to come."""
    project, wc = dep.project_root, dep.root
    notes = []
    if run(wc, "symbolic-ref", "-q", "--short", "HEAD", check=False).stdout.strip() != branch:
        run(wc, "checkout", "-q", "-B", branch)
    pointer_path = project_file.find(project)
    pointer = project_file.read(pointer_path)
    if pointer.get("criterion_branch", DEFAULT_BRANCH) != branch or "criterion_branch" not in pointer:
        pointer.update({"criterion_branch": branch, "updated": datetime.date.today().isoformat()})
        project_file.write(pointer_path, pointer)
        run(project, "add", pointer_path.name, check=False)
        from catalyst import journal

        journal.append(
            dep,
            journal.AppendRequest(
                command="catalyst criterion create",
                action="update",
                artifact="criterion branch",
                targets=[],
                intent=[f"The pointer names the shared branch ({branch}) the working copy will be published on."],
                files=[str(pointer_path)],
                actor=_actor(dep),
                allow_unchanged=True,
            ),
        )
        run(wc, "add", "-A")
        run(wc, *_ident(wc, _actor(dep)), "commit", "-q", "-m", "Journal the criterion branch")
        notes.append(f"recorded criterion_branch ({branch}) in {pointer_path.name} (staged, not committed)")
    notes.append(
        f"the working copy is versioned locally on branch {branch}, with no criterion repository: "
        "`catalyst criterion push`, `sync` or `join` ask for its URL when first run (or take --url)"
    )
    return notes


def _unignore(project: Path) -> str | None:
    """Drop /.criterion from the product's .gitignore; returns the old text."""
    gitignore = project / ".gitignore"
    if not gitignore.is_file():
        return None
    old = gitignore.read_text(encoding="utf-8")
    lines = [
        line
        for line in old.splitlines()
        if line.strip() not in ("/.criterion", ".criterion", "/.criterion/", ".criterion/")
        and not line.startswith("# catalyst working copy:")
    ]
    gitignore.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return old


def _record_shared(project: Path, url: str, branch: str) -> Path:
    """Record the sharing in the pointer and stage the product files."""
    pointer_path = project_file.find(project)
    pointer = project_file.read(pointer_path)
    pointer.update(
        {
            "repoed": True,
            "catalyst_repo_url": url,
            "criterion_branch": branch,
            "updated": datetime.date.today().isoformat(),
        }
    )
    project_file.write(pointer_path, pointer)
    run(
        project,
        "add",
        pointer_path.name,
        str(repo_place(project)[0] / ".gitmodules"),
        *([".gitignore"] if (project / ".gitignore").is_file() else []),
    )
    return pointer_path


def _publish(dep: Deployment, url: str, branch: str) -> list[str]:
    """The remote half of `create`: push the working copy to `url` and make
    it the product repository's `.criterion` submodule."""
    project, wc = dep.project_root, dep.root
    link = project / ".criterion"
    notes = []
    if run(wc, "remote", "get-url", "origin", check=False).returncode == 0:
        run(wc, "remote", "set-url", "--", "origin", url)
    else:
        run(wc, "remote", "add", "--", "origin", url)
    remote_head = run(wc, "ls-remote", "--heads", "--", "origin", branch).stdout.strip()
    if remote_head:
        run(wc, "fetch", "-q", "--", "origin", branch)
        if run(wc, "merge-base", "--is-ancestor", f"origin/{branch}", "HEAD", check=False).returncode != 0:
            raise CriterionError(f"{url} already has a '{branch}' branch this working copy does not contain")
    run(wc, "push", "-q", "-u", "--", "origin", f"HEAD:refs/heads/{branch}")
    try:
        share_pins(wc)
        notes.append(f"pushed the working copy and its journal pins to {url} ({branch})")
    except CriterionError as exc:
        notes.append(f"pushed the working copy to {url} ({branch}); journal pins not shared yet: {exc}")
    agent_owned = os.path.realpath(link)
    gitignore = project / ".gitignore"
    link.unlink()
    old_gitignore = _unignore(project)
    try:
        run(project, "submodule", "add", "-b", branch, "--", url, ".criterion")
    except CriterionError as exc:
        # put the project back exactly as it was: symlink, .gitignore, no half submodule
        run(project, "rm", "-q", "--cached", "-r", "--ignore-unmatch", ".criterion", check=False)
        shutil.rmtree(project / ".criterion", ignore_errors=True)
        git_dir = Path(out(project, "rev-parse", "--absolute-git-dir"))
        top, prefix = repo_place(project)
        shutil.rmtree(git_dir / "modules" / f"{prefix}.criterion", ignore_errors=True)
        gm = top / ".gitmodules"
        if gm.is_file() and not gm.read_text(encoding="utf-8").strip():
            gm.unlink()
            run(top, "rm", "-q", "--cached", "--ignore-unmatch", ".gitmodules", check=False)
        link.symlink_to(agent_owned)
        if old_gitignore is not None:
            gitignore.write_text(old_gitignore, encoding="utf-8")
        raise CriterionError(
            f"adding the submodule failed, so nothing changed in the project "
            f"(the working copy is still at {agent_owned}, now also on {url}): {exc}"
        ) from exc
    notes.append("added .criterion as a submodule of the product repository (staged, not committed)")
    pointer_path = _record_shared(project, url, branch)
    from catalyst import journal
    from catalyst.deployment import load

    shared = load(project)
    actor = _actor(shared)
    journal.append(
        shared,
        journal.AppendRequest(
            command="catalyst criterion create",
            action="update",
            artifact="deployment shared",
            targets=[],
            intent=[
                f"The working copy is now the .criterion submodule of {url}; the pointer records the "
                "sharing and .gitignore no longer ignores .criterion."
            ],
            files=[
                str(project / p) for p in (pointer_path.name, ".gitmodules", ".gitignore") if (project / p).is_file()
            ],
            actor=actor,
            allow_unchanged=True,
        ),
    )
    run(wc, "add", "-A")
    run(wc, *_ident(wc, actor), "commit", "-q", "-m", "Journal the sharing of the deployment")
    run(wc, "push", "-q", "--", "origin", f"HEAD:refs/heads/{branch}")
    notes.append(
        "journaled the product files it changed (pointer, .gitmodules, .gitignore); share the "
        "product repository's journal pins with `catalyst journal pin --share` when you push it"
    )
    notes.append(f"updated {pointer_path.name} (repoed, catalyst_repo_url, criterion_branch)")
    notes.append(f"the old agent-owned copy at {agent_owned} is no longer used; remove it once satisfied")
    return notes


def _push_branch(wc: Path, url: str, branch: str) -> None:
    if run(wc, "remote", "get-url", "origin", check=False).returncode == 0:
        run(wc, "remote", "set-url", "--", "origin", url)
    else:
        run(wc, "remote", "add", "--", "origin", url)
    if run(wc, "ls-remote", "--heads", "--", "origin", branch).stdout.strip():
        run(wc, "fetch", "-q", "--", "origin", branch)
        if run(wc, "merge-base", "--is-ancestor", f"origin/{branch}", "HEAD", check=False).returncode != 0:
            raise CriterionError(f"{url} already has a '{branch}' branch this criterion does not contain")
    run(wc, "push", "-q", "-u", "--", "origin", f"HEAD:refs/heads/{branch}")


def _publish_home(dep: Deployment, url: str, branch: str) -> list[str]:
    """Share a home-store criterion: push it to `url` and record the remote in
    catalyst.toml. No submodule — a collaborator's `catalyst criterion join`
    clones it into their own home store."""
    project, wc = dep.project_root, dep.root
    _push_branch(wc, url, branch)
    notes = [f"pushed the criterion to {url} ({branch})"]
    try:
        share_pins(wc)
    except CriterionError as exc:
        notes.append(f"journal pins not shared yet: {exc}")
    pointer_path = project_file.find(project)
    pointer = project_file.read(pointer_path)
    pointer.update(
        {
            "repoed": True,
            "catalyst_repo_url": url,
            "criterion_branch": branch,
            "updated": datetime.date.today().isoformat(),
        }
    )
    project_file.write(pointer_path, pointer)
    in_repo = run(project, "rev-parse", "--git-dir", check=False).returncode == 0
    if in_repo:
        run(project, "add", "--", pointer_path.name, check=False)
    from catalyst import journal
    from catalyst.deployment import load

    shared = load(project)
    journal.append(
        shared,
        journal.AppendRequest(
            command="catalyst criterion create",
            action="update",
            artifact="deployment shared",
            targets=[],
            intent=[
                f"The criterion is shared through {url}; catalyst.toml records the remote, and a collaborator "
                "joins with `catalyst criterion join`."
            ],
            files=[str(pointer_path)] if in_repo else [str(wc / "version.txt")],
            actor=_actor(shared),
            allow_unchanged=True,
        ),
    )
    run(wc, "add", "-A")
    run(wc, *_ident(wc, _actor(shared)), "commit", "-q", "-m", "Journal the sharing of the criterion")
    run(wc, "push", "-q", "--", "origin", f"HEAD:refs/heads/{branch}")
    notes.append(f"recorded the remote in {pointer_path.name} (staged, not committed)")
    return notes


def join_home(project_root: Path, url: str | None = None, runtime: bool = True) -> str:
    """Join a shared home-store deployment on this machine: clone its criterion
    repository into `$CATALYST_HOME/projects/<name>/criterion` (or bring an
    existing clone up to date), on the shared branch, with its runtime."""
    pointer = project_file.read_dir(project_root)
    name = project_file.project_name(pointer)
    if not name:
        raise CriterionError("the project file names no project")
    url = url or pointer.get("catalyst_repo_url")
    if not url:
        raise NeedsURL("catalyst.toml names no criterion repository")
    check_url(url)
    branch = check_branch(str(pointer.get("criterion_branch") or DEFAULT_BRANCH))
    target = project_file.home_criterion(name)
    if target.exists() and any(target.iterdir()):
        if remote_url(target) != url:
            raise CriterionError(
                f"{target} exists with another remote ({remote_url(target)}) — a different project with the same name?"
            )
        if dirty(target):
            raise CriterionError(
                f"{len(dirty(target))} uncommitted change(s) in {target} — commit or discard them first"
            )
        run(target, "fetch", "-q", "--prune", "origin")
        guard_branch_reset(target, branch)
        run(target, "checkout", "-q", "-B", branch, f"origin/{branch}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        res = subprocess.run(
            ["git", "clone", "-q", "-b", branch, "--", url, str(target)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if res.returncode != 0:
            raise CriterionError(f"cloning {url} ({branch}) failed: {res.stderr.strip()}")
    share_pins(target, publish=False)
    if runtime:
        import tempfile

        from catalyst import runtime as rt

        with tempfile.TemporaryDirectory() as tmp:
            pyz = rt.own_pyz(Path(tmp))
            rt.install_into(target, rt.pyz_version(pyz), pyz)
    return out(target, "rev-parse", "--short", "HEAD")


def _users(dep: Deployment) -> list[dict]:
    try:
        data = json.loads((dep.root / "IAM" / "users" / "users.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [u for u in data.get("users", []) if isinstance(u, dict)]


def _add_submodule(project_root: Path, url: str) -> None:
    """Add an existing criterion repository as the product's `.criterion`
    submodule, on the pointer's shared branch (staged, not committed)."""
    check_url(url)
    pointer = project_file.read_dir(project_root)
    branch = check_branch(str(pointer.get("criterion_branch") or DEFAULT_BRANCH))
    link = project_root / ".criterion"
    if link.is_symlink():
        link.unlink()  # a dangling link to another machine's working copy
    elif link.exists():
        raise CriterionError(".criterion exists and is not a submodule — move it out of the way first")
    if not run(project_root, "ls-remote", "--heads", "--", url, branch, check=False).stdout.strip():
        raise CriterionError(
            f"{url} has no '{branch}' branch — publish a working copy there first "
            "(`catalyst criterion create <url>` where it lives)"
        )
    _unignore(project_root)
    run(project_root, "submodule", "add", "-b", branch, "--", url, ".criterion")
    _record_shared(project_root, url, branch)


def join(project_root: Path, url: str | None = None) -> str:
    """Check out the shared working copy in a clone of the product
    repository. A product with no `.criterion` submodule yet needs the
    criterion repository's URL: a local working copy on this machine is
    published there (as `create <url>`); otherwise the repository is added
    as the submodule."""
    added = False
    if url is not None:
        check_url(url)
    legacy = project_root / ".criterion"
    if (project_root / project_file.NAME).is_file() and not (legacy.is_symlink() or legacy.exists()):
        return join_home(project_root, url)
    if not is_submodule(project_root):
        from catalyst.deployment import load

        link = project_root / ".criterion"
        if link.is_symlink() and link.exists():
            dep = load(project_root)
            if remote_url(dep.root):
                raise CriterionError(
                    "this project has no .criterion submodule; its local working copy "
                    f"already has a criterion repository ({remote_url(dep.root)}) — "
                    "`catalyst criterion create <url>` to make it the submodule"
                )
            ensure_remote(dep, url)
        else:
            if not url:
                raise NeedsURL("this project has no .criterion submodule")
            _add_submodule(project_root, url)
            added = True
    run(project_root, "submodule", "update", "--init", ".criterion")
    wc = project_root / ".criterion"
    pointer = project_file.read_dir(project_root)
    branch = check_branch(str(pointer.get("criterion_branch") or DEFAULT_BRANCH))
    run(wc, "fetch", "-q", "--prune", "origin")
    if run(wc, "rev-parse", "-q", "--verify", f"origin/{branch}", check=False).returncode != 0:
        raise CriterionError(f"the criterion repository has no '{branch}' branch")
    changes = dirty(wc)
    if changes:
        raise CriterionError(f"{len(changes)} uncommitted change(s) in .criterion — commit or discard them first")
    guard_branch_reset(wc, branch)
    run(wc, "checkout", "-q", "-B", branch, f"origin/{branch}")
    share_pins(wc, publish=False)
    if run(project_root, "remote", "get-url", "origin", check=False).returncode == 0:
        try:
            share_pins(project_root, publish=False)  # the product repository's journal blobs
        except CriterionError:
            pass
    if added:
        # the product files join changed, recorded in the working copy; they
        # land with the next `catalyst criterion push`
        from catalyst import journal
        from catalyst.deployment import load

        shared = load(project_root)
        journal.append(
            shared,
            journal.AppendRequest(
                command="catalyst criterion join",
                action="update",
                artifact="deployment shared",
                targets=[],
                intent=[
                    f"This product now checks out the criterion repository {pointer.get('catalyst_repo_url')} "
                    "as its .criterion submodule; the pointer records the sharing."
                ],
                files=[
                    str(project_root / p)
                    for p in (project_file.find(project_root).name, ".gitmodules", ".gitignore")
                    if (project_root / p).is_file()
                ],
                actor=_actor(shared),
                allow_unchanged=True,
            ),
        )
    return out(wc, "rev-parse", "--short", "HEAD")


# --- protect ----------------------------------------------------
def protection_payload(check_name: str = "catalyst") -> dict:
    return {
        "required_status_checks": {"strict": True, "contexts": [check_name]},
        "enforce_admins": False,
        "required_pull_request_reviews": {"required_approving_review_count": 0},
        "restrictions": None,
        "allow_force_pushes": False,
        "allow_deletions": False,
    }


def github_repo(url: str) -> str | None:
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    return m.group(1) if m else None


def protect(dep: Deployment, apply: bool) -> str:
    url = run(dep.root, "remote", "get-url", "origin", check=False).stdout.strip()
    repo = github_repo(url)
    if repo is None:
        raise CriterionError(f"branch protection is set up for GitHub remotes only (origin: {url or 'none'})")
    branch = shared_branch(dep)
    payload = json.dumps(protection_payload())
    endpoint = f"repos/{repo}/branches/{branch}/protection"
    if not apply:
        return f"would PUT {endpoint}:\n{payload}\n(re-run with --yes to apply)"
    if shutil.which("gh") is None:
        raise CriterionError("gh is not installed")
    res = proc.run(["gh", "api", "-X", "PUT", endpoint, "--input", "-"], input=payload)
    if res.returncode != 0:
        raise CriterionError(f"gh api {endpoint} failed: {res.stderr.strip() or res.stdout.strip()}")
    return f"protected {repo}:{branch} — pull requests required, status check 'catalyst' required"
