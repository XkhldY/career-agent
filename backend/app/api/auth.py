"""Auth API: register, login, current user."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from app.core import db
from app.core.config import settings

router = APIRouter()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


class AuthRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict[str, Any]


def _create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiration_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(request: Request) -> dict[str, Any]:
    """FastAPI dependency — extracts and validates the JWT bearer token."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    payload = _decode_token(auth[7:])
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = db.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    user.pop("password_hash", None)
    # is_admin is now a real DB column, set via create_tables() or manual update.
    user["is_admin"] = bool(user.get("is_admin"))
    return user


def require_admin(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Dependency: require the current user to be an admin (403 otherwise)."""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def get_optional_user(request: Request) -> dict[str, Any] | None:
    """Returns user dict if a valid JWT is present, None otherwise. Never raises."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = _decode_token(auth[7:])
    except HTTPException:
        return None
    email = payload.get("email")
    if not email:
        return None
    user = db.get_user_by_email(email)
    if user:
        user.pop("password_hash", None)
    return user


def _user_response(user: dict[str, Any]) -> dict[str, Any]:
    """Strip password_hash and return a safe user dict with is_admin from DB."""
    safe = {k: v for k, v in user.items() if k != "password_hash"}
    safe["is_admin"] = bool(safe.get("is_admin"))
    return safe


@router.post("/register", response_model=AuthResponse)
def register(body: AuthRequest):
    if not settings.has_database:
        raise HTTPException(status_code=503, detail="Database not configured")

    password_hash = _hash_password(body.password)
    user = db.create_user(body.email, password_hash)
    if user is None:
        raise HTTPException(status_code=409, detail="Email already registered")

    token = _create_token(user["id"], user["email"])
    return {"token": token, "user": _user_response(user)}


@router.post("/login", response_model=AuthResponse)
def login(body: AuthRequest):
    if not settings.has_database:
        raise HTTPException(status_code=503, detail="Database not configured")

    user = db.get_user_by_email(body.email)
    if not user or not _verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = _create_token(user["id"], user["email"])
    return {"token": token, "user": _user_response(user)}


@router.get("/me")
def me(user: dict[str, Any] = Depends(get_current_user)):
    """Return current user with is_admin so the frontend can hide Jobs/Crawler for non-admins."""
    return user
