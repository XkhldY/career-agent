"""
PostgreSQL schema and helpers for job runs and job metadata.
Uses app.core.config.settings.database_url.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from typing import Any, Generator
from urllib.parse import unquote, urlparse

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None  # type: ignore

from app.core.config import settings

JOB_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS job_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMPTZ DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    query_or_source TEXT,
    jobs_added_count INT NOT NULL DEFAULT 0
);
"""

JOBS_DDL = """
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_run_id UUID REFERENCES job_runs(id),
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    company TEXT,
    chroma_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_jobs_run ON jobs(job_run_id);
CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url);
"""

USERS_DDL = """
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);
"""


def _parse_db_url(url: str) -> dict[str, Any] | None:
    """Parse postgresql URL into kwargs for psycopg2.connect."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("postgresql", "postgres"):
            return None
        netloc = parsed.netloc
        path = (parsed.path or "/").lstrip("/")
        if "@" not in netloc or not path:
            return None
        userinfo, hostport = netloc.rsplit("@", 1)
        if ":" not in userinfo:
            return None
        user, password = userinfo.split(":", 1)
        password = unquote(password)
        if ":" in hostport:
            host, port_str = hostport.rsplit(":", 1)
            port = int(port_str, 10)
        else:
            host = hostport
            port = 5432
        kwargs: dict[str, Any] = {
            "host": host,
            "port": port,
            "user": unquote(user),
            "password": password,
            "dbname": path,
        }
        if parsed.query:
            from urllib.parse import parse_qs
            qs = parse_qs(parsed.query, keep_blank_values=True)
            kwargs["sslmode"] = qs.get("sslmode", ["require"])[0]
        # else: leave sslmode unset; get_connection() will set require only for RDS
        return kwargs
    except Exception:
        return None


def create_tables() -> bool:
    """Create all tables if they do not exist. Returns True if DB is configured and DDL ran."""
    if not settings.has_database or not psycopg2:
        return False
    with connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute(JOB_RUNS_DDL)
            cur.execute(JOBS_DDL)
            cur.execute(USERS_DDL)
            # Ensure is_admin exists on older databases.
            cur.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;"
            )
            # Ensure your account is marked admin once in the DB.
            cur.execute(
                "UPDATE users SET is_admin = TRUE WHERE lower(email) = %s;",
                ("xkhaloda@gmail.com",),
            )
    return True


def get_connection():
    if not settings.has_database or not psycopg2:
        return None
    url = settings.database_url.strip()
    kwargs = _parse_db_url(url)
    try:
        if kwargs:
            host = kwargs.get("host", "")
            if "sslmode" not in kwargs and ("rds." in host or "amazonaws" in host):
                kwargs["sslmode"] = "require"
            return psycopg2.connect(**kwargs)
        if "sslmode=" not in url and (".rds." in url or "amazonaws" in url):
            url = f"{url}?sslmode=require" if "?" not in url else f"{url}&sslmode=require"
        return psycopg2.connect(url)
    except Exception:
        return None


@contextmanager
def connection() -> Generator[Any, None, None]:
    conn = get_connection()
    if conn is None:
        yield None
        return
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_job_run(query_or_source: str = "") -> str | None:
    """Insert a job run row; returns run id or None if no DB."""
    if not settings.has_database or not psycopg2:
        return None
    run_id = str(uuid.uuid4())
    with connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO job_runs (id, status, query_or_source) VALUES (%s, 'running', %s)",
                (run_id, query_or_source),
            )
    return run_id


def finish_job_run(run_id: str, jobs_added: int) -> None:
    """Set job_run finished_at and jobs_added_count."""
    if not settings.has_database or not psycopg2:
        return
    with connection() as conn:
        if conn is None:
            return
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE job_runs SET finished_at = now(), status = 'completed', jobs_added_count = %s WHERE id = %s",
                (jobs_added, run_id),
            )


def insert_jobs(run_id: str | None, jobs: list[dict[str, Any]], chroma_ids: list[str]) -> int:
    """Insert job rows. ON CONFLICT (url) DO NOTHING. Returns number inserted."""
    if not settings.has_database or not psycopg2 or not jobs:
        return 0
    inserted = 0
    with connection() as conn:
        if conn is None:
            return 0
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for j, cid in zip(jobs, chroma_ids):
                url = (j.get("url") or "").strip()[:2000]
                if not url:
                    continue
                title = (j.get("title") or "")[:500]
                company = (j.get("company") or "")[:500]
                try:
                    cur.execute(
                        """
                        INSERT INTO jobs (job_run_id, url, title, company, chroma_id)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (url) DO NOTHING
                        """,
                        (run_id, url, title, company, cid),
                    )
                    inserted += cur.rowcount
                except Exception:
                    pass
    return inserted


def get_recent_jobs(limit: int = 50, since_minutes: int | None = None) -> list[dict[str, Any]]:
    """Return recent jobs. If since_minutes is set, only jobs created in the last N minutes."""
    if not settings.has_database or not psycopg2:
        return []
    limit = max(1, min(limit, 100))
    with connection() as conn:
        if conn is None:
            return []
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if since_minutes is not None and since_minutes > 0:
                cur.execute(
                    """
                    SELECT id, job_run_id, url, title, company, created_at
                    FROM jobs
                    WHERE created_at >= now() - make_interval(mins => %s)
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (since_minutes, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT id, job_run_id, url, title, company, created_at
                    FROM jobs
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            rows = cur.fetchall()
    out = []
    for r in rows:
        d = dict(r)
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        out.append(d)
    return out


def get_job_by_id(job_id: str) -> dict[str, Any] | None:
    """Return a single job by UUID, or None if not found or DB not configured."""
    if not settings.has_database or not psycopg2 or not job_id:
        return None
    try:
        uuid.UUID(job_id)
    except (ValueError, TypeError):
        return None
    with connection() as conn:
        if conn is None:
            return None
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, job_run_id, url, title, company, created_at FROM jobs WHERE id = %s",
                (job_id,),
            )
            row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d


def get_job_by_url(url: str) -> dict[str, Any] | None:
    """Return a single job by URL, or None if not found or DB not configured."""
    if not settings.has_database or not psycopg2 or not (url or "").strip():
        return None
    url = url.strip()
    with connection() as conn:
        if conn is None:
            return None
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, job_run_id, url, title, company, created_at FROM jobs WHERE url = %s",
                (url,),
            )
            row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d


def delete_all_jobs() -> tuple[int, int]:
    """Remove all rows from jobs and job_runs. Returns (jobs_deleted, runs_deleted)."""
    if not settings.has_database or not psycopg2:
        return (0, 0)
    with connection() as conn:
        if conn is None:
            return (0, 0)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM jobs")
            jobs_deleted = cur.rowcount
            cur.execute("DELETE FROM job_runs")
            runs_deleted = cur.rowcount
    return (jobs_deleted, runs_deleted)


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------


def create_user(email: str, password_hash: str) -> dict[str, Any] | None:
    """Insert a user row. Returns user dict or None on conflict / no DB."""
    if not settings.has_database or not psycopg2:
        return None
    with connection() as conn:
        if conn is None:
            return None
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO users (email, password_hash)
                VALUES (%s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING id, email, is_admin, created_at
                """,
                (email, password_hash),
            )
            row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    d["id"] = str(d["id"])
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d


def get_user_by_email(email: str) -> dict[str, Any] | None:
    """Return user dict (including password_hash) or None."""
    if not settings.has_database or not psycopg2 or not email:
        return None
    with connection() as conn:
        if conn is None:
            return None
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, email, password_hash, is_admin, created_at FROM users WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    d["id"] = str(d["id"])
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d
