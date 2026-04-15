"""Chat API: POST /api/chat – answer questions over jobs in the store with citations."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agents.shared.store import get_store
from app.api.auth import get_current_user
from app.core import db
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

CHAT_MODEL_ID = os.environ.get("BEDROCK_CHAT_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")
MAX_MESSAGE_LENGTH = 4000
TOP_K_JOBS = 5  # number of job sources/citations returned


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH, description="User message")


def _invoke_bedrock(system: str, user_content: str) -> str:
    """Call Bedrock Claude for a single completion. Returns assistant text."""
    import boto3
    region = settings.aws_region or "us-east-1"
    client = boto3.client("bedrock-runtime", region_name=region)
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": system,
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": user_content}]},
        ],
    }
    response = client.invoke_model(
        modelId=CHAT_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    out = json.loads(response["body"].read())
    content = out.get("content", [])
    if not content:
        return ""
    return content[0].get("text", "").strip()


def _build_citations(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn store hits into citation dicts with id, url, title, company (from DB when possible)."""
    citations = []
    seen_urls = set()
    for h in hits:
        url = (h.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        title = (h.get("title") or "").strip() or "Job"
        job = db.get_job_by_url(url) if settings.has_database else None
        if job:
            citations.append({
                "id": str(job.get("id", "")),
                "url": job.get("url", url),
                "title": job.get("title") or title,
                "company": job.get("company") or "",
            })
        else:
            citations.append({
                "id": None,
                "url": url,
                "title": title,
                "company": "",
            })
    return citations


@router.post("")
def post_chat(request: ChatRequest, _user=Depends(get_current_user)):
    """
    Answer the user's question using jobs in the vector store. Returns reply and citations
    (id, url, title, company) for "View full job" in the UI.
    """
    message = request.message.strip()
    store = get_store()
    hits = store.retrieve_with_metadata(message, top_k=TOP_K_JOBS)

    if not hits:
        return {
            "reply": "I don't have any jobs in the store yet. Run a crawl from the Crawl tab first, then I can answer questions about them.",
            "citations": [],
        }

    # Build context with numbered jobs so the model can list them; include company from document when present.
    job_context = "\n\n---\n\n".join(
        f"[Job {i+1}] Title: {h.get('title') or 'Untitled'}\nURL: {h.get('url', '')}\n{h.get('document', '')[:2000]}"
        for i, h in enumerate(hits)
    )
    system = (
        "You are a helpful assistant. Answer using ONLY the job listings below. Do not make up jobs or details.\n"
        "When the user asks for a list of jobs (e.g. '10 Python developer jobs'), list each job on its own line with:\n"
        "number, job title, and company name. Use the exact Title and company from each listing so citations match.\n"
        "Do not summarize multiple jobs into one bullet. For other questions, answer concisely and cite specific jobs by title and company."
    )
    user_content = f"Job listings:\n{job_context}\n\nUser question: {message}"

    try:
        reply = _invoke_bedrock(system, user_content)
    except Exception as e:
        logger.exception("Bedrock chat failed: %s", e)
        raise HTTPException(status_code=503, detail="Chat service temporarily unavailable.")

    citations = _build_citations(hits)
    return {"reply": reply or "I couldn't generate a reply.", "citations": citations}
