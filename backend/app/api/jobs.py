"""Jobs API: list, get by id/url, crawl. List and crawl are admin-only."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.auth import get_current_user, require_admin
from app.core import db
from app.services.agent import run_crawl_sync

router = APIRouter()

DEFAULT_QUERY = "software engineer jobs"
DEFAULT_MAX_JOBS = 10


class CrawlRequest(BaseModel):
    query: str = Field(default=DEFAULT_QUERY, description="Search query for job listings")
    max_jobs: int = Field(default=DEFAULT_MAX_JOBS, ge=1, le=20, description="Max jobs to find and add")


@router.get("")
def list_jobs(limit: int = 50, _admin=Depends(require_admin)):
    """Return recent jobs from the database. Admin only."""
    limit = max(1, min(limit, 100))
    jobs = db.get_recent_jobs(limit=limit)
    return {"jobs": jobs}


@router.get("/by-url")
def get_job_by_url(url: str = Query(..., description="Job URL"), _user=Depends(get_current_user)):
    """Return a single job by URL (for Chat tab citations). Any logged-in user."""
    job = db.get_job_by_url(url)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}")
def get_job(job_id: str, _user=Depends(get_current_user)):
    """Return a single job by UUID (for Chat tab 'View full job'). Any logged-in user."""
    job = db.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/crawl")
def post_crawl(request: CrawlRequest, _admin=Depends(require_admin)):
    """Run job crawl synchronously and return recent jobs from the database. Admin only."""
    run_crawl_sync(request.query, request.max_jobs)
    jobs = db.get_recent_jobs(limit=request.max_jobs * 2, since_minutes=5)
    if jobs:
        message = f"Crawl finished for query '{request.query}'. Showing {len(jobs)} job(s) below."
    else:
        message = (
            f"Crawl finished for query '{request.query}' but no jobs were found. "
            "To get results, set one of SERPAPI_API_KEY, TAVILY_API_KEY, or BRAVE_SEARCH_API_KEY in your .env (see .env.example)."
        )
    return {
        "status": "success",
        "message": message,
        "query": request.query,
        "max_jobs": request.max_jobs,
        "jobs": jobs,
    }
