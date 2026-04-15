"""Tests for app.core.db (no real DB required when DATABASE_URL unset)."""

import uuid

import pytest


@pytest.fixture(autouse=True)
def no_database(monkeypatch):
    """Make db module think no database is configured."""
    from app.core import db
    monkeypatch.setattr(db.settings, "database_url", "")


def test_get_recent_jobs_returns_empty_when_no_db():
    from app.core import db
    assert db.get_recent_jobs() == []
    assert db.get_recent_jobs(limit=10, since_minutes=5) == []


def test_get_job_by_id_returns_none_when_no_db():
    from app.core import db
    assert db.get_job_by_id(str(uuid.uuid4())) is None
    assert db.get_job_by_id("") is None
    assert db.get_job_by_id("not-a-uuid") is None


def test_get_job_by_url_returns_none_when_no_db():
    from app.core import db
    assert db.get_job_by_url("https://example.com/job") is None
    assert db.get_job_by_url("") is None


def test_delete_all_jobs_returns_zero_when_no_db():
    from app.core import db
    assert db.delete_all_jobs() == (0, 0)
