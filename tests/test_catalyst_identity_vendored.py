"""The vendored identity code is catalyst-users' release, unchanged (fw-IDENTITY-000006)."""

import hashlib
import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

IDENTITY = Path(__file__).resolve().parents[1] / "scripts" / "catalyst" / "identity"


def vendored() -> dict[str, Path]:
    """Every vendored module by its path relative to the package (`providers/keycloak.py`)."""
    return {p.relative_to(IDENTITY).as_posix(): p for p in IDENTITY.rglob("*.py") if "__pycache__" not in p.parts}


def test_every_vendored_file_matches_its_recorded_hash():
    version = json.loads((IDENTITY / "VERSION").read_text(encoding="utf-8"))
    assert version["package"] == "catalyst-users" and version["release"]
    assert set(vendored()) == set(version["files"]), "a vendored file was added or removed by hand"
    for name, digest in version["files"].items():
        actual = hashlib.sha256((IDENTITY / name).read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        assert actual == digest, (
            f"{name} differs from catalyst-users {version['release']}: change it there, then vendor"
        )


def test_the_vendored_code_names_no_catalyst_users_import():
    """No import of catalyst_users is left (the entry-point group and the docstrings may still name it)."""
    for name, path in vendored().items():
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(from|import) catalyst_users\b", text, re.M), name
        assert '"catalyst_users.providers.' not in text, name  # the registry's built-in module names


def test_the_vendored_code_imports_with_the_standard_library_only():
    scripts = str(IDENTITY.parents[1])
    names = [n[: -len(".py")].replace("/", ".").removesuffix(".__init__") for n in vendored() if n != "__init__.py"]
    modules = "; ".join(f"import catalyst.identity.{n}" for n in names)
    code = f"import sys; sys.path.insert(0, {scripts!r}); {modules}"
    result = subprocess.run([sys.executable, "-I", "-S", "-c", code], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_it_is_importable_in_process():
    assert importlib.import_module("catalyst.identity.oidc").OIDCClient
