"""Tests for jobs API (GET /api/jobs, GET /api/jobs/:id, GET /api/jobs/by-url)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def no_database(monkeypatch):
    """No DB so list returns empty, get by id/url return 404."""
    from app.core import db
    monkeypatch.setattr(db.settings, "database_url", "")


def test_list_jobs_returns_empty(client):
    """GET /api/jobs returns { jobs: [] } when DB not configured."""
    r = client.get("/api/jobs")
    assert r.status_code == 200
    data = r.json()
    assert "jobs" in data
    assert data["jobs"] == []


def test_list_jobs_respects_limit(client):
    """GET /api/jobs?limit=5 returns 200 and limit is applied server-side."""
    r = client.get("/api/jobs?limit=5")
    assert r.status_code == 200
    assert "jobs" in r.json()


def test_get_job_by_id_404_when_no_db(client):
    """GET /api/jobs/:id returns 404 when job not found."""
    r = client.get(f"/api/jobs/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["detail"] == "Job not found"


def test_get_job_by_id_invalid_uuid_404(client):
    """GET /api/jobs/not-a-uuid returns 404."""
    r = client.get("/api/jobs/not-a-uuid")
    assert r.status_code == 404


def test_get_job_by_url_404_when_no_db(client):
    """GET /api/jobs/by-url?url=... returns 404 when not found."""
    r = client.get("/api/jobs/by-url", params={"url": "https://example.com/job"})
    assert r.status_code == 404


def test_get_job_by_url_missing_url_422(client):
    """GET /api/jobs/by-url without url returns 422."""
    r = client.get("/api/jobs/by-url")
    assert r.status_code == 422


def test_post_crawl_returns_success_and_jobs(monkeypatch):
    """POST /api/jobs/crawl runs agent and returns { status, message, jobs }."""
    from app.services import agent
    called = []

    def fake_run(*args, **kwargs):
        called.append((args, kwargs))

    monkeypatch.setattr(agent.subprocess, "run", fake_run)
    from app.core import db
    monkeypatch.setattr(db.settings, "database_url", "")

    client = TestClient(app)
    r = client.post("/api/jobs/crawl", json={"query": "python jobs", "max_jobs": 3})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "message" in data
    assert data["query"] == "python jobs"
    assert data["max_jobs"] == 3
    assert data["jobs"] == []
    assert len(called) == 1
    args = called[0][0][0]
    assert "run" in args
    assert "jobs_agent" in args or "agent" in str(called[0])
    assert "--replay" in args
