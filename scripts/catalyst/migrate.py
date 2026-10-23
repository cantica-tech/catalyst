"""`catalyst migrate` (roadmap R3.4, design G-43): what a deployment is
behind on, and the mechanical part of catching up.

Three kinds of step, in this order:

- `layout`: a legacy deployment (a `*.catalyst` pointer, an in-project
  `.criterion`, a symlink or a submodule) moves to catalyst's home store,
  as `catalyst move --to-home` does.
- `template`: a type whose deployed templates do not hold the template the
  kernel or its module ships today gets it as its next version, with a row
  in its catalog — the step the migrations ask for in prose ("add the
  kernel's template as its next version"). A template already held, as any
  version, is never added again: a team's own later version stays the
  latest.
- `judgment`: each step a migration since the previous sync leaves to a
  person, listed, never taken.

`plan` changes nothing; `apply` takes the layout and template steps,
journaled, and lists the judgment ones again.
"""

from __future__ import annotations

import datetime
import re
import shutil
import tempfile
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

import project_file
from catalyst import compose, journal
from catalyst.deployment import Deployment, load

# a migration's step that adds a template as the next version: catalyst does it (`template` steps)
TEMPLATE_STEP = re.compile(r"templates/[\w.-]+\.template\.md`? as (?:its|the) next version")
JUDGMENT = re.compile(r"^\d+\.\s+\*\*Judgment(?:,\s*([^*:]*))?:?\*\*:?\s*(.*)$")
CATALOG_ROW = re.compile(r"^\| v(\d+) \|")


class MigrateError(Exception):
    pass


@dataclass
class Step:
    kind: str  # layout, template, judgment
    target: str  # what it is about: the project, a templates folder, a migration file
    detail: str
    auto: bool  # whether `apply` takes it
    source: str | None = None  # the migration that asks for it (judgment)
    type: str | None = None  # a module type's prefix (a template step the person opts into)
    taken: bool = False  # `apply` took it


@dataclass
class Plan:
    project: str
    criterion: str | None
    kernel: str | None
    since: str | None  # the kernel before the last sync: judgment steps are listed from there
    steps: list[Step] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {**{k: v for k, v in asdict(self).items() if k != "steps"}, "steps": [asdict(s) for s in self.steps]}


def kernel_dir(path: Path, tmp: Path) -> Path:
    """A kernel release as a directory: `framework/kernel` of a checkout, a
    release's kernel directory, or its zip (extracted under `tmp`)."""
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            zf.extractall(tmp / "kernel")
        found = next((p.parent for p in sorted((tmp / "kernel").rglob("rules-of-rules.template.md"))), None)
        if found is None:
            raise MigrateError(f"{path} holds no catalyst kernel")
        return found
    if not (path / "rules-of-rules.template.md").is_file():
        raise MigrateError(f"{path} is not a catalyst kernel (framework/kernel or a kernel release)")
    return path


def _versions(folder: Path) -> dict[int, Path]:
    out = {}
    for p in folder.glob("TEMPLATE-*-v*.*"):
        m = re.search(r"-v(\d+)\.\w+$", p.name)
        if m:
            out[int(m.group(1))] = p
    return out


def _norm(text: str, params: compose.Params | None) -> str:
    """A template's text as a seeded copy reads: a version copied raw from the
    kernel (its notice and placeholders kept) counts as the same template."""
    if params is not None:
        text = compose.sign_meta_ids(compose.resolve(compose.strip_notice(text), params), params.userid)
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def _wanted(dep: Deployment, kernel: Path | None) -> list[tuple[Path, str, str, str, str | None]]:
    """Each templates folder the deployment keeps, with the template's name,
    the text a deployment made today would hold, where that comes from, and
    the module type's prefix (None for a kernel type)."""
    from catalyst import generate, init as init_mod

    root = dep.root
    params = compose.deployed_params(root, dep.module.id if dep.module else "")
    out: list[tuple[Path, str, str, str, str | None]] = []
    if kernel is not None:
        for rel, (name, src) in init_mod.KERNEL_TYPES.items():
            folder = root / rel / "templates"
            if folder.is_dir() and (kernel / "templates" / src).is_file():
                text = init_mod.seeded_text(kernel / "templates" / src, params)
                out.append((folder, name, text, f"kernel templates/{src}", None))
    for manifest in dep.installed():
        tree = root / "modules" / manifest.id
        for etd in sorted(manifest.entity_types.values(), key=lambda e: e.id_prefix):
            folder_dir = dep.folder(etd)
            if folder_dir is None or not (folder_dir / "templates").is_dir():
                continue
            name, item, _ = init_mod.type_templates(tree, manifest, etd)
            if item is not None and item.is_file():
                text = init_mod.seeded_text(item, params)
                where = f"module {manifest.id} {item.relative_to(tree).as_posix()}"
            elif etd.generated and etd.naming != "free-form":
                text, where = generate.template(etd), f"module {manifest.id} (generated {etd.id_prefix} template)"
            else:
                continue
            out.append((folder_dir / "templates", name, text, where, etd.id_prefix))
    return out


