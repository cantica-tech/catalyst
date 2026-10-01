"""Four-eyes analysis of existing code (`fw-STRUCTURE-000015`,
ANALYSIS-PLAYBOOK.md).

An `ANALYSIS-` record follows one run through its phases:

  start      the record, the scope and the code state (inventory.json)
  record     two independent, blind passes: A.json, B.json
  diff       their findings matched: agreed / A-only / B-only / conflicting
  reconcile  the reconciler's list, accounting for every finding of both
  decide     one human decision per reconciled finding
  close      only when every accepted finding names an artifact that exists

The reports live in `analyses/reports/<ID>/`. Research agents write
findings files only; the artifacts an accepted finding becomes are written
by the orchestrating session, after the user's decision. `problems()` is
the one set of checks `close` and `catalyst check` both apply.
"""
from __future__ import annotations

import datetime
import difflib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from catalyst.corpus import Artifact, Corpus, load_corpus
from catalyst.deployment import Deployment
from catalyst.scope import governs

PREFIX = "ANALYSIS"
KINDS = ("domain", "rule", "defect")
STATUSES = ("holds", "partial", "missing")        # a rule: implemented / buggy or incomplete / not implemented
CONFIDENCE = ("high", "medium", "low")
MODES = ("bootstrap", "incremental")
PHASES = ("Extracting", "Reconciling", "Deciding", "Closed", "Abandoned")
AGREED = "both passes"                            # the verification of an agreed finding


class AnalysisError(Exception):
    pass


# --- where things are ----------------------------------------------------
def folder(dep: Deployment) -> Path:
    etd = dep.etds.get(PREFIX)
    found = dep.folder(etd) if etd else None
    if found is None:
        raise AnalysisError("this deployment has no analyses/ folder — `/sync-framework` (migration 0.44.0)")
    return found


def reports(dep: Deployment, analysis_id: str) -> Path:
    return folder(dep) / "reports" / analysis_id


def find(dep: Deployment, corpus: Corpus, analysis_id: str) -> Artifact:
    for art in corpus.by_prefix.get(PREFIX, []):
        if art.id == analysis_id or art.id.rsplit("-", 1)[0] == analysis_id:
            return art
    raise AnalysisError(f"no analysis {analysis_id}")


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise AnalysisError(f"{path.name} is not valid JSON: {exc}") from exc


def _write(path: Path, data) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _git(repo: Path, *args: str) -> str:
    res = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if res.returncode != 0:
        raise AnalysisError(f"git {' '.join(args)} failed: {res.stderr.strip()}")
    return res.stdout


def _set_field(md: Path, name: str, value: str) -> None:
    text = md.read_text(encoding="utf-8")
    new, n = re.subn(rf"^(\| \*\*{re.escape(name)}\*\* \| )[^|\n]*?( \|)$", rf"\g<1>{value}\g<2>",
                     text, count=1, flags=re.M)
    if n == 0:
        new, n = re.subn(rf"^(\| \*\*{re.escape(name)}\*\* \|)\s*\|$", rf"\g<1> {value} |", text, count=1,
                         flags=re.M)
    if n == 0:
        raise AnalysisError(f"{md.name} has no `{name}` field")
    md.write_text(new, encoding="utf-8")


def phase(art: Artifact) -> str:
    return (art.get("Status") or "").strip().strip("`")


