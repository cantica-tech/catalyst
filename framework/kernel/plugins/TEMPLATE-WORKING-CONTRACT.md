# TEMPLATE-WORKING-CONTRACT

Use this template to define the working contract for a plugin.

## Metadata

Every plugin must carry these six fields — this is the minimum metadata
`CODE-OF-CONDUCT.md` §4 requires, and the framework reads the `Active`
field at startup to decide which plugins to load into memory. Generate the
UUID once, when the plugin is first defined, and never change it afterward.

- Name: <plugin-name>
- Description: <one-line description of what the plugin does>
- UUID: <generate a UUID once; never change it afterward>
- Version: <the plugin's current version, matching its own version.txt>
- Active: <true|false — whether the framework should load this plugin into memory at startup>
- Type: <plugin type, e.g. repository>

## Purpose

- Describe the plugin's purpose and the repository capability it provides.

## Scope

- List the functional area(s) this plugin covers.

## Contributes

Optional — only for a **content-contributing plugin** (`Rules-of-Rules.md`
§17, INV-22): one that deploys artifact-type folders and/or slash
commands into the target project on activation, rather than only
running a background service. Omit this section entirely for a plugin
that doesn't contribute deployable content.

- Artifact-type folder(s): `<name>` — templates resolve from
  `<this plugin's own repository, or a named prototype schema under
  plugins/_prototyping/ while this plugin hasn't graduated out of it>`.
- Command file(s): `<name>.md`, ... — deployed into the target
  project's `.claude/commands/`.

Deactivation removes exactly this content; it never touches artifact
instances the deployment already created with it.

## Responsibilities

- Describe what the plugin is responsible for.

## Constraints

- Describe any limitations, dependencies, or safety constraints.

## Activation requirements

- State whether the plugin requires explicit activation before use.