def _template_steps(dep: Deployment, kernel: Path | None) -> list[tuple[Step, Path, str, str]]:
    steps = []
    params = compose.deployed_params(dep.root, dep.module.id if dep.module else "")
    for folder, name, text, where, prefix in _wanted(dep, kernel):
        held = _versions(folder)
        if any(_norm(p.read_text(encoding="utf-8"), params) == _norm(text, params) for p in held.values()):
            continue
        n = max(held, default=0) + 1
        rel = folder.relative_to(dep.root).as_posix()
        target = f"{rel}/TEMPLATE-{name}-v{n}.md"
        if prefix is None:  # the kernel's migrations require it wherever templates are kept
            step = Step("template", target, f"add {where} as {name}'s v{n}", True)
        else:  # a module's are optional (its migrations say so): the person opts in, per type
            step = Step(
                "template",
                target,
                f"add {where} as {name}'s v{n} (optional: `catalyst migrate --apply --template {prefix}`)",
                False,
                type=prefix,
            )
        steps.append((step, folder, name, text))
    return steps


# --- people out of the criterion (migration 0.106.0, design 29) ---------------------------
def _identity_step(dep: Deployment) -> Step | None:
    """What a deployment still holds of people that catalyst-users now holds: a registry to retire, a
    `catalyst.toml` pointer to move into `IAM/identity.json`, the groups templates to add."""
    from catalyst import provider

    iam = dep.root / "IAM"
    parts = []
    if not (dep.root / provider.POINTER).is_file() and (dep.pointer or {}).get("identity_issuer"):
        parts.append("write IAM/identity.json from catalyst.toml's identity_* keys")
    for kept in ("users/users.json", "roles/roles.json"):
        if (iam / kept).is_file():
            parts.append(f"retire IAM/{kept} as {kept.split('/')[1].replace('.json', '.retired.json')}")
    if (iam / "roles" / "roles.json").is_file():
        parts.append("keep its roles as the roles template's next version (display names and ids)")
    if not (iam / "groups" / "templates").is_dir():
        parts.append("add the groups templates")
    return Step("identity", "IAM", "; ".join(parts), True) if parts else None


