# Backend (FastAPI)

API and ADK jobs agent. PostgreSQL + Chroma. All agent and store code lives in `backend/`.

## Run tests

From repo root:

```bash
PYTHONPATH=backend pytest backend/tests/ -v
```

## Run API

From repo root (so `.env` and `.venv` are used):

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

Then: `GET http://localhost:8000/api/jobs`, `POST http://localhost:8000/api/jobs/crawl` with body `{"query": "...", "max_jobs": 10}`.

## Clean DB

From repo root (loads `.env` from root or backend):

```bash
python backend/scripts/clean_db.py
```

## Endpoints

- `GET /api/jobs` – list recent jobs
- `GET /api/jobs/by-url?url=...` – get job by URL
- `GET /api/jobs/{id}` – get job by UUID
- `POST /api/jobs/crawl` – run job crawl (body: `query`, `max_jobs`)
