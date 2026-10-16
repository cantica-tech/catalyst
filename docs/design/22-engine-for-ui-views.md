# 22 — What the engine owes a UI's views (R5.6–R5.9 design note for the owner, 2026-10-13)

> **Status: decided (owner, 2026-10-13).** All six decisions as recommended: mentions reported apart and left out of
> the closure; the inbox starts with unrecorded changes, `RECON-` cases and analyses; the name `inbox`; `--static
> <dir>`; schemas in `spec/` as each is built; one release per addition (R5.6, R5.9, R5.7, R5.8). **R5.6 released** (kernel 0.61.0, 2026-10-13, REQ-000030): `catalyst impact`, `GET /v1/impact/<id>`, `spec/impact.schema.json`. **R5.9 released** (kernel 0.62.0, 2026-10-13, REQ-000031): `journal show --artifact <id> --content`, `GET /v1/history/<id>`, `spec/history.schema.json`. **R5.7 released** (kernel 0.63.0, 2026-10-14, REQ-000032): `catalyst inbox`, `GET /v1/inbox`, `spec/inbox.schema.json`. **R5.8 released** (kernel 0.64.0, 2026-10-14, REQ-000033): `serve --local --static <dir>`. All four additions are released.
>
> Was: draft for the owner. `06` R5.6 to R5.9 were added when the UI roadmap notes were integrated:
> four things the views of R6 need and the engine does not yet give. This note measures what kernel 0.57.1 serves,
> proposes each addition, and lists the decisions. It names no UI product: the kernel serves any client.

## 1. Where things stand

`catalyst serve` (0.53.0, 0.54.0) answers over HTTP, read-only in local mode (`serve --local`, loopback, one project):

| Route | Gives |
|---|---|
| `/v1/graph` | rules, domains, artifacts with their fields, links and mentions, and the module's types |
| `/v1/list`, `/v1/backlog`, `/v1/view/<id>` | the same as the CLI verbs |
| `/v1/journal` | entries, filtered like `journal show` (since, artifact, actor, rule) |
| `/v1/check` | the check report (local mode only) |
| `/v1/events` | a stream: one event after each change |
| `/v1/head`, `/v1/changes`, `/v1/blobs/…`, `POST /v1/have`, `POST /v1/push` | the share driver's side |

What a view cannot get today: what a change to one entity would reach; one list of what waits for a person; the
content of an entity before and after each change; and the page itself from the same server.

## 2. The four additions

| # | Addition | CLI | Route | Built from |
|---|---|---|---|---|
| R5.6 | **Impact closure**: for one ID, what it rests on (upstream) and what rests on it (downstream), transitively, each with the path that links it | `catalyst impact <id> [--up\|--down] [--depth N] [--json]` | `/v1/impact/<id>` | the graph's links: reference fields, derived fields, a rule's domain |
| R5.7 | **Decision requests**: one list of what waits for a person, each with its evidence and the verb that settles it | `catalyst inbox [--json]` | `/v1/inbox` | `unrecorded` (adopt or revert), open `RECON-` cases (`reconcile`), analyses awaiting a decision (`analysis decide`), check errors that name their fixing verb |
| R5.8 | **The page from the same server**: static files served beside the API | `catalyst serve --local --static <dir>` | `/` | a directory given by the caller; the kernel ships none |
| R5.9 | **History of one entity**: its journal entries with the content before and after | `catalyst journal show --artifact <id> --content` | `/v1/history/<id>` | the journal's blob hashes, read from git (the pinned blobs) |

All four are read-only and need no new stored state. Each has `--json`, tests, and the same answer from the CLI and
the server.

## 3. What stays out

* **Writes over HTTP in local mode.** A board that moves a card (R6.11) or an inbox that settles a case (R6.4) must
  run `status set`, `journal adopt` or `reconcile`. Today a client runs the CLI for that. Serving writes locally
  raises the trust questions of `09` §4 (a user gesture, workspace trust); it is a separate decision, after the
  read side proves itself.
* **Token usage and streamed agent output** (R5.5): another item.
* **Schemas** (R5.1): the four payloads would be the first ones worth describing in `spec/`; see decision 5.

## 4. Decisions for the owner

1. **Which links count for impact.** Reference and derived fields and a rule's domain (recommended), with *mentions*
   (an ID cited in prose) reported apart as weak links and left out of the closure; or mentions included.
2. **What the inbox holds in its first release.** Unrecorded changes, open `RECON-` cases and analyses awaiting a
   decision (recommended: each already has a verb that settles it). Check errors and artifacts waiting in a state
   (a requirement `Proposed`, say) can follow, since "waiting" there depends on the module's states.
3. **The name**: `inbox` (recommended, the word the views use) or `decisions`.
4. **Static files**: `--static <dir>` given by the caller (recommended: the kernel names no UI and ships no page), or
   a page shipped inside the kernel. With `--static`, the page reads the per-session token from the URL the server
   prints at start; the server keeps to loopback and refuses a foreign `Origin` (`09` §4).
5. **Schemas with them.** Describe these four payloads as JSON Schemas in `spec/` as they are built (recommended: it
   starts R5.1 where it is cheapest), or leave R5.1 whole for later.
6. **Releases**: one per addition (recommended, as for module v3: R5.6, then R5.9, R5.7, R5.8), or one release for
   the four.
