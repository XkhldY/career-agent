"""Run the jobs agent (ADK) in replay mode for job crawl."""

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
AGENTS_DIR = BACKEND_DIR / "app" / "agents"


def run_crawl_sync(query: str, max_jobs: int) -> None:
    """Run the jobs agent in replay mode (blocking). Agents live in backend/app/agents."""
    max_jobs = max(1, min(50, max_jobs))
    logger.info("Running job crawl (adk replay): query=%r, max_jobs=%d", query, max_jobs)
    prompt = f"Find up to {max_jobs} jobs and add them to the store. Search query: {query}."
    replay = {"state": {}, "queries": [prompt]}
    replay_path = BACKEND_DIR / "scripts" / "replay_jobs_crawl.json"
    replay_path.parent.mkdir(parents=True, exist_ok=True)
    replay_path.write_text(json.dumps(replay, indent=2))

    adk = PROJECT_ROOT / ".venv" / "bin" / "adk"
    if not adk.exists():
        adk = Path(PROJECT_ROOT / ".venv" / "Scripts" / "adk.exe")
    if not adk.exists():
        adk_exe = shutil.which("adk")
        adk = Path(adk_exe) if adk_exe else None
    if not adk or not str(adk):
        logger.warning("adk not found, crawl skipped")
        return
    env = {**os.environ, "PYTHONPATH": str(BACKEND_DIR)}
    agent_path = AGENTS_DIR / "jobs_agent"
    cwd = str(PROJECT_ROOT) if (PROJECT_ROOT / ".venv").exists() else str(BACKEND_DIR)
    subprocess.run(
        [str(adk), "run", str(agent_path), "--replay", str(replay_path)],
        cwd=cwd,
        env=env,
    )
    logger.info("Job crawl (adk) process finished")
