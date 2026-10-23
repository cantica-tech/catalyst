# 0.105.0 — Identity providers

From `0.104.x` to `0.105.0` (REQ-000086, design `28`).

## What changes

- A deployment chooses who signs: `catalyst.toml` `identity = "local"` (the default, also when the key is absent:
  exactly as before) or `identity = "oidc"` with `identity_issuer` and `identity_client` (`CLI.md`, "Identity
  providers").
- With a provider: `catalyst identity login|logout|whoami|status`; every signature is the verified, logged-in
  identity; an identity's first signature appends its line to the new, append-only `IAM/signers.jsonl`; roles come
  through each role's new, optional `provider_role`; `catalyst user …` refuses.
- `catalyst serve --identity-issuer` also accepts the provider's tokens.
- `ACCESS-CONTROL.md` and `INVARIANTS.md` (INV-16, INV-26) say so; the recomposed copies change.
- A shared criterion merges `IAM/signers.jsonl` by union: `.gitattributes` gains the line at its next
  `catalyst criterion push`, journaled.
- Nothing existing changes behaviour: a deployment without `identity` is `local`.

## Steps

1. `catalyst sync apply --kernel <0.105.0>`: the CLI, the runtime and the recomposed documents.
2. **Judgment, optional:** to sign with an identity provider, with the owner's agreement: map each role
   (`catalyst role modify <role> --provider-role <the provider's role>`) while a registered user can still sign,
   then `catalyst identity configure oidc --issuer <url> [--client <id>] --as <them>`, and each person
   `catalyst identity login`.
3. `catalyst check`.
