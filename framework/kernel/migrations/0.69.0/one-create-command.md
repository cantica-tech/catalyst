# 0.69.0 — One `/create <type>`; meta-tags dropped

From `0.68.x` to `0.69.0` (ADR-021).

## What changes

- `/create <type> <title>` is a kernel command; each module type is one of its parts. The old `/create-<type>`
  names stay aliases. `catalyst task create -- <type> "<title>"` replaces `catalyst task create-<type>`.
- Meta-tags are dropped (decision B4): no `/meta-tag`, no `META-TAG` type.

## Steps

1. `catalyst sync apply --kernel <0.69.0>` (with `--module` for a module release that writes its create commands as
   parts). It recomposes `CODE-OF-CONDUCT.md` and `Taskfile.common.yml`, and removes
   `development/meta-tags/` and `definitions/meta-tag.md` when the folder holds no `tag-*.md`.
2. **Judgment:** if the plan says the meta-tags folder is kept because it holds tags, decide with the user whether to
   keep them as they are (nothing reads them any more) or retire them by hand; never delete one without a yes (L7).
3. A module still on its old create bullets keeps working: its commands are not parts of `/create`, and its own
   create tasks remain until it moves.
