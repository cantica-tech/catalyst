# Results — 2026-10-26: catalyst-docs phase 6, the realm's search behind catalyst-users

| What                                                                                              | Where                                 |
| ------------------------------------------------------------------------------------------------- | ------------------------------------- |
| [catalyst-kb-engine 0.9.0](https://github.com/cantica-tech/catalyst-kb-engine/releases/tag/0.9.0) | REQ-000010-7TE7wuaB (Active); PR 7    |

1. **`catalyst-kb-engine serve --build <dir>`** answers `GET /search` (passages citing their source, document and
   entity) and `GET /me`, only to a bearer token the realm's provider vouches for, through catalyst-users' FastAPI
   integration: active introspection, the realm's issuer, the `catalyst-api` audience
   (`eng-SEARCH-000003-7TE7wuaB`).
   - Any other token is refused (401), and a provider out of reach refuses too (503).
   - Every person of the realm may search everything, for now (design 01 §10.1).
   - Settings come from catalyst-users' environment. No token or secret is logged or returned, no API description is
     served, and it listens on this machine unless told otherwise.
2. **catalyst-users is used as a library** (0.7.0, the engine's `serve` extra): no change to it was needed.
3. Checks: 10 offline tests with catalyst-users' own token checks, only the provider's introspection replaced:
   - a realm token gets passages (200);
   - another realm's issuer, an outside host, an inactive, another audience's and an expired token are refused (401);
   - no token is refused (401), an unreachable provider refuses (503);
   - the realm check runs before parameter validation.

   ruff, pyright, 88 tests, CI on 3.11 and 3.13.

## Problems

- **The live check is not done.** The service needs the local realm's `catalyst-api` client secret, which Keycloak
  generated. Looking for where it is stored was refused as credential exploration, rightly: the owner supplies it.
  The requirement stays Active until then.

## What's left

- **The live check, with the owner**: a realm token answered, a token from outside the realm refused, on the local
  Keycloak. Then design 01's six phases are done.
- **Search quality**: 12 of 52 questions still missed in hybrid mode (keyword ranking is the next lever).
- **The reference's test fixtures**: a source's import should name what it draws on.