# --- the findings format ---------------------------------------------------
def validate_findings(findings, *, inventory: set[str], rules: set[str], domains: set[str],
                      reconciled: bool = False) -> list[str]:
    """Problems with a list of findings (a pass's, or the reconciler's).
    A defect names the rule it breaks: an existing rule ID, or the id of a
    rule finding in the same list."""
    if not isinstance(findings, list):
        return ["`findings` is not a list"]
    problems: list[str] = []
    rule_findings = {f.get("id") for f in findings if isinstance(f, dict) and f.get("kind") == "rule"}
    seen: set[str] = set()
    for n, f in enumerate(findings, 1):
        if not isinstance(f, dict):
            problems.append(f"finding {n} is not an object")
            continue
        fid = f.get("id")
        where = f"finding {fid or n}"
        if not fid or not isinstance(fid, str):
            problems.append(f"{where}: no `id`")
        elif fid in seen:
            problems.append(f"{where}: duplicate id")
        seen.add(fid)
        kind = f.get("kind")
        if kind not in KINDS:
            problems.append(f"{where}: `kind` must be one of {', '.join(KINDS)}")
        for key in ("title", "statement"):
            if not str(f.get(key) or "").strip():
                problems.append(f"{where}: no `{key}`")
        if f.get("confidence") not in CONFIDENCE:
            problems.append(f"{where}: `confidence` must be one of {', '.join(CONFIDENCE)}")
        if kind == "rule" and f.get("status") not in STATUSES:
            problems.append(f"{where}: a rule's `status` must be one of {', '.join(STATUSES)}")
        evidence = f.get("evidence") or []
        if kind in ("rule", "defect") and not evidence:
            problems.append(f"{where}: a {kind} needs `evidence` (file and line in the scope)")
        for e in evidence if isinstance(evidence, list) else []:
            path = e.get("path") if isinstance(e, dict) else None
            if not path:
                problems.append(f"{where}: evidence without a `path`")
            elif path not in inventory:
                problems.append(f"{where}: evidence {path} is not in the analysed scope")
            line = e.get("line") if isinstance(e, dict) else None
            if line is not None and (not isinstance(line, int) or line < 1):
                problems.append(f"{where}: evidence line must be a positive integer")
        if kind == "domain" and f.get("code") and not re.fullmatch(r"[A-Z]{3,7}", str(f["code"])):
            problems.append(f"{where}: a domain `code` is 3–7 uppercase letters")
        if kind == "defect":
            breaks = f.get("breaks")
            if not breaks:
                problems.append(f"{where}: a defect names the rule it `breaks` (an existing rule ID, "
                                "or a rule finding's id)")
            elif breaks not in rules and breaks not in rule_findings:
                problems.append(f"{where}: `breaks` {breaks} is neither an existing rule nor a rule finding")
        if reconciled:
            sources = f.get("sources")
            if not isinstance(sources, list) or not sources:
                problems.append(f"{where}: no `sources` (the pass findings it reconciles)")
            if not str(f.get("verification") or "").strip():
                problems.append(f"{where}: no `verification`")
    return problems


# --- matching two passes ------------------------------------------------------
def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", str(s).lower()).strip()


def _paths(f: dict) -> set[str]:
    return {e.get("path") for e in f.get("evidence") or [] if isinstance(e, dict) and e.get("path")}


def similarity(a: dict, b: dict) -> float:
    """How likely two findings (one per pass) describe the same thing."""
    if a.get("kind") != b.get("kind"):
        return 0.0
    if a.get("kind") == "domain" and a.get("code") and a.get("code") == b.get("code"):
        return 1.0
    text = difflib.SequenceMatcher(None, _norm(f"{a.get('title')} {a.get('statement')}"),
                                   _norm(f"{b.get('title')} {b.get('statement')}")).ratio()
    pa, pb = _paths(a), _paths(b)
    overlap = len(pa & pb) / len(pa | pb) if pa | pb else 0.0
    return 0.6 * text + 0.4 * overlap


MATCH = 0.45


def diff(a: list[dict], b: list[dict]) -> dict:
    """Pair each finding of pass A with at most one of pass B, best match
    first, and classify: agreed, conflicting (matched, but a different
    status or a different broken rule), A-only, B-only."""
    scored = sorted(((similarity(x, y), i, j) for i, x in enumerate(a) for j, y in enumerate(b)),
                    reverse=True)
    used_a: set[int] = set()
    used_b: set[int] = set()
    agreed, conflicting = [], []
    for score, i, j in scored:
        if score < MATCH or i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        x, y = a[i], b[j]
        reasons = []
        if x.get("kind") == "rule" and x.get("status") != y.get("status"):
            reasons.append(f"status {x.get('status')} vs {y.get('status')}")
        if x.get("kind") == "defect" and x.get("breaks") != y.get("breaks"):
            reasons.append(f"breaks {x.get('breaks')} vs {y.get('breaks')}")
        pair = {"a": x["id"], "b": y["id"], "kind": x.get("kind"), "score": round(score, 2)}
        if reasons:
            conflicting.append({**pair, "reason": "; ".join(reasons)})
        else:
            agreed.append(pair)
    return {"agreed": agreed, "conflicting": conflicting,
            "a_only": [x["id"] for i, x in enumerate(a) if i not in used_a],
            "b_only": [y["id"] for j, y in enumerate(b) if j not in used_b]}


