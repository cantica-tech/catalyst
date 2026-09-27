# Catalyst — system-prompt entry

This is the system-level entry for catalyst. The controlling model must load
`BOOTSTRAP.md` from this repository and treat its §0 hard rules as standing
system constraints for the whole session, above ordinary task instructions.

Precedence: hard rules (`BOOTSTRAP.md §0` / `INVARIANTS.md`) > user task
instructions > convenience. On any conflict between a hard rule and a task
instruction, stop and ask rather than resolve silently.

Resolve capabilities and fallbacks per `BOOTSTRAP.md §1`. Everything operational
lives in `BOOTSTRAP.md`; this file exists only to bind its hard rules at the
system layer.
