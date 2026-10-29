# Results — 2026-10-27: Azure DevOps repositories and local checkouts in catalyst-kb-engine and catalyst-kb-container

The owner asked for Azure DevOps repositories in the knowledge base engine and the container's scripts, the
visibility check above all; then for the container's script to take a directory. Earlier the same day,
catalyst-kb-container became a Python project (`pyproject.toml`, `uv.lock`), installable online where no bundled wheel
fits, and its wheelhouse is recorded in a committed `wheelhouse.toml` rather than committed itself.

| What | Where |
|---|---|
| catalyst-kb-engine 0.12.0: REQ-000013 (`eng-SOURCE-000002` amended), STEP-000018 | `cantica-tech/catalyst-kb-engine` #10, tag `0.12.0`; criterion PR #18 (waits on approval) |
| catalyst-kb-container: Azure DevOps and directories, engine 0.12.0 | `cantica-tech/catalyst-kb-container`, development |

## 1. The engine: Azure DevOps beside GitHub

- A repository URL is GitHub's (`owner/name`) or Azure DevOps' (`org/project/name`: `dev.azure.com`,
  `<org>.visualstudio.com`, ssh).
- An Azure DevOps repository's visibility is its project's, asked of the REST API
  (`_apis/git/repositories/<name>`), anonymously or with `AZURE_DEVOPS_EXT_PAT`. A private project asked anonymously
  redirects to sign-in: unknown, so `Private`, and a source recorded `Public` is refused, as `eng-SOURCE-000002` wants.
- Azure DevOps repositories are read, staged and cited like GitHub's; their documents and history link to Azure DevOps.
  GitHub's output is unchanged, so incremental builds re-embed nothing.
- `catalyst-kb-engine repository <url>`: host, name, clone URL and visibility as JSON, for scripts.

## 2. The container: URLs of either host, and directories

- `build-kb.sh` asks the engine, not `gh`, whether each repository is public, and clones from the URL it gives.
- A directory is read in place when it is a git checkout whose `origin` is public, with nothing uncommitted and nothing
  unpushed (what is embedded through Copilot must be what the public repository holds); a full clone when `-H` is set.
- `kb-container.sh` mounts every path given, relative ones outside the current directory too, and passes
  `AZURE_DEVOPS_EXT_PAT` by name. A repository named twice is refused up front.

## Checks

- Engine: 104 tests (10 new), ruff; CI green on #10. Real answers: a public Azure DevOps project's repository is
  `Public`, a private one unknown; GitHub unchanged.
- Container, on this machine: a build from a public Azure DevOps URL with history (4 documents, 20 chunks, embedded
  through Copilot); from a local checkout read in place; refusals for a private checkout, a non-repository URL, a
  private Azure DevOps project, uncommitted changes, unpushed commits and a shallow clone with history. The x86_64 image
  rebuilt at 0.12.0 and run from another directory with `../<checkout>`: 3 documents, 16 chunks.

## 3. Then: any git URL, ssh or https (catalyst-kb-engine 0.13.0)

The owner found the script still refused repositories: it took GitHub and Azure DevOps https URLs only in their plain
forms. REQ-000014 (`eng-SOURCE-000002` amended, STEP-000019; #11, tag `0.13.0`; criterion PR #19): every git URL form
— `https://` with a user or `.git`, `http://`, `ssh://` with a user or a port, `user@host:path` — for GitHub, Azure
DevOps (also `ssh.dev.azure.com` and `vs-ssh.visualstudio.com`) and any other host. A repository on another host is
public only when git reads it anonymously, with no credential helper, `.netrc` or git configuration of this machine
(a test proves a `url.insteadOf` cannot vouch); the same read confirms a GitHub or Azure DevOps repository its host
cannot answer for. Everything is cloned over https. Fixed on the way: a `.visualstudio.com` URL ending `.git` named
the repository `<name>.git`. The container pins 0.13.0 (wheels refetched, the x86_64 image and the bundle rebuilt).

Checks: 125 engine tests, ruff, CI green on #11; real hosts — GitHub, Azure DevOps and GitLab over ssh and https,
public; a private GitHub repository, private; missing ones, unknown. Through `kb-container.sh` and the 0.13.0 image: an
Azure DevOps ssh URL built (3 documents, 16 chunks); a local checkout whose origin is an ssh URL, read in place and
built; a missing repository given as `ssh://…:22/…`, refused.

## What's left

- Done since: the owner merged criterion PRs #18, #176 and #115; the UI 0.66.0 is on the Marketplace. The bundle
  `dist/catalyst-kb-container-linux.tar.gz` is built at engine 0.12.0, with the x86_64 image only: the owner chose to
  skip aarch64 for now, so the 0.11.0 ARM image was removed and an ARM machine builds the image from the `Dockerfile`
  on its first run.
- Done since: catalyst-docs' public site builds with engine 0.12.0 (it pinned 0.8.0): checked locally first, its
  pages identical to 0.8.0's (285 reference documents, 12 guide pages, publish-check passing); #4 merged, the Pages run
  built and deployed.
- The owner: merge criterion PR #19 (catalyst-kb-engine's, REQ-000014).
- catalyst-docs' site stays on engine 0.12.0: it reads GitHub https URLs only, which 0.13.0 does not change.
- Not done: the aarch64 image at 0.13.0; a private Azure DevOps project with a token (no token here).
- Signed as the system account: nobody was logged in to the local Keycloak.
- Every deployment checked here (catalyst-kb-engine, catalyst-knowledge-base) is on kernel 0.117.1: the
  `~/.catalyst-users` link the 0.110.1 ones needed can go once no other machine needs it.
