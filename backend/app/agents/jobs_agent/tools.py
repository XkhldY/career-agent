"""
Tools for the jobs agent: search_jobs, search_and_save_jobs, add_jobs_to_store, fetch_and_extract_job.
Option A: use search_and_save_jobs only (search API → save title, snippet, URL to store/DB; no portal fetching).
Web search: Tavily first, then Brave fallback. Chroma + Bedrock for store; PostgreSQL for job metadata when DATABASE_URL set.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

import httpx
from google.adk.tools import FunctionTool

from app.agents.shared.store import VectorStore, get_store
from app.core import db as recruitment_db
from app.core.config import settings

# Lazy single store instance for tools
_store: VectorStore | None = None

# Domains to exclude: job aggregators; we want company career pages (e.g. careers.salesforce.com, careers.adobe.com).
# Lever/Greenhouse host company-specific job pages (e.g. company.lever.co) so we allow those.
AGGREGATOR_DOMAINS = frozenset({
    "linkedin.com", "indeed.com", "glassdoor.com", "ziprecruiter.com",
    "monster.com", "simplyhired.com", "careerbuilder.com", "flexjobs.com",
    "idealist.org", "naukri.com", "indeed.co.uk", "indeed.ca",
})


def _get_store() -> VectorStore:
    global _store
    if _store is None:
        _store = get_store()
    return _store


def _is_career_page_url(url: str) -> bool:
    """Return True if URL looks like a company career page (exclude known aggregators)."""
    if not (url or url.strip()):
        return False
    try:
        parsed = urlparse(url.strip().lower())
        netloc = (parsed.netloc or "").strip()
        if not netloc:
            return False
        # Strip leading 'www.'
        if netloc.startswith("www."):
            netloc = netloc[4:]
        # Exclude aggregator domains (and subdomains, e.g. uk.linkedin.com)
        for agg in AGGREGATOR_DOMAINS:
            if agg in netloc or netloc.endswith("." + agg):
                return False
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 1. search_jobs: Tavily search with Brave fallback
# ---------------------------------------------------------------------------

def _search_with_tavily(query: str, limit: int, exclude_domains: list[str] | None = None) -> list[dict[str, str]]:
    """Search via Tavily Search API. Returns list of {title, url, snippet}. Optionally exclude domains (e.g. aggregators)."""
    api_key = settings.tavily_api_key or os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return []
    payload = {
        "query": query,
        "max_results": limit,
        "search_depth": "basic",
    }
    if exclude_domains:
        payload["exclude_domains"] = list(exclude_domains)[:150]  # Tavily max 150
    resp = httpx.post(
        "https://api.tavily.com/search",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json=payload,
        timeout=20.0,
    )
    # If Tavily rejects the request (including quota exceeded), let caller fall back.
    resp.raise_for_status()
    data = resp.json()
    results: list[dict[str, str]] = []
    for item in data.get("results", []) or []:
        title = item.get("title") or ""
        url = item.get("url") or ""
        content = item.get("content") or ""
        if url:
            results.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": content,
                }
            )
    return results


def _search_with_brave(query: str, limit: int) -> list[dict[str, str]]:
    """Search via Brave Search API. Returns list of {title, url, snippet}."""
    api_key = settings.brave_search_api_key or os.environ.get("BRAVE_SEARCH_API_KEY")
    if not api_key:
        return []
    resp = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={
            "X-Subscription-Token": api_key,
        },
        params={
            "q": query,
            "count": limit,
            "offset": 0,
        },
        timeout=20.0,
    )
    resp.raise_for_status()
    data = resp.json()
    results: list[dict[str, str]] = []
    for item in (data.get("web") or {}).get("results", []) or []:
        title = item.get("title") or ""
        url = item.get("url") or ""
        desc = item.get("description") or ""
        if url:
            results.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": desc,
                }
            )
    return results


def search_jobs(query: str, max_results: int = 10, exclude_aggregators: bool = False) -> dict[str, Any]:
    """
    Search the web for job listings using Tavily, with Brave as fallback.

    - First tries Tavily (`TAVILY_API_KEY` env var) with max_results up to 20.
    - If exclude_aggregators is True, Tavily is called with exclude_domains so LinkedIn, Indeed, etc. are not returned.
    - If Tavily fails (e.g. quota exhausted) or returns no results, falls back to Brave.
    - Returns: {status, results: [{title, snippet, url}], source}
    """
    max_results = min(max(1, max_results), 20)
    errors: list[str] = []
    exclude_domains = list(AGGREGATOR_DOMAINS) if exclude_aggregators else None

    # Try Tavily first
    try:
        tavily_results = _search_with_tavily(query, max_results, exclude_domains=exclude_domains)
    except httpx.HTTPStatusError as e:
        # Treat 4xx/5xx as failure; record and fall back.
        errors.append(f"Tavily HTTP {e.response.status_code}: {e.response.text[:200]}")
        tavily_results = []
    except Exception as e:  # noqa: BLE001
        errors.append(f"Tavily error: {e}")
        tavily_results = []

    if tavily_results:
        return {
            "status": "success",
            "source": "tavily",
            "results": tavily_results,
        }

    # Brave fallback
    try:
        brave_results = _search_with_brave(query, max_results)
    except httpx.HTTPStatusError as e:
        errors.append(f"Brave HTTP {e.response.status_code}: {e.response.text[:200]}")
        brave_results = []
    except Exception as e:  # noqa: BLE001
        errors.append(f"Brave error: {e}")
        brave_results = []

    if brave_results:
        return {
            "status": "success",
            "source": "brave",
            "results": brave_results,
        }

    return {
        "status": "error",
        "message": "Both Tavily and Brave search failed or returned no results.",
        "errors": errors,
        "results": [],
    }


def _build_job_search_query(query: str) -> str:
    """Build a search query that forces company career page URLs (inurl:careers OR inurl:jobs)."""
    q = (query or "").strip() or "software engineer jobs"
    if "inurl:careers" in q.lower() or "inurl:jobs" in q.lower():
        return q
    return f"({q}) (inurl:careers OR inurl:jobs)"


# ---------------------------------------------------------------------------
# 1b. Google Jobs search (SerpApi) – same results as google.com/search?q=...&udm=8, parsed
# ---------------------------------------------------------------------------
def _search_google_jobs_serpapi(query: str, limit: int) -> list[dict[str, Any]]:
    """
    Search Google Jobs via SerpApi. Returns list of job dicts with title, company, location,
    description, salary, url (real apply link when possible). Requires SERPAPI_API_KEY (or serpapi_api_key in settings).
    """
    api_key = settings.serpapi_api_key or os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        return []
    q = (query or "").strip() or "software engineer jobs"
    params = {
        "engine": "google_jobs",
        "q": q,
        "gl": os.environ.get("SERPAPI_GL", "us"),
        "hl": os.environ.get("SERPAPI_HL", "en"),
        "api_key": api_key,
    }
    location = os.environ.get("SERPAPI_LOCATION")
    if location:
        params["location"] = location
    try:
        logger.info("Google Jobs: querying SerpApi (engine=google_jobs, q=%r)", q)
        resp = httpx.get(
            "https://serpapi.com/search",
            params=params,
            timeout=25.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("Google Jobs: SerpApi request failed: %s", e)
        return []
    raw_jobs = data.get("jobs_results") or []
    logger.info("Google Jobs: SerpApi returned %d raw results", len(raw_jobs))
    jobs_out: list[dict[str, Any]] = []
    for job in raw_jobs[:limit]:
        title = (job.get("title") or "").strip()
        company = (job.get("company_name") or "").strip()
        location_str = (job.get("location") or "").strip()
        description = (job.get("description") or "").strip()
        det = job.get("detected_extensions") or {}
        salary = (det.get("salary") or "").strip()
        # Prefer real apply URL: first career-page link from apply_options, else first apply link, else share_link
        share_link = (job.get("share_link") or "").strip()
        apply_opts = job.get("apply_options") or []
        url = share_link
        for opt in apply_opts:
            link = (opt.get("link") or "").strip()
            if not link:
                continue
            if _is_career_page_url(link):
                url = link
                break
            if url == share_link:
                url = link
        if not url and apply_opts:
            url = (apply_opts[0].get("link") or "").strip() or share_link
        jobs_out.append({
            "title": title or "Job",
            "company": company,
            "location": location_str,
            "description": description,
            "salary": salary,
            "url": url or "",
        })
    return jobs_out


def search_google_jobs(query: str, max_results: int = 10) -> dict[str, Any]:
    """
    Search Google Jobs (e.g. google.com/search?q=...&udm=8). Uses SerpApi when SERPAPI_API_KEY
    is set; returns job list with title, company, location, description, salary, and apply URL.
    """
    jobs = _search_google_jobs_serpapi(query, max_results)
    if jobs:
        logger.info("Google Jobs: returning %d parsed jobs", len(jobs))
        return {"status": "success", "source": "google_jobs", "results": jobs}
    logger.info("Google Jobs: no results (SERPAPI_API_KEY may be unset or SerpApi returned empty)")
    return {"status": "error", "message": "Google Jobs returned no results (is SERPAPI_API_KEY set?).", "results": []}


search_jobs_tool = FunctionTool(func=search_jobs)
search_google_jobs_tool = FunctionTool(func=search_google_jobs)


# ---------------------------------------------------------------------------
# 2. search_and_save_jobs: Google Jobs first (SerpApi), then Tavily/Brave + fetch & parse
# ---------------------------------------------------------------------------
def search_and_save_jobs(query: str, max_results: int = 10) -> dict[str, Any]:
    """
    Search for job listings: first tries Google Jobs (SerpApi; same as google.com/search?q=...&udm=8),
    which returns parsed job descriptions and apply links. If unavailable, falls back to Tavily/Brave
    with company career page filter and fetches each page to extract full job data.
    """
    q = (query or "").strip() or "software engineer jobs"
    logger.info("Job crawl started: query=%r, max_results=%d", q, max_results)

    # 1) Try Google Jobs (SerpApi) – returns list of jobs with description and apply URL
    logger.info("Job crawl: searching Google Jobs (SerpApi)...")
    google_out = search_google_jobs(query=q, max_results=max_results)
    if google_out.get("status") == "success" and google_out.get("results"):
        jobs = []
        for r in google_out["results"]:
            title = (r.get("title") or "").strip() or "Job"
            company = (r.get("company") or "").strip()
            location = (r.get("location") or "").strip()
            description = (r.get("description") or "").strip()
            url = (r.get("url") or "").strip()
            salary = (r.get("salary") or "").strip()
            if not url:
                continue
            jobs.append({"title": title, "company": company, "location": location, "description": description, "url": url, "salary": salary})
        if jobs:
            logger.info("Job crawl: saving %d jobs to store (source=google_jobs)", len(jobs))
            result = add_jobs_to_store(jobs)
            result["source"] = "google_jobs"
            result["message"] = f"Found {len(jobs)} jobs from Google Jobs (parsed descriptions and apply links)."
            logger.info("Job crawl completed: added %d jobs from Google Jobs", len(jobs))
            return result
        logger.info("Job crawl: Google Jobs returned results but none had valid URLs, falling back to web search")

    # 2) Fallback: Tavily/Brave with inurl:careers|jobs, filter to career pages, fetch & extract
    logger.info("Job crawl: falling back to Tavily/Brave (inurl:careers|jobs)...")
    search_query = _build_job_search_query(q)
    fetch_limit = min(max(max_results * 3, 15), 20)
    out = search_jobs(query=search_query, max_results=fetch_limit, exclude_aggregators=True)
    if out.get("status") != "success" or not out.get("results"):
        logger.warning("Job crawl: web search returned no results: %s", out.get("message", ""))
        return {
            "status": "error",
            "message": out.get("message", "Search returned no results. Set SERPAPI_API_KEY for Google Jobs."),
            "added": 0,
            "source": out.get("source"),
        }
    logger.info("Job crawl: web search returned %d results, filtering to career-page URLs...", len(out["results"]))
    career_urls = []
    seen = set()
    for r in out["results"]:
        u = (r.get("url") or "").strip()
        if not u or u in seen or not _is_career_page_url(u):
            continue
        seen.add(u)
        career_urls.append(u)
        if len(career_urls) >= max_results:
            break
    if not career_urls:
        logger.info("Job crawl: no career-page URLs after filter, done (0 added)")
        return {
            "status": "success",
            "added": 0,
            "source": out.get("source", ""),
            "message": "No company career page URLs found. Set SERPAPI_API_KEY to use Google Jobs.",
        }
    logger.info("Job crawl: fetching and extracting %d career pages...", len(career_urls))
    jobs = []
    for i, url in enumerate(career_urls, 1):
        logger.info("Job crawl: fetching job %d/%d: %s", i, len(career_urls), url[:80] + "..." if len(url) > 80 else url)
        extracted = fetch_and_extract_job(url)
        if extracted.get("status") != "success":
            continue
        title = (extracted.get("title") or "").strip()
        description = (extracted.get("description") or "").strip()
        if not title and not description:
            continue
        jobs.append({
            "title": title or "Job",
            "company": (extracted.get("company") or "").strip(),
            "location": (extracted.get("location") or "").strip(),
            "description": description,
            "url": url,
            "salary": (extracted.get("salary") or "").strip(),
        })
    if not jobs:
        logger.warning("Job crawl: no jobs extracted from %d career pages", len(career_urls))
        return {"status": "success", "added": 0, "source": out.get("source", ""), "message": "Could not extract job data from career pages."}
    logger.info("Job crawl: saving %d extracted jobs to store...", len(jobs))
    result = add_jobs_to_store(jobs)
    result["source"] = out.get("source", "")
    result["career_urls_processed"] = len(career_urls)
    logger.info("Job crawl completed: added %d jobs (source=%s)", result["added"], result["source"])
    return result


search_and_save_jobs_tool = FunctionTool(func=search_and_save_jobs)


# ---------------------------------------------------------------------------
# 2b. Fetch page text: httpx first, Tavily Extract as fallback (for 403 / blocks)
# ---------------------------------------------------------------------------
def _fetch_page_text(url: str) -> str | None:
    """Fetch page content: try httpx first; on failure try Tavily Extract. Returns plain text or None."""
    try:
        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            resp = client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; JobCrawler/1.0)"},
            )
            resp.raise_for_status()
            text = resp.text
    except Exception:
        text = None
    if text and len(text.strip()) > 100:
        return text
    # Fallback: Tavily Extract
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return None
    try:
        r = httpx.post(
            "https://api.tavily.com/extract",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={"urls": [url], "format": "text", "extract_depth": "advanced"},
            timeout=30.0,
        )
        r.raise_for_status()
        data = r.json()
        for item in data.get("results") or []:
            if item.get("url") == url or url in (item.get("url") or ""):
                raw = (item.get("raw_content") or "").strip()
                if raw:
                    return raw
        if data.get("results"):
            raw = (data["results"][0].get("raw_content") or "").strip()
            if raw:
                return raw
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# 3. fetch_and_extract_job: fetch URL and use Bedrock to extract job fields
# ---------------------------------------------------------------------------
def _extract_job_with_bedrock(page_text: str, url: str) -> dict[str, Any]:
    """Call Bedrock to extract structured job fields from page text."""
    import boto3
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
    client = boto3.client("bedrock-runtime", region_name=region)
    # Use a model that supports tool use / structured output; Claude Haiku is fast and cheap
    model_id = os.environ.get("BEDROCK_JOB_EXTRACT_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")
    prompt = f"""Extract job posting fields from the following web page text. Return ONLY a valid JSON object with these keys: title, company, location, description, salary (optional, use empty string if not found), url. Use the provided URL for the url field. If the page is not a job posting, return {{"title": "", "company": "", "location": "", "description": "", "salary": "", "url": "{url}"}}.

