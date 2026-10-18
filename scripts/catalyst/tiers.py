"""Ceremony tiers (rr-META-006): the active module's `tiers:`, else the
kernel's default. A tier names the artifact type it opens (`none`: the
change needs no artifact, only its journal entry) and, for a tier with no
artifact, the commit-subject prefix that marks it (`chore:`). The kernel
gives no tier any other meaning."""

from __future__ import annotations

import re

from module_loader import DEFAULT_TIERS, Tier


def tiers_for(dep) -> list[Tier]:
    """The union of the installed modules' tiers, in install order (a tier
    two modules declare is the first one's: `module install` refuses two
    meanings for one id); the kernel's default when none declares any."""
    one = getattr(dep, "module", None)
    alone = [one] if one is not None else []
    modules = getattr(dep, "installed", lambda: alone)()
    found: dict[str, Tier] = {}
    for module in modules:
        for tier in module.tiers or DEFAULT_TIERS:  # a module that declares none has the default ones
            found.setdefault(tier.id, tier)
    return list(found.values()) or list(DEFAULT_TIERS)


def inferred(dep, artifact: str) -> str | None:
    """The tier an artifact's own type opens (R4.8): a change to an artifact
    whose type exactly one tier names (`artifact: <PREFIX>`) is of that tier,
    when the change names none. None when no tier, or several, name it."""
    prefix = artifact.split("-", 1)[0] if re.match(r"^[A-Z][A-Z0-9]*-\d", artifact) else ""
    named = [t.id for t in tiers_for(dep) if prefix and t.artifact == prefix]
    return named[0] if len(named) == 1 else None


def ids(dep) -> list[str]:
    return [t.id for t in tiers_for(dep)]


def check(dep, tier: str | None) -> None:
    """ValueError when `tier` is not one the active module declares."""
    if tier is None:
        return
    known = ids(dep)
    if tier not in known:
        raise ValueError(f"tier '{tier}' is not one of {', '.join(known)} (the installed modules' tiers)")


def commit_prefixes(dep=None) -> tuple[str, ...]:
    """The subject prefixes of the tiers that need no artifact."""
    source = tiers_for(dep) if dep is not None else DEFAULT_TIERS
    return tuple(t.commit for t in source if not t.needs_artifact and t.commit)


def prefix_re(prefixes: tuple[str, ...]) -> re.Pattern:
    """A subject starting with one of `prefixes`, optionally scoped:
    `chore:` matches `chore: x` and `chore(R3): x`."""
    words = [re.escape(p.rstrip(":").strip()) for p in prefixes if p.rstrip(":").strip()]
    if not words:
        return re.compile(r"(?!x)x")  # nothing is a chore
    return re.compile(rf"^(?:{'|'.join(words)})(?:\([^)]*\))?:", re.I)
