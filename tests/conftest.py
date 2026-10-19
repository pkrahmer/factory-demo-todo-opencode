"""Fixtures shared by the test modules of several layers."""

from pathlib import Path

import pytest


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """A path under `tmp_path` where no SQLite file exists yet."""
    return tmp_path / "todo.db"
