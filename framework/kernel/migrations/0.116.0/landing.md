# 0.116.0 — Landing, phase 1: how each change was made, and how changes will land

From `0.115.0` to `0.116.0` (REQ-000099, design 33).

## What changes

- Every journal entry catalyst writes carries `via`: `agent` (made in an agent's session), `person`, or `server` (a
  server's own entry); fw-STRUCTURE-000022. An entry written before has none, and none is rewritten (L7). A reader
  that ignores unknown fields is unaffected (`FORMAT.md` §7).
- A criterion declares how its changes land, `IAM/landing.json` (fw-STRUCTURE-000023): the kernel's `standard` policy
  when absent. `catalyst landing init` chooses one, `catalyst landing show` says which applies, `catalyst check`
  validates it. Nothing lands through it yet (design 33's phase 2).

## Steps

1. `catalyst sync apply --kernel <0.116.0>`: nothing else is mechanical. A criterion without `IAM/landing.json` has the
   `standard` policy.
2. **Judgment, with the user:** choose the landing policy (`standard`, `open`, `reviewed`, `host`; design 33 §4),
   recommending `standard`, and run `catalyst landing init --policy <chosen>` as an admin. Its journal entry is the
   Admin's assent to every landing the policy allows.