def coverage(recon: dict, a: list[dict], b: list[dict], d: dict) -> list[str]:
    """Every finding of both passes is kept (a final finding's `sources`)
    or dropped with a reason, exactly once; a final finding that is not a
    plain agreement says how it was verified against the code."""
    problems = []
    wanted = {f"A:{f['id']}" for f in a} | {f"B:{f['id']}" for f in b}
    counted: dict[str, int] = {}
    for f in recon.get("findings") or []:
        for s in f.get("sources") or []:
            counted[s] = counted.get(s, 0) + 1
    for drop in recon.get("dropped") or []:
        s = drop.get("source") if isinstance(drop, dict) else None
        if not s:
            problems.append("a dropped entry has no `source`")
            continue
        counted[s] = counted.get(s, 0) + 1
        if not str(drop.get("reason") or "").strip():
            problems.append(f"dropped {s}: no `reason`")
    for s in sorted(wanted - set(counted)):
        problems.append(f"{s} is neither reconciled nor dropped")
    for s in sorted(set(counted) - wanted):
        problems.append(f"{s} is not a finding of either pass (sources are `A:<id>` or `B:<id>`)")
    for s, n in sorted(counted.items()):
        if n > 1 and s in wanted:
            problems.append(f"{s} is accounted for {n} times")
    plain = {frozenset((f"A:{p['a']}", f"B:{p['b']}")) for p in d.get("agreed", [])}
    for f in recon.get("findings") or []:
        if frozenset(f.get("sources") or []) not in plain and \
                str(f.get("verification") or "").strip().lower() in ("", AGREED):
            problems.append(f"finding {f.get('id')}: found by one pass or contested — say how it was "
                            "verified against the code in `verification`")
    return problems


# --- the lifecycle -------------------------------------------------------------
@dataclass
class Context:
    dep: Deployment
    corpus: Corpus
    art: Artifact
    dir: Path

    @property
    def inventory(self) -> set[str]:
        inv = _read(self.dir / "inventory.json") or {}
        return set((inv.get("files") or {}).keys())

    def load(self, name: str):
        return _read(self.dir / name)


def context(dep: Deployment, analysis_id: str, corpus: Corpus | None = None) -> Context:
    corpus = corpus or load_corpus(dep)
    art = find(dep, corpus, analysis_id)
    return Context(dep, corpus, art, reports(dep, art.id))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "analysis"


def start(dep: Deployment, scope: list[str], mode: str, signer: dict, name: str | None = None) -> Context:
    from catalyst.ids import next_entity_id
    if mode not in MODES:
        raise AnalysisError(f"mode must be one of {', '.join(MODES)}")
    if dep.standalone:
        raise AnalysisError("an analysis reads the product's code — run it from the project")
    project = dep.project_root
    scope = [s.rstrip("/") or "." for s in scope] or ["."]
    listed = _git(project, "ls-files", "-s", "--", *scope).splitlines()
    files = {}
    for line in listed:
        meta, path = line.split("\t", 1)
        if not governs(project, path):
            continue                          # the working copy, a nested deployment, opted out
        files[path] = meta.split()[1]
    if not files:
        raise AnalysisError(f"no tracked file in {' '.join(scope)}")
    head = _git(project, "rev-parse", "HEAD").strip()
    corpus = load_corpus(dep)
    if mode == "bootstrap" and corpus.rules:
        raise AnalysisError(f"this deployment already has {len(corpus.rules)} rule(s) — use --mode incremental")
    art_id = next_entity_id(dep, corpus, PREFIX, signer)
    slug = _slug(name or " ".join(scope))
    md = folder(dep) / f"{art_id.rsplit('-', 1)[0]}-{art_id.rsplit('-', 1)[1]}-{slug}.md"
    today = datetime.date.today().isoformat()
    md.write_text(f"""# `{art_id}` — {name or 'analysis of ' + ' '.join(scope)}

| Field | Value |
|---|---|
| **ID** | `{art_id}` |
| **Name** | `{slug}` |
| **Filename** | `{md.name}` |
| **Status** | Extracting |
| **Mode** | {mode} |
| **Scope** | {' '.join(scope)} |
| **Code state** | {head} |
| **Opened** | {today} |
| **Closed** | |
| **Signed-off-by** | {signer.get('name')} |

## Passes

Two independent, blind passes (`ANALYSIS-PLAYBOOK.md`), recorded with
`catalyst analysis record {art_id} --pass A|B`.

## Reconciliation

*(after both passes)*

## Decisions

*(after reconciliation)*

## Summary

*(at close)*
""", encoding="utf-8")
    existing = {}
    if mode == "incremental":
        existing = {
            "rules": sorted(corpus.rules),
            "domains": sorted(corpus.domains),
            "grounded": sorted(a.id for prefix, arts in corpus.by_prefix.items()
                               if dep.etds[prefix].grounding == "required" for a in arts),
        }
    _write(reports(dep, art_id) / "inventory.json",
           {"analysis": art_id, "mode": mode, "scope": scope, "code_state": head, "files": files,
            "existing": existing})
    return context(dep, art_id)


