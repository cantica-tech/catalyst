# Results — 2026-10-18: the desktop app ships for macOS, Windows and Linux (R6.20)

The desktop app (Catalyst Studio) is packaged for the three platforms, and the UI's `Desktop` workflow builds all
three: its third test run passed on macOS, Windows and Linux. Signing switches on by itself once the credentials
exist; until then every build is unsigned and the run says so.

| Platform | Files | Signing |
|---|---|---|
| macOS (Apple silicon and Intel) | `.dmg`, `.zip` | Developer ID certificate and Apple notarization, once Apple's secrets exist |
| Windows (x64 and arm64) | NSIS installer `.exe` | Azure Artifact Signing over a federated sign-in, once its variables exist |
| Linux (x64 and arm64) | `.AppImage`, `.deb` | none |

## What was built

- **Packaging:** electron-builder packs the app from its own bundled directory, with no dependencies, and ships
  the Studio bundle beside it as a resource.
- **The `Desktop` workflow:** when a UI release is published, it builds on each operating system and attaches the
  files to that release; run by hand, it keeps them as downloads.
- **Setup steps:** what to configure in Azure, Apple and GitHub is in the UI repository's `docs/desktop.md`.
- **Recorded:** the rule `electron-DESKTOP-000003` and the requirement `REQ-000054` in the UI's criterion.

## Problems along the way, all fixed

- **The launcher window was blank when packaged.** A `data:` page may not load a `file:` script, and the
  development setup was the same, so it had probably never worked. The script is now inline under its nonce; an
  unsigned macOS (Intel) build starts and its window loads without a console error.
- **The first test run failed on all three platforms:** the workflow had not built one of the UI's packages. It now
  builds every package first.
- **The second run failed on Linux only:** the `.deb` needs a homepage and a maintainer. It names the repository
  and "Cantica Tech".
- **Microsoft renamed Azure Trusted Signing to Artifact Signing.** The setup is the same; the doc gives both names
  of the signer role.

Not tested: the built apps beyond the macOS start; nobody has installed the Windows or Linux files or clicked
through any of them.

## What is needed from the owner

1. **Windows, from Azure:** the signing account's name and endpoint, the certificate profile's name, and an app
   registration with a GitHub federated credential for the `release` environment, given the signer role; its
   tenant, client and subscription IDs. Six variables, none secret.
2. **macOS, from Apple:** the Developer ID certificate (`.p12` and its password) and an App Store Connect API key;
   stored as secrets.
3. **Linux:** a public address for the `.deb`'s maintainer field.
4. **Auto-update:** Azure Blob Storage or GitHub Releases for the update feed.

## Still open

- The desktop app needs `catalyst` installed on the machine; it does not bundle it yet.
- On Windows, the installer is signed but the app inside it is not signed separately yet.
- The app icon is the catalyst logo until the brand work (R6.21) gives one.
