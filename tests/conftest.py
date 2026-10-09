import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import pytest


@pytest.fixture(autouse=True)
def _isolated_catalyst_home(tmp_path_factory, monkeypatch):
    """No test reads or writes the real $HOME/.catalyst."""
    monkeypatch.setenv("CATALYST_HOME", str(tmp_path_factory.mktemp("catalyst-home")))
