# 33 — Landing: how a non-admin's change reaches the criterion's repository (design for the owner, 2026-10-25)

> **Status: decided (owner, 2026-10-25), all six of §9 as recommended.** Phase 1 built in kernel 0.116.0 (REQ-000099, §10). Builds on designs `19` (`catalyst serve`), `25`
> (approval gates), `26` (proposals), `29` (grants from catalyst-users), `30` (the server as the boundary), `31` (who
> changes what) and `32` (membership, no members without a server). It adds no right: who may change what stays `29`
> and `31`'s. It decides how an accepted change becomes commits on the criterion repository's shared branch.

## 1. The request

- A person who is not an admin changes a project's criterion in one of two ways: their **catalyst session** (an agent
  working for them) creates or updates entities as the work happens, or they **create or update entities
  explicitly** (a UI, the CLI), within their grants.
- Either way the change must reach the criterion's git repository, by a process each project defines.
- That process is defined in **one JSON document**, with **one standard process as the default**, and chosen during
  the project's onboarding, at the same step as its roles.

## 2. Today

| What                      | Who, and how                                                                                                                                                                                                                                                                   |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Every write               | A catalyst verb (`new`, `edit`, `rename`, `status set`, `link`, `restore`, `propose`), journaled and signed by the identity catalyst-users verifies (L1, `ACCESS-CONTROL.md` §3).                                                                                                 |
| May they make it          | Grants (`cmd:<command>`, `create:<TYPE>`, design `29`), the type's `contributors_create`, linked or not (`31` §4: a linked entity's change is a proposal), approval gates (`IAM/gates.json`, `25`), governing workflows.                                                         |
| The git transport         | `catalyst criterion push`: rebase, check, a topic branch `<user>/<timestamp>`, a pull request; `criterion protect` requires pull requests and the `catalyst` check; the check runs on `pull_request_target` from the base branch. **Admins only**: `30` §5 and `32` §2.10 keep non-admins off clones. |
| The served transport      | Non-admins' CLI, agent and UI are clients of `catalyst serve`, which applies a push all or nothing, the signer being the token's person (`19` §3). The server's truth is **its own database**: nothing it accepts reaches the git repository (`19` §10, S4 `share export --git` not built). |
| Agent and person          | The journal names the actor and the command, not whether an agent made the change or the person did.                                                                                                                                                                         |

**The gap.** A non-admin's change is accepted by the server and stays there: the criterion's repository, every
admin's clone and the CI gate never see it. And nothing says, per project, how changes should land: one pull request
per change or per session, who reviews, when one merges itself.

## 3. The model: the server lands for them

```mermaid
flowchart LR
    S["catalyst session<br/>(the person's agent)"] -->|verbs, via: agent| SV
    P["the person, explicitly<br/>(UI, CLI)"] -->|verbs, via: person| SV
    SV["catalyst serve<br/>grants, gates, workflows,<br/>visibility: accepted"] --> Q["held batches<br/>(the server's database)"]
    Q -->|IAM/landing.json:<br/>group, branch, review| PR["topic branch + pull request<br/>on the criterion repository"]
    PR -->|catalyst check (CI)<br/>+ review the policy asks| M["shared branch<br/>(criterion)"]
    M -->|criterion sync| A["admins' clones"]
    M -->|pull| SV
```

1. **Non-admins never get write access to the repository.** It stays readable and writable by admins only (`30`
   §5). The server writes to it with **its own credential**: a deploy key or a GitHub App installation, scoped to
   that one repository.
2. **Accepting and landing are two steps.** Accepting is today's: the server checks the signer, grants, gates,
   workflows and visibility, and refuses a change with nothing applied. Landing is new: each accepted batch is
   **held**, then turned into commits on a topic branch and a pull request as the project's landing policy says.
3. **The signature is the person's, the commit is the server's.** The commit's author is the server's identity; each
   commit carries a `Signed-off-by:` trailer per signer, and the journal entry it holds is the person's, verified when
   it was made (`ACCESS-CONTROL.md` §4: a signature is verified where it is made). Nothing is re-signed.
4. **Each change records how it was made**: the journal entry gains `"via": "agent" | "person"`. A verb run through
   `catalyst mcp` or `catalyst agent run`, or under the agent's hooks, is `agent`; a verb from a UI or a terminal is
   `person`. The policy may treat the two differently.
5. **Merging follows the policy, never the agent's judgment** (L4). A pull request that falls behind is rebased by the
   server (the union merge of the journal and indexes, as `criterion push` does). A real conflict stops the landing and
   opens a `RECON-` case for a human. The server never resolves one.
6. **Admins are unchanged.** They keep their clones and `criterion push`. A policy may also route their changes
   (§4, `who`), but by default it governs non-admins and the server's own writes (`32`'s fingerprints).

