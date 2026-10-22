# 0.104.0 — Workflow governance

From `0.103.x` to `0.104.0` (REQ-000084).

## What changes

- A condition on an entity's fields (`Classification at least Confidential`) can make a module's guard (`holds`), a
  gate (`when`) or a governing workflow's move depend on a value (`CLI.md`, "Workflow governance").
- A type can declare when its open entities are due (`due`): one past it is listed by `catalyst inbox` as `overdue`,
  with the role it escalates to, and `catalyst check` warns.
- A `WORKFLOW-` can govern a type: `Governs` and `Escalates to` are new optional fields, and its `## Transitions` table
  is enforced while it is `Active`. The workflow template gains them (a new template version).
- Nothing existing changes behaviour: no workflow governs a type until one says so, no type has a due date until its
  module declares one, and a gate without `when` applies as before.

## Steps

1. `catalyst sync apply --kernel <0.104.0>`: the CLI, the runtime and the recomposed documents.
2. **Judgment:** if the deployment keeps `workflows/templates/`, add the kernel's `templates/workflow.template.md` as
   its next version (`TEMPLATE-WORKFLOW-v<N+1>.md`) with a row in its templates catalog, journaled
   (`catalyst migrate --apply` does it).
3. **Judgment, optional:** a workflow that should govern a type gains `Governs`, `Escalates to` and its Transitions
   table, with the owner's agreement, then becomes `Active`; `catalyst check` reports what it names wrongly.
4. `catalyst check`.
