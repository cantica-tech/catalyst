"""What catalyst generates for a type declared in a v3 `module.yaml`
(module v3, M3): its item template and its definition document, from its
fields, states, sections and `definition:`. A module may still ship a file
for either; the file wins."""

from __future__ import annotations

import re

from module_loader import ETD

NONE_YET = "*(none yet)*"
REF_KINDS = ("ref", "ref-list")


def type_slug(etd: ETD) -> str:
    """The type's name as definitions and templates name it (`house-keeping`)."""
    return re.sub(r"[^a-z0-9]+", "-", etd.name.lower()).strip("-")


def template(etd: ETD) -> str:
    """The item template: the title, the field table `catalyst new` fills
    (a field's `hint:`, else a placeholder for its kind), then each section
    under its heading with its hint."""
    status = next((f for f in etd.fields if f.name == "Status"), None)
    rows = [
        ("ID", f"`{etd.id_prefix}-NNNNNN`"),
        ("Name", "`short-name`"),
        ("Filename", f"`{etd.id_prefix}-NNNNNN-short-name.md`"),
        ("Status", status.hint if status and status.hint else etd.workflow.initial),
        ("Opened", "YYYY-MM-DD"),
    ]
    for f in etd.fields:
        if f.name in ("ID", "Status"):
            continue
        if f.hint:
            value = f.hint
        elif f.kind in REF_KINDS:
            value = NONE_YET
        elif f.kind == "enum" and f.allowed_values:
            value = " / ".join(f.allowed_values)
        elif f.kind == "date":
            value = "YYYY-MM-DD"
        else:
            value = ""
        rows.append((f.name, value))
    if not any(f.name.lower() == "signed-off-by" for f in etd.fields):  # every artifact is signed
        rows.append(("Signed-off-by", "the signer"))
    lines = [f"# `{etd.id_prefix}-NNNNNN` — {{{{title}}}}", "", "| Field | Value |", "|---|---|"]
    lines += [f"| **{name}** | {value} |" for name, value in rows]
    for heading, hint in etd.sections:
        lines += ["", f"## {heading}", ""]
        if hint:
            lines.append(hint)
    return "\n".join(lines) + "\n"


def definition(etd: ETD) -> str:
    """The definition document, version 1, frozen once deployed."""
    slug = type_slug(etd)
    closed = ", ".join(f"`{s}`" for s in etd.workflow.closed_states) or "none"
    return (
        f"# `{slug}` — entity definition (v1)\n\n"
        "| Field | Value |\n|---|---|\n"
        f"| **Entity type** | `{slug}` |\n| **Version** | 1 |\n\n"
        "## Description\n\n"
        f"{etd.definition or f'A `{etd.id_prefix}-NNNNNN` {etd.name.lower()}.'}\n\n"
        f"States: {', '.join(f'`{s}`' for s in etd.workflow.states)}; closed: {closed}.\n"
    )


def create_command(etd: ETD) -> str:
    """The `/create-<type>` command a v3 type gets when its module's
    catalogue part does not define one."""
    return f"create-{type_slug(etd)}"


def _field_args(etd: ETD) -> str:
    args = []
    for f in etd.fields:
        if f.name in ("ID", "Status") or (f.kind not in REF_KINDS and f.kind not in ("enum", "text")):
            continue
        piece = f"--field {f.name}=<{'IDs' if f.kind == 'ref-list' else 'ID' if f.kind == 'ref' else 'value'}>"
        args.append(piece if f.required else f"[{piece}]")
    return " ".join(args)


def catalogue_entry(etd: ETD) -> str:
    """The command's bullet and procedure for the command catalogue (§4)."""
    name = create_command(etd)
    part = name.removeprefix("create-")
    required = [f.name for f in etd.fields if f.required and f.name not in ("ID", "Status")]
    sections = ", ".join(f"`{h}`" for h, _ in etd.sections) or "none"
    closed = ", ".join(f"`{s}`" for s in etd.workflow.closed_states) or "none"
    return (
        f"- `/create {part} <title>` (`/{name}`) — create a new {etd.name.lower()} (`{etd.id_prefix}-NNNNNN`) "
        f"immediately, register it in its index and journal it (generated from the module's `module.yaml`).\n\n"
        f'When the user enters `/create {part}: ...` or `/{name}: ...`, run `catalyst new {etd.id_prefix} --title "<t>" '
        f"{_field_args(etd)} --command /{name} --as <signer>`, then write its sections ({sections}). "
        f"Required fields: {', '.join(f'`{r}`' for r in required) or 'none'}. "
        f"It starts `{etd.workflow.initial}`; closed states: {closed}"
        + (
            f"; entering {', '.join(f'`{s}`' for s in etd.workflow.guards)} is guarded (`catalyst status set` says why)"
            if etd.workflow.guards
            else ""
        )
        + ".\n"
    )
