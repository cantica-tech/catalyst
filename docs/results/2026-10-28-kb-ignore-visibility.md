# Results — 2026-10-28: the container's builder may ignore visibility (catalyst-kb-engine 0.14.0)

The owner asked for a flag to ignore visibility in catalyst-kb-container's `build-kb.sh`, which read public
repositories only.

| What | Where |
|---|---|
| catalyst-kb-engine 0.14.0: REQ-000015 (`eng-PUBLISH-000001` amended), STEP-000020; BUG-000003 (`eng-SOURCE-000002`) | `cantica-tech/catalyst-kb-engine` #12, tag `0.14.0`; criterion PR #20 (waits on approval) |
| catalyst-kb-container: `-I`, engine 0.14.0 | `cantica-tech/catalyst-kb-container`, development (`b672814`) |

## 1. `build-kb.sh -I`

- A private repository, or one whose visibility cannot be confirmed, is read instead of refused. On the host it is
  cloned from the URL given, with the person's own git credentials (ssh keys, credential helper); in the container
  over https, with the GitHub sign-in and `AZURE_DEVOPS_EXT_PAT`, which the entry point gives git in its environment
  only (nothing written).
- Visibility is not skipped, only no longer a refusal: each repository's is still checked and recorded in
  `sources.json`. A private one makes the knowledge base `Internal`: every document in it, public ones too (the
  knowledge base's classification is a floor), and both builds. Copilot may then embed `Internal` text: that is what
  the flag consents to.
- Without `-I` nothing changes. A public checkout read in place must still hold nothing uncommitted or unpushed.

## 2. The engine

- REQ-000015: `read-sources --sources` without `--public-only` reads a list naming private sources (recorded `Private`,
  or with no visibility for their host to tell); with `--public-only`, and in `publish-check`, such a list is refused
  as before.
- BUG-000003, found while doing it: the anonymous visibility read (0.13.0) cleared git's configuration files but not
  git configuration given in the environment (`GIT_CONFIG_COUNT`/`KEY`/`VALUE`, `GIT_CONFIG_PARAMETERS`), so a
  credential or `url.insteadOf` there could make a private repository read as public — exactly how the container now
  passes sign-ins. It drops them; its test fails before the fix and passes after.

## Checks

- Engine: 128 tests, ruff; CI green on #12 (both commits).
- Host: the private catalyst-kb-container refused without `-I`; with it, cloned with the owner's credentials, 3
  documents, 33 chunks, all `Internal`; mixed with a public Azure DevOps repository given as an ssh URL, 6 documents,
  49 chunks, all `Internal`.
- Container (x86_64 image at 0.14.0): the same private repository given as `git@github.com:…`, refused without `-I`;
  with it, cloned over https with the GitHub sign-in, 3 documents, 33 chunks, `Internal`.

## What's left

- The owner: merge criterion PR #20 (catalyst-kb-engine's) and PR #19 if still open; catalyst's journal PR for this
  note.
- Not tried: a private Azure DevOps repository with a token (no token here), in the container or on the host.
- The aarch64 image at 0.14.0, deferred by the owner.
- Signed as the system account: nobody was logged in to the local Keycloak.