def record(ctx: Context, which: str, data: dict, replace: bool = False) -> list[str]:
    """Store one blind pass. Returns warnings."""
    if phase(ctx.art) != "Extracting":
        raise AnalysisError(f"{ctx.art.id} is {phase(ctx.art)}: passes are recorded while Extracting")
    which = which.upper()
    if which not in ("A", "B"):
        raise AnalysisError("--pass is A or B")
    target = ctx.dir / f"{which}.json"
    if target.exists() and not replace:
        raise AnalysisError(f"pass {which} is already recorded")
    findings = data.get("findings") if isinstance(data, dict) else None
    problems = validate_findings(findings, inventory=ctx.inventory, rules=set(ctx.corpus.rules),
                                 domains=ctx.corpus.domains)
    if problems:
        raise AnalysisError(f"pass {which} rejected:\n  " + "\n  ".join(problems))
    warnings = []
    other = ctx.load("B.json" if which == "A" else "A.json")
    if other is not None and _canon(other.get("findings")) == _canon(findings):
        warnings.append("both passes are identical — were they really run independently?")
    _write(target, {"pass": which, "findings": findings})
    return warnings


def _canon(findings) -> str:
    """A pass's findings without their pass-specific ids: a `breaks` that
    names a finding of the same pass is replaced by that finding's title."""
    titles = {f.get("id"): f.get("title") for f in findings or [] if isinstance(f, dict)}

    def strip(f):
        if not isinstance(f, dict):
            return f
        out = {k: v for k, v in f.items() if k != "id"}
        if out.get("breaks") in titles:
            out["breaks"] = titles[out["breaks"]]
        return out
    return json.dumps(sorted(json.dumps(strip(f), sort_keys=True) for f in findings or []))


def run_diff(ctx: Context) -> dict:
    if phase(ctx.art) not in ("Extracting", "Reconciling"):
        raise AnalysisError(f"{ctx.art.id} is {phase(ctx.art)}")
    a, b = ctx.load("A.json"), ctx.load("B.json")
    if a is None or b is None:
        raise AnalysisError("both passes are needed first (`catalyst analysis record --pass A|B`)")
    d = diff(a["findings"], b["findings"])
    _write(ctx.dir / "diff.json", d)
    _set_field(ctx.art.file, "Status", "Reconciling")
    return d


def reconcile(ctx: Context, data: dict) -> None:
    if phase(ctx.art) != "Reconciling":
        raise AnalysisError(f"{ctx.art.id} is {phase(ctx.art)}: reconcile after `catalyst analysis diff`")
    a, b, d = ctx.load("A.json"), ctx.load("B.json"), ctx.load("diff.json")
    if not isinstance(data, dict):
        raise AnalysisError("the reconciled file is an object with `findings` and `dropped`")
    problems = validate_findings(data.get("findings"), inventory=ctx.inventory, rules=set(ctx.corpus.rules),
                                 domains=ctx.corpus.domains, reconciled=True)
    problems += coverage(data, a["findings"], b["findings"], d)
    if problems:
        raise AnalysisError("reconciliation rejected:\n  " + "\n  ".join(problems))
    _write(ctx.dir / "reconciled.json", {"findings": data["findings"], "dropped": data.get("dropped") or []})
    _set_field(ctx.art.file, "Status", "Deciding")


def _artifact_exists(corpus: Corpus, kind: str, ref: str) -> bool:
    if kind == "domain":
        return ref in corpus.domains
    if kind == "rule":
        return ref in corpus.rules
    return ref in corpus.artifacts


