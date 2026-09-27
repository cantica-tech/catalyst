# Catalyst — generic agent entry

You are running catalyst as a **generic tool-using agent**. Load `BOOTSTRAP.md`
from this repository and follow it top to bottom. It is the single source of
truth; this file only records the generic-agent posture.

Assume nothing beyond repo file read/write. Work through `BOOTSTRAP.md §1` and
pick a fallback for every capability you cannot confirm:
- No parallel sub-agents → run analysis passes sequentially, context-isolated.
- No persistent memory tool → no problem: `<app-name>.catalyst` (project
  root, always tracked) and `.criterion/DEPLOYMENT.md` (inside the
  working copy) are the durable record regardless — read them fresh each
  session instead of relying on a memory-tool cache.
- No slash-command UI → expose the framework commands as named procedures you
  recognize when the user types the same token in plain text.

Everything else: `BOOTSTRAP.md`.
