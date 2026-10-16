# spec

JSON Schemas of what catalyst's read verbs print with `--json` and its
server returns, one file per payload. A client generates its types from
them; `tests/test_spec.py` and each verb's own tests check its output
against its schema, with the checker in `tests/schema_check.py`.

| Schema | Verb | Route |
|---|---|---|
| `impact.schema.json` | `catalyst impact <id> --json` | `GET /v1/impact/<id>` |
| `history.schema.json` | `catalyst journal show --artifact <id> --content --json` | `GET /v1/history/<id>` |
| `inbox.schema.json` | `catalyst inbox --json` | `GET /v1/inbox` |
| `list.schema.json` | `catalyst list <type> --json` | `GET /v1/list?type=<type>` |
| `view.schema.json` | `catalyst view <id> --json` | `GET /v1/view/<id>` |
| `backlog.schema.json` | `catalyst backlog --json` | `GET /v1/backlog` |
| `graph.schema.json` | `catalyst graph --json` | `GET /v1/graph` |
| `journal.schema.json` | `catalyst journal show --json` | `GET /v1/journal` |
| `check.schema.json` | `catalyst check --json` | `GET /v1/check` (local mode) |
| `commands.schema.json` | `catalyst spec --json` | `GET /v1/commands` |
| `command-spec.schema.json` | `catalyst spec <command> [<part>] --json` | `GET /v1/spec/<command>[/<part>]` |
| `run-event.schema.json` | `catalyst agent run <command> --json` (one per line) | — (no route starts a run) |

The schemas of a module's own files are with the kernel
(`framework/kernel/schemas/`).