## 4. The document: `IAM/landing.json`

One file per criterion, beside `gates.json`, with a schema in the kernel (`schemas/landing.schema.json`). **No file
means the standard policy**, so every project has a landing process from its first day.

- **`target`**: where changes land: `"git"` today; the shared branch and the server's credential name
  (`credential`), never the secret itself.
- **`rules`**: an ordered list. **The first rule that matches a held change decides how it lands.**
  - **match**: `via` (`agent`, `person`), `who` (roles from catalyst-users), `change` (`unlinked`, `linked`,
    `proposal-accepted`, `server`), `types`.
  - **`group`**: what one pull request carries:
    - `change`: each batch alone;
    - `session`: everything one agent session pushed, landed when the session ends (its Stop hook), or after
      `idle_minutes`;
    - `window`: everything held, every `minutes`.
  - **`review`**: who must approve before merging: `none`, or a number of approvals from a role, and where: `catalyst`
    (in the inbox, `catalyst approve` on the batch, the role from catalyst-users) or `host` (the pull request's
    reviews, which only admins can give, since only they reach the repository).
  - **`merge`**:
    - `auto`: the server merges once the `catalyst` check passes and the review holds;
    - `admin`: an admin merges by hand.
- **`default`**: the rule for a change that no rule matches.

**`catalyst` review is the default**: it works with any git host, needs no repository account for the reviewer, and
keeps the provider as the one authority on who may approve.

### 4.1 The standard policy (the default)

```json
{
  "$schema": "https://github.com/cantica-tech/catalyst/framework/kernel/schemas/landing.schema.json",
  "policy": "standard",
  "target": { "kind": "git", "branch": "criterion", "credential": "serve-landing" },
  "rules": [
    {
      "id": "server-own",
      "match": { "change": "server" },
      "group": "change",
      "review": "none",
      "merge": "auto"
    },
    {
      "id": "agent-session",
      "match": { "via": "agent" },
      "group": { "by": "session", "idle_minutes": 30 },
      "review": { "where": "catalyst", "approvals": 1, "role": "Criterion Admin" },
      "merge": "auto"
    },
    {
      "id": "explicit-unlinked",
      "match": { "via": "person", "change": "unlinked" },
      "group": "change",
      "review": "none",
      "merge": "auto"
    },
    {
      "id": "accepted-proposal",
      "match": { "change": "proposal-accepted" },
      "group": "change",
      "review": "none",
      "merge": "auto"
    }
  ],
  "default": {
    "group": "change",
    "review": { "where": "catalyst", "approvals": 1, "role": "Criterion Admin" },
    "merge": "auto"
  }
}
```

What it means:

- **The server's own writes** (fingerprints) land at once: the green check is enough.
- **An agent session's changes** land as one pull request per session, approved by a Criterion Admin. This is the
  "four eyes on what an agent did" the laws ask for, at one approval per session rather than per entity.
- **A person's explicit change to an unlinked entity** lands at once: they made it themselves, within their grants,
  and it touches nothing else (`31` §4.2).
- **A linked entity's change** is already a proposal (`31` §4.2): its review is the governing workflow's. Only the
  accepted result lands, without a second review.
- **Anything else** waits for a Criterion Admin.

### 4.2 Other policies a project may choose

| Policy       | Differs from standard                                                                                      | For                                          |
| ------------ | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| `open`       | every rule `review: none`, `merge: auto`; still one pull request per change and the check required          | a small trusted team, an internal knowledge base |
| `reviewed`   | every rule reviewed, explicit changes included; `group: window`, 60 minutes                                 | regulated work, a public criterion           |
| `host`       | review `where: host`: the pull request's own reviews, `merge: admin`                                       | a team that already reviews on GitHub        |

A project names one as `"policy"` and overrides any rule. A named policy is the kernel's template
(`templates/landing.<policy>.template.json`), copied at onboarding, then the project's own: `/sync-framework` never
changes it (L6, as for `gates.json`).

### 4.3 What `catalyst check` adds

- the schema; every role, type and credential name known;
- a project with members other than admins (`32`) has a server with a landing credential;
- `merge: auto` on a protected branch: the server's credential may merge (a GitHub App that is not admin, so
  protection still binds it);
- `review` naming a role no one holds: a warning (nothing would ever land).

## 5. Onboarding: roles and landing as one step

The checklist's identity step (`INSTANTIATION-CHECKLIST.md`) becomes **"people, roles and landing"**, worked
together because each depends on the other: who reviews is a role, and whether members exist decides whether landing
needs a server.

1. `catalyst-users roles provision` (the roles) and `catalyst-users criteria add <name> --admin <admin>` (the admins
   and members groups).
