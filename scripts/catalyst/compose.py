"""Compose a deployment's governing documents from the kernel's templates and
the active module's contributions (MODULE-SPECIFICATION.md §6).

- CODE-OF-CONDUCT.md: the kernel's rules-of-development template, with the
  module's `## 3.` and `## 4.` bodies inserted at the end of the matching
  kernel sections under `### From module <id>` (§6.2).
- rules/Rules-of-Rules.md: the kernel's rules-of-rules template, with the
  module's meta-rule sections appended under `### From module <id>` (§6.1).
- ACCESS-CONTROL.md: the kernel's, verbatim.
- Taskfile.common.yml: the kernel's template tasks, then the module's (§6.5),
  each run from the caller's directory (`dir: '{{.USER_WORKING_DIR}}'`).

Every composed document resolves the instantiation placeholders
(`{{RULES_DIR}}`, `{{RULE_DOCS_LIST}}`, `{{TEST_LOCATIONS}}`; the others
are illustrative and stay), replaces the template's own notice with an
instantiation note, and writes meta-rule IDs in the deployment's signed form
(`rr-META-0NN` -> `rr-META-0000NN-<userid>`, rr-META-020).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

SHORT_META_RE = re.compile(r"\brr-META-0(\d{2})(?![\d-])")
TASK_RE = re.compile(r"^  [A-Za-z0-9_-]+:\n(?!    dir:)", re.M)
PARAMS_FILE = "composition.json"  # the parameters a deployment was composed with


@dataclass
class Params:
    module_id: str
    userid: str
    rule_docs: list[str] = field(default_factory=list)  # e.g. ["business-rules.md"]
    test_locations: str = "*(to be named: where this project's tests live)*"
    rules_dir: str = "rules"

    def as_dict(self) -> dict:
        return {
            "module": self.module_id,
            "userid": self.userid,
            "rule_docs": self.rule_docs,
            "test_locations": self.test_locations,
            "rules_dir": self.rules_dir,
        }


def sign_meta_ids(text: str, userid: str, namespaces: tuple[str, ...] = ()) -> str:
    """Widen and sign the short meta-rule IDs: the kernel's `rr-META-0NN`,
    and a module namespace's `rr-<NS>-NNN` (module v3, M4)."""
    text = SHORT_META_RE.sub(lambda m: f"rr-META-0000{m.group(1)}-{userid}", text)
    for ns in namespaces:
        text = re.sub(
            rf"\brr-{re.escape(ns)}-(\d{{3}})(?![\d-])",
            lambda m, ns=ns: f"rr-{ns}-000{m.group(1)}-{userid}",
            text,
        )
    return text


Modules = Path | list[Path] | None  # one module's directory, several in install order, or none


def module_dirs(module: Modules) -> list[Path]:
    """The modules to compose with, in install order."""
    if module is None:
        return []
    return list(module) if isinstance(module, list) else [module]


def _module_id(module: Path, p: Params, alone: bool) -> str:
    """The id a module's part is headed with: the deployment's own when it
    has one module (as always), else each module's."""
    if alone:
        return p.module_id
    from module_loader import parse_simple_yaml

    data = parse_simple_yaml((module / "module.yaml").read_text(encoding="utf-8"))
    return str(data.get("id") or module.name) if isinstance(data, dict) else module.name


def module_namespaces(module: Modules) -> tuple[str, ...]:
    from module_loader import load_module

    found = []
    for mod in module_dirs(module):
        manifest = load_module(module_dir=mod)
        if manifest is not None and manifest.namespace and manifest.namespace not in found:
            found.append(manifest.namespace)
    return tuple(found)


def resolve(text: str, p: Params) -> str:
    docs = ", ".join(f"`{d}`" for d in p.rule_docs) or "*(no rule document yet)*"
    return (
        text.replace("{{RULES_DIR}}", p.rules_dir)
        .replace("{{RULE_DOCS_LIST}}", docs)
        .replace("{{TEST_LOCATIONS}}", p.test_locations)
    )


def strip_notice(text: str) -> str:
    """Drop a template's leading `> ...` notice block (and the blank line after)."""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(">")), None)
    if start is None or start > 4:
        return text
    end = start
    while end < len(lines) and lines[end].startswith(">"):
        end += 1
    if end < len(lines) and not lines[end].strip():
        end += 1
    return "\n".join(lines[:start] + lines[end:]) + ("\n" if text.endswith("\n") else "")


