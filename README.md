# Agentics

Job crawl and talent chat app. Three main folders:

- **backend/** – Python FastAPI API, ADK jobs agent, PostgreSQL + Chroma. See `backend/README.md`.
- **frontend/** – Next.js app (Crawl + Chat tabs). To be scaffolded.
- **terraform/** – AWS (RDS, Chroma EC2). Run `terraform apply` then set `DATABASE_URL` and `CHROMA_HOST` from outputs.

## Quick start

1. From repo root, use the same venv for backend and ADK:
   ```bash
   pip install -r backend/requirements.txt
   # Or: pip install -r requirements.txt  # if kept in sync
   ```
2. Copy `.env.example` to `.env` and set `DATABASE_URL`, `CHROMA_HOST`, AWS keys, and API keys.
3. Run backend: `PYTHONPATH=backend uvicorn app.main:app --reload --port 8000`
4. Run job crawl: `POST http://localhost:8000/api/jobs/crawl` with `{"query": "...", "max_jobs": 10}`.

Clean DB (PostgreSQL + Chroma): `python backend/scripts/clean_db.py` (loads `.env` from root or backend).
