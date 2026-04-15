"""Pytest fixtures and env for backend tests."""

import os
from pathlib import Path

import pytest

# Ensure backend app is on path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in os.environ.get("PYTHONPATH", ""):
    os.environ["PYTHONPATH"] = f"{BACKEND_ROOT}{os.pathsep}{os.environ.get('PYTHONPATH', '')}"


@pytest.fixture(autouse=True)
def reset_env_for_unit_tests(monkeypatch):
    """For unit tests that don't need a real DB, unset DATABASE_URL so db module returns empty."""
    # Don't override if test explicitly needs DB (e.g. integration)
    yield