def replace_notice(text: str, note: str) -> str:
    """Swap the template's leading `> ...` notice block for `note`."""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(">")), None)
    if start is None or start > 4:
        return text
    end = start
    while end < len(lines) and lines[end].startswith(">"):
        end += 1
    return "\n".join(lines[:start] + [f"> {note}"] + lines[end:]) + ("\n" if text.endswith("\n") else "")


def section_body(text: str, number: int) -> str:
    """The body of `## <number>. ...` (heading excluded) up to the next `## `."""
    m = re.search(rf"^## {number}\.[^\n]*\n", text, re.M)
    if not m:
        return ""
    nxt = re.search(r"^## ", text[m.end() :], re.M)
    return text[m.end() : m.end() + nxt.start() if nxt else len(text)].strip("\n")


def insert_at_section_end(text: str, number: int, block: str) -> str:
    """Insert `block` just before the heading that follows `## <number>.`."""
    m = re.search(rf"^## {number}\.[^\n]*\n", text, re.M)
    if not m:
        return text.rstrip("\n") + "\n\n" + block + "\n"
    nxt = re.search(r"^## ", text[m.end() :], re.M)
    at = m.end() + nxt.start() if nxt else len(text)
    head = text[:at].rstrip("\n")
    return head + "\n\n" + block.rstrip("\n") + "\n\n" + text[at:]


def module_body(text: str) -> str:
    """A module contribution file minus its own title and preamble: from its
    first `## ` section on."""
    m = re.search(r"^## ", text, re.M)
    return text[m.start() :].strip("\n") if m else text.strip("\n")


def generated_commands(module: Path | None, existing: str) -> list:
    """The v3 types whose `/create-<type>` the module's catalogue part does
    not define (module v3, M3): catalyst generates those commands. A
    catalogue entry counts with its arguments (`/create-x <id>`); a type
    stored as rows gets none."""
    from catalyst import generate
    from module_loader import load_module

    if module is None:
        return []
    manifest = load_module(module_dir=module)
    if manifest is None:
        return []
    return [
        etd
        for etd in manifest.entity_types.values()
        if etd.generated
        and etd.naming != "free-form"  # rows of a file: no document to create
        and not re.search(rf"`/{re.escape(generate.create_command(etd))}[` :]", existing)
    ]


def code_of_conduct(kernel: Path, module: Modules, p: Params) -> str:
    from catalyst import generate

    text = (kernel / "rules-of-development.template.md").read_text(encoding="utf-8")
    note = (
        "Instantiates the catalyst kernel's development-rules template "
        "(`framework/kernel/rules-of-development.template.md` in the `catalyst` repository)"
    )
    mods = module_dirs(module)
    contributed = []
    for mod in mods:
        contribution = ""
        if (mod / "code-of-conduct.module.md").is_file():
            contribution = (mod / "code-of-conduct.module.md").read_text(encoding="utf-8")
        generated = "\n".join(generate.catalogue_entry(e) for e in generated_commands(mod, contribution))
        if not (contribution or generated):
            continue
        mid = _module_id(mod, p, len(mods) == 1)
        contributed.append(mid)
        for n in (4, 3):  # 4 first: inserting §3 would shift nothing, but keep order explicit
            body = section_body(contribution, n) if contribution else ""
            if n == 4 and generated:
                body = (body.rstrip("\n") + "\n\n" if body.strip() else "") + generated
            if body:
                text = insert_at_section_end(text, n, f"### From module {mid}\n\n{body}")
    if len(contributed) == 1 and len(mods) == 1:
        note += (
            f", with the active module's `code-of-conduct.module.md` §3 and §4 inserted at the "
            f"end of the matching sections under `### From module {contributed[0]}` "
            "(`MODULE-SPECIFICATION.md` §6.2)"
        )
    elif contributed:
        note += (
            ", with each installed module's `code-of-conduct.module.md` §3 and §4 inserted at the "
            "end of the matching sections under its own `### From module <id>` heading, in install order: "
            + ", ".join(f"`{m}`" for m in contributed)
            + " (`MODULE-SPECIFICATION.md` §6.2)"
        )
    text = replace_notice(text, note + ".")
    return sign_meta_ids(resolve(text, p), p.userid, module_namespaces(module))


