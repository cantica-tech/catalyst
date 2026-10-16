# 14 — Where the shared criterion lives: git, relational, NoSQL (evaluation, 2026-10-08)

> Owner request (2026-10-08): "That remains to be seen: git repo, database, server? It needs to be a light
> implementation, and potentially it should support a git repo, a traditional RDB (down to SQLite) or a NoSQL
> database. Something easy now needs to be available so the work can continue, but those three need to be explored."
> Context: each person's criterion lives at `$HOME/.catalyst/projects/<name>/criterion` (`13`); this document is about
> the **shared copy** several people synchronise through (`13` Q5).

## 1. Facts that drive the choice

* **A criterion is tiny.** Measured today: ~1.1 MB, 218–283 files, ~170 journal entries per project. Volume rules out
  nothing; the choice is about collaboration, offline work and operations, not scale.
* **The truth is the journal.** Append-only, hash-chained entries plus the files they record (`08` Proposal D). Every
  other view (artifacts, indexes, backlog) can be rebuilt from it. A backend only has to store *entries* and *blobs*
  and hand them back in order.
* **Writes are rare and small; reads are frequent.** A person writes a few entries an hour; the UI and agents read
  constantly.
* **Offline matters.** People and agents work on laptops, in CI, on planes. A backend that requires a live server for
  every write breaks the flow.
* **The CLI is stdlib-only** (it runs from a per-criterion venv, `13` §7). SQLite is in the stdlib; PostgreSQL,
  MongoDB and CouchDB clients are not (CouchDB is plain HTTP, so `urllib` is enough).

## 2. One small interface, several drivers

Keep the on-disk format (markdown artifacts + `journal.jsonl`) as the **working form** in
`$HOME/.catalyst/projects/<name>/criterion`, and make sharing a driver behind five operations:

| Operation | Meaning |
|---|---|
| `pull()` | bring the shared entries and blobs the local copy lacks |
| `push(entries, blobs)` | publish local entries; refuse if the chain diverged (then `pull` and re-append) |
| `head()` | the shared chain's last entry hash |
| `lock(scope)` / `unlock` | optional: short-lived write lock where the backend has one |
| `info()` | driver name, location, capabilities |

`catalyst.toml` names the driver: `share = "git"` (with a URL), `"sqlite"`, `"postgres"`, `"couchdb"`, … or none
(local only). Each driver is a few hundred lines; the rest of catalyst never knows which one is used.

## 3. The three families, honestly

### Git repository (what exists today)

* **Fit:** very good. The journal is a file; blobs are git objects already; history, diff and review come free; hosting
  is free (GitHub, GitLab, any server); works offline; backup = the remote.
* **Costs:** merges. Two people appending to one `journal.jsonl` conflict on the last line, and regenerated indexes
  conflict too. Fix: one journal shard per author (append-only files never conflict), indexes never committed
  (rebuilt). Pull requests per change are heavy; direct pushes to the shared branch with the chain check as the gate are
  enough for most teams. Access control is per repository only.
* **Effort:** already built (`catalyst criterion create/push/sync`); needs sharding and the `$HOME` location.
* **Verdict:** **the default now.** Light, proven, no new service.

### Relational database (SQLite → PostgreSQL)

* **SQLite:** stdlib, zero install, one file, transactions, real sequences for IDs, fast queries for the UI. But a
  SQLite file **cannot be shared** safely (not over network drives, not through sync folders: locking breaks). So it is
  either a **local index** (fast reads for views and the UI, rebuilt from the journal) or the storage **behind a small
  server** (`catalyst serve`, one process, HTTP).
* **PostgreSQL:** the real multi-user backend: concurrent writers, row-level access control, managed hosting
  everywhere. Costs: a server to run and back up, a client library (not stdlib) or the `catalyst serve` HTTP layer in
  front, schema migrations, and no human-readable history — review needs the markdown projection exported.
* **Schema:** two tables carry everything — `entries(seq, hash, prev_hash, actor, time, json)` and
  `blobs(sha, bytes)`; artifacts and indexes are views or rebuilt.
* **Verdict:** **SQLite as a local read index: worth doing early** (cheap, speeds the UI and `list`/`view`/`backlog`).
  **SQLite or PostgreSQL behind `catalyst serve`: the natural multi-user server** (decision A2, ~6 months).

### NoSQL (document stores)

* **Document stores (MongoDB, Firestore, DynamoDB):** an artifact maps neatly to a document, but catalyst's value is in
  the **links between** artifacts and in an **ordered, hash-chained append** — neither is what these stores are good at
  (ordering and conditional append need care; transactions are limited or costly). Every one needs a client library
  and a hosted service; vendor lock-in is real. Little gained over SQLite/PostgreSQL.
* **CouchDB (and PouchDB/Couchbase Lite):** the one NoSQL family that fits: plain HTTP + JSON (stdlib `urllib` is
  enough), and **multi-master replication with offline sync built in** — the same model as git (every copy works
  offline, copies reconcile), with conflicts surfaced as documents. Cost: a CouchDB server to run.
* **Verdict:** **explore CouchDB only**, as a spike, if offline-first multi-master sync without git becomes a need
  (non-developer users, mobile). Skip the other document stores.

## 4. Comparison

| Criterion | Git | SQLite (local) | SQLite/PostgreSQL behind `catalyst serve` | CouchDB |
|---|---|---|---|---|
| Works today | **yes** | no | no | no |
| Extra service to run | no (hosting) | no | **yes** | **yes** |
| Offline work | **yes** | **yes** (local only) | queue + sync | **yes** (replication) |
| Concurrent writers | merge (sharded: fine) | n/a | **yes** | yes (conflict docs) |
| Fine-grained access control | repository-level | n/a | **yes** | per database |
| Human-readable history / review | **yes** | no | export needed | no |
| Stdlib client | git CLI | **yes** | HTTP (own server) | **yes** (HTTP) |
| Fits the hash-chained journal | **yes** | **yes** | **yes** | with care |
| Implementation size (driver) | exists | ~200 lines (index) | ~600 lines (server + driver) | ~300 lines |

## 5. Recommendation

1. **Now:** git stays the sharing driver — it works today, so work continues. Two fixes make it light: **journal
   shards per author** (no merge conflicts on append) and **indexes never shared** (rebuilt locally).
2. **Next (cheap, useful even alone):** **SQLite local index** in each criterion, rebuilt from the journal; it makes
   `list`/`view`/`backlog` and the UI fast, and it is the same schema a server will use.
3. **Explore (spikes, one week each, behind the §2 interface):**
   * **`catalyst serve` with SQLite, then PostgreSQL** — the multi-user server of decision A2.
   * **CouchDB** — only if offline multi-master without git is wanted.
4. **Do not build:** MongoDB/Firestore/DynamoDB drivers — no gain over the above for this data.

## 6. Roadmap placement

* R3.2 (store interface): the §2 interface, git driver first (from today's `criterion` code), journal shards (R3.3).
* R3.6 (`git-remote`, required): unchanged, now "the git driver".
* R3.9 (multi-user server): `catalyst serve` over SQLite, PostgreSQL optional; the SQLite local index lands first
  (it can ship before R3.9).
* New spike, after R3.9: CouchDB driver, decision then.
