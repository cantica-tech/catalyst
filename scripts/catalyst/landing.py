"""Landing policies (design `docs/design/33`, fw-STRUCTURE-000023): how an
accepted change reaches the criterion's repository.

`IAM/landing.json` holds ordered rules; the first whose `match` fits a change
decides how it lands: what one pull request carries (`group`), who must
approve it (`review`) and how it merges (`merge`); `default` decides when no
rule matches. No file means the kernel's `standard` policy. The policy is
chosen at onboarding with the roles (`catalyst landing init`), and the
journaled choice is the Admin's assent (L3) to every landing it allows
(decision 33.1). Phase 1 declares and validates it; nothing lands yet.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from catalyst import journal
from catalyst.corpus import Corpus
from catalyst.deployment import Deployment

LANDING = Path("IAM") / "landing.json"
SCHEMA = "https://github.com/cantica-tech/catalyst/framework/kernel/schemas/landing.schema.json"
NAME = re.compile(r"^[a-z][a-z0-9-]{0,40}$")
TOP = ("$schema", "policy", "target", "rules", "default")
MATCH = ("via", "who", "change", "types")
VIA = ("agent", "person")
CHANGES = ("unlinked", "linked", "proposal-accepted", "server")
GROUPS = {"change": None, "session": "idle_minutes", "window": "minutes"}  # each kind's minutes key
WHERE = ("catalyst", "host")
MERGES = ("auto", "admin")
DEFAULT_POLICY = "standard"


class LandingError(Exception):
    pass


def _review(role: str, where: str = "catalyst") -> dict:
    return {"where": where, "approvals": 1, "role": role}


def _rule(rid: str, match: dict, group, review, merge: str = "auto") -> dict:
    return {"id": rid, "match": match, "group": group, "review": review, "merge": merge}


def _policy(name: str, rules: list[dict], default: dict) -> dict:
    return {
        "$schema": SCHEMA,
        "policy": name,
        "target": {"kind": "git", "branch": "criterion", "credential": "serve-landing"},
        "rules": rules,
        "default": default,
    }


_LEAD = "Criterion Admin"
_SERVER = _rule("server-own", {"change": "server"}, "change", "none")
_SESSION = {"by": "session", "idle_minutes": 30}
_WINDOW = {"by": "window", "minutes": 60}

# The kernel's policies (design 33 §4.1, §4.2), held equal to `templates/landing.<name>.template.json` by a test.
POLICIES: dict[str, dict] = {
    "standard": _policy(
        "standard",
        [
            _SERVER,
            _rule("agent-session", {"via": "agent"}, _SESSION, _review(_LEAD)),
            _rule("explicit-unlinked", {"via": "person", "change": "unlinked"}, "change", "none"),
            _rule("accepted-proposal", {"change": "proposal-accepted"}, "change", "none"),
        ],
        {"group": "change", "review": _review(_LEAD), "merge": "auto"},
    ),
    "open": _policy("open", [_SERVER], {"group": "change", "review": "none", "merge": "auto"}),
    "reviewed": _policy(
        "reviewed",
        [_SERVER, _rule("agent-session", {"via": "agent"}, _SESSION, _review(_LEAD))],
        {"group": _WINDOW, "review": _review(_LEAD), "merge": "auto"},
    ),
    "host": _policy(
        "host",
        [
            _SERVER,
            _rule("agent-session", {"via": "agent"}, _SESSION, _review(_LEAD, "host"), "admin"),
            _rule("explicit-unlinked", {"via": "person", "change": "unlinked"}, "change", "none"),
            _rule("accepted-proposal", {"change": "proposal-accepted"}, "change", "none"),
        ],
        {"group": "change", "review": _review(_LEAD, "host"), "merge": "admin"},
    ),
}


def policy(name: str) -> dict:
    """A copy of the kernel's policy `name`."""
    if name not in POLICIES:
        raise LandingError(f"no landing policy {name!r} (the kernel's: {', '.join(POLICIES)})")
    return copy.deepcopy(POLICIES[name])