def rules_of_rules(kernel: Path, module: Modules, p: Params) -> str:
    text = (kernel / "rules-of-rules.template.md").read_text(encoding="utf-8")
    note = (
        "Instantiates the catalyst kernel's rules-of-rules template "
        "(`framework/kernel/rules-of-rules.template.md` in the `catalyst` repository)"
    )
    mods = module_dirs(module)
    contributed = []
    for mod in mods:
        if not (mod / "rules-of-rules.module.md").is_file():
            continue
        mid = _module_id(mod, p, len(mods) == 1)
        contributed.append(mid)
        body = module_body((mod / "rules-of-rules.module.md").read_text(encoding="utf-8"))
        text = text.rstrip("\n") + f"\n\n---\n\n### From module {mid}\n\n{body}\n"
    if len(contributed) == 1 and len(mods) == 1:
        note += (
            f", with the active module's `rules-of-rules.module.md` appended under "
            f"`### From module {contributed[0]}` (`MODULE-SPECIFICATION.md` §6.1)"
        )
    elif contributed:
        note += (
            ", with each installed module's `rules-of-rules.module.md` appended under its own "
            "`### From module <id>` heading, in install order: "
            + ", ".join(f"`{m}`" for m in contributed)
            + " (`MODULE-SPECIFICATION.md` §6.1)"
        )
    text = replace_notice(text, note + ".")
    return sign_meta_ids(resolve(text, p), p.userid, module_namespaces(module))


def access_control(kernel: Path, p: Params) -> str:
    return sign_meta_ids((kernel / "ACCESS-CONTROL.md").read_text(encoding="utf-8"), p.userid)


def _task(name: str, bullets: list[str]) -> str:
    """A §4 command's task: its name, the first sentence of its bullet, and
    the dispatch to the command, under the name the agent serves it by
    (`CMD_PREFIX`: `/catalyst:` for the MCP server's prompts, else `/`)."""
    first = " ".join(line.strip() for line in bullets[0].splitlines())
    text = first.split("—", 1)[1].strip() if "—" in first else first.lstrip("- ")
    desc = re.split(r"(?<=\.)\s|:\s(?=`)", text, maxsplit=1)[0].rstrip(".")
    desc = desc if len(desc) <= 110 else desc[:107].rstrip() + "..."
    desc = desc.replace("\\", "\\\\").replace('"', '\\"')
    return f'  {name}:\n    desc: "{desc}"\n    cmds:\n      - \'{{{{.AGENT_CMD}}}} "{{{{.CMD_PREFIX}}}}{name} {{{{.CLI_ARGS}}}}"\'\n'


def taskfile(kernel: Path, module: Modules, p: Params) -> str:
    """The criterion's Taskfile: the template's header and utility tasks, and
    one task per command of the composed §4 (ADR-021: §4 is the registry)."""
    from catalyst import spec

    template = (kernel / "templates" / "Taskfile.common.template.yml").read_text(encoding="utf-8").rstrip("\n")
    head, utility = template.split("\ntasks:\n", 1)
    s = spec.parse(code_of_conduct(kernel, module, p))
    tasks = "\n".join(_task(name, bullets) for name, bullets in s.bullets.items())
    text = f"{head}\ntasks:\n{tasks}\n{utility}"
    # the file sits in the criterion and is run on its own: a task works in
    # the project it was called from, not in the criterion
    text = TASK_RE.sub(lambda m: m.group(0) + "    dir: '{{.USER_WORKING_DIR}}'\n", text)
    return text + "\n"


# --- recompose: three-way merge on sync ------------------------------------
DOCUMENTS = {
    "CODE-OF-CONDUCT.md": lambda k, m, p: code_of_conduct(k, m, p),
    "rules/Rules-of-Rules.md": lambda k, m, p: rules_of_rules(k, m, p),
    "ACCESS-CONTROL.md": lambda k, m, p: access_control(k, p),
    "Taskfile.common.yml": lambda k, m, p: taskfile(k, m, p),
}


@dataclass
class Recomposed:
    path: str
    changed: bool
    conflicts: int
    frozen: bool = False


