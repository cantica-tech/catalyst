"""The vendored identity code is catalyst-users' release, unchanged (fw-IDENTITY-000006)."""

import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path

IDENTITY = Path(__file__).resolve().parents[1] / "scripts" / "catalyst" / "identity"


def test_every_vendored_file_matches_its_recorded_hash():
    version = json.loads((IDENTITY / "VERSION").read_text(encoding="utf-8"))
    assert version["package"] == "catalyst-users" and version["release"]
    on_disk = {p.name for p in IDENTITY.glob("*.py")}
    assert on_disk == set(version["files"]), "a vendored file was added or removed by hand"
    for name, digest in version["files"].items():
        actual = hashlib.sha256((IDENTITY / name).read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        assert actual == digest, (
            f"{name} differs from catalyst-users {version['release']}: change it there, then vendor"
        )


def test_the_vendored_code_names_no_catalyst_users_import():
    for path in IDENTITY.glob("*.py"):
        assert "catalyst_users" not in path.read_text(encoding="utf-8"), path.name


def test_the_vendored_code_imports_with_the_standard_library_only():
    scripts = str(IDENTITY.parents[1])
    modules = "; ".join(f"import catalyst.identity.{p.stem}" for p in IDENTITY.glob("*.py") if p.stem != "__init__")
    code = f"import sys; sys.path.insert(0, {scripts!r}); {modules}"
    result = subprocess.run([sys.executable, "-I", "-S", "-c", code], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_it_is_importable_in_process():
    assert importlib.import_module("catalyst.identity.oidc").OIDCClient
