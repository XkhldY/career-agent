#!/usr/bin/env python3
"""
Bulk crawl script: aim to ingest ~1000 Python developer jobs.

Usage (from repo root):
  PYTHONPATH=backend .venv/bin/python backend/scripts/bulk_crawl_python_jobs.py

The script will:
 - Run the existing jobs agent multiple times with the query "python developer jobs"
 - After each run, check how many jobs are in the database
 - Stop once at least TARGET_JOBS rows exist in jobs, or after MAX_RUNS runs

Notes:
 - Requires DATABASE_URL to be configured and reachable
 - Uses the same ADK agent pipeline as the API crawl
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from app.core import db
from app.core.config import settings
from app.services.agent import run_crawl_sync

ROOT = Path(__file__).resolve().parent.parent


def count_jobs() -> int:
    """Return total number of jobs in the database."""
    # db.get_recent_jobs returns at most 100; we want a full count via SQL.
    if not settings.has_database:
        return 0
    from app.core.db import connection  # avoid circular import at module import time

    with connection() as conn:
        if conn is None:
            return 0
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM jobs")
            row = cur.fetchone()
    return int(row[0]) if row else 0


def main() -> None:
    # Ensure external tools (e.g. SerpApi, Tavily, Brave) see keys when running outside Docker.
    # Settings already read .env for DATABASE_URL; this makes SERPAPI_API_KEY, etc. available in os.environ.
    load_dotenv(ROOT.parent / ".env")

    if not settings.has_database:
        print("DATABASE_URL is not configured. Aborting.")
        sys.exit(1)

    TARGET_JOBS = 1000
    BATCH_SIZE = 50  # run_crawl_sync caps at 50 internally
    MAX_RUNS = 80    # safety limit

    # 20 different tech developer job types to diversify the dataset
    QUERIES = [
        "python developer jobs",
        "full stack developer jobs",
        "frontend react developer jobs",
        "backend node.js developer jobs",
        "devops engineer jobs",
        "data engineer jobs",
        "machine learning engineer jobs",
        "mobile ios developer jobs",
        "mobile android developer jobs",
        "software engineer jobs",
        "cloud engineer jobs",
        "site reliability engineer jobs",
        "golang developer jobs",
        "java backend developer jobs",
        "typescript developer jobs",
        "rust developer jobs",
        "data scientist jobs",
        "platform engineer jobs",
        "security engineer jobs",
        "ai engineer jobs",
    ]

    start = count_jobs()
    print("Starting bulk crawl for diverse tech developer roles.")
    print(f"Existing jobs in DB: {start}")
    print(f"Target: {TARGET_JOBS} jobs (batch size {BATCH_SIZE}, {len(QUERIES)} query types)")

    runs = 0
    while runs < MAX_RUNS:
        current = count_jobs()
        if current >= TARGET_JOBS:
            print(f"Reached target: {current} jobs in DB. Done.")
            break

        runs += 1
        remaining = max(TARGET_JOBS - current, 0)
        query = QUERIES[(runs - 1) % len(QUERIES)]
        print(f"\n--- Batch {runs}/{MAX_RUNS} ---")
        print(f"Before: {current} jobs | target: {TARGET_JOBS} | remaining: ~{remaining}")
        print(f"Invoking jobs agent for query: {query!r} (max {BATCH_SIZE} jobs)")

        run_crawl_sync(query, BATCH_SIZE)

        after = count_jobs()
        added = after - current
        print(f"Batch {runs} done — {after} jobs in DB (+{added} this batch, {max(TARGET_JOBS - after, 0)} to go)")

        # Small pause between runs to avoid hammering external APIs
        time.sleep(3)

    final = count_jobs()
    print(f"\nBulk crawl finished after {runs} run(s).")
    print(f"Jobs in DB: {final}")
    if final < TARGET_JOBS:
        print(
            "Warning: fewer than target jobs ingested. This is expected if "
            "external search or extraction could not find enough distinct postings."
        )


if __name__ == "__main__":
    main()

