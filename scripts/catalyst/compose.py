"""Compose a deployment's governing documents from the kernel's templates and
the active module's contributions (MODULE-SPECIFICATION.md §6).

- CODE-OF-CONDUCT.md: the kernel's rules-of-development template, with the
  module's `## 3.` and `## 4.` bodies inserted at the end of the matching
  kernel sections under `### From module <id>` (§6.2).
- rules/Rules-of-Rules.md: the kernel's rules-of-rules template, with the
  module's meta-rule sections appended under `### From module <id>` (§6.1).
- ACCESS-CONTROL.md: the kernel's, verbatim.
- Taskfile.common.yml: the kernel's template tasks, then the module's (§6.5).

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
PARAMS_FILE = "composition.json"          # the parameters a deployment was composed with


@dataclass
class Params:
    module_id: str
    userid: str
    rule_docs: list[str] = field(default_factory=list)     # e.g. ["business-rules.md"]
    test_locations: str = "*(to be named: where this project's tests live)*"
    rules_dir: str = "rules"

    def as_dict(self) -> dict:
        return {"module": self.module_id, "userid": self.userid, "rule_docs": self.rule_docs,
                "test_locations": self.test_locations, "rules_dir": self.rules_dir}


def sign_meta_ids(text: str, userid: str) -> str:
    return SHORT_META_RE.sub(lambda m: f"rr-META-0000{m.group(1)}-{userid}", text)


def resolve(text: str, p: Params) -> str:
    docs = ", ".join(f"`{d}`" for d in p.rule_docs) or "*(no rule document yet)*"
    return (text.replace("{{RULES_DIR}}", p.rules_dir)
                .replace("{{RULE_DOCS_LIST}}", docs)
                .replace("{{TEST_LOCATIONS}}", p.test_locations))


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
    nxt = re.search(r"^## ", text[m.end():], re.M)
    return text[m.end():m.end() + nxt.start() if nxt else len(text)].strip("\n")


def insert_at_section_end(text: str, number: int, block: str) -> str:
    """Insert `block` just before the heading that follows `## <number>.`."""
    m = re.search(rf"^## {number}\.[^\n]*\n", text, re.M)
    if not m:
        return text.rstrip("\n") + "\n\n" + block + "\n"
    nxt = re.search(r"^## ", text[m.end():], re.M)
    at = m.end() + nxt.start() if nxt else len(text)
    head = text[:at].rstrip("\n")
    return head + "\n\n" + block.rstrip("\n") + "\n\n" + text[at:]


def module_body(text: str) -> str:
    """A module contribution file minus its own title and preamble: from its
    first `## ` section on."""
    m = re.search(r"^## ", text, re.M)
    return text[m.start():].strip("\n") if m else text.strip("\n")


def code_of_conduct(kernel: Path, module: Path | None, p: Params) -> str:
    text = (kernel / "rules-of-development.template.md").read_text(encoding="utf-8")
    note = ("Instantiates the catalyst kernel's development-rules template "
            "(`framework/kernel/rules-of-development.template.md` in the `catalyst` repository)")
    if module is not None and (module / "code-of-conduct.module.md").is_file():
        contribution = (module / "code-of-conduct.module.md").read_text(encoding="utf-8")
        for n in (4, 3):        # 4 first: inserting §3 would shift nothing, but keep order explicit
            body = section_body(contribution, n)
            if body:
                text = insert_at_section_end(text, n, f"### From module {p.module_id}\n\n{body}")
        note += (f", with the active module's `code-of-conduct.module.md` §3 and §4 inserted at the "
                 f"end of the matching sections under `### From module {p.module_id}` "
                 "(`MODULE-SPECIFICATION.md` §6.2)")
    text = replace_notice(text, note + ".")
    return sign_meta_ids(resolve(text, p), p.userid)


def rules_of_rules(kernel: Path, module: Path | None, p: Params) -> str:
    text = (kernel / "rules-of-rules.template.md").read_text(encoding="utf-8")
    note = ("Instantiates the catalyst kernel's rules-of-rules template "
            "(`framework/kernel/rules-of-rules.template.md` in the `catalyst` repository)")
    if module is not None and (module / "rules-of-rules.module.md").is_file():
        body = module_body((module / "rules-of-rules.module.md").read_text(encoding="utf-8"))
        text = text.rstrip("\n") + f"\n\n---\n\n### From module {p.module_id}\n\n{body}\n"
        note += (f", with the active module's `rules-of-rules.module.md` appended under "
                 f"`### From module {p.module_id}` (`MODULE-SPECIFICATION.md` §6.1)")
    text = replace_notice(text, note + ".")
    return sign_meta_ids(resolve(text, p), p.userid)


def access_control(kernel: Path, p: Params) -> str:
    return sign_meta_ids((kernel / "ACCESS-CONTROL.md").read_text(encoding="utf-8"), p.userid)


def taskfile(kernel: Path, module: Path | None, p: Params) -> str:
    text = (kernel / "templates" / "Taskfile.common.template.yml").read_text(encoding="utf-8").rstrip("\n")
    if module is not None and (module / "Taskfile.module.yml").is_file():
        mod = (module / "Taskfile.module.yml").read_text(encoding="utf-8")
        m = re.search(r"^tasks:\s*\n", mod, re.M)
        tasks = mod[m.end():] if m else ""
        if tasks.strip():
            text += f"\n\n  # --- From module {p.module_id} " + "-" * 20 + "\n" + tasks.rstrip("\n")
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
        return Params(d.get("module", module_id), d["userid"], list(d.get("rule_docs", [])),
                      d.get("test_locations", Params.test_locations), d.get("rules_dir", "rules"))
    ror = (root / "rules" / "Rules-of-Rules.md").read_text(encoding="utf-8") \
        if (root / "rules" / "Rules-of-Rules.md").is_file() else ""
    signers = re.findall(r"rr-META-\d{6}-([A-Za-z0-9]{8})", ror)
    userid = max(set(signers), key=signers.count) if signers else "XXXXXXXX"
    docs_line = re.search(r"from one of this project's rule documents: (.+?)\. These", ror, re.S)
    docs = re.findall(r"`([^`]+\.md)`", docs_line.group(1)) if docs_line else []
    tests = re.search(r"Name the\s+project's test locations here: (.+?)\. A rule with zero", ror, re.S)
    return Params(module_id, userid, docs,
                  re.sub(r"\s+", " ", tests.group(1)).strip() if tests else Params.test_locations)


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


def recompose(root: Path, params: Params, base: tuple[Path, Path | None],
              new: tuple[Path, Path | None], write: bool = True, force: bool = False) -> list[Recomposed]:
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
        with tempfile.TemporaryDirectory() as tmp:
            ours = Path(tmp) / "ours"
            ours.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
            (Path(tmp) / "base").write_text(old, encoding="utf-8")
            (Path(tmp) / "theirs").write_text(fresh, encoding="utf-8")
            res = subprocess.run(["git", "merge-file", "-L", "deployed", "-L", "old template",
                                  "-L", "new template", str(ours), str(Path(tmp) / "base"),
                                  str(Path(tmp) / "theirs")], capture_output=True, text=True)
            merged = ours.read_text(encoding="utf-8")
        if res.returncode > 127:
            raise RuntimeError(f"git merge-file failed on {rel}: {res.stderr.strip()}")
        conflicts = res.returncode if res.returncode > 0 else 0
        changed = merged != target.read_text(encoding="utf-8")
        if write and changed:
            target.write_text(merged, encoding="utf-8")
        results.append(Recomposed(rel, changed, conflicts))
    return results
