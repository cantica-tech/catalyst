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
| `runs.schema.json` | `catalyst agent runs --json` | `GET /v1/runs` (local mode) |
| `approvals.schema.json` | `catalyst approvals <id> --json` | `GET /v1/approvals/<id>` |
| `try.schema.json` | `catalyst try <verb …> --json` | — (the host runs it, design 27) |
| `analyses.schema.json` | `catalyst analysis list --json` | `GET /v1/analyses` |
| `analysis.schema.json` | `catalyst analysis status <id> --json` | `GET /v1/analyses/<id>` |
| `module-releases.schema.json` | `catalyst module available <id> --json` | `GET /v1/modules/<id>/available` (local mode) |
| `audit.schema.json` | `catalyst audit --json` | `GET /v1/audit` (local mode) |
| `definitions.schema.json` | `catalyst definition list --json` | `GET /v1/definitions` |
| `share-status.schema.json` | `catalyst share status --json` | `GET /v1/share` (local mode) |
| `validate.schema.json` | `catalyst validate --json` | — |
| `journal-verify.schema.json` | `catalyst journal verify --json` | — |
| `report.schema.json` | `catalyst report --json` | — |
| `change.schema.json` | `catalyst new --json`, `catalyst rename --json`, `catalyst restore --json`, `catalyst status set --json`, `catalyst link --json` | — |
| `user.schema.json` | `catalyst user add --json`, `catalyst user remove --json`, `catalyst user modify --json`, `catalyst user assign-role --json` | — |
| `role.schema.json` | `catalyst role add --json`, `catalyst role modify --json` | — |
| `freeze.schema.json` | `catalyst freeze --json`, `catalyst unfreeze --json` | — |
| `definition-migrate.schema.json` | `catalyst definition migrate --json` | — |

The schemas of a module's own files are with the kernel
(`framework/kernel/schemas/`), with the schema of a deployment's approval
gates (`gates.schema.json`, for `IAM/gates.json`).