def decide(ctx: Context, finding: str, verdict: str, signer: dict, artifact: str | None = None,
           reason: str | None = None) -> None:
    if phase(ctx.art) != "Deciding":
        raise AnalysisError(f"{ctx.art.id} is {phase(ctx.art)}: decisions come after reconciliation")
    recon = ctx.load("reconciled.json")
    by_id = {f["id"]: f for f in recon["findings"]}
    if finding not in by_id:
        raise AnalysisError(f"no reconciled finding {finding}")
    if verdict not in ("accept", "reject"):
        raise AnalysisError("the decision is accept or reject")
    kind = by_id[finding]["kind"]
    if verdict == "accept":
        if not artifact:
            raise AnalysisError(f"an accepted {kind} names the artifact it became (--artifact) — write it first")
        if not _artifact_exists(ctx.corpus, kind, artifact):
            raise AnalysisError(f"{artifact} does not exist in the deployment (a {kind} becomes "
                                f"{'a registered DOMAIN code' if kind == 'domain' else 'a rule ID' if kind == 'rule' else 'an artifact'})")
    decisions = ctx.load("decisions.json") or {"decisions": {}}
    decisions["decisions"][finding] = {
        "verdict": verdict, "artifact": artifact, "reason": reason,
        "by": signer.get("name"), "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }
    _write(ctx.dir / "decisions.json", decisions)


def problems(ctx: Context, status: str | None = None) -> list[str]:
    """What keeps this analysis from being consistent with its phase (or
    with `status`, the phase it would move to): the checks `close` and
    `catalyst check` share."""
    status = status or phase(ctx.art)
    if status not in PHASES:
        return [f"Status {status!r} is not one of {', '.join(PHASES)}"]
    if status in ("Extracting", "Abandoned"):
        return []
    out = []
    if not (ctx.dir / "inventory.json").is_file():
        out.append("no inventory.json (`catalyst analysis start` writes it)")
    a, b, d = ctx.load("A.json"), ctx.load("B.json"), ctx.load("diff.json")
    if a is None or b is None:
        return out + ["both passes are not recorded (A.json, B.json)"]
    if d is None:
        return out + ["no diff.json (`catalyst analysis diff`)"]
    if status == "Reconciling":
        return out
    recon = ctx.load("reconciled.json")
    if recon is None:
        return out + ["no reconciled.json (`catalyst analysis reconcile`)"]
    out += coverage(recon, a["findings"], b["findings"], d)
    if status == "Deciding":
        return out
    decided = (ctx.load("decisions.json") or {}).get("decisions", {})
    for f in recon["findings"]:
        dec = decided.get(f["id"])
        if dec is None:
            out.append(f"finding {f['id']} has no decision")
        elif dec.get("verdict") == "accept" and not _artifact_exists(ctx.corpus, f["kind"], dec.get("artifact") or ""):
            out.append(f"finding {f['id']} was accepted as {dec.get('artifact')}, which does not exist")
    return out


def close(ctx: Context) -> dict:
    if phase(ctx.art) != "Deciding":
        raise AnalysisError(f"{ctx.art.id} is {phase(ctx.art)}: close after every decision")
    found = problems(ctx, "Closed")
    if found:
        raise AnalysisError("cannot close:\n  " + "\n  ".join(found))
    _set_field(ctx.art.file, "Status", "Closed")
    _set_field(ctx.art.file, "Closed", datetime.date.today().isoformat())
    recon = ctx.load("reconciled.json")
    decided = ctx.load("decisions.json")["decisions"]
    counts: dict[str, dict[str, int]] = {}
    for f in recon["findings"]:
        v = decided[f["id"]]["verdict"]
        counts.setdefault(f["kind"], {"accept": 0, "reject": 0})[v] += 1
    accepted = sorted({d["artifact"] for d in decided.values() if d["verdict"] == "accept"})
    summary = "; ".join(f"{k}: {c['accept']} accepted, {c['reject']} rejected" for k, c in sorted(counts.items()))
    text = ctx.art.file.read_text(encoding="utf-8")
    text = text.replace("## Summary\n\n*(at close)*",
                        f"## Summary\n\n{summary or 'no findings'}.\n\nArtifacts: "
                        + (", ".join(f"`{x}`" for x in accepted) or "none") + ".")
    ctx.art.file.write_text(text, encoding="utf-8")
    return counts


def abandon(ctx: Context, reason: str) -> None:
    if phase(ctx.art) in ("Closed", "Abandoned"):
        raise AnalysisError(f"{ctx.art.id} is already {phase(ctx.art)}")
    _set_field(ctx.art.file, "Status", "Abandoned")
    _set_field(ctx.art.file, "Closed", datetime.date.today().isoformat())
    text = ctx.art.file.read_text(encoding="utf-8")
    ctx.art.file.write_text(text.replace("## Summary\n\n*(at close)*", f"## Summary\n\nAbandoned: {reason}"),
                            encoding="utf-8")


def files_of(ctx: Context) -> list[Path]:
    """The record and its reports, for the journal."""
    return [ctx.art.file] + sorted(p for p in ctx.dir.glob("*.json"))