def _raw(dep: Deployment) -> dict | None:
    path = dep.root / LANDING
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LandingError(f"{LANDING.as_posix()}: not JSON ({exc})") from None
    if not isinstance(data, dict):
        raise LandingError(f"{LANDING.as_posix()}: an object is expected")
    return data


def effective(dep: Deployment) -> tuple[dict, str]:
    """(the policy in force, where it comes from): the file, else the kernel's standard policy."""
    data = _raw(dep)
    if data is None:
        return policy(DEFAULT_POLICY), f"the kernel's {DEFAULT_POLICY} policy (no {LANDING.as_posix()})"
    return data, LANDING.as_posix()


def _roles(dep: Deployment) -> set[str]:
    from catalyst.corpus import roles

    return {str(r.get("name")) for r in roles(dep)}


def _how(where: str, rule: dict, roles: set[str]) -> list[str]:
    """What is wrong with one rule's (or the default's) group, review and merge."""
    out = []
    group = rule.get("group")
    if isinstance(group, str):
        if group not in GROUPS:
            out.append(f"{where}: `group` is one of {', '.join(GROUPS)}")
    elif isinstance(group, dict):
        kind = group.get("by")
        if kind not in GROUPS:
            out.append(f"{where}: `group.by` is one of {', '.join(GROUPS)}")
        else:
            key = GROUPS[kind]
            extra = set(group) - {"by", *([key] if key else [])}
            if extra:
                out.append(f"{where}: `group` has no {', '.join(sorted(extra))}")
            minutes = group.get(key) if key else None
            if (
                key
                and minutes is not None
                and (not isinstance(minutes, int) or isinstance(minutes, bool) or minutes < 1)
            ):
                out.append(f"{where}: `group.{key}` is a whole number of minutes, at least 1")
    else:
        out.append(f'{where}: `group` is "change", "session", "window" or {{"by": …}}')
    review = rule.get("review")
    if review != "none":
        if not isinstance(review, dict) or set(review) - {"where", "approvals", "role"}:
            out.append(f'{where}: `review` is "none" or {{"where", "approvals", "role"}}')
        else:
            if review.get("where", "catalyst") not in WHERE:
                out.append(f"{where}: `review.where` is one of {', '.join(WHERE)}")
            n = review.get("approvals")
            if not isinstance(n, int) or isinstance(n, bool) or n < 1:
                out.append(f"{where}: `review.approvals` is a whole number, at least 1")
            if review.get("role") not in roles:
                out.append(f"{where}: `review.role` {review.get('role')!r} is not a role of the roles template")
    if rule.get("merge") not in MERGES:
        out.append(f"{where}: `merge` is one of {', '.join(MERGES)}")
    return out


def _match(where: str, match, dep: Deployment, roles: set[str]) -> list[str]:
    if not isinstance(match, dict):
        return [f"{where}: `match` is an object"]
    out = []
    extra = set(match) - set(MATCH)
    if extra:
        out.append(f"{where}: `match` has no {', '.join(sorted(extra))} (it takes {', '.join(MATCH)})")
    if "via" in match and match["via"] not in VIA:
        out.append(f"{where}: `match.via` is one of {', '.join(VIA)}")
    if "change" in match and match["change"] not in CHANGES:
        out.append(f"{where}: `match.change` is one of {', '.join(CHANGES)}")
    for key, known, what in (
        ("who", roles, "a role of the roles template"),
        ("types", set(dep.etds), "a declared type"),
    ):
        if key not in match:
            continue
        values = match[key]
        if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values):
            out.append(f"{where}: `match.{key}` is a non-empty list of names")
            continue
        out += [f"{where}: `match.{key}` {v!r} is not {what}" for v in values if v not in known]
    return out


