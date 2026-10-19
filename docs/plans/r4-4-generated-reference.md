# R4.4 — The kernel's reference generated from the code

Owner decision D7 (2026-10-19): the kernel's reference documents are generated from the code. Before it, two parts
were generated (0.66.1, HK-000002): the command index in `CLI.md` and the kernel's types in `FORMAT.md`. The rest,
about 290 KB, was written by hand.

## What "generated" covers

A reference states facts the code already holds: the arguments a command takes, the shape of what it prints, the
keys a file may carry, the migrations a release ships. Those facts are generated between markers
(`<!-- generated: … -->`), and `scripts/gen_docs.py --check` fails CI when a document disagrees with the code.

What a command is for, why a rule exists, and how to decide a case are explanation, not facts the code holds. That
prose stays written by hand, next to the generated parts, and is checked against the code where it names something
the code defines.

## Phases

| Phase | Document | Generated from | Check |
|---|---|---|---|
| 1 (0.97.0) | `CLI.md`: every command's arguments and options with their help, choices, defaults | the CLI's parser; every argument now has help text | the prose may name only options the CLI has (`flag_drift`) |
| 2 | `CLI.md`: each machine-readable output, the schema that describes it | `spec/*.schema.json` and `spec/README.md` | every `--json` command has a schema |
| 3 | `FORMAT.md`: `catalyst.toml`'s keys; `MODULE-SPECIFICATION.md`: `module.yaml`'s keys | one registry of project-file keys in the code; `framework/kernel/schemas/*.json` | the prose names only keys that exist |
| 4 | `SYNCHRONIZE.md`: the migrations, from–to and summary | `framework/kernel/migrations/migrations.md` | the list matches the index |
| 5 | `INVARIANTS.md`: the law-and-invariant table's "enforced by" | the checks that cite each invariant | each invariant names code that enforces it, or says it is judged |

Each phase ships in its own release with no migration: generated sections change no deployed file except the
kernel documents a sync already recomposes.

## Phase 1, done in 0.97.0

- `scripts/gen_docs.py`: `cli_options`, every leaf command's arguments, and `flag_drift`, which flags any `--option`
  the prose names that no command has, except other tools' flags (git, uv, an agent's CLI).
- `scripts/catalyst/__main__.py`: `_fill_help` gives the arguments their parsers left bare (105 of 338) their
  help, so `catalyst <command> --help` says it too.
- `CLI.md`: an "Options reference" section.
