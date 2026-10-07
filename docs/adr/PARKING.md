# ADR Parking Lot (R2–R7 and Beyond)

This document lists architecture decisions expected to emerge in future phases (R2–R7) and post-1.0 evolution. Decisions here are anticipated based on the roadmap but are not yet formally documented.

## R2: Framework CLI Verbs (W1–W5)

As 23 kernel rules + 4 SE rules merge into 16 target CLI verbs, new ADRs will cover:

- **ADR-015: CLI verb design** — How verbs compose rules into commands (e.g., `/create-rule` combines 3 rules)
- **ADR-016: Backward compatibility** — How old prose commands degrade to new CLI verbs
- **ADR-017: Multi-verb workflows** — Workflows spanning multiple CLI verbs (e.g., /start-work → /create-step → /push)

## R3: Migration and Store Transition

New ADRs for the locator-based store and migration from legacy .criterion pointer:

- **ADR-018: Migration strategy** — How existing deployments transition from pointer to locator (in-place, parallel, or staged)
- **ADR-019: Store backward compatibility** — Read-only vs. read-write access to old-format deployments
- **ADR-020: Multi-repo criterion** — How shared .criterion symlinks evolve when repositories move

## R4: Plugins and Role-Based Access

As plugins stabilize and multi-team deployments scale:

- **ADR-021: Plugin versioning** — How plugins declare and check compatibility with kernel versions
- **ADR-022: Role-based command filtering** — How the CLI hides verbs from users without permission
- **ADR-023: Cross-team audit trails** — How deployments shared across teams maintain audit isolation

## R5: New UIs (SPA, Desktop, VS Code Thin)

As new user interfaces replace the CLI as the primary entry point:

- **ADR-024: UI-agnostic data model** — How UIs access rules, workflows, and artifacts without direct file access
- **ADR-025: Real-time sync protocol** — How UIs stay synchronized with the criterion working copy
- **ADR-026: Conflict resolution in multi-user UIs** — How concurrent edits (two users, one rule) are handled

## R6: Deployment Registry and Discovery

As catalyst scales to multiple organizations and projects:

- **ADR-027: Deployment registry schema** — How deployments advertise themselves (name, module, rules, team)
- **ADR-028: Cross-deployment rule imports** — How one deployment's rules reference another's
- **ADR-029: Team federation** — How multiple teams share governance across deployments

## R7: Observability and Compliance

Post-release infrastructure for production deployments:

- **ADR-030: Metrics and instrumentation** — What catalyst emits (rules executed, workflow states, user actions)
- **ADR-031: Compliance audit log format** — Structure of immutable audit logs for regulatory requirements
- **ADR-032: Alerting on rule violations** — How deployments notify when rules are broken or rules change

## Post-1.0: Long-Term Evolution

Design decisions deferred beyond R7:

- **Multi-module UI composition** — How the new UIs let users switch between multiple modules
- **LLM-assisted rule writing** — How AI helps generate or refine rules from natural language
- **GraphQL API** — Alternative query interface for programmatic rule access
- **Mobile/offline support** — How catalyst works without continuous network connectivity

## Adding to the Parking Lot

When a new design question arises:

1. Create a descriptive title (e.g., "CLI verb design for rule merging")
2. Add it to the appropriate phase section above
3. Link from related code, migrations, or issues
4. When the decision is made, create the actual ADR file and move it to [README.md](README.md)

## See Also

- [README.md](README.md) — Accepted and pending ADRs (R0–R1)
- `framework/kernel/migrations/0.46.0/` — Detailed phase planning documents
- Roadmap: `/roadmap-*` or `.criterion/development/ROADMAP.md`
