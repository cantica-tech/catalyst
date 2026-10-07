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
    "Tier first: a chore (no rule's behaviour changes) is one `catalyst journal append --tier chore` "
    "entry with no target; a fix restores a rule (--tier fix); a feature adds or changes behaviour "
    "(--tier feature) — CODE-OF-CONDUCT.md §9. Signer and IDs: §2 (`catalyst id next`, rules with "
    "`catalyst id next-rule`, never by hand). Artifact-changing commands end with "
    "`catalyst index regen`, then `catalyst journal append`, then `catalyst check`. Commit the "
    "working copy and the product repository only with the user's assent (INV-4). Rules for every "
    "command: `catalyst spec --general`.")


class SpecError(Exception):
    pass


@dataclass
class Section4:
    bullets: dict[str, list[str]] = field(default_factory=dict)     # command -> bullet blocks
    procedures: dict[str, list[str]] = field(default_factory=dict)  # command -> paragraphs
    aliases: dict[str, str] = field(default_factory=dict)           # alias -> primary
    general: list[str] = field(default_factory=list)


def section4_text(text: str) -> list[str]:
    m = re.search(r"^## 4\.[^\n]*\n", text, re.M)
    if not m:
        raise SpecError("CODE-OF-CONDUCT.md has no '## 4.' section")
    end = re.search(r"^## 5\.", text[m.end():], re.M)
    return text[m.end():m.end() + end.start() if end else len(text)].splitlines()


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
            while (i < len(lines) and lines[i].strip() and not BULLET_START.match(lines[i])
                   and not lines[i].startswith("#")):
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
            for alias in names[1:]:
                s.aliases.setdefault(alias, names[0])
    # A paragraph belongs to the known command its first line names; else it
    # continues the previous command's procedure if it mentions that command
    # or continues a list or code block; else it is general.
    known = set(s.bullets) | set(s.aliases)
    owner: str | None = None
    for kind, body in blocks:
        if kind != "para":
            owner = None
            continue
        first = body.splitlines()[0]
        named = [s.aliases.get(n, n) for n in MENTION.findall(first + " ") if n in known]
        if named:
            owner = named[0]
        elif owner is None or not (f"/{owner}" in body or first.startswith(("  ", "```", "1.", "- ", "* "))):
            owner = None
        if owner:
            s.procedures.setdefault(owner, []).append(body)
        else:
            s.general.append(body)
    return s


def load_section4(dep: Deployment) -> Section4:
    return parse((dep.root / "CODE-OF-CONDUCT.md").read_text(encoding="utf-8"))


def spec_text(s: Section4, command: str) -> str:
    asked = command.lstrip("/")
    name = s.aliases.get(asked, asked)
    if name not in s.bullets and name not in s.procedures:
        raise SpecError(f"/{asked} is not in CODE-OF-CONDUCT.md §4")
    title = f"/{asked}" + (f" (alias of /{name})" if asked != name else "")
    out = [f"# {title} — from CODE-OF-CONDUCT.md §4", "", *s.bullets.get(name, [])]
    if s.procedures.get(name):
        out += ["", "\n\n".join(s.procedures[name])]
    out += ["", PREAMBLE]
    return "\n".join(out).rstrip() + "\n"


def spec(dep: Deployment, command: str) -> str:
    return spec_text(load_section4(dep), command)


def general(dep: Deployment) -> str:
    s = load_section4(dep)
    return "# Rules for every command — from CODE-OF-CONDUCT.md §4\n\n" + "\n\n".join(s.general) + "\n"


def commands(dep: Deployment) -> list[str]:
    return sorted(load_section4(dep).bullets)
