"""Who may make which change (owner decision D5, R4.6; INV-16, rr-META-011).

A writing verb names the command its change is for. The signer may make it
when one of their roles grants that command: a role's `actions` entry that
starts with `/` grants the command it names (`/status on tasks` grants
`status`; an alias such as `/user-add` grants that alias; a command grants
all its aliases), and `*` grants everything, as does the kernel's `Admin`
role (so an upgrade never locks its administrators out). Descriptive actions grant
nothing. A command the deployment's §4 does not have, and a tier named as
the command, are not checked. `catalyst.toml` `role_check = "warn"` turns a
refusal into a warning.
"""

from __future__ import annotations

from catalyst.deployment import Deployment

EVERYTHING = "*"
ADMIN = "Admin"


def required(dep: Deployment, command: str, also: tuple[str, ...] = ()) -> list[str] | None:
    """The command names any of which grants `command` (with `also`'s
    aliases when the deployment has them), or None when it is not one of the
    deployment's commands."""
    from catalyst import spec

    bare = command.strip().lstrip("/").split(" ")[0] if command.strip() else ""
    try:
        s = spec.load_section4(dep)
    except spec.SpecError:
        return None
    names: list[str] = []
    for name in (bare, *also):
        if name in s.aliases:
            names += [name, s.aliases[name]]
        elif name in s.bullets:
            names.append(name)
    return list(dict.fromkeys(names)) or None


def grants(dep: Deployment, signer: dict) -> set[str]:
    """The commands the signer's grants allow (`*` for all), from catalyst-users: the `cmd:<command>` client roles
    their token carries (fw-IDENTITY-000008)."""
    return {str(g)[4:] for g in signer.get("grants") or [] if str(g).startswith("cmd:")}


CREATE = "create"
TYPED_CREATE = "create:"


def creation_refusal(dep: Deployment, signer: dict, prefix: str) -> str | None:
    """Why the signer may not create an entity of type `prefix`, or None (design 31 §4.1, `fw-STRUCTURE-000020`).
    An admin (`cmd:*`) creates any type. Anyone else creates a module's type only, one its module leaves open to
    contributors (`contributors_create`, true by default), with `cmd:create` (or an alias of it) or `create:<TYPE>`."""
    held = grants(dep, signer)
    if EVERYTHING in held or ADMIN in (signer.get("roles") or []):
        return None
    who = signer.get("name") or signer.get("git_username") or "the signer"
    owners = [m for m in dep.installed() if prefix in m.entity_types]
    if not owners:
        return f"{who} may not create {prefix}: it is the kernel's, created by an admin only (design 31)"
    if not owners[-1].entity_types[prefix].contributors_create:
        return f"{who} may not create {prefix}: module {owners[-1].id} keeps it to admins (contributors_create: false)"
    typed = {str(g)[len(TYPED_CREATE) :] for g in signer.get("grants") or [] if str(g).startswith(TYPED_CREATE)}
    if prefix in typed or held & set(required(dep, CREATE) or [CREATE]):
        return None
    return f"{who} may not create {prefix}: no grant allows it (`cmd:create`, or `create:{prefix}`, from catalyst-users)"


def mode(dep: Deployment) -> str:
    """`enforce` (the default) or `warn`, from `catalyst.toml` `role_check`."""
    value = str((dep.pointer or {}).get("role_check") or "enforce").strip().lower()
    return "warn" if value == "warn" else "enforce"


def refusal(dep: Deployment, signer: dict, command: str, also: tuple[str, ...] = ()) -> str | None:
    """Why the signer may not make a change for `command`, or None."""
    needed = required(dep, command, also)
    if needed is None:
        return None
    held = grants(dep, signer)
    if EVERYTHING in held or held & set(needed):
        return None
    roles = ", ".join(str(r) for r in signer.get("roles") or []) or "no role"
    return (
        f"{signer.get('name')} ({roles}) may not run /{needed[0]}: none of their grants allows it. "
        f"Grant it in catalyst-users: `cmd:{needed[-1]}` composed into one of their roles, or a role that has it "
        "(fw-IDENTITY-000008, rr-META-011)"
    )