def _take_identity(dep: Deployment, kernel: Path | None, stamp: str) -> tuple[list[Path], list[str]]:
    import json

    from catalyst import provider

    iam = dep.root / "IAM"
    touched: list[Path] = []
    done: list[str] = []
    toml = project_file.find(dep.project_root) if not dep.standalone else None
    data = project_file.read(toml) if toml is not None else {}
    if not (dep.root / provider.POINTER).is_file() and data.get("identity_issuer"):
        doc = {"provider": "keycloak", "issuer": str(data["identity_issuer"]).rstrip("/")}
        if data.get("identity_client"):
            doc["client"] = data["identity_client"]
        (dep.root / provider.POINTER).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        touched.append(dep.root / provider.POINTER)
        for key in ("identity", "identity_issuer", "identity_client"):
            data.pop(key, None)
        if toml is not None:
            project_file.write(toml, data)
        done.append(f"wrote IAM/identity.json ({doc['issuer']}); catalyst.toml's identity keys removed")
    roles = iam / "roles" / "roles.json"
    if roles.is_file():
        try:
            listed = json.loads(roles.read_text(encoding="utf-8")).get("roles") or []
        except (OSError, ValueError, AttributeError):
            listed = []
        catalogue = {
            "roles": [
                {
                    "name": r["name"],
                    "id": provider.role_id(r),
                    **{k: v for k, v in r.items() if k not in ("name", "id", "provider_role")},
                }
                for r in listed
                if isinstance(r, dict) and r.get("name")
            ]
        }
        folder = iam / "roles" / "templates"
        folder.mkdir(parents=True, exist_ok=True)
        held = [
            int(m.group(1))
            for f in folder.glob("TEMPLATE-ROLES-v*.json")
            if (m := re.search(r"-v(\d+)\.json$", f.name))
        ]
        n = max(held, default=0) + 1
        file = folder / f"TEMPLATE-ROLES-v{n}.json"
        file.write_text(json.dumps(catalogue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        catalog = folder / "templates-role.md"
        rows = (
            catalog.read_text(encoding="utf-8")
            if catalog.is_file()
            else "# `ROLES` templates — catalog\n\n| Version | File | Timestamp | Notes |\n|---|---|---|---|\n"
        )
        catalog.write_text(
            rows.rstrip("\n")
            + f"\n| v{n} | `{file.name}` | {stamp} | The deployment's roles, for display (migration 0.106.0). |\n",
            encoding="utf-8",
        )
        touched += [file, catalog]
        done.append(
            f"kept the deployment's {len(catalogue['roles'])} role(s) as TEMPLATE-ROLES-v{n}.json (display only)"
        )
    for kept in ("users", "roles"):
        old = iam / kept / f"{kept}.json"
        if old.is_file():
            new = old.with_name(f"{kept}.retired.json")
            old.rename(new)
            touched += [old, new]
            done.append(f"retired IAM/{kept}/{kept}.json as {new.name}")
    groups = iam / "groups" / "templates"
    if not groups.is_dir():
        groups.mkdir(parents=True)
        src = (kernel / "templates" / "groups.template.json") if kernel else None
        text = src.read_text(encoding="utf-8") if src and src.is_file() else '{\n  "groups": []\n}\n'
        (groups / "TEMPLATE-GROUPS-v1.json").write_text(text, encoding="utf-8")
        (groups / "templates-group.md").write_text(
            f"# `GROUPS` templates — catalog\n\n| Version | File | Timestamp | Notes |\n|---|---|---|---|\n| v1 | `TEMPLATE-GROUPS-v1.json` | {stamp} | Initial version (migration 0.106.0). |\n",
            encoding="utf-8",
        )
        (groups / "README.md").write_text(
            "# `groups` templates\n\nHow groups are shown (fw-IDENTITY-000010): display only.\n", encoding="utf-8"
        )
        touched += [groups / "TEMPLATE-GROUPS-v1.json", groups / "templates-group.md", groups / "README.md"]
        done.append("added the groups templates")
    return touched, done


def _since(dep: Deployment, current: str) -> str | None:
    """The kernel this deployment was at before its last sync, from the
    journal's sync entries; None when the journal names none."""
    seen: list[str] = []
    for _, entry, _ in journal.read(dep):
        if not entry or entry.get("action") != "sync":
            continue
        m = re.match(r"kernel (\d+\.\d+\.\d+)", str(entry.get("artifact") or ""))
        if m and (not seen or seen[-1] != m.group(1)):
            seen.append(m.group(1))
    older = [v for v in seen if _vt(v) < _vt(current)]
    return older[-1] if older else None


def _vt(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", version)[:3])


def _judgment_steps(dep: Deployment, kernel: Path | None, since: str | None, current: str) -> list[Step]:
    """Each step left to a person by a migration in (since, current], kernel's then each module's."""
    from catalyst import sync

    if since is None:
        return []
    indexes = [(kernel / "migrations" if kernel else None, "kernel")]
    indexes += [(dep.root / "modules" / m.id / "migrations", m.id) for m in dep.installed()]
    steps = []
    for folder, owner in indexes:
        if folder is None:
            continue
        top = current if owner == "kernel" else "999.0.0"
        # a migration applies when its target is past `since`, whatever version it starts from
        for m in sync.migrations(folder / "migrations.md", "0.0.0", top, owner):
            if _vt(m["to"]) <= _vt(since):
                continue
            doc = folder / m["file"]
            if not doc.is_file():
                continue
            for line in _items(doc.read_text(encoding="utf-8")):
                j = JUDGMENT.match(line)
                if not j:
                    continue
                text = " ".join(j.group(2).split())
                if j.group(1):  # "optional", "only if the owner asks": the qualifier stays
                    text = f"({j.group(1).strip()}) {text}"
                if TEMPLATE_STEP.search(text):
                    continue  # catalyst takes it: a `template` step
                steps.append(Step("judgment", f"{owner} {m['to']}", text, False, f"{owner}: migrations/{m['file']}"))
    return steps


def _items(text: str) -> list[str]:
    """A migration's numbered steps, each joined onto one line."""
    items: list[str] = []
    in_steps = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_steps = line.strip().lower() == "## steps"
            continue
        if not in_steps:
            continue
        if re.match(r"^\d+\.\s", line):
            items.append(line.strip())
        elif items and line.startswith("   ") and line.strip():
            items[-1] += " " + line.strip()
    return items


def plan(project: Path, kernel: Path | None, since: str | None = None) -> Plan:
    """What `project` is behind on; judgment steps from the migrations after `since`
    (default: the kernel before its last sync)."""
    data = project_file.read_dir(project)
    name = project_file.project_name(data)
    criterion = project_file.resolve(project)
    home = project_file.home_criterion(name) if name else None
    p = Plan(str(project), str(criterion) if criterion else None, None, None)
    legacy = project_file.find(project)
    if legacy is not None and (legacy.name != "catalyst.toml" or criterion is None or criterion != home):
        what = ", ".join(project_file.legacy_parts(project, criterion)) if criterion else "a legacy pointer"
        p.steps.append(Step("layout", str(project), f"move the criterion to the home store ({what})", True))
    if criterion is None:
        return p
    dep = load(project)
    current = (dep.root / "version.txt").read_text(encoding="utf-8").strip()
    p.kernel = current
    p.steps += [s for s, *_ in _template_steps(dep, kernel)]
    identity = _identity_step(dep)
    if identity is not None:
        p.steps.append(identity)
    p.since = since or _since(dep, current)
    p.steps += _judgment_steps(dep, kernel, p.since, current)
    return p


def apply(
    project: Path,
    kernel: Path | None,
    actor: str,
    intent: list[str],
    runtime: bool = True,
    templates: set[str] | None = None,
    since: str | None = None,
) -> tuple[Plan, list[str]]:
    """Take the layout step, the kernel's template steps and the module
    template steps `templates` opts into (type prefixes or template names,
    or `all`); return the plan as it stood and what was done."""
    chosen = {t.upper() for t in templates or set()}
    from catalyst import move

    before = plan(project, kernel, since)
    done: list[str] = []
    layout = next((s for s in before.steps if s.kind == "layout"), None)
    if layout is not None:
        _, moved = move.to_home(project, runtime=runtime, actor=actor)
        done += moved
        layout.taken = True
    dep = load(project)
    touched: list[Path] = []
    stamp = datetime.date.today().isoformat()
    for step, folder, name, text in _template_steps(dep, kernel):
        if not (step.auto or "ALL" in chosen or step.type in chosen or name in chosen):
            continue
        n = int(step.target.rsplit("-v", 1)[1].split(".")[0])
        file = folder / f"TEMPLATE-{name}-v{n}.md"
        file.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
        catalog = folder / f"templates-{name.lower()}.md"
        rows = (
            catalog.read_text(encoding="utf-8")
            if catalog.is_file()
            else (f"# `{name}` templates — catalog\n\n| Version | File | Timestamp | Notes |\n|---|---|---|---|\n")
        )
        what = step.detail[4:].split(" (optional")[0]
        rows = rows.rstrip("\n") + f"\n| v{n} | `{file.name}` | {stamp} | {what} (`catalyst migrate`). |\n"
        catalog.write_text(rows, encoding="utf-8")
        touched += [file, catalog]
        done.append(f"added {what}")
        for s in before.steps:
            if s.target == step.target:
                s.taken = True
    identity = next((s for s in before.steps if s.kind == "identity"), None)
    if identity is not None:
        moved, said = _take_identity(dep, kernel, stamp)
        touched += moved
        done += said
        identity.taken = True
    if touched:
        journal.append(
            dep,
            journal.AppendRequest(
                command="catalyst migrate",
                action="update",
                artifact=f"kernel {before.kernel}",
                targets=[],
                intent=intent or [f"the templates kernel {before.kernel} and its modules ship, added as next versions"],
                files=[str(t) for t in touched],
                actor=actor,
                tier="chore",
            ),
        )
    return before, done


def with_kernel(path: Path | None):
    """A context giving the kernel directory for `path` (None: no kernel)."""

    class _Ctx:
        def __enter__(self) -> Path | None:
            self.tmp = Path(tempfile.mkdtemp(prefix="catalyst-migrate-"))
            return kernel_dir(path, self.tmp) if path is not None else None

        def __exit__(self, *exc) -> None:
            shutil.rmtree(self.tmp, ignore_errors=True)

    return _Ctx()
