"""`catalyst spec <command>`: only the part of the deployed CODE-OF-CONDUCT.md
§4 a command needs — its bullet and its procedure paragraphs — instead of
the whole document. Keeps each command's reading load within a budget (the
canonical text is still §4; this only selects).

Every §4 paragraph lands somewhere: with the command its first line names,
as the continuation of the previous command's procedure, or in the general
part (`catalyst spec --general`) that every command's spec points to.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from catalyst.deployment import Deployment

BULLET_START = re.compile(r"^- `/([a-z][a-z0-9-]*)")
# `/name`, `/name <args>` and the colon form `/name: ...` all name a command.
MENTION = re.compile(r"`/([a-z][a-z0-9-]*)(?=[`\s:])")
PREAMBLE = (
    "Tier first (Rules-of-Rules.md §6): a chore (no rule's behaviour changes) is one `catalyst journal append "
    "--tier chore` entry with no target; a fix restores a rule (--tier fix); a feature adds or changes behaviour "
    "(--tier feature). Signer and IDs: `--as`, `catalyst id next`, rules with `catalyst id next-rule`, never by "
    "hand. Artifact-changing commands end with `catalyst index regen`, then `catalyst journal append`, then "
    "`catalyst check`. Nothing is pushed, published or committed in the project without the user's yes (law "
    "L3). Rules for every command: `catalyst spec --general`; any law or rule: `catalyst why`."
)


class SpecError(Exception):
    pass


@dataclass
class Section4:
    bullets: dict[str, list[str]] = field(default_factory=dict)  # command -> bullet blocks
    procedures: dict[str, list[str]] = field(default_factory=dict)  # command -> paragraphs
    aliases: dict[str, str] = field(default_factory=dict)  # alias -> primary
    general: list[str] = field(default_factory=list)
    # A command with parts (`/create <type>`, ADR-021): the aliases each bullet
    # and paragraph names, so `create-item` reads only its own part; empty = shared
    bullet_tags: dict[str, list[set[str]]] = field(default_factory=dict)  # command -> per bullet
    procedure_tags: dict[str, list[set[str]]] = field(default_factory=dict)  # command -> per paragraph


def _names(text: str, aliases: dict[str, str]) -> list[str]:
    """The commands a line names: `/x`, `/x: ...`, and `/x <part>` read as
    the alias `x-<part>` when there is one (`/create item` is `/create-item`)."""
    out = []
    for m in re.finditer(r"`/([a-z][a-z0-9-]*)(?:[` :]|\s)(?:([a-z][a-z0-9-]*))?", text):
        name, part = m.group(1), m.group(2)
        out.append(f"{name}-{part}" if part and f"{name}-{part}" in aliases else name)
    return out


def section4_text(text: str) -> list[str]:
    m = re.search(r"^## 4\.[^\n]*\n", text, re.M)
    if not m:
        raise SpecError("CODE-OF-CONDUCT.md has no '## 4.' section")
    end = re.search(r"^## 5\.", text[m.end() :], re.M)
    return text[m.end() : m.end() + end.start() if end else len(text)].splitlines()


def blocks_of(lines: list[str]) -> list[tuple[str, str]]:
    """("bullet"|"para"|"heading", text) in order."""
    blocks: list[tuple[str, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if BULLET_START.match(line):
            block = [line]
            i += 1
            while i < len(lines) and lines[i].startswith("  ") and not BULLET_START.match(lines[i]):
                block.append(lines[i])
                i += 1
            blocks.append(("bullet", "\n".join(block)))
        elif not line.strip():
            i += 1
        elif line.startswith("#"):
            blocks.append(("heading", line))
            i += 1
        else:
            block = [line]
            i += 1
            while (
                i < len(lines)
                and lines[i].strip()
                and not BULLET_START.match(lines[i])
                and not lines[i].startswith("#")
            ):
                block.append(lines[i])
                i += 1
            blocks.append(("para", "\n".join(block)))
    return blocks


def parse(text: str) -> Section4:
    s = Section4()
    blocks = blocks_of(section4_text(text))
    for kind, body in blocks:
        if kind == "bullet":
            names = MENTION.findall(body.split("—", 1)[0] + " ")
            if not names:  # e.g. `/x|y`: names no command; never crash the parse
                continue
            s.bullets.setdefault(names[0], []).append(body)
            s.bullet_tags.setdefault(names[0], []).append(set(names[1:]))
            for alias in names[1:]:
                s.aliases.setdefault(alias, names[0])
    # A paragraph belongs to the known command its first line names; else it
    # continues the previous command's procedure if it mentions that command
    # or continues a list or code block; else it is general.
    known = set(s.bullets) | set(s.aliases)
    owner: str | None = None
    tag: set[str] = set()
    for kind, body in blocks:
        if kind != "para":
            owner = None
            continue
        first = body.splitlines()[0]
        named = [n for n in _names(first + " ", s.aliases) if n in known]
        if named:
            new_owner, new_tag = s.aliases.get(named[0], named[0]), {n for n in named if n in s.aliases}
            # naming only the command continues the part in progress; a new procedure starts with "When"
            if not (new_owner == owner and not new_tag and tag and not first.startswith("When ")):
                tag = new_tag
            owner = new_owner
        elif owner is None or not (f"/{owner}" in body or first.startswith(("  ", "```", "1.", "- ", "* "))):
            owner = None
        if owner:
            s.procedures.setdefault(owner, []).append(body)
            s.procedure_tags.setdefault(owner, []).append(tag)
        else:
            s.general.append(body)
    return s


def _parted(s: Section4, name: str) -> bool:
    """A command with parts: more than one bullet, some naming their own aliases."""
    return len(s.bullets.get(name, [])) > 1 and any(s.bullet_tags.get(name, []))


def load_section4(dep: Deployment) -> Section4:
    return parse((dep.root / "CODE-OF-CONDUCT.md").read_text(encoding="utf-8"))


def spec_text(s: Section4, command: str, part: str | None = None) -> str:
    asked = command.lstrip("/")
    if part and f"{asked}-{part}" in s.aliases and _parted(s, asked):  # `catalyst spec create item`
        asked = f"{asked}-{part}"
    name = s.aliases.get(asked, asked)
    if name not in s.bullets and name not in s.procedures:
        raise SpecError(f"/{asked} is not in CODE-OF-CONDUCT.md §4")
    title = f"/{asked}" + (f" (alias of /{name})" if asked != name else "")
    bullets, procedures = s.bullets.get(name, []), s.procedures.get(name, [])
    note = []
    if _parted(s, name):
        # the shared part, and only the asked part's own (all parts' bullets when none is asked)
        btags, ptags = s.bullet_tags[name], s.procedure_tags.get(name, [])
        if asked == name:
            procedures = [p for p, t in zip(procedures, ptags, strict=True) if not t]
            parts = sorted(a for t in btags for a in t)
            note = [f"One part's procedure: `catalyst spec {name} <part>` (or an alias: {', '.join(parts)})."]
        else:
            mine = {asked}.union(*(t for t in btags if asked in t))
            bullets = [b for b, t in zip(bullets, btags, strict=True) if not t or t & mine]
            procedures = [p for p, t in zip(procedures, ptags, strict=True) if not t or t & mine]
    out = [f"# {title} — from CODE-OF-CONDUCT.md §4", "", *bullets]
    if procedures:
        out += ["", "\n\n".join(procedures)]
    if note:
        out += ["", *note]
    out += ["", PREAMBLE]
    return "\n".join(out).rstrip() + "\n"


def spec(dep: Deployment, command: str, part: str | None = None) -> str:
    return spec_text(load_section4(dep), command, part)


def general(dep: Deployment) -> str:
    s = load_section4(dep)
    return "# Rules for every command — from CODE-OF-CONDUCT.md §4\n\n" + "\n\n".join(s.general) + "\n"


def commands(dep: Deployment) -> list[str]:
    return sorted(load_section4(dep).bullets)


def parts(dep: Deployment) -> list[str]:
    """The aliases that name one part of a command with parts (`create-item`)."""
    s = load_section4(dep)
    return sorted(a for name in s.bullets if _parted(s, name) for t in s.bullet_tags[name] for a in t)
