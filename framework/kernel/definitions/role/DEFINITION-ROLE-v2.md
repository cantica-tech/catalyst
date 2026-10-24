# `role` — entity definition (v2)

| Field | Value |
|---|---|
| **Entity type** | `role` |
| **Version** | 2 |

## Description

A role is a role of the provider catalyst-users reaches, composed of grants: `cmd:<command>` for each command it
allows (`cmd:*` for every one) and `reconcile:<level>` for the reconciliation level it gives. People hold roles
directly or through their groups, and their token carries the grants. The deployment's roles template only names a
role and shows it; it grants nothing. Roles are provisioned and changed in catalyst-users
(`catalyst-users roles provision`), never in the criterion.