def deployed_params(root: Path, module_id: str) -> Params:
    """The composition parameters a deployment was built with: its
    composition.json when present (written by `catalyst init`), else read
    back from its own Rules-of-Rules (older deployments)."""
    import json

    saved = root / PARAMS_FILE
    if saved.is_file():
        d = json.loads(saved.read_text(encoding="utf-8"))
        return Params(
            d.get("module", module_id),
            d["userid"],
            list(d.get("rule_docs", [])),
            d.get("test_locations", Params.test_locations),
            d.get("rules_dir", "rules"),
        )
    ror = (
        (root / "rules" / "Rules-of-Rules.md").read_text(encoding="utf-8")
        if (root / "rules" / "Rules-of-Rules.md").is_file()
        else ""
    )
    signers = re.findall(r"rr-META-\d{6}-([A-Za-z0-9]{8})", ror)
    userid = max(set(signers), key=signers.count) if signers else "XXXXXXXX"
    docs_line = re.search(r"from one of this project's rule documents: (.+?)\. These", ror, re.S)
    docs = re.findall(r"`([^`]+\.md)`", docs_line.group(1)) if docs_line else []
    tests = re.search(r"Name the\s+project's test locations here: (.+?)\. A rule with zero", ror, re.S)
    return Params(
        module_id, userid, docs, re.sub(r"\s+", " ", tests.group(1)).strip() if tests else Params.test_locations
    )


def frozen_paths(root: Path) -> set[str]:
    """Paths listed in `.frozen` (the working copy's or the project's), as
    working-copy-relative paths."""
    found = set()
    for f in (root / ".frozen", root.parent / ".frozen"):
        if f.is_file():
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    found.add(line.removeprefix(".criterion/"))
    return found


# What catalyst generates into a composed document, never edited by hand:
# a v3 type's catalogue entry
GENERATED_ENTRY = re.compile(
    r"^- `/create[ -][^\n]*\(generated from the module's `module\.yaml`\)\.\n\nWhen the user enters [^\n]*\n", re.M
)
GENERATED_DOCUMENT = "Taskfile.common.yml"


def _entry_key(entry: str) -> str:
    m = re.search(r"`/(create-[a-z0-9-]+)`", entry)
    return m.group(1) if m else entry


def _as_generated(rel: str, old: str, deployed: str) -> tuple[str, str]:
    """The base and the deployed text with what catalyst generated taken as
    the deployment holds it: a change to the generator itself then reaches the
    deployment through the merge, as a template change does. Returns (base, ours)."""
    if rel == "CODE-OF-CONDUCT.md":
        mine = {_entry_key(m.group(0)): m.group(0) for m in GENERATED_ENTRY.finditer(deployed)}
        old = GENERATED_ENTRY.sub(lambda m: mine.get(_entry_key(m.group(0)), m.group(0)), old)
    return old, deployed


def recompose(
    root: Path,
    params: Params,
    base: tuple[Path, Modules],
    new: tuple[Path, Modules],
    write: bool = True,
    force: bool = False,
) -> list[Recomposed]:
    """For each composed document: merge what changed between the base and
    new templates into the deployed file, keeping the deployment's own
    edits (`git merge-file`). Conflicts are left marked in the file."""
    import subprocess
    import tempfile

    results = []
    frozen = set() if force else frozen_paths(root)
    for rel, build in DOCUMENTS.items():
        target = root / rel
        if not target.is_file():
            continue
        if rel in frozen:
            results.append(Recomposed(rel, False, 0, frozen=True))
            continue
        old, fresh = build(*base, params), build(*new, params)
        if rel == GENERATED_DOCUMENT:  # wholly generated from §4, never edited by hand: written as composed
            changed = fresh != target.read_text(encoding="utf-8")
            if write and changed:
                target.write_text(fresh, encoding="utf-8")
            results.append(Recomposed(rel, changed, 0))
            continue
        old, deployed = _as_generated(rel, old, target.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            ours = Path(tmp) / "ours"
            ours.write_text(deployed, encoding="utf-8")
            (Path(tmp) / "base").write_text(old, encoding="utf-8")
            (Path(tmp) / "theirs").write_text(fresh, encoding="utf-8")
            res = subprocess.run(
                [
                    "git",
                    "merge-file",
                    "-L",
                    "deployed",
                    "-L",
                    "old template",
                    "-L",
                    "new template",
                    str(ours),
                    str(Path(tmp) / "base"),
                    str(Path(tmp) / "theirs"),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            merged = ours.read_text(encoding="utf-8")
        if res.returncode > 127:
            raise RuntimeError(f"git merge-file failed on {rel}: {res.stderr.strip()}")
        conflicts = res.returncode if res.returncode > 0 else 0
        changed = merged != target.read_text(encoding="utf-8")
        if write and changed:
            target.write_text(merged, encoding="utf-8")
        results.append(Recomposed(rel, changed, conflicts))
    return results
