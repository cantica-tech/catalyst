# `entity` — entity definition (v1)

| Field | Value |
|---|---|
| **Entity type** | `entity` |
| **Version** | 1 |

## Description

The base entity represents the foundational, abstract definition gathering all
commonalities shared across all catalyst entity types (such as the active
module's entity types, rules, domains, workflows, users, roles, and
reconciliations).
It defines core commonalities including unique identification, versioning, status
tracking, sign-off provenance, traceability, and a mandatory or canonical **Name** field.
The **Name** field (`**Name**` in metadata tables or rule headings) provides a concise,
human-readable summary or slug (e.g. `password-reset-flow` or `Password Reset Flow`)
that summarizes the purpose of the entity, following the naming standards established in
Rules of Rules. Extending this base entity definition shall automatically extend all other
derived entity definitions across the framework.
