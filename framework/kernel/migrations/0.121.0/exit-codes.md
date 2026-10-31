# 0.121.0 — No deployment exits 4; module releases live in the distribution repository

From `0.120.0` to `0.121.0` (REQ-000110, REQ-000111, REQ-000112).

## What changes

- The CLI's exit codes (fw-STRUCTURE-000025, `CLI.md` "Exit codes"): no deployment — no `catalyst.toml` at or above
  the directory or `--project`, a criterion that is not reachable, `--working-copy` naming no working copy — exits
  `4`, no longer `2`. `2` is a usage error only (argparse's and the arguments a command refuses itself, `--working-copy`
  given to a command that finds the project itself), and a blocking `hook stop`, as before. `move`, `migrate` and
  `task` outside a project exited `1`; they exit `4` too. `agent run` that cannot start for want of an adapter or of
  the agent's CLI on `PATH` exits `1`; a command `CODE-OF-CONDUCT.md` §4 does not have stays `2`.
- `check`, `hook stop`, `hook start` and `hook commit-msg` outside any project still exit `0`; an unreachable
  criterion still fails `check` (`1`) and blocks `hook stop` (`2`). `where` and `open` still exit `1` for a criterion
  they report missing.
- `catalyst id next` and `id next-rule` take `--peek` (the next ID, reserving nothing) and `--json`
  (`spec/id-next.schema.json`). Reserving stays the default.

## Steps

Nothing mechanical for a deployment: no file in a criterion or a project changes.

1. A caller that runs the catalyst CLI and tested exit code `2` to mean "no deployment" (a script, an editor
   extension, a CI step, an MCP server) tests `4`. To work with kernels before `0.121.0` as well, it can accept `2`
   where a usage error cannot happen (a fixed, valid command line), and read `4` as the same thing.
2. A release workflow that ran `scripts/package_release.py --push` expecting it to commit a module release onto the
   module repository's `main`: the release is now only in the distribution repository (`--publish-dir`), published
   from the module checkout at its version's tag. Release zips already committed in a module repository are that
   repository's to remove.
