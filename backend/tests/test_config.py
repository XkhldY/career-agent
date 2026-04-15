"""Tests for app.core.config."""

import pytest


def test_settings_load_without_env():
    """When database_url is empty, has_database is False."""
    from app.core.config import Settings
    s = Settings(database_url="")
    assert s.has_database is False
    assert s.chroma_port == 8000
    assert s.aws_region == "us-east-1"


def test_settings_has_database_when_url_set(monkeypatch):
    """When DATABASE_URL is set, has_database is True."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
    from app.core.config import Settings
    s = Settings()
    assert s.has_database is True
