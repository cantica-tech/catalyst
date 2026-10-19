#!/usr/bin/env python3
"""Generated sections of the kernel's reference documents (roadmap R4.4).

Parts of `CLI.md` and `FORMAT.md` restate what the code already knows: the
commands and their options, the kernel's own entity types. Written by hand,
they drift. This writes them from the source of truth, between markers in the
document, and leaves the prose around them alone:

    <!-- generated: <name> (scripts/gen_docs.py; do not edit by hand) -->
    ...
    <!-- end generated: <name> -->

`gen_docs.py` rewrites every marked section; `gen_docs.py --check` exits 1,
naming each section that differs, without writing (the tests run it).
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KERNEL = ROOT / "framework" / "kernel"
sys.path.insert(0, str(ROOT / "scripts"))

BEGIN = "<!-- generated: {name} (scripts/gen_docs.py; do not edit by hand) -->"
END = "<!-- end generated: {name} -->"


def _parser() -> argparse.ArgumentParser:
    from catalyst.__main__ import build_parser

    return build_parser()


def _subcommands(parser: argparse.ArgumentParser, prefix: str = "catalyst") -> list[tuple[str, str, list[str]]]:
    """(command, help, options) for every command and subcommand, in the
    parser's order."""
    rows = []
    for action in parser._actions:  # argparse keeps its tree here
        if not isinstance(action, argparse._SubParsersAction):
            continue
        helps = {a.dest: a.help or "" for a in action._choices_actions}
        for name, sub in action.choices.items():
            path = f"{prefix} {name}"
            nested = _subcommands(sub, path)
            if nested:
                rows += nested
                continue
            options = sorted(
                {
                    max(a.option_strings, key=len)
                    for a in sub._actions
                    if a.option_strings and a.help != argparse.SUPPRESS and "--help" not in a.option_strings
                }
            )
            positionals = [
                a.metavar or a.dest for a in sub._actions if not a.option_strings and a.help != argparse.SUPPRESS
            ]
            usage = " ".join([path, *(f"<{p}>" for p in positionals if isinstance(p, str))])
            rows.append((usage, " ".join((helps.get(name) or "").split()), options))
    return rows


def cli_index() -> str:
    lines = [
        "Every command and its options, from the CLI itself; the sections below describe each.",
        "",
        "| Command | What it does | Options |",
        "|---|---|---|",
    ]
    for usage, text, options in _subcommands(_parser()):
        opts = ", ".join(f"`{o}`" for o in options) or "—"
        what = text.replace("|", "\\|") or "—"
        lines.append(f"| `{usage}` | {what} | {opts} |")
    return "\n".join(lines)


def _leaves(parser: argparse.ArgumentParser, prefix: str = "catalyst") -> list[tuple[str, argparse.ArgumentParser]]:
    """(command, its parser) for every leaf command, in the parser's order."""
    out = []
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, sub in action.choices.items():
                nested = _leaves(sub, f"{prefix} {name}")
                out += nested or [(f"{prefix} {name}", sub)]
    return out


def _argument(a: argparse.Action) -> tuple[str, str]:
    """(how an argument is written, what it does) for the options reference."""
    if a.option_strings:
        names = ", ".join(f"`{o}`" for o in sorted(a.option_strings, key=len))
        takes = a.metavar or (a.dest.upper() if a.nargs != 0 and not isinstance(a.const, bool) else None)
        if isinstance(a, (argparse._StoreTrueAction, argparse._StoreFalseAction, argparse._CountAction)):
            takes = None
        written = names + (f" `{takes}`" if takes and isinstance(takes, str) else "")
    else:
        written = f"`<{a.metavar or a.dest}>`" + (" …" if a.nargs in ("*", "+", argparse.REMAINDER) else "")
    what = " ".join((a.help or "").split()).replace("|", "\\|")
    notes = []
    if a.choices and not isinstance(a.choices, dict):
        notes.append("one of " + ", ".join(f"`{c}`" for c in a.choices))
    if isinstance(a, argparse._AppendAction) and "repeatable" not in (a.help or ""):
        notes.append("repeatable")
    if a.option_strings and a.default not in (None, False, [], argparse.SUPPRESS) and not isinstance(a.default, bool):
        notes.append(f"default `{a.default}`")
    if notes:
        what = f"{what} ({'; '.join(notes)})" if what else "; ".join(notes).capitalize()
    return written, what or "—"


