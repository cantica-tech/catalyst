# Rules of Work Items — template

> Copy to `{{WORK_ITEMS_DIR}}/rules-of-work-items.md` and resolve every
> `{{PLACEHOLDER}}`. See [`INSTANTIATION-GUIDE.md`](INSTANTIATION-GUIDE.md).

Standards for the agile process layer — epics, stories, tasks, spikes,
sprints (or your methodology's equivalents; see the "Agile-methodology
agnostic" note in the framework [`README.md`](README.md)). Sits above
`CODE-OF-CONDUCT.md`, which sits above
`{{RULES_DIR}}/Rules-of-Rules.md`. Work items never bypass that chain.

```
EPIC ─▶ STORY ─▶ TASK           (agile layer — this document)
          │
          ▼
       <PREFIX>-NNNNNN          (the active module's rule-linked work)
          │
          ▼
       rule IDs                 (documented behavior)
```

---

## 1. A story is not a substitute for a development artifact

Every `STORY-NNNNNN` links to exactly one grounded development artifact of
the active module (`<PREFIX>-NNNNNN`). That artifact owns rule targets,
conflict checks, and new-rule proposals. The story is the sized, scheduled
slice of that same work.

If a story has no development artifact yet, create one before pulling the
story into a sprint/iteration. (A non-grounded planning entry of the active
module may motivate a story too, but it never substitutes for the grounded
artifact — it isn't rule-linked.)

## 2. Tasks inherit their parent story's rule target

A `TASK-NNNNNN` never gets its own rule target — it inherits its parent
story's. If task-level work needs a rule the story doesn't cover, fix the
story's development artifact first rather than letting scope creep in unreviewed.

## 3. Spikes exist to produce rules or estimates, not code

A `SPIKE-NNNNNN` is time-boxed and never itself "implements" anything. Its
outcome is a new rule proposal (handed to a development artifact of the active module), an
implementation approach, or a go/no-go decision. A spike that ships
production code has stopped being a spike.

## 4. Epics are decomposition, not a fourth rule namespace

An epic names the `DOMAIN` code(s) it spans and groups child stories. It
never targets a rule directly. "Done" means all child stories are done.

## 5. Iteration containers schedule work items; they don't reclassify them

Whatever container your methodology uses (`SPRINT-NNN`, `BOARD-NNNNNN`,
etc.) holds `STORY-`/`TASK-`/`SPIKE-` IDs as-is — it never restates
acceptance criteria or rule targets. Retro/review action items that imply
a process change get filed as a development artifact of the active
module, not left as an untracked note.

## 6. Boards are Kanban/Scrumban's container, not Scrum's

A `BOARD-NNNNNN` is the Kanban-flavor structural counterpart to
`SPRINT-NNN` (§2 of `INSTANTIATION-GUIDE.md`): a trackable container,
`Status` of `Active`/`Archived`, that stories/tasks reference instead of
sprint membership. A pure-Scrum deployment has no need for it, the same
way a pure-Kanban deployment has no need for `sprints/` — pick the one
your flavor actually uses, not both by default.

> `WORKFLOW-NNNNNN` used to be part of this schema. It's now a core
> type — always present, no plugin required — see `Rules-of-Rules.md`
> §19 and `INVARIANTS.md` INV-24.

## 7. Tickets are a plugin-territory slot, not a core work-item type

`tickets/` is scaffolded like every other artifact type (`Rules-of-Rules.md`
§15) but core catalyst defines no `TICKET-NNNNNN` semantics, no `/create-ticket`
command, and no lifecycle for it. Its actual population — typically
syncing from or mirroring an external tracker — is the job of whichever
project-management-type plugin is activated for that concern
(`Rules-of-Rules.md` §8, INV-13). If no such plugin is active, the folder
stays empty; that is not a deployment error.

## 8. IDs

Per `Rules-of-Rules.md` §8: `(EPIC|STORY|TASK|SPIKE|BOARD)-NNNNNN`
(6 digits), `SPRINT-NNN` (3 digits), each sequence global within its own
type, never reused. `TICKET-NNNNNN` is reserved but not core-managed (§7
above) — whichever plugin populates it owns its own ID/sequencing
behavior. `WORKFLOW-NNNNNN` has its own global sequence too, but is
core-managed now — see `Rules-of-Rules.md` §19.

## 9. Templates

| Type | Folder | Template |
|---|---|---|
| Board | `boards/` | `templates/board.template.md` |
| Epic | `epics/` | `templates/epic.template.md` |
| Story | `stories/` | `templates/story.template.md` |
| Task | `tasks/` | `templates/task.template.md` |
| Spike | `spikes/` | `templates/spike.template.md` |
| Sprint | `sprints/` | `templates/sprint.template.md` |
| Ticket | `tickets/` | (plugin-provided — §7 above) |

Each folder's template deploys nested and versioned per
`Rules-of-Rules.md` §15 — e.g. `boards/templates/TEMPLATE-BOARD-v1.md`,
not a bare `boards/TEMPLATE-BOARD.md`.