2. **Choose the landing policy**: `catalyst landing init [--policy standard|open|reviewed|host]` writes
   `IAM/landing.json`, journaled. The agent asks the user which one, showing §4.1's table and recommending
   `standard`.
3. `catalyst criterion protect --yes`: pull requests and the `catalyst` check required.
4. When the project has members other than admins: `catalyst serve key init`, then `catalyst serve landing connect
   <repository>` installs the server's credential (a deploy key or a GitHub App) and checks it can push a topic
   branch and open a pull request.
5. `catalyst check`: §4.3's findings clear.

A project without a server still gets the file. It has admins only (`32` §2.10), so only `server-own` and the admin
path apply, but the day it gains members, the process is already decided.

## 6. Worked example

bob is a Developer in `catalyst-users`, not an admin; alice is its Criterion Admin.

1. bob's agent session creates `REQ-000013` and two `STEP-`s: three batches, `via: agent`, accepted by the server and
   held.
2. bob explicitly retitles `TEST-000004`, which nothing links to: `via: person`, `unlinked`. Rule
   `explicit-unlinked`: the server opens `bob/20261026T091503Z`, the check passes, and it merges. alice's next `criterion
   sync` brings it.
3. bob's session ends. Rule `agent-session`: one pull request, `bob/session-20261026T0840Z`, holding the three
   batches. alice's inbox shows `landing · bob's session · 3 changes`, with the diff. She approves it (`catalyst
   approve` on the held session), the check passes, and the server merges it.
4. Meanwhile carol had changed `REQ-000013`'s domain. The rebase stops on `REQ-000013`: nothing merges, and
   `RECON-000021` is opened for alice. bob's batches stay held until she decides.

## 7. What changes in the rules

- An invariant beside `rr-META-013`: **"a non-admin's change lands only through the server, by the project's
  landing policy; the server never merges what the policy does not allow nor resolves a conflict."** This touches the
  frozen prose surface, so it needs an ADR lifting the freeze for it (ADR-017).
- L3 is unchanged in wording: the person's yes is given when they push to the server (`19` §3, preview then
  `--yes`). The server's landing is the Admin's yes, given once at onboarding by choosing the policy (§9, decision 1).
- Approving a landing is a new gate kind in `ACCESS-CONTROL.md` §1, under the same rule as every gate: never by the
  change's author.

## 8. Phases

1. **`via`** in the journal entry, and `IAM/landing.json` with its schema, templates, `catalyst landing init` and
   `check`. No landing yet.
2. **The server lands**: held batches, the credential (`serve landing connect`), topic branches and pull requests,
   `group: change`, `merge: auto`, a rebase stopped by a conflict turned into a `RECON-` case. This is `19`'s S4 in
   another form.
3. **Review in catalyst**: the inbox's `landing` kind, `catalyst approve` on a held batch, `group: session` (the
   Stop hook tells the server a session has ended) and `window`.
4. **`host` review** and the other templates; the onboarding checklist's combined step.

## 9. Decided (owner, 2026-10-25), as recommended

1. **The server lands without asking each time**: choosing the policy at onboarding is the Admin's assent (L3) to
   every landing it allows, and the choice is journaled as that assent.
2. **An agent session is reviewed once per session**, not per change, in the standard policy.
3. **A person's explicit change to an unlinked entity** lands without review in the standard policy: `31` already
   lets them make it directly.
4. **The server's credential**: a GitHub App on GitHub (scoped, not a person, bound by protection), a deploy key on
   other hosts.
5. **Where reviewers act**: catalyst's inbox by default, the host's pull request as an option.
6. **`via` is in every journal entry**, a format change shipped with its migration (B6): it is history worth
   keeping.

## 10. As built (phase 1, kernel 0.116.0)

- **`via`** is set in `journal.write` for every entry: `CATALYST_VIA` when it says `agent` or `person`, else `agent`
  when `AI_AGENT`, `CLAUDECODE` or `GEMINI_CLI` is set, else `person`; `catalyst mcp` and `catalyst agent run` set
  `CATALYST_VIA=agent` for what they run, and the server's fingerprint entry says `server`.
- **The policies** are kept in `scripts/catalyst/landing.py` (`POLICIES`), held equal to
  `framework/kernel/templates/landing.<name>.template.json` by a test; `catalyst landing init` writes one, so the CLI
  needs no kernel checkout.
- **`landing init`** is an admin's (`cmd:*` or the `Admin` role) and journals the choice as a `chore`, naming it the
  Admin's assent; `--force` replaces an existing file.
- **`check`**: `landing:` errors for the file; a warning only for a criterion shared through a server with no
  `target.credential` (whether it has members is the server's, design 32, so the warning covers every served one).
- **Onboarding**: step 6 of `INSTANTIATION-GUIDE.md` §1 and its checklist item.
