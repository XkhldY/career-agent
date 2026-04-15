#!/usr/bin/env python3
"""
Bulk crawl from a curated list of Greenhouse and Lever company slugs (no discovery).
Use this to scale toward 50k by adding many slugs to curated_company_slugs.txt or
passing --slugs-file.

Usage (from repo root):
  CHROMA_HOST=localhost CHROMA_PORT=8000 PYTHONPATH=backend .venv/bin/python backend/scripts/bulk_crawl_curated_companies.py
  CHROMA_HOST=localhost CHROMA_PORT=8000 PYTHONPATH=backend .venv/bin/python backend/scripts/bulk_crawl_curated_companies.py --slugs-file backend/scripts/curated_company_slugs.txt
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from app.agents.jobs_agent.tools import add_jobs_to_store
from app.core.config import settings

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent

# Same relax logic as bulk_crawl_greenhouse_lever (90 days, all locations).
DAYS_RECENT = 90
CUTOFF = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=DAYS_RECENT)


def is_recent(date_str: str) -> bool:
    try:
        from dateutil import parser
        d = parser.parse(date_str).replace(tzinfo=None)
        return d > CUTOFF
    except Exception:
        return False


def should_keep_job(location: str | None, posted: str) -> bool:
    return is_recent(posted)


def crawl_greenhouse_company(company: str) -> list[dict[str, Any]]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
    jobs: list[dict[str, Any]] = []
    try:
        data = requests.get(url, timeout=10).json()
    except Exception:
        return jobs
    for job in data.get("jobs", []) or []:
        title = job.get("title", "")
        location = (job.get("location") or {}).get("name", "")
        posted = job.get("updated_at", "")
        absolute_url = job.get("absolute_url", "")
        description = job.get("content", "") or ""
        if not should_keep_job(location, posted):
            continue
        jobs.append({
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "url": absolute_url,
            "salary": "",
        })
    return jobs


def crawl_lever_company(company: str) -> list[dict[str, Any]]:
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    jobs: list[dict[str, Any]] = []
    try:
        data = requests.get(url, timeout=10).json()
    except Exception:
        return jobs
    for job in data or []:
        if not isinstance(job, dict):
            continue
        categories = job.get("categories") or {}
        location = categories.get("location", "") or ""
        ts_ms = job.get("createdAt") or 0
        posted_iso = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).replace(tzinfo=None).isoformat()
        if not should_keep_job(location, posted_iso):
            continue
        jobs.append({
            "title": job.get("text", ""),
            "company": company,
            "location": location,
            "description": job.get("description", "") or "",
            "url": job.get("hostedUrl", "") or "",
            "salary": "",
        })
    return jobs


# Default curated slugs (well-known Greenhouse/Lever tenants). Add more in curated_company_slugs.txt.
DEFAULT_GREENHOUSE = [
    "asana", "figma", "stripe", "notion", "discord", "robinhood", "plaid", "affirm",
    "square", "airbnb", "doordash", "instacart", "pinterest", "snap", "twilio", "datadog",
    "hashicorp", "mongodb", "elastic", "confluent", "snowflake", "unity", "roblox",
    "niantic", "cruise", "nuro", "aurora", "scale", "openai", "anthropic", "cohere",
    "brex", "ramp", "mercury", "deel", "remote", "gitlab", "sourcegraph", "vercel",
    "netlify", "supabase", "planetscale", "railway", "flyio", "render", "replit",
]
DEFAULT_LEVER = [
    "flexport", "anduril", "lattice", "rippling", "gusto", "carta", "benchling",
    "freenome", "tempus", "insitro", "recursion", "strive", "whatnot", "stockx",
    "clerk", "launchdarkly", "postman", "segment", "amplitude", "mixpanel", "heap",
    "fullstory", "logdna", "cribl", "calendly", "loom", "maze", "mural", "miro",
    "linear", "height", "clickup", "airtable", "coda", "notion", "slite",
]


def load_slugs_from_file(path: Path) -> tuple[list[str], list[str]]:
    """Read file: lines 'greenhouse:slug' or 'lever:slug' or 'slug' (try greenhouse then lever)."""
    gh: list[str] = []
    lever: list[str] = []
    for line in path.read_text().encode("utf-8", errors="ignore").decode("utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("greenhouse:"):
            gh.append(line.split(":", 1)[1].strip())
        elif line.lower().startswith("lever:"):
            lever.append(line.split(":", 1)[1].strip())
        else:
            gh.append(line)
    return gh, lever


def main() -> None:
    load_dotenv(ROOT.parent / ".env")

    parser = argparse.ArgumentParser(description="Crawl curated Greenhouse/Lever companies into DB.")
    parser.add_argument("--slugs-file", type=Path, default=None, help="Path to file with greenhouse:slug or lever:slug per line.")
    parser.add_argument("--batch-size", type=int, default=100, help="Chunk size for Chroma/DB inserts.")
    args = parser.parse_args()

    if not settings.has_database:
        print("DATABASE_URL is not configured. Aborting.")
        sys.exit(1)

    gh_slugs = list(DEFAULT_GREENHOUSE)
    lever_slugs = list(DEFAULT_LEVER)
    if args.slugs_file and args.slugs_file.exists():
        extra_gh, extra_lever = load_slugs_from_file(args.slugs_file)
        gh_slugs = list(dict.fromkeys(gh_slugs + extra_gh))
        lever_slugs = list(dict.fromkeys(lever_slugs + extra_lever))
        print(f"Loaded {len(extra_gh)} Greenhouse + {len(extra_lever)} Lever slugs from {args.slugs_file}.")
    else:
        if args.slugs_file:
            print(f"Slugs file not found: {args.slugs_file}; using built-in list only.")
        print(f"Using built-in list: {len(gh_slugs)} Greenhouse, {len(lever_slugs)} Lever companies.")

    all_jobs: list[dict[str, Any]] = []

    print("Crawling Greenhouse jobs...")
    for i, company in enumerate(gh_slugs, 1):
        jobs = crawl_greenhouse_company(company)
        if jobs:
            print(f"  [{i}/{len(gh_slugs)}] {company}: {len(jobs)} jobs")
            all_jobs.extend(jobs)
        time.sleep(0.3)
    print("Crawling Lever jobs...")
    for i, company in enumerate(lever_slugs, 1):
        jobs = crawl_lever_company(company)
        if jobs:
            print(f"  [{i}/{len(lever_slugs)}] {company}: {len(jobs)} jobs")
            all_jobs.extend(jobs)
        time.sleep(0.3)

    if not all_jobs:
        print("No jobs found.")
        return

    seen: set[tuple[str, str, str, str]] = set()
    unique: list[dict[str, Any]] = []
    for j in all_jobs:
        key = (
            (j.get("title") or "").strip(),
            (j.get("company") or "").strip(),
            (j.get("location") or "").strip(),
            (j.get("url") or "").strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(j)

    print(f"Raw jobs: {len(all_jobs)}, after dedupe: {len(unique)}. Adding to store in batches of {args.batch_size}...")
    total_added = 0
    for i in range(0, len(unique), args.batch_size):
        batch = unique[i : i + args.batch_size]
        result = add_jobs_to_store(batch)
        added = result.get("added", 0)
        total_added += int(added or 0)
        print(f"  Batch {i // args.batch_size + 1}: size={len(batch)}, added={added}, running_total={total_added}")
    print(f"Done. Added {total_added} jobs (Chroma & Postgres).")


if __name__ == "__main__":
    main()
