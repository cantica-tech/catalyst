# 27 — Impact simulation: try a change on a scratch copy, see what it breaks (draft for the owner, 2026-10-17)

> **Status: draft, for the owner's decision (§7).** Asked for by the Studio's roadmap (R6.47 in the UI repository's
> `24`): "try a change on a scratch copy, see what breaks, then apply". Uses `check`, `impact` (R5.6) and, for
> proposals, [`26`](26-proposals.md).

## 1. Today

Before a change, catalyst can say what *depends* on an entity (`catalyst impact <ID>`: what it reaches up and down
the chain), and a verb refuses what it knows to be wrong (a transition the workflow does not allow, a guard, a gate).
What it cannot say is what the change *would do* to the rest of the record: which `check` findings it adds or clears,
which index or back-reference it moves, which gate it would make wait. The only way to know is to make the change and
run `check`, then undo it with another journaled change (`restore`), which leaves both in the journal for good.

## 2. `catalyst try`: one change, made on a copy

```
catalyst try <verb> <its arguments…> [--json] [--keep]
catalyst try --proposal <RECON-id> [--json] [--keep]
```

1. **A scratch copy** of the criterion is made under `$CATALYST_HOME/scratch/<project>-<time>/`, outside the project
   (law L5): a detached `git worktree` of the criterion's HEAD, so the journal's blobs are there, with the criterion's
   files as they are now copied over it — uncommitted changes and new files included, never its `.venv` or `bin/`.
   The copy is loaded as a bare working copy (`load_working_copy`), as `catalyst serve` reads one. The worktree is
   removed when the try ends, and `git worktree prune` clears one a crash left behind; nothing is ever committed in
   it.
2. **`check` runs on the copy** before the change: the baseline.
3. **The change is made on the copy**, with the real verb and its real refusals: `status set`, `new`, `link`,
   `rename`, `restore`, `approve`, `reconcile`, or a proposal's `accept` (`26`). It journals inside the copy, never
   in the criterion. A refused change is the answer: `try` prints the refusal and exits `1`, as the verb would.
4. **`check` runs again**, and `impact` on the entity changed.
5. **The difference is reported**, then the copy is deleted (kept with `--keep`, for a person to look inside).

Nothing in the criterion or the project changes; the journal holds nothing of a try. Making the change for real is
running the same verb without `try`, or accepting the proposal: one path for every write (law L1), so what was tried is
exactly what is then done.

## 3. What it reports

```json
{
  "change": "catalyst status set REQ-000004 Done",
  "ok": true,
  "refused": null,
  "files": [{ "path": "requirements/REQ-000004-….md", "before": "<blob>", "after": "<blob>" }],
  "check": {
    "added": [{ "level": "error", "text": "…", "entity": "STEP-000009" }],
    "cleared": [{ "level": "warning", "text": "…", "entity": "REQ-000004" }]
  },
  "impact": { "…": "what `catalyst impact <ID> --json` gives for the entity changed" },
  "gates": [{ "id": "REQ-000004", "gate": "req-done", "missing": 1 }]
}
```

- `files`: every file the change wrote, with its blob before and after (indexes and back-references included), so a
  client shows the diffs with the same content as `history`.
- `check`: the findings the change adds and the ones it clears, each with its entity (`check --json` findings,
  kernel 0.78.0), compared as text; findings present before and after are left out.
- `impact`: the trace of the entity changed, for "what else this reaches".
- `gates`: what the change would leave waiting for an approval (`25`): a gated rule's new text, an entity that lands
  one move from a gated state.

The payload gets its schema (`spec/try.schema.json`); the text output says the same in a few lines.

## 4. Cost and limits

Measured on catalyst's own criterion (2026-10-17): the worktree and the copy of its current files take under half a
second, and `check` on the copy about one second, with no error, as on the criterion (its project-side warnings left out,
§4's first limit). A plain copy
without `.git` does not work: the journal's checks need the criterion's git objects, and on such a copy `check`
reports every journaled blob missing (2,285 errors on that criterion). Two things are not simulated: the project side of `check` (unrecorded
changes in the product repository, which no criterion change affects), and sharing (a try never pushes). A change
that depends on time (`restore --to <time>`) runs against the copy's journal, which is the criterion's.

## 5. In the Studio

Wherever the Studio offers an action through its host (W1) — a board move, a restore, a proposal's acceptance — it
can offer **Try it** first: the host runs `catalyst try <the same action> --json`, and the Studio shows the findings
added and cleared, the files' diffs and the gates that would wait, then **Do it** runs the real action with the
host's confirmation. The action's fields are checked exactly as for the real action (studio-SHELL-000016), since they
become the same arguments.

## 6. What it is not

Not a sandbox for the product's code: only the criterion is copied. Not a preview that can drift from the real thing:
the real verb runs, with its real refusals, on a real copy. Not a way to apply a change: a try leaves nothing behind.

## 7. Choices to confirm

1. **The name**: `catalyst try <verb …>` (recommended: it reads as what it does), or `catalyst simulate`.
2. **The scratch copy is a `git worktree` with the current files copied over it** (recommended: the journal's blobs
   are there, and so are uncommitted and new files), or a `git clone --shared` of the criterion with the same overlay
   (no worktree entry in the criterion's `.git`, a few more milliseconds).
3. **No `--apply`** (recommended: the real verb, run after, is the only write path), or `try --apply` replaying the
   change.
4. **In the Studio, Try it needs no confirmation dialog** (recommended: it changes nothing the person owns, only a
   scratch copy under `$CATALYST_HOME`), or every host run is confirmed, Try it included.
5. **What can be tried at 1.0**: catalyst's writing verbs and a proposal's acceptance (recommended), or also an
   arbitrary file edit (`--file <path>=<content>`), which a proposal (`26`) already covers.

## 8. Steps once confirmed

| Step | Content |
|---|---|
| T1 | The scratch copy (a worktree with the current files over it, loaded as a bare working copy, removed or kept, pruned after a crash); `catalyst try <verb …>` for the writing verbs; the before/after `check` difference and the files written |
| T2 | `impact` and `gates` in the report; `spec/try.schema.json`; `CLI.md` |
| T3 | `try --proposal <RECON-id>`, once proposals exist (`26` P2) |
| T4 | The Studio (UI repository, R6.47): Try it beside each host action, the difference shown, then Do it |

About 2–3 kernel sessions (one release; T3 with the proposals), then 1–2 for the Studio.
