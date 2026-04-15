#!/usr/bin/env python3
"""
Bulk crawl script: ingest recent US/remote tech jobs from Greenhouse and Lever
directly into the local Postgres database and Chroma.

Usage (from repo root):
  CHROMA_HOST=localhost CHROMA_PORT=8000 PYTHONPATH=backend .venv/bin/python backend/scripts/bulk_crawl_greenhouse_lever.py
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Relax filters to scale toward 50k: keep all locations, 90-day window.
RELAX_FILTERS = True
DAYS_RECENT = 90 if RELAX_FILTERS else 30

import httpx
import requests
from bs4 import BeautifulSoup
from dateutil import parser
from dotenv import load_dotenv

from app.agents.jobs_agent.tools import add_jobs_to_store
from app.core.config import settings

ROOT = Path(__file__).resolve().parent.parent

CUTOFF = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=DAYS_RECENT)


def is_recent(date_str: str) -> bool:
    try:
        d = parser.parse(date_str).replace(tzinfo=None)
        return d > CUTOFF
    except Exception:
        return False


def should_keep_job(location: str | None, posted: str) -> bool:
    if RELAX_FILTERS:
        # All locations; only filter by recency.
        return is_recent(posted)
    if not location:
        return False
    loc = location.lower()
    if "united states" not in loc and "remote" not in loc:
        return False
    if not is_recent(posted):
        return False
    return True


def _discover_companies_via_google(site: str, query: str, pages: int = 5) -> list[str]:
    """Discover company slugs using SerpApi Google Search (engine=google)."""
    api_key = settings.serpapi_api_key or ""
    if not api_key:
        print(f"SerpApi key not configured; skipping discovery for {site}.")
        return []
    companies: set[str] = set()
    full_query = f"site:{site} {query}"
    for page in range(pages):
        params = {
            "engine": "google",
            "q": full_query,
            "start": page * 10,
            "api_key": api_key,
        }
        try:
            resp = httpx.get("https://serpapi.com/search", params=params, timeout=20.0)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"Error calling SerpApi for {site} page {page + 1}: {e}")
            break
        results = (data.get("organic_results") or [])[:10]
        if not results:
            print(f"No organic results for {site} page {page + 1}; stopping discovery.")
            break
        for r in results:
            link = (r.get("link") or "") or ""
            m = None
            if "boards.greenhouse.io" in site:
                m = re.search(r"boards\.greenhouse\.io/([^/]+)/?", link)
            elif "jobs.lever.co" in site:
                m = re.search(r"jobs\.lever\.co/([^/]+)/?", link)
            if m:
                companies.add(m.group(1))
        time.sleep(1)
    print(f"Discovered {len(companies)} unique companies for {site} via Google.")
    return sorted(companies)


# Multiple discovery queries per site to maximize company coverage (scale toward 50k).
GREENHOUSE_QUERIES = [
    "software engineer",
    "data engineer",
    "devops engineer",
    "backend engineer",
    "frontend engineer",
]
LEVER_QUERIES = [
    "engineer",
    "developer",
    "software engineer",
    "data engineer",
]


def discover_greenhouse_companies(pages: int = 10) -> list[str]:
    site = "boards.greenhouse.io"
    companies: set[str] = set()
    for q in GREENHOUSE_QUERIES:
        companies.update(_discover_companies_via_google(site, q, pages=pages))
        time.sleep(1)
    return sorted(companies)


def discover_lever_companies(pages: int = 10) -> list[str]:
    site = "jobs.lever.co"
    companies: set[str] = set()
    for q in LEVER_QUERIES:
        companies.update(_discover_companies_via_google(site, q, pages=pages))
        time.sleep(1)
    return sorted(companies)


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
        jobs.append(
            {
                "title": title,
                "company": company,
                "location": location,
                "description": description,
                "url": absolute_url,
                "salary": "",
            }
        )
    return jobs


def crawl_lever_company(company: str) -> list[dict[str, Any]]:
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    jobs: list[dict[str, Any]] = []
    try:
        data = requests.get(url, timeout=10).json()
    except Exception:
        return jobs
    for job in data or []:
        categories = job.get("categories") or {}
        location = categories.get("location", "") or ""
        posted_iso = datetime.utcfromtimestamp(job.get("createdAt", 0) / 1000 or 0).isoformat()
        if not should_keep_job(location, posted_iso):
            continue
        jobs.append(
            {
                "title": job.get("text", ""),
                "company": company,
                "location": location,
                "description": job.get("description", "") or "",
                "url": job.get("hostedUrl", "") or "",
                "salary": "",
            }
        )
    return jobs


def main() -> None:
    # Load .env so DATABASE_URL and other settings are available when running outside Docker.
    load_dotenv(ROOT.parent / ".env")

    if not settings.has_database:
        print("DATABASE_URL is not configured. Aborting.")
        return

    print("Discovering Greenhouse companies...")
    gh_companies = discover_greenhouse_companies()
    print(f"Found {len(gh_companies)} Greenhouse companies.")

    print("Discovering Lever companies...")
    lever_companies = discover_lever_companies()
    print(f"Found {len(lever_companies)} Lever companies.")

    all_jobs: list[dict[str, Any]] = []

    print("Crawling Greenhouse jobs...")
    for company in gh_companies:
        company_jobs = crawl_greenhouse_company(company)
        if company_jobs:
            print(f"  {company}: {len(company_jobs)} jobs")
            all_jobs.extend(company_jobs)

    print("Crawling Lever jobs...")
    for company in lever_companies:
        company_jobs = crawl_lever_company(company)
        if company_jobs:
            print(f"  {company}: {len(company_jobs)} jobs")
            all_jobs.extend(company_jobs)

    if not all_jobs:
        print("No jobs found.")
        return

    # Deduplicate by (title, company, location, url)
    seen_keys: set[tuple[str, str, str, str]] = set()
    unique_jobs: list[dict[str, Any]] = []
    for j in all_jobs:
        key = (
            (j.get("title") or "").strip(),
            (j.get("company") or "").strip(),
            (j.get("location") or "").strip(),
            (j.get("url") or "").strip(),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_jobs.append(j)

    print(f"Discovered {len(all_jobs)} raw jobs, {len(unique_jobs)} after de-duplication.")

    # Add to Chroma + Postgres using existing pipeline, in batches to avoid Chroma 413 errors.
    print("Adding jobs to store and database in batches...")
    batch_size = 100
    total_added = 0
    for i in range(0, len(unique_jobs), batch_size):
        batch = unique_jobs[i : i + batch_size]
        result = add_jobs_to_store(batch)
        added = result.get("added", 0)
        total_added += int(added or 0)
        print(
            f"  Batch {i // batch_size + 1}: size={len(batch)}, "
            f"added={added}, running_total={total_added}"
        )

    print(f"Done. Added {total_added} jobs (Chroma & Postgres, with DB-level URL dedupe).")


if __name__ == "__main__":
    main()