def problems(dep: Deployment, corpus: Corpus | None = None) -> list[str]:
    """What is wrong with `IAM/landing.json`, one line each (`check` reports them as errors). No file, none."""
    try:
        data = _raw(dep)
    except LandingError as exc:
        return [str(exc)]
    if data is None:
        return []
    name = LANDING.as_posix()
    out, roles = [], _roles(dep)
    extra = set(data) - set(TOP)
    if extra:
        out.append(f"{name}: no field {', '.join(sorted(extra))} (it takes {', '.join(TOP)})")
    if not isinstance(data.get("policy"), str) or not NAME.match(data["policy"]):
        out.append(f"{name}: `policy` names the policy (lowercase letters, digits, dashes)")
    target = data.get("target")
    if not isinstance(target, dict) or target.get("kind") != "git":
        out.append(f'{name}: `target` is {{"kind": "git", "branch": …, "credential": …}}')
    else:
        if set(target) - {"kind", "branch", "credential"}:
            out.append(f"{name}: `target` takes kind, branch and credential")
        for key in ("branch", "credential"):
            if target.get(key) is not None and not isinstance(target[key], str):
                out.append(f"{name}: `target.{key}` is a name")
    rules = data.get("rules")
    if not isinstance(rules, list):
        out.append(f"{name}: `rules` is a list")
        rules = []
    seen: set[str] = set()
    for i, rule in enumerate(rules):
        where = f"{name} rule {i + 1}"
        if not isinstance(rule, dict):
            out.append(f"{where}: not an object")
            continue
        rid = rule.get("id")
        if not isinstance(rid, str) or not NAME.match(rid):
            out.append(f"{where}: `id` is a lowercase name (letters, digits, dashes)")
        elif rid in seen:
            out.append(f"{where}: `id` {rid} is declared twice")
        else:
            seen.add(rid)
            where = f"{name} rule {rid}"
        extra = set(rule) - {"id", "match", "group", "review", "merge"}
        if extra:
            out.append(f"{where}: no field {', '.join(sorted(extra))}")
        out += _match(where, rule.get("match"), dep, roles)
        out += _how(where, rule, roles)
    default = data.get("default")
    if not isinstance(default, dict):
        out.append(f"{name}: `default` is an object (group, review, merge)")
    else:
        if set(default) - {"group", "review", "merge"}:
            out.append(f"{name} default: it takes group, review and merge only")
        out += _how(f"{name} default", default, roles)
    return out


def warnings(dep: Deployment) -> list[str]:
    """What will not land as declared: a served criterion (members, design 32) with no credential to land with."""
    if str(dep.pointer.get("share") or "") != "serve":
        return []
    try:
        data, source = effective(dep)
    except LandingError:
        return []  # `problems` reports it
    target = data.get("target")
    if isinstance(target, dict) and target.get("credential"):
        return []
    return [f"{source}: a served criterion names no `target.credential`: its members' changes could not land"]


def init(dep: Deployment, name: str, signer: dict, force: bool = False, intent: list[str] | None = None) -> Path:
    """Write the kernel's policy `name` to `IAM/landing.json`, journaled as the Admin's assent (decision 33.1)."""
    from catalyst import permissions

    if not permissions.is_admin(signer):
        who = signer.get("name") or signer.get("git_username") or "the signer"
        raise LandingError(f"{who} may not choose the landing policy: an admin's (design 33 §5)")
    data = policy(name)
    path = dep.root / LANDING
    if path.exists() and not force:
        raise LandingError(f"{LANDING.as_posix()} exists: pass --force to replace it with the {name} policy")
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    actor = str(signer.get("git_username") or signer.get("name"))
    journal.append(
        dep,
        journal.AppendRequest(
            command="catalyst landing init",
            action="update" if existed else "create",
            artifact="landing policy",
            targets=[],
            intent=[
                f"the {name} landing policy, chosen by {actor}: the Admin's assent (L3) to every landing it allows "
                "(design 33, decision 33.1)",
                *(intent or []),
            ],
            files=[str(path)],
            actor=actor,
            tier="chore",
        ),
    )
    return path
