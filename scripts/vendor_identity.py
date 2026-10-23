"""Vendor catalyst-users' standard-library core into `scripts/catalyst/identity/` (fw-IDENTITY-000006).

    python3 scripts/vendor_identity.py <catalyst-users checkout> <release tag>

Each core module is read at the tag (never the working tree), its `catalyst_users` imports rewritten to
`catalyst.identity`, and written beside a `VERSION` file naming the release and each file's sha256, which
`tests/test_catalyst_identity_vendored.py` checks. A change to this code is made in catalyst-users first.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

CORE = ("errors", "config", "http", "oidc", "identity", "credentials", "session")
DEST = Path(__file__).resolve().parent / "catalyst" / "identity"
INIT = '''"""The identity code: catalyst-users' standard-library core, vendored (fw-IDENTITY-000006).

Never edit these files here: change catalyst-users, release it, then run
`python3 scripts/vendor_identity.py <catalyst-users checkout> <tag>`. `VERSION`
names the release and each file's sha256.
"""
'''


def rewrite(source: str) -> str:
    source = re.sub(r"\bfrom catalyst_users import\b", "from catalyst.identity import", source)
    return re.sub(r"\bfrom catalyst_users\.", "from catalyst.identity.", source)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(checkout: str, tag: str) -> int:
    repo = Path(checkout)
    files: dict[str, str] = {}
    DEST.mkdir(parents=True, exist_ok=True)
    for name in CORE:
        source = subprocess.run(
            ["git", "-C", str(repo), "show", f"{tag}:src/catalyst_users/{name}.py"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        text = rewrite(source)
        (DEST / f"{name}.py").write_text(text, encoding="utf-8")
        files[f"{name}.py"] = digest(text)
    (DEST / "__init__.py").write_text(INIT, encoding="utf-8")
    files["__init__.py"] = digest(INIT)
    version = {"package": "catalyst-users", "repository": "cantica-tech/catalyst-users", "release": tag, "files": files}
    (DEST / "VERSION").write_text(json.dumps(version, indent=2) + "\n", encoding="utf-8")
    print(f"vendored catalyst-users {tag}: {', '.join(sorted(files))}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
