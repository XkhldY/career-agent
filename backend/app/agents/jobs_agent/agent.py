"""
Jobs agent: finds jobs from company career pages, fetches and parses each page,
saves full job data to the store and DB. Uses Tavily/Brave; Chroma + Bedrock.
"""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from .tools import search_and_save_jobs_tool

BEDROCK_MODEL = "bedrock/anthropic.claude-3-haiku-20240307-v1:0"

root_agent = Agent(
    name="jobs_agent",
    model=LiteLlm(model=BEDROCK_MODEL),
    description="Finds job listings from company career pages, fetches and parses each page, and saves full job data to the vector store and database.",
    instruction=(
        "You are a job-ingestion agent. You have one tool:\n"
        "search_and_save_jobs(query, max_results) – search for job listings (Tavily, then Brave), keep only company career page URLs (exclude LinkedIn, Indeed, Glassdoor, etc.), fetch each page and extract full job data (title, company, location, description, salary) with AI, then save to the store and database.\n"
        "When the user asks to find jobs (e.g. 'Find 10 Python developer jobs' or 'software engineer jobs Seattle'):\n"
        "- Call search_and_save_jobs with their query and a sensible max_results (e.g. 5–10).\n"
        "- Reply with how many jobs were added, the query used, and that results are from company career pages (not aggregators).\n"
        "If search returns no career-page URLs or extraction fails, say so. Do not invent URLs or data."
    ),
    tools=[search_and_save_jobs_tool],
)
