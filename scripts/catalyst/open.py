"""`catalyst open` (roadmap R3.5): make a project ready on this machine and
say where it stands — the one step after `git clone`, and the start of every
session.

Explicitly run, it acts, and only in catalyst's home (never in the project):
a criterion missing on this machine is cloned from the repository
`catalyst.toml` names (`share join`); the criterion's runtime is filled from
its own vendored CLI; the launcher is installed; `--agent` records this
user's agent. As the session-start hook (`act=False`) it changes nothing,
touches no network, and reports what `catalyst open` would do. Either way it
reports versions, the shared copy, and a to-do list of exact commands.

It replaces the prose session-start procedures: the symlink repair, the
agent switch (`catalyst open --agent <id>`) and the memory note
(`catalyst where` is the record).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import project_file


@dataclass
class Opening:
    project: str
    name: str | None
    criterion: str | None
    kind: str  # home, legacy, missing
    pinned: str | None = None  # catalyst.toml's kernel_version
    criterion_version: str | None = None  # the criterion's version.txt
    runtime: str | None = None  # the catalyst in the criterion's .venv
    agent: str = "claude-code"
    share: dict | None = None
    done: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    todo: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.todo

    def as_dict(self) -> dict:
        return {**asdict(self), "ready": self.ready}

    def render(self) -> str:
        lines = [
            f"catalyst: {self.name or '?'} — criterion {self.criterion or 'not on this machine'} ({self.kind})",
            f"  kernel {self.criterion_version or '?'} (catalyst.toml pins {self.pinned or '?'}), "
            f"runtime {self.runtime or 'none'}, agent {self.agent}",
        ]
        if self.share:
            s = self.share
            where = s.get("location") or "not shared"
            sync = f", {s['ahead']} ahead / {s['behind']} behind as last fetched" if s.get("ahead") is not None else ""
            lines.append(f"  shared: {s['driver']} ({where}){sync}")
        lines += [f"  done: {d}" for d in self.done]
        lines += [f"  note: {n}" for n in self.notes]
        lines += [f"  to do: {t}" for t in self.todo]
        if self.ready:
            lines.append("  ready")
        return "\n".join(lines)


def _base(version: str | None) -> str | None:
    m = re.match(r"\d+\.\d+\.\d+", version or "")
    return m.group(0) if m else None


def open_project(project: Path, act: bool = True, fetch: bool = False, agent: str | None = None) -> Opening:
    data = project_file.read_dir(project)
    name = project_file.project_name(data)
    criterion = project_file.resolve(project)
    home = project_file.home_criterion(name) if name else None
    kind = "home" if criterion is not None and criterion == home else "legacy" if criterion else "missing"
    o = Opening(str(project), name, str(criterion) if criterion else None, kind, pinned=data.get("kernel_version"))
    if not name:
        o.todo.append("catalyst.toml names no project_name")
        return o

    if agent:
        target = project_file.user_agent_file(name)
        if act:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(agent + "\n", encoding="utf-8")
            o.done.append(f"agent {agent} recorded for this user ({target})")
        else:
            o.todo.append(f"`catalyst open --agent {agent}` (records this user's agent)")
    o.agent = agent if agent and act else project_file.agent_of(data)

    if kind == "missing":
        url = data.get("catalyst_repo_url")
        if not url:
            o.todo.append(
                "no criterion on this machine, and catalyst.toml names no repository: "
                "`catalyst share join <url>`, or `catalyst init` for a new deployment"
            )
            return o
        if not act:
            o.todo.append(f"`catalyst open` (clones the shared criterion from {url})")
            return o
        from catalyst import criterion as cr

        cr.join_home(project, str(url), runtime=False)
        fetch = True  # a fresh criterion: the product's journal pins too
        criterion, o.kind, o.criterion = home, "home", str(home)
        o.done.append(f"joined: cloned {url} into {home}")
    if o.kind == "legacy":
        o.todo.append("`catalyst move --to-home` (this deployment keeps its criterion in the project)")
        return o

    if criterion is None:  # unreachable: missing was joined or returned above
        return o
    version_file = criterion / "version.txt"
    o.criterion_version = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else None
    _runtime(o, criterion, act)
    if o.pinned and o.criterion_version and o.pinned != o.criterion_version:
        o.todo.append(
            f"the criterion is at kernel {o.criterion_version}, catalyst.toml pins {o.pinned}: "
            "`catalyst share pull` if the shared copy is ahead, else sync (`/sync-framework`) and commit catalyst.toml"
        )
    if act and fetch:
        _product_pins(o, project)
    _share(o, project, fetch)
    return o


def _product_pins(o: Opening, project: Path) -> None:
    """The product repository's journal pins (blobs of product files that
    were journaled but never committed), shared by `journal pin --share`."""
    from catalyst import criterion as cr
    from catalyst.deployment import DeploymentNotFound, WorkingCopyMissing, load

    try:
        cr.fetch_product_pins(load(project))
    except (DeploymentNotFound, WorkingCopyMissing, cr.CriterionError) as exc:
        o.notes.append(f"the product's journal pins were not fetched: {exc}")


def _runtime(o: Opening, criterion: Path, act: bool) -> None:
    from catalyst import runtime as rt

    launcher = project_file.home() / "bin" / "catalyst"
    if not launcher.is_file():
        if act:
            rt.install_launcher()
            o.done.append(f"installed the launcher {launcher} (put {launcher.parent} on PATH)")
        else:
            o.todo.append("`catalyst open` (installs the launcher)")
    o.runtime = rt.installed_version(criterion / ".venv")
    pyz = criterion / "bin" / "catalyst.pyz"
    if not pyz.is_file():
        o.notes.append("the criterion vendors no bin/catalyst.pyz: its runtime cannot be filled")
        return
    stale = _base(o.runtime) != _base(o.criterion_version) or o.runtime is None
    if act:
        version = rt.pyz_version(pyz)  # the vendored CLI's own label
        if version != o.runtime:
            rt.install_into(criterion, version, pyz)
            o.done.append(f"filled the criterion's runtime with catalyst {version}")
            o.runtime = version
    elif stale:
        o.todo.append(
            f"`catalyst open` (the criterion's runtime is {o.runtime or 'missing'}, its CLI {o.criterion_version})"
        )


def _share(o: Opening, project: Path, fetch: bool) -> None:
    from catalyst import store
    from catalyst.deployment import DeploymentNotFound, WorkingCopyMissing, load

    try:
        st = store.share_for(load(project)).status(fetch=fetch)
    except (DeploymentNotFound, WorkingCopyMissing, store.ShareError) as exc:
        o.notes.append(f"shared copy not read: {exc}")
        return
    o.share = {"driver": st.driver, "location": st.location, "ahead": st.ahead, "behind": st.behind}
    if st.dirty:
        o.notes.append(f"{len(st.dirty)} change(s) not published yet (`catalyst share push`)")
    if st.behind:
        o.todo.append(f"`catalyst share pull` (the shared copy has {st.behind} commit(s) this one lacks)")
