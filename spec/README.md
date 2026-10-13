# spec

JSON Schemas of what catalyst's read verbs print with `--json` and its
server returns, one file per payload. A client generates its types from
them; a test in `tests/` checks each verb's output against its schema.

| Schema | Verb | Route |
|---|---|---|
| `impact.schema.json` | `catalyst impact <id> --json` | `GET /v1/impact/<id>` |
| `history.schema.json` | `catalyst journal show --artifact <id> --content --json` | `GET /v1/history/<id>` |

The schemas of a module's own files are with the kernel
(`framework/kernel/schemas/`).
