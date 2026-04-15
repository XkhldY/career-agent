#!/usr/bin/env python3
"""Clean PostgreSQL jobs and Chroma collection. Load .env from repo root or backend/."""

from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Load .env from root or backend
try:
    from dotenv import load_dotenv
    for d in (ROOT, BACKEND):
        if (d / ".env").exists():
            load_dotenv(d / ".env")
            break
except ImportError:
    pass

from app.core import db
from app.agents.shared.store import clear_collection


def main():
    jobs_deleted, runs_deleted = db.delete_all_jobs()
    print(f"PostgreSQL: deleted {jobs_deleted} job(s), {runs_deleted} job run(s).")
    chroma_deleted = clear_collection()
    print(f"ChromaDB: cleared {chroma_deleted} document(s).")
    if jobs_deleted == 0 and runs_deleted == 0 and chroma_deleted == 0:
        print("Nothing to clean (DBs empty or not configured).")
    else:
        print("Done.")


if __name__ == "__main__":
    main()
