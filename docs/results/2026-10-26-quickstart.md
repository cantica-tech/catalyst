# Results: the beta quickstart, re-run (kernel 0.117.1), 2026-10-26

The catalyst-docs lead found catalyst's public docs describing an older layout: a criterion in the project
(`.criterion/`), a `<name>.catalyst` pointer, and advisory roles. Fixing them showed that `beta/QUICKSTART.md` no longer
worked at all. Since kernel 0.105.0, `catalyst init` needs an identity provider. The owner left the choice open, so
the quickstart was rewritten with the recommended option (an identity provider first, every signer still verified)
and run end to end. The run found three kernel bugs.

## What shipped

- **`README.md` and `framework/kernel/GLOSSARY.md`** (in 0.117.0) describe the current kernel:
  - `catalyst.toml`;
  - the criterion in catalyst's home;
  - people, grants and roles from catalyst-users;
  - a criterion's admins;
  - membership on a served criterion.
- **`beta/QUICKSTART.md`**, rewritten:
  - Step 0 adds uv, Docker and a catalyst-users checkout.
  - Step 1 starts a throwaway Keycloak on port 8081, runs `catalyst-users setup`, then login and role provisioning.
    It all happens in a sandboxed `CATALYST_HOME`, and one command removes it.
  - `init` installs into catalyst's home.
  - The rule is written into `$CRIT`.
  - The bug is made with `catalyst new` and closed with `status set`.
  - The target goes from 15 to 25 minutes.
- **BUG-000040:** `catalyst init` signs as whoever the provider verifies, unless `--user` or `--git-username` names
  someone.
  - Before, a `git config user.name` that differed from the provider's name refused the install with "not logged in".
  - The deployment now records the verified identity.
  - A name the system account isn't is refused, saying so.
- **BUG-000041:** `catalyst init` installs the `catalyst` command when it fills the criterion's runtime. Before, a
  fresh machine had none until `catalyst runtime install`, and `agent install` refused.
- **BUG-000039:** the commit-msg hook runs the criterion's own CLI, found through `catalyst.toml`, when no launcher
  is installed. When it finds no CLI at all, it says the message went unchecked. Before, it let every commit through,
  silently.
- **`beta/TRIAL.md` and `beta/FEEDBACK.md`** follow the new flow: people from catalyst-users, the criterion in
  catalyst's home, six quickstart steps. RM-000029's newcomer time is measured on steps 2 to 6, since a team's
  identity provider already exists.
- **Kernel 0.117.0** (the landing, design 33 phase 2, catalyst-0c's work): its release PR was green but never merged
  after that session ended. Following the owner's standing release rule, it was merged, tagged and published to the
  distribution repository.

## Tested

- The quickstart, run block by block in a sandbox, a fresh Keycloak each time, from a shell whose git name is not
  the realm admin's. The final run:
  - the hook refuses the untraced commit;
  - `catalyst trace` shows 3 of 3 commits traced;
  - `catalyst check` passes with 0 errors and 0 warnings;
  - `catalyst report` shows the bug Fixed;
  - the criterion commits.
- New tests for each bug. The whole suite: 891 passed.
- ruff, pyright and the standards lint pass on a clean copy.

## What's left

- **One step stays manual:** a reader still approves `catalyst-users login` in the browser, the only step that is not
  pasted.
- **Old hooks:** a hook installed before 0.117.1 keeps the old script until `catalyst hook install` rewrites it. No
  migration rewrites it.
- **catalyst-88's README edits** (the public site link, the journal's `via` field) are uncommitted in catalyst's
  working tree, theirs to commit.
