"""FastAPI application for job crawl and chat APIs."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, jobs
from app.core.db import create_tables

app = FastAPI(title="Agentics API", version="0.1.0")


@app.on_event("startup")
def on_startup():
    create_tables()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
