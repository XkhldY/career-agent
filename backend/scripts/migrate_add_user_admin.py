#!/usr/bin/env python3
"""
One-off migration: add users.is_admin column and set xkhaloda@gmail.com as admin.
Run from repo root: PYTHONPATH=backend .venv/bin/python backend/scripts/migrate_add_user_admin.py
"""

from pathlib import Path

from dotenv import load_dotenv

from app.core.config import settings
from app.core.db import connection

ROOT = Path(__file__).resolve().parent.parent
ADMIN_EMAIL = "xkhaloda@gmail.com"


def main() -> None:
    load_dotenv(ROOT.parent / ".env")
    if not settings.has_database:
        print("DATABASE_URL not set. Skipping migration.")
        return
    with connection() as conn:
        if conn is None:
            print("Could not connect to database. Check DATABASE_URL.")
            return
        with conn.cursor() as cur:
            cur.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;"
            )
            print("Column users.is_admin ensured.")
            cur.execute(
                "UPDATE users SET is_admin = TRUE WHERE lower(trim(email)) = %s;",
                (ADMIN_EMAIL.lower(),),
            )
            n = cur.rowcount
            print(f"Updated {n} row(s) for {ADMIN_EMAIL!r} (is_admin = TRUE).")
    print("Migration done.")


if __name__ == "__main__":
    main()
