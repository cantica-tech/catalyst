# catalyst quickstart

**Target: 25 minutes, on a stopwatch.** Start it when you begin step 1 and
note the time at the end of each step — [`FEEDBACK.md`](FEEDBACK.md) asks
for it.

You will set up an identity provider, install catalyst into a fresh
repository, document one rule, fix the code that breaks it, commit the fix
with a traced message, and check the result. Every command is meant to be
pasted as is, in order, into one shell (bash or zsh). No agent is needed:
this is the path the agent follows for you, done by hand, so you can see
each piece.

Everything goes into a sandbox of its own: a catalyst home in the current
directory and a throwaway Keycloak, so nothing of this machine's own setup
is read or changed. The last section removes it all.

## 0. Before the clock starts

You need:

- `python3` 3.11 or later, [uv](https://docs.astral.sh/uv/), `git` (with
  `git config user.name` and `user.email` set) and Docker;
- three checkouts: catalyst, with its CLI built into `dist/catalyst.pyz`;
  the process module the trial uses, `catalyst-software-engineering`
  (listed in catalyst's `framework/modules/catalog.md`); and
  catalyst-users, which reaches the identity provider for catalyst.

```sh
git clone -b development git@github.com:cantica-tech/catalyst.git   # the beta branch until the beta release is cut
git clone -b development git@github.com:cantica-tech/catalyst-software-engineering.git
git clone -b development git@github.com:cantica-tech/catalyst-users.git
(cd catalyst-users && uv sync --all-extras)
cd catalyst && PYTHONPATH=scripts python3 -c 'from pathlib import Path; import package_release as p; print(p.build_cli(Path("."), Path("dist/catalyst.pyz")))' && cd ..
docker pull quay.io/keycloak/keycloak:26.4.0
```

(`task build:cli` builds the CLI too, if you have Task.) Then set these
once, in the shell you will use, from the directory holding the three
checkouts:

```sh
CATALYST="$PWD/catalyst"
MODULE="$PWD/catalyst-software-engineering"
USERS="$PWD/catalyst-users"
export CATALYST_HOME="$PWD/quickstart-home"   # catalyst's home for this trial, instead of ~/.catalyst
catalyst_users() { uv run -q --project "$USERS" catalyst-users "$@"; }
```

## 1. An identity provider (6 minutes)

catalyst keeps no list of people: everyone who signs is a person of an
identity provider, reached through catalyst-users. Start an empty Keycloak
on port 8081:

```sh
docker run -d --rm --name catalyst-quickstart -p 127.0.0.1:8081:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin -e KC_BOOTSTRAP_ADMIN_PASSWORD=dev-only-admin-password \
  quay.io/keycloak/keycloak:26.4.0 start-dev
until curl -sf http://127.0.0.1:8081/realms/master >/dev/null; do sleep 3; done; echo "Keycloak is up"
```

Choose a password for yourself, the realm's admin. It is kept in a file
only you can read, and setup records the command that reads it, never the
password:

```sh
mkdir -p "$CATALYST_HOME" && printf 'choose-a-password' > "$CATALYST_HOME/ada.password" && chmod 600 "$CATALYST_HOME/ada.password"
catalyst_users setup --type keycloak \
  --provider "{\"url\": \"http://127.0.0.1:8081\", \"realm\": \"catalyst\", \"definition\": \"$USERS/keycloak/realm-catalyst.json\"}" \
  --username ada --password-command "cat $CATALYST_HOME/ada.password" \
  --server-admin admin --server-admin-password-command "printf dev-only-admin-password" \
  --email ada@example.com --first-name Ada --last-name Lovelace --criterion greet
```

What happened: setup created the realm `catalyst` with you as its admin
(`ada`), the group of the criterion you are about to install (`greet`), you
as that criterion's admin, and catalyst-users' settings in
`$CATALYST_HOME/users/` (your username and the command that reads your
password, nothing secret). This machine now has a **system account**: when
no one is logged in, it signs as you.

Now give catalyst's roles their rights. This runs with your own login: open
the link it prints, sign in as `ada` with your password, and approve.

```sh
catalyst_users login
catalyst_users roles provision "$USERS/keycloak/catalyst-roles.json" \
  --login-client catalyst-cli --login-client catalyst-admin-cli
catalyst_users whoami --system
```

`whoami --system` shows what catalyst will see: `ada`, the issuer
`http://127.0.0.1:8081/realms/catalyst`, the grants `cmd:*` and
`reconcile:full`, and `administers greet`.

## 2. A fresh repository (1 minute)

A one-function program whose greeting is wrong on purpose.

```sh
mkdir greet && cd greet
git init -q
printf 'def greet(name):\n    return "hello " + name\n' > greet.py
git add greet.py && git commit -qm "chore: project skeleton"
```

## 3. Install catalyst (3 minutes)

```sh
python3 "$CATALYST/dist/catalyst.pyz" init --name greet --module software-engineering \
  --rule-doc greeting-rules:gr --kernel "$CATALYST/framework/kernel" --module-dir "$MODULE"
export PATH="$CATALYST_HOME/bin:$PATH"
CRIT="$CATALYST_HOME/projects/greet/criterion"
catalyst where
catalyst hook install
git add catalyst.toml && git commit -qm "chore: install catalyst"
```

What happened: `init` found the identity provider catalyst-users is set up
for, and built the **criterion** — the project's rules, entity folders,
journal and the CLI it was deployed with — in catalyst's home, at `$CRIT`,
never in the project. The project gained one file, `catalyst.toml`, which
names the criterion and holds no path, so it is the same on every clone.
`init` also installed the `catalyst` command (`$CATALYST_HOME/bin`), and you
signed first: the criterion's signers ledger (`IAM/signers.jsonl`) holds
your issuer and subject, and the eight-character **userid** it gave you,
which every ID you create ends with. `hook install` added a `commit-msg`
hook: from now on every commit must cite an artifact or rule ID, or start
`chore:` — as these two did. Run everything from `greet/`.

## 4. Document the first rule (5 minutes)

A rule lives in a **domain**, registered first; its ID comes from the CLI.

```sh
cat > "$CRIT/rules/domains/gr-GREET-greeting-output.md" <<EOF
# \`GREET\` — Greeting output

**Document:** rules/greeting-rules.md
**Name:** greeting-output
**Defined:** $(date +%F)
**Parent:** none
**Sub-domains:** none

## Scope

What the greeting says, and how it is written.

## Relationship to other domains

None.
EOF
echo "| [\`GREET\`](gr-GREET-greeting-output.md) | rules/greeting-rules.md | $(date +%F) |" >> "$CRIT/rules/domains/domains.md"
RULE=$(catalyst id next-rule gr GREET) && echo "$RULE"
```

Now the rule itself: these replace the scaffolds `init` wrote for the
rule document and the global rules index.

```sh
cat > "$CRIT/rules/greeting-rules.md" <<EOF
# Greeting rules

Prefix: \`gr\`.

## Contents

- [\`GREET\`](#greeting-output) — \`$RULE\`

## Greeting output

> **Domain:** \`GREET\` — see [domains/gr-GREET-greeting-output.md](domains/gr-GREET-greeting-output.md).

### \`$RULE\` The greeting is capitalised and punctuated

✅ working. \`greet("Ada")\` returns \`Hello, Ada!\`. Implemented: \`greet.py\`.

## Linked Artifacts — Quick Index

*(none yet)*
EOF
cat > "$CRIT/rules/rules.md" <<EOF
# Rules index

## Documents

| Prefix | Document | Domains |
|---|---|---|
| \`gr\` | [\`greeting-rules.md\`](greeting-rules.md) | \`GREET\` |

## Rule IDs

- \`$RULE\` — The greeting is capitalised and punctuated
EOF
catalyst journal append --command "catalyst journal append" --action create --artifact "$RULE" --target "$RULE" \
  --intent "Document how the greeting must read, so the code has a rule to answer to." \
  --file "$CRIT/rules/greeting-rules.md" --file "$CRIT/rules/rules.md" \
  --file "$CRIT/rules/domains/domains.md" --file "$CRIT/rules/domains/gr-GREET-greeting-output.md"
catalyst check
```

`journal append` recorded who changed which files, why, and each file's
content hash before and after. `check` should pass with no errors.

## 5. A traced fix (4 minutes)

`greet.py` breaks the rule you just wrote, so this change restores a
documented rule's behaviour: a **fix**. With this module, a fix is a bug
report targeting the rule.

```sh
BUG=$(catalyst new BUG --title "Greeting is not capitalised" --field "Targets=$RULE" --field Domain=GREET \
  --field Severity=Low --field Area=greet.py --tier fix --intent "greet() breaks $RULE" | cut -d' ' -f1) && echo "$BUG"
printf 'def greet(name):\n    return f"Hello, {name}!"\n' > greet.py
catalyst journal append --command fix --action update --artifact "$BUG" --target "$RULE" --tier fix \
  --intent "Restore $RULE: the greeting was lower-case and unpunctuated." --file greet.py
catalyst status set "$BUG" Fixed
```

`new` made the bug's file from the module's template, gave it its ID, and
journaled it; `status set` moved it through its workflow, journaled too.

## 6. Commit with a traced message, and check (3 minutes)

First, an untraced commit — the hook refuses it:

```sh
git add greet.py
git commit -m "fix the greeting" || echo "refused, as expected"
```

Then the same commit, citing the bug (the short form, without your userid,
is enough):

```sh
git commit -qm "${BUG%-*}: capitalise and punctuate the greeting"
catalyst trace HEAD
catalyst check
catalyst report
git -C "$CRIT" add -A && git -C "$CRIT" commit -qm "${BUG%-*}: greeting rule and fix"
```

`trace HEAD` checks every commit in the history: three, all traced. The
last line commits the criterion: it has its own history, and nothing you
record in it is kept there until you commit it (in a shared deployment,
`catalyst criterion push` does this and opens a pull request). `check`
passes. `report` shows the journal entries, the tiers, `commits traced:
3/3` and the fixed bug.

**Stop the clock.**

## What you have

- `greet.py` line 2 answers "why is it like this?": its commit cites the
  bug, the bug targets the rule, the rule says what the greeting must be,
  and the journal holds each file's exact before-and-after.
- `catalyst journal restore <timestamp> /tmp/greet-then` rebuilds every
  recorded file as it stood at any moment — `greet.py` as `hello` before the
  fix, `Hello,` after.
- Each change is signed by a person the identity provider vouched for, and
  the provider decides what each person may do.
- In real work your agent does steps 4 and 5 for you (`/create bug`, the
  rule edit), and you review them.

## Clean up

```sh
cd .. && docker rm -f catalyst-quickstart && rm -rf greet "$CATALYST_HOME"
```

Now fill in [`FEEDBACK.md`](FEEDBACK.md). The full picture: the example
project in the release distribution, `framework/kernel/CLI.md`, and
catalyst-users' `docs/onboarding.md` for a provider of your own.