def cli_options() -> str:
    """Every command's arguments, from the parser: what `catalyst <command> --help` says, in one place."""
    lines = [
        "Every command's arguments and options, generated from the CLI's own parser; `catalyst <command> --help` "
        "says the same. The sections above describe what each command does and why.",
        "",
        "| Command | Argument | What it does |",
        "|---|---|---|",
    ]
    for command, sub in _leaves(_parser()):
        args = [a for a in sub._actions if a.help != argparse.SUPPRESS and "--help" not in a.option_strings]
        if not args:
            lines.append(f"| `{command}` | — | — |")
        for i, a in enumerate(args):
            written, what = _argument(a)
            lines.append(f"| {'`' + command + '`' if i == 0 else ''} | {written} | {what} |")
    return "\n".join(lines)


# Other tools' flags the prose names (git, uv, an agent's CLI): never catalyst's, so not checked against its parser
EXTERNAL_FLAGS = {"--no-verify", "--shared", "--output-format", "--scope", "--relocatable"}


def flag_drift(text: str) -> list[str]:
    """Each `--flag` the hand-written prose of CLI.md names that no command of the parser has (R4.4): the prose is
    checked against the code. `--prefix-*` stands for every option it begins."""
    options: set[str] = set()

    def walk(p: argparse.ArgumentParser) -> None:
        for a in p._actions:
            options.update(a.option_strings)
            if isinstance(a, argparse._SubParsersAction):
                for sub in a.choices.values():
                    walk(sub)

    walk(_parser())
    prose = re.sub(r"<!-- generated: .*?<!-- end generated: [\w-]+ -->", "", text, flags=re.S)
    found = set(re.findall(r"(?<![\w-])(--[a-z][a-z0-9-]*-\*|--[a-z][a-z0-9-]*[a-z0-9])", prose))
    drift = []
    for flag in sorted(found):
        if flag in EXTERNAL_FLAGS:
            continue
        if flag.endswith("*"):
            if not any(o.startswith(flag[:-1]) for o in options):
                drift.append(flag)
        elif flag not in options:
            drift.append(flag)
    return drift


def kernel_types() -> str:
    from module_loader import load_kernel_entities

    lines = [
        "The kernel's own entity types, from `framework/kernel/entities/`; a module adds its own.",
        "",
        "| Prefix | Type | Folder | States | Closed |",
        "|---|---|---|---|---|",
    ]
    for prefix, etd in sorted(load_kernel_entities().items()):
        folder = f"{etd.location}/{etd.folder}" if etd.location else etd.folder
        states = ", ".join(etd.workflow.states) or "—"
        closed = ", ".join(etd.workflow.closed_states) or "—"
        lines.append(f"| `{prefix}` | {etd.name} | `{folder}/` | {states} | {closed} |")
    return "\n".join(lines)


SECTIONS: dict[str, tuple[Path, Callable[[], str]]] = {
    "cli-index": (KERNEL / "CLI.md", cli_index),
    "kernel-types": (KERNEL / "FORMAT.md", kernel_types),
    "cli-options": (KERNEL / "CLI.md", cli_options),
}


def render(text: str, name: str, body: str) -> str:
    begin, end = BEGIN.format(name=name), END.format(name=name)
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise SystemExit(f"gen_docs: no `{begin}` … `{end}` section to fill")
    return pattern.sub(lambda _: f"{begin}\n\n{body}\n\n{end}", text)


def main(argv: list[str] | None = None) -> int:
    check = "--check" in (argv if argv is not None else sys.argv[1:])
    stale = []
    for name, (path, build) in SECTIONS.items():
        text = path.read_text(encoding="utf-8")
        fresh = render(text, name, build())
        if fresh != text:
            stale.append(f"{path.relative_to(ROOT)} ({name})")
            if not check:
                path.write_text(fresh, encoding="utf-8")
    drift = flag_drift((KERNEL / "CLI.md").read_text(encoding="utf-8"))
    if drift:
        print("CLI.md names options no command has: " + ", ".join(drift))
        return 1
    if stale:
        print(("out of date: " if check else "rewrote: ") + ", ".join(stale))
        return 1 if check else 0
    print("generated sections up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
