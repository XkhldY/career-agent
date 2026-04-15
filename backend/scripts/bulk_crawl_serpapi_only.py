#!/usr/bin/env python3
"""
Bulk crawl script using SerpApi Google Jobs directly (no ADK agent orchestration).

Goal: quickly ingest ~1000 diverse tech developer jobs into Postgres (and Chroma)
by calling search_google_jobs and add_jobs_to_store directly.

Usage (from repo root):
  CHROMA_HOST=localhost CHROMA_PORT=8000 PYTHONPATH=backend .venv/bin/python backend/scripts/bulk_crawl_serpapi_only.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from app.core import db
from app.core.config import settings
from app.agents.jobs_agent.tools import search_google_jobs, add_jobs_to_store

ROOT = Path(__file__).resolve().parent.parent


def count_jobs() -> int:
    """Return total number of jobs in the database."""
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
    # Ensure SERPAPI_API_KEY and friends are in the environment when running outside Docker.
    load_dotenv(ROOT.parent / ".env")

    if not settings.has_database:
        print("DATABASE_URL is not configured. Aborting.")
        sys.exit(1)
    if not settings.serpapi_api_key:
        print("SERPAPI_API_KEY / serpapi_api_key is not configured. Aborting.")
        sys.exit(1)

    TARGET_JOBS = 1000
    MAX_PER_QUERY = 50
    MAX_ROUNDS = 10  # each round hits all queries once

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
    print("Starting SerpApi-only bulk crawl for diverse tech developer roles.")
    print(f"Existing jobs in DB: {start}")
    print(f"Target: {TARGET_JOBS} jobs (up to {MAX_PER_QUERY} per query, {len(QUERIES)} query types)")

    round_idx = 0
    while round_idx < MAX_ROUNDS:
        current = count_jobs()
        if current >= TARGET_JOBS:
            print(f"Reached target: {current} jobs in DB. Done.")
            break
        round_idx += 1
        print(f"\n=== Round {round_idx}/{MAX_ROUNDS} ===")

        for i, query in enumerate(QUERIES, 1):
            before = count_jobs()
            if before >= TARGET_JOBS:
                print(f"Reached target: {before} jobs in DB. Stopping early.")
                break
            remaining = max(TARGET_JOBS - before, 0)
            print(f"\n--- Query {i}/{len(QUERIES)} (round {round_idx}) ---")
            print(f"Query: {query!r}")
            print(f"Before: {before} jobs | remaining to target: ~{remaining}")

            out = search_google_jobs(query=query, max_results=MAX_PER_QUERY)
            if out.get("status") != "success" or not out.get("results"):
                print(f"Google Jobs returned no results for {query!r} (message={out.get('message')}).")
                continue

            jobs = out["results"]
            print(f"Google Jobs returned {len(jobs)} results for {query!r}; adding to store/DB...")
            # add_jobs_to_store will embed into Chroma and insert into Postgres with URL dedupe.
            result = add_jobs_to_store(jobs)
            added = result.get("added", 0)
            after = count_jobs()
            print(f"Added {added} jobs from query {query!r}. DB count is now {after}.")

            # Small pause to be nice to APIs
            time.sleep(2)

        # Small pause between rounds
        time.sleep(5)

    final = count_jobs()
    print(f"\nSerpApi-only bulk crawl finished after {round_idx} round(s).")
    print(f"Jobs in DB: {final}")
    if final < TARGET_JOBS:
        print(
            "Warning: fewer than target jobs ingested. This is expected if "
            "SerpApi could not find enough distinct postings across all queries."
        )


if __name__ == "__main__":
    main()

