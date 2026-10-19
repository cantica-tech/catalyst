# Results — 2026-10-19: the brand roadmap (R6.21) and R6.29 disabled

R6.21 is now a roadmap of its own, written after a research spike. R6.29 is disabled. Nothing was released: the
work is documents and entities in the UI's repository and criterion.

| What | Where (the UI's repository and criterion) |
|---|---|
| The spike: what, where, who, how | `docs/design/25-brand-spike.md` |
| The `brand` roadmap, 12 items | `development/roadmaps/brand.md`: `RM-000032` to `RM-000043`, registered in `roadmaps.md` |
| The workflow "Brand change" | `WORKFLOW-000001`, Active |
| R6.21 marked rewritten, R6.29 marked disabled | `docs/roadmap.md` |
| Decisions C5 (brand work runs as its own roadmap) and C6 (no module UI code for now) | `docs/decisions.md` |

## 1. The spike

- **What:** ten parts of the brand. The product name (Catalyst Studio, decided but never legally cleared), the CLI
  name, the maker's name, the internal vocabulary, the mark, colours, type, voice and tagline, the brand in the CLI,
  and a guide.
- **Where:** every surface found, across the UI (extension, desktop app, Studio, README), the kernel and modules
  (README, `pyproject.toml`, the badge), GitHub (the organisation's profile and repository descriptions), the
  Marketplace, the distribution repository and the company site.
- **Who:**
  - The owner decides and signs; only the owner is registered in the UI's IAM.
  - Trademark counsel is external and not chosen yet.
  - A designer is external, or Claude drafts.
  - Claude applies the changes.
- **How:** the law first. Of the three outcomes (keep the name, make it distinctive, rename), work that holds under
  any of them can start now. The mark, the tagline in print, the store banner and any filing wait for counsel's
  advice.

Findings worth acting on:

- The extension's flask icon (`catalyst.svg`) has a stock-icon signature (`id="Capa_1"`). Its licence is unknown.
- The UI's README still says the extension is published as "Catalyst framework".
- The UI repository's GitHub description still says "Catalyst UI".
- The kernel's and the process module's repositories have no description at all.
- The maker is spelled two ways: "Cantica Tech" and "CanticaTech".
- Web searches found many uses of "Catalyst" in software (Sony, ETC, Catalyst Development Corporation, catalyst.io,
  Coupa, Catalyst AI, Tailwind, Zoho). None of these searches is a legal clearance.
- The relevant trademark classes are 9 (downloadable software) and 42 (software services). Reported fees, to be
  checked on the offices' own pages: about $350 per class at the USPTO, and about €850 for one class plus €50 for a
  second at the EUIPO.

## 2. The roadmap

The 12 items, all `Not triaged`, in order:

1. The spike (done when you have read it).
2. Legal clearance.
3. Name decision.
4. Asset licence audit and replacement.
5. Colour and type system.
6. Mark and app icon.
7. Voice and tagline.
8. Name consistency sweep.
9. Brand in the CLI.
10. Store and web presence.
11. Brand guide and asset pack.
12. Internal vocabulary (recommended: not now).

The sequence is 1 → 2 → 3 → 6 and 10. Items 4, 5, 7, 8 and 9 can run beside the legal track. Item 11 comes last.

## 3. The workflow

"Brand change" has seven steps: propose (a `FEAT-` citing its `RM-` row), check the law, decide, list every surface,
apply (one `REQ-` per repository), verify, then release and publish with the owner's yes. No change is applied before
the law has answered for anything published.

## 4. R6.29

R6.29 is disabled rather than dropped. D3 holds: a module is data only, and the Studio draws it from `module.yaml`.
It will be revisited if a module needs something `module.yaml` cannot express.

## Problems along the way

- I first set the workflow's status by editing the file. That edit was reverted, and the status was changed with
  `catalyst status set`.
- One journal entry named a command the deployment doesn't have (`/create-workflow`); catalyst warned, and the
  entries after it name `catalyst new`.

## What's left

**The brand roadmap:**

- Choose trademark counsel; that unblocks item 2.
- Items 4, 5, 7, 8 and 9 can start now if you say so.
- Item 7 needs your choice of tagline.

**The UI's roadmap, not done:**

- R6.20, the desktop app: signing, auto-update, bundling `catalyst` with the app, and signing the app inside the
  Windows installer.
- R6.29 is disabled.

**The kernel's roadmap, not done:**

- R4.8 journal hygiene (partly done): short placeholder intents and repeated `/status` entries.
- R4.4 generated docs (partly done): the kernel's prose is still written by hand, which needs a content decision.
- R4.6 unverifiable hard rules (partly done): the role check is still advisory.
- R4.9 N4: module signatures wait for R7's release feed.
- R3.4: `catalyst migrate` was not built (it is optional).
- RM-026, RM-028 and RM-029 of the beta path wait on a trial by a real person.

**Waiting on the owner:**

- A new Marketplace access token, so that UI 0.54.0 can be uploaded.
- The Windows (Azure) and macOS (Apple) signing credentials, a public address for the Linux package's maintainer,
  and the choice of update feed.
- Trademark counsel, and the tagline.

**Not tried by a person:** the Team and Share views in a real host, the desktop installers, and the Copilot and
Gemini CLI adapters with the real CLIs.
