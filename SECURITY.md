# Security policy

## Supported versions

catalyst is pre-1.0. Only the latest released version receives fixes.

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub's
[private vulnerability reporting](https://github.com/cantica-tech/catalyst/security/advisories/new)
rather than a public issue. You should get an acknowledgement within a few
days.

## Scope

catalyst is largely instructions that a coding agent follows inside your
repository. Reports we particularly want:

- instructions that could lead an agent to push, publish, delete or leak
  data without the user's explicit assent;
- ways a synced `.criterion/` working copy or a plugin could inject
  instructions into another contributor's agent session;
- scripts in `scripts/` that write outside the files they document.
