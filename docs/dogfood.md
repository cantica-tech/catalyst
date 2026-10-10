# `/dogfood` — vetting catalyst against its own rules

Catalyst-development only: the procedure `.claude/commands/dogfood.md` runs in this repository. It is never part of
what a deployment receives (moved out of the deployed handbook, ADR-018; it was `rr-META-018` and the `/dogfood`
part of `rr-META-013`).

## The base check

`/check-rules` plus a four-eyes drift check: whether catalyst's actual state still matches what its own rule
document claims — for each existing rule, is the cited evidence still accurate. It reports and never fixes. After a
run that ends clean, or with fixes applied and reverified, **offer** to share the result — `/share push` if the
deployment is shared, `/share create` otherwise — and never run either without the user's yes (law L3).

## The recreation drift check: `/dogfood recreate`

The base check cannot catch an invariant or law that was added but never retrofitted into any rule: there is nothing
existing for it to evaluate. `recreate` re-derives coverage independently, blind to the live rule document, and
compares. Opt-in and expensive (a full, careful codebase read): run it before cutting a release, not every time. It
audits the last **committed** state (a git worktree).

### The isolated agent

One agent, spawned with `isolation: "worktree"`. The criterion lives in catalyst's home, outside the repository, so a
worktree has no path to it — but isolation alone is not enough; the agent's prompt states explicit prohibitions:
never run `catalyst where`, `catalyst open` or any command that resolves the criterion; never read anything under
`$CATALYST_HOME` or `$HOME/.catalyst`; never read a `.criterion` in any form; never consult `git log` or commit
messages — current file content only.

The prompt is **hand-authored and self-contained**, never this procedure's text forwarded: naming the live rule
document's path would leak exactly what blindness hides.

**Deliverable:** for each law and invariant in `framework/kernel/INVARIANTS.md`, found or not found, with evidence — a
`file:line` citation, or "behavioural, not machine-checkable". A coverage judgment per item, not a rewritten rule
document.

### Why one agent, not four eyes

`ANALYSIS-PLAYBOOK.md` uses four eyes for extracting what exists in code; here the second opinion already comes from
comparing the isolated agent's findings with the live deployment, so a second blind agent only doubles the cost of a
periodic check. A one-time bootstrap (`INSTANTIATION-GUIDE.md` §4) keeps the full four-eyes process.

### Comparison

By the orchestrating session, after the agent returns — comparing two finished documents needs no blindness. A
judgment-based read, never a string search for `INV-N`: rules often cite a line of `INVARIANTS.md` rather than the
label, and line numbers drift. Two outcomes per item, of equal severity:

- the isolated agent found evidence, but no live rule covers the item;
- a live rule claims coverage, but the isolated agent found no evidence.

Report only; never fix automatically.