Page text:
{page_text[:12000]}

JSON:"""
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    })
    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    out = json.loads(response["body"].read())
    content = out.get("content", [])
    if not content:
        return {"title": "", "company": "", "location": "", "description": "", "salary": "", "url": url}
    text = content[0].get("text", "")
    # Parse JSON from response (may be wrapped in markdown)
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"title": "", "company": "", "location": "", "description": "", "salary": "", "url": url}


def fetch_and_extract_job(url: str) -> dict[str, Any]:
    """
    Fetch a job page URL (httpx, then Tavily Extract if blocked) and extract title, company,
    location, description, salary using Bedrock. Returns a dict with keys: title, company,
    location, description, salary, url, status.
    """
    text = _fetch_page_text(url)
    if not text or len(text.strip()) < 50:
        return {
            "status": "error",
            "error": "Could not fetch page (blocked or empty)",
            "title": "",
            "company": "",
            "location": "",
            "description": "",
            "salary": "",
            "url": url,
        }
    # Strip HTML tags if present (Tavily may return text already)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    job = _extract_job_with_bedrock(text[:12000], url)
    job["status"] = "success"
    return job


fetch_and_extract_job_tool = FunctionTool(func=fetch_and_extract_job)


# ---------------------------------------------------------------------------
# 4. add_jobs_to_store: normalize job dicts, add to Chroma and PostgreSQL
# ---------------------------------------------------------------------------
def add_jobs_to_store(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Add job records to the vector store (Chroma) and optionally to PostgreSQL.
    Each job should have title, company, location, description, url.
    """
    if not jobs:
        logger.info("add_jobs_to_store: no jobs to add")
        return {"status": "success", "added": 0, "message": "No jobs to add."}
    logger.info("add_jobs_to_store: adding %d jobs to Chroma and DB", len(jobs))
    store = _get_store()
    texts = []
    metadatas = []
    for j in jobs:
        title = j.get("title") or ""
        company = j.get("company") or ""
        location = j.get("location") or ""
        description = j.get("description") or ""
        url = j.get("url") or ""
        salary = j.get("salary") or ""
        text = f"Title: {title}\nCompany: {company}\nLocation: {location}\nDescription: {description}\nSalary: {salary}\nURL: {url}"
        texts.append(text)
        metadatas.append({"source": "job", "title": title[:500], "url": url[:1000]})
    ids = store.add_documents(texts=texts, metadatas=metadatas)
    # PostgreSQL: job_runs + jobs when DATABASE_URL is set
    run_id = None
    if settings.has_database:
        run_id = recruitment_db.insert_job_run(query_or_source="add_jobs_to_store")
        if run_id:
            recruitment_db.insert_jobs(run_id, jobs, ids)
            recruitment_db.finish_job_run(run_id, len(ids))
            logger.info("add_jobs_to_store: saved to PostgreSQL (job_run_id=%s)", run_id)
    return {
        "status": "success",
        "added": len(ids),
        "ids": ids,
        "job_run_id": run_id,
    }


add_jobs_to_store_tool = FunctionTool(func=add_jobs_to_store)
