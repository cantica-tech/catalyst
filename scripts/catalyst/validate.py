"""Chain validation, driven by the entity type definitions (ETDs).

Errors are structural breaks of the traceability chain, reported from day
one: duplicate IDs, a reference that resolves to nothing, a missing grounding
link, an unregistered signer, a rule absent from the global index, an ID or
filename that doesn't match its type's shape. Warnings are ETD-shape
mismatches in otherwise sound data (a status outside the ETD's allowed
values, a one-sided back-reference, a reference to the wrong type, index
drift that `catalyst index regen` repairs); `--strict` turns them into
errors.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from catalyst.corpus import Artifact, Corpus, is_empty, norm_field, ref_values
from catalyst.deployment import Deployment
from module_loader import ETD, FieldDefinition

ERROR, WARNING = "error", "warning"
SIGNER_FIELD = "Signed-off-by"


@dataclass
class Finding:
    level: str
    code: str
    where: str
    message: str

    def as_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        return f"{self.level.upper():7} {self.code:18} {self.where}: {self.message}"


class Validator:
    def __init__(self, dep: Deployment, corpus: Corpus):
        self.dep = dep
        self.corpus = corpus
        self.findings: list[Finding] = []
        userids = {str(u.get("userid")) for u in corpus.users if u.get("userid")}
        self.userid_alt = "|".join(sorted(re.escape(u) for u in userids)) or "[A-Za-z0-9]{8}"

    def add(self, level: str, code: str, where: str, message: str) -> None:
        self.findings.append(Finding(level, code, where, message))

    def rel(self, path) -> str:
        try:
            return f".criterion/{path.relative_to(self.dep.root)}"
        except ValueError:
            return str(path)

    # --- rules ---------------------------------------------------------
    def check_rules(self) -> None:
        for rule_id, defs in sorted(self.corpus.rules.items()):
            if len(defs) > 1:
                places = ", ".join(f"{self.rel(d.file)}:{d.line}" for d in defs)
                self.add(
                    ERROR,
                    "duplicate-id",
                    self.rel(defs[0].file),
                    f"rule `{rule_id}` is defined {len(defs)} times ({places})",
                )
            d = defs[0]
            if d.file.name == "Rules-of-Rules.md" and rule_id.startswith("rr-META-"):
                continue  # meta-rules are self-governing, never in rules.md
            if self.corpus.indexed_rules and rule_id not in self.corpus.indexed_rules:
                self.add(
                    ERROR,
                    "rule-unindexed",
                    f"{self.rel(d.file)}:{d.line}",
                    f"rule `{rule_id}` is not listed in rules/rules.md (INV-8)",
                )

    # --- artifacts -----------------------------------------------------
    def resolve(self, value: str, target: str | None) -> tuple[bool, str | None]:
        """(resolves at all, the type it resolved to)."""
        c = self.corpus
        if value in c.rules:
            kind = "rule"
        elif value in c.domains:
            kind = "domain"
        elif value in c.artifacts:
            kind = c.artifacts[value][0].prefix
        else:
            kind = next((p for p, ids in c.row_items.items() if value in ids), None)
        if kind is None:
            return False, None
        return True, kind

    def check_ref_field(self, art: Artifact, fd: FieldDefinition, raw: str) -> list[str]:
        values = ref_values(raw)
        if fd.kind == "ref" and len(values) > 1:
            self.add(
                WARNING,
                "cardinality",
                self.rel(art.file),
                f"`{fd.name}` holds {len(values)} values; the ETD declares a single ref",
            )
        for v in values:
            ok, kind = self.resolve(v, fd.target_type)
            if not ok:
                self.add(
                    ERROR, "dangling-ref", self.rel(art.file), f"`{fd.name}` cites `{v}`, which resolves to nothing"
                )
            elif fd.target_type and kind not in fd.target_type.split("|"):
                self.add(
                    WARNING,
                    "ref-type",
                    self.rel(art.file),
                    f"`{fd.name}` cites `{v}` (a {kind}); the ETD expects {fd.target_type}",
                )
            elif kind == "rule" and self.corpus.rules[v][0].retired:
                self.add(WARNING, "retired-target", self.rel(art.file), f"`{fd.name}` cites retired rule `{v}`")
        return values

    def check_artifact(self, art: Artifact, etd: ETD) -> None:
        where = self.rel(art.file)
        # ID and filename shape
        id_re = re.compile(rf"^{re.escape(etd.id_prefix)}-(\d{{6}})-({self.userid_alt})$")
        m = id_re.match(art.id)
        if not m:
            self.add(ERROR, "id-shape", where, f"ID `{art.id}` is not {etd.id_prefix}-NNNNNN-<registered userid>")
        elif not art.file.name.startswith(f"{etd.id_prefix}-{m.group(1)}-"):
            self.add(
                ERROR, "id-shape", where, f"filename does not start with {etd.id_prefix}-{m.group(1)}- (ID `{art.id}`)"
            )
        # declared fields
        grounded = etd.grounding == "none"
        # "**Closed**", "Closed ✅", "`Closed`" all mean Closed
        m = re.match(r"[\s*`_]*([A-Za-z][A-Za-z -]*[A-Za-z])", art.get("Status") or "")
        status = m.group(1).lower() if m else ""
        closed = status in {s.lower() for s in etd.workflow.closed_states}
        for fd in etd.fields:
            if fd.name == "ID":
                continue
            raw = art.get(fd.name)
            if raw is None or is_empty(raw):
                if fd.required:
                    self.add(ERROR, "required-field", where, f"required field `{fd.name}` is missing or empty")
                elif fd.required_when_closed and closed:
                    self.add(
                        ERROR,
                        "closed-incomplete",
                        where,
                        f"`{fd.name}` must be filled before a {etd.name.lower()} is {status}",
                    )
                continue
            if fd.kind == "enum" and fd.allowed_values:
                allowed = {a.lower() for a in fd.allowed_values}
                if raw.strip().strip("`").lower() not in allowed:
                    self.add(
                        WARNING,
                        "enum-value",
                        where,
                        f"`{fd.name}` is '{raw.strip()}', not one of {', '.join(fd.allowed_values)}",
                    )
            if fd.kind in ("ref", "ref-list"):
                values = self.check_ref_field(art, fd, raw)
                if etd.grounding_field and norm_field(fd.name) == norm_field(etd.grounding_field):
                    grounded = grounded or any(self.resolve(v, None)[0] for v in values)
                if fd.backref:
                    self.check_backref(art, fd, values)
        if etd.grounding in ("required", "inherited") and not grounded:
            self.add(
                ERROR,
                "ungrounded",
                where,
                f"no resolvable `{etd.grounding_field}` — every {etd.name.lower()} must ground "
                f"({etd.grounding}) to a documented rule (INV-5)",
            )
        # signer
        signer = art.get(SIGNER_FIELD)
        if signer is None or is_empty(signer):
            self.add(ERROR, "signer", where, "no Signed-off-by")
        elif self.corpus.users and self.corpus.user(signer.strip("` ")) is None:
            self.add(ERROR, "signer", where, f"Signed-off-by '{signer}' is not a registered user (INV-16)")

    def check_backref(self, art: Artifact, fd: FieldDefinition, values: list[str]) -> None:
        for v in values:
            for target in self.corpus.artifacts.get(v, []):
                raw = target.get(fd.backref or "")
                if raw is None or art.id not in ref_values(raw):
                    self.add(
                        WARNING,
                        "backref",
                        self.rel(art.file),
                        f"`{fd.name}` cites `{v}`, whose `{fd.backref}` does not cite `{art.id}` back",
                    )

    def check_artifacts(self) -> None:
        for art_id, defs in sorted(self.corpus.artifacts.items()):
            if len(defs) > 1:
                places = ", ".join(self.rel(d.file) for d in defs)
                self.add(
                    ERROR, "duplicate-id", self.rel(defs[0].file), f"`{art_id}` is defined {len(defs)} times ({places})"
                )
        for prefix, arts in sorted(self.corpus.by_prefix.items()):
            etd = self.dep.etds[prefix]
            for art in arts:
                self.check_artifact(art, etd)
            rows = self.corpus.index_rows.get(prefix, {})
            files = {a.id: a.file.name for a in arts}
            folder = self.dep.folder(etd)
            index_rel = self.rel(folder / f"{folder.name}.md") if folder else prefix
            for art_id, name in files.items():
                if art_id not in rows:
                    self.add(
                        WARNING,
                        "index-drift",
                        index_rel,
                        f"`{art_id}` ({name}) is not registered — run `catalyst index regen`",
                    )
                elif rows[art_id] != name:
                    self.add(WARNING, "index-drift", index_rel, f"`{art_id}` links {rows[art_id]}, the file is {name}")
            for art_id in rows:
                if art_id not in files:
                    self.add(ERROR, "index-orphan", index_rel, f"registers `{art_id}`, which has no file")

    def run(self) -> list[Finding]:
        self.check_rules()
        self.check_artifacts()
        order = {ERROR: 0, WARNING: 1}
        self.findings.sort(key=lambda f: (order[f.level], f.where, f.code))
        return self.findings


def validate(dep: Deployment, corpus: Corpus) -> list[Finding]:
    return Validator(dep, corpus).run()
