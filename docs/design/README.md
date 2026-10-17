# Design notes

The design notes behind catalyst's roadmap, moved here from the owner's working notes as each one is checked
(owner decision D2, 2026-10-17), each reworded where it named a product or project built on catalyst. A note keeps the number it was written under, so a number in backticks
(`` `13` ``) names another note: here when its file is in this folder, still in the working notes otherwise.

A note records what was proposed or decided when it was written, with its own status line at the top. Where it
and the code disagree, the code, `framework/kernel/` and `CHANGELOG.md` are right; the note is the reasoning.

| Note | Subject |
|---|---|
| [01a](01a-kernel-concepts-install.md) | The kernel's concepts and its install, inventoried (the analysis behind the roadmap) |
| [01b](01b-kernel-rules-sync-commands.md) | The kernel's rules, sync and commands, inventoried |
| [07](07-ideal-architecture.md) | The ideal architecture: one engine, a protocol, many clients |
| [08](08-criterion-proposals.md) | Where the criterion lives: the proposals compared |
| [13](13-criterion-home-requirement.md) | The criterion's home: `$HOME/.catalyst`, never in the project |
| [14](14-sharing-backends.md) | Sharing backends: git, the server |
| [15](15-agent-adapters-mcp.md) | Agent adapters and the MCP server |
| [17](17-ten-laws-draft.md) | The ten laws, drafted |
| [18](18-handbook-outline.md) | The handbook and the command catalogue |
| [19](19-server-design.md) | `catalyst serve`: the shared server and local mode |
| [20](20-module-v3-design.md) | Module format 3 |
| [21](21-module-install-design.md) | Installing modules |
| [22](22-engine-for-ui-views.md) | What the engine owes a UI's views: impact, history, inbox, a served page |
| [25](25-approval-gates.md) | Approval gates, opt-in: declared in IAM, approvals of a version, enforced by `status set` and `check` (draft) |
