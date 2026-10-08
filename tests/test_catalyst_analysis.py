"""Four-eyes code analysis (`catalyst analysis`, fw-STRUCTURE-000015): the
lifecycle, and every refusal that makes the four-eyes process real."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from catalyst import analysis as an
from catalyst.check import run as run_check
from catalyst.corpus import load_corpus
from catalyst.deployment import load
from catalyst_fixtures import USER, USERID, make_project, write

RULE = f"br-AUTH-000001-{USERID}"
ITEM = f"ITEM-000001-{USERID}"


@pytest.fixture
def project(tmp_path, monkeypatch):
    project = make_project(tmp_path, git=True)
    write(project / "src" / "login.py", "def login(user, password):\n    return check(password)\n")
    write(project / "src" / "session.py", "TIMEOUT = 0  # never expires\n")
    subprocess.run(["git", "-C", str(project), "add", "src"], check=True)
    subprocess.run(["git", "-C", str(project), "commit", "-q", "-m", "code"], check=True)
    (project / ".criterion" / "analyses").mkdir()
    monkeypatch.chdir(project)
    return project


def signer(project):
    return load_corpus(load(project)).user(USER)


def finding(fid, kind, title, **kw):
    f = {"id": fid, "kind": kind, "title": title, "statement": f"{title}.", "area": "auth",
         "confidence": "high", "evidence": [{"path": "src/login.py", "line": 1}]}
    if kind == "rule":
        f["status"] = "holds"
    f.update(kw)
    return f


PASS_A = {"findings": [
    finding("A1", "rule", "Sessions expire", status="partial",
            evidence=[{"path": "src/session.py", "line": 1}]),
    finding("A2", "defect", "Session timeout is zero", breaks="A1",
            evidence=[{"path": "src/session.py", "line": 1}]),
    finding("A3", "rule", "Passwords are checked on login"),
]}
PASS_B = {"findings": [
    finding("B1", "rule", "Sessions expire", status="missing",          # disagrees on status
            evidence=[{"path": "src/session.py", "line": 1}]),
    finding("B2", "rule", "Passwords are checked on login"),
    finding("B3", "domain", "Session management", code="SESSION", evidence=[]),
]}


def started(project):
    return an.start(load(project), ["src"], "incremental", signer(project), "login and sessions")


def test_start_records_scope_code_state_and_inventory(project):
    ctx = started(project)
    assert ctx.art.id == f"ANALYSIS-000001-{USERID}"
    inv = ctx.load("inventory.json")
    assert set(inv["files"]) == {"src/login.py", "src/session.py"}
    assert inv["code_state"] == subprocess.run(["git", "-C", str(project), "rev-parse", "HEAD"],
                                               capture_output=True, text=True, encoding="utf-8").stdout.strip()
    assert RULE in inv["existing"]["rules"] and ITEM in inv["existing"]["grounded"]
    assert an.phase(ctx.art) == "Extracting"
    with pytest.raises(an.AnalysisError, match="already has 1 rule"):
        an.start(load(project), ["src"], "bootstrap", signer(project))


def test_passes_are_validated_and_recorded_once(project):
    ctx = started(project)
    bad = {"findings": [finding("X1", "defect", "No rule", breaks="nope"),
                        finding("X2", "rule", "Outside", evidence=[{"path": "README.md"}])]}
    with pytest.raises(an.AnalysisError) as exc:
        an.record(ctx, "A", bad)
    assert "neither an existing rule" in str(exc.value) and "not in the analysed scope" in str(exc.value)
    an.record(ctx, "A", PASS_A)
    with pytest.raises(an.AnalysisError, match="already recorded"):
        an.record(ctx, "A", PASS_A)
    assert an.record(ctx, "B", {"findings": [dict(f, id=f["id"].replace("A", "B"),
                                                  **({"breaks": "B1"} if f.get("breaks") else {}))
                                             for f in PASS_A["findings"]]}) == \
        ["both passes are identical — were they really run independently?"]


def test_diff_classifies_agreed_conflicting_and_single_pass(project):
    ctx = started(project)
    with pytest.raises(an.AnalysisError, match="both passes"):
        an.run_diff(ctx)
    an.record(ctx, "A", PASS_A)
    an.record(ctx, "B", PASS_B)
    d = an.run_diff(ctx)
    assert [(p["a"], p["b"]) for p in d["agreed"]] == [("A3", "B2")]
    assert [(p["a"], p["b"]) for p in d["conflicting"]] == [("A1", "B1")]
    assert d["a_only"] == ["A2"] and d["b_only"] == ["B3"]
    assert an.phase(an.context(load(project), ctx.art.id).art) == "Reconciling"


RECONCILED = {
    "findings": [
        finding("F1", "rule", "Sessions expire", status="partial", sources=["A:A1", "B:B1"],
                evidence=[{"path": "src/session.py", "line": 1}],
                verification="read session.py: a timeout exists but is 0 — partial, not missing"),
        finding("F2", "defect", "Session timeout is zero", breaks="F1", sources=["A:A2"],
                evidence=[{"path": "src/session.py", "line": 1}],
                verification="session.py:1 sets TIMEOUT = 0"),
        finding("F3", "rule", "Passwords are checked on login", sources=["A:A3", "B:B2"],
                verification="both passes"),
    ],
    "dropped": [{"source": "B:B3", "reason": "one file does not make a domain; folded into AUTH"}],
}


def reconciled(project):
    ctx = started(project)
    an.record(ctx, "A", PASS_A)
    an.record(ctx, "B", PASS_B)
    an.run_diff(ctx)
    return an.context(load(project), ctx.art.id)


def test_reconciliation_must_account_for_every_finding(project):
    ctx = reconciled(project)
    missing = {"findings": RECONCILED["findings"], "dropped": []}
    with pytest.raises(an.AnalysisError, match="B:B3 is neither reconciled nor dropped"):
        an.reconcile(ctx, missing)
    unverified = json.loads(json.dumps(RECONCILED))
    unverified["findings"][1]["verification"] = "both passes"
    with pytest.raises(an.AnalysisError, match="F2: found by one pass or contested"):
        an.reconcile(ctx, unverified)
    twice = json.loads(json.dumps(RECONCILED))
    twice["dropped"].append({"source": "A:A3", "reason": "dup"})
    with pytest.raises(an.AnalysisError, match="A:A3 is accounted for 2 times"):
        an.reconcile(ctx, twice)
    an.reconcile(ctx, RECONCILED)
    assert an.phase(an.context(load(project), ctx.art.id).art) == "Deciding"


def test_decisions_need_real_artifacts_and_close_needs_them_all(project):
    ctx = reconciled(project)
    an.reconcile(ctx, RECONCILED)
    ctx = an.context(load(project), ctx.art.id)
    who = signer(project)
    with pytest.raises(an.AnalysisError, match="names the artifact"):
        an.decide(ctx, "F3", "accept", who)
    with pytest.raises(an.AnalysisError, match="does not exist"):
        an.decide(ctx, "F3", "accept", who, artifact="br-AUTH-000099-" + USERID)
    an.decide(ctx, "F3", "accept", who, artifact=RULE)            # an existing rule covers it
    an.decide(ctx, "F2", "accept", who, artifact=ITEM)
    with pytest.raises(an.AnalysisError, match="F1 has no decision"):
        an.close(ctx)
    assert an.phase(an.context(load(project), ctx.art.id).art) == "Deciding"
    an.decide(ctx, "F1", "reject", who, reason="covered by the existing rule")
    counts = an.close(an.context(load(project), ctx.art.id))
    assert counts == {"defect": {"accept": 1, "reject": 0}, "rule": {"accept": 1, "reject": 1}}
    art = an.context(load(project), ctx.art.id).art
    assert an.phase(art) == "Closed" and art.get("Closed")
    assert f"`{RULE}`" in art.file.read_text(encoding="utf-8")
    assert not [e for e in run_check(load(project)).errors if e.startswith("analysis:")]


def test_check_rejects_a_record_its_reports_do_not_support(project):
    ctx = reconciled(project)
    an.reconcile(ctx, RECONCILED)
    (ctx.dir / "B.json").unlink()                                 # a pass lost after the fact
    errors = [e for e in run_check(load(project)).errors if e.startswith("analysis:")]
    assert errors and "both passes are not recorded" in errors[0]


def test_abandon(project):
    ctx = started(project)
    an.abandon(ctx, "scope too wide")
    art = an.context(load(project), ctx.art.id).art
    assert an.phase(art) == "Abandoned" and "scope too wide" in art.file.read_text(encoding="utf-8")
    with pytest.raises(an.AnalysisError, match="already Abandoned"):
        an.abandon(an.context(load(project), ctx.art.id), "again")


def test_cli_lifecycle_journals_every_phase(project, tmp_path, capsys):
    from catalyst.__main__ import main
    assert main(["analysis", "start", "src", "--name", "cli run"]) == 0
    aid = f"ANALYSIS-000001-{USERID}"
    for which, data in (("A", PASS_A), ("B", PASS_B)):
        write(tmp_path / f"{which}.json", json.dumps(data))
        assert main(["analysis", "record", aid, "--pass", which, str(tmp_path / f"{which}.json")]) == 0
    assert main(["analysis", "diff", aid]) == 0
    write(tmp_path / "r.json", json.dumps(RECONCILED))
    assert main(["analysis", "reconcile", aid, str(tmp_path / "r.json")]) == 0
    assert main(["analysis", "decide", aid, "F1", "reject", "--reason", "covered"]) == 0
    assert main(["analysis", "decide", aid, "F2", "accept", "--artifact", ITEM]) == 0
    assert main(["analysis", "decide", aid, "F3", "accept", "--artifact", RULE]) == 0
    assert main(["analysis", "close", aid]) == 0
    assert main(["analysis", "status", aid]) == 0
    assert "Closed" in capsys.readouterr().out
    lines = (project / ".criterion" / "development" / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    commands = [c for c in (json.loads(line)["command"] for line in lines) if c.startswith("catalyst analysis")]
    assert commands == ["catalyst analysis start"] + ["catalyst analysis record"] * 2 + [
        "catalyst analysis diff", "catalyst analysis reconcile"] + ["catalyst analysis decide"] * 3 + [
        "catalyst analysis close"]
    assert main(["analysis", "record", aid, "--pass", "A", str(tmp_path / "A.json")]) == 1
    assert "Closed" in capsys.readouterr().err


def test_the_playbooks_findings_example_is_valid():
    """The documented format is the one the CLI accepts."""
    import re
    text = (Path(__file__).resolve().parents[1] / "framework" / "kernel" / "ANALYSIS-PLAYBOOK.md").read_text(encoding="utf-8")
    example = json.loads(re.search(r"```json\n(.*?)```", text, re.S).group(1))
    assert an.validate_findings(example["findings"], inventory={"src/session.py"}, rules=set(),
                                domains=set()) == []
