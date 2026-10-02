"""Authentication dependencies (Sanctum-style bearer tokens)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .errors import unauthenticated
from .models import AuthToken, User, utcnow
from .security import hash_token, new_token


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        return None
    token = header[7:].strip()
    return token or None


def create_token(db: Session, user: User, name: str = "spa") -> str:
    """Issue a new personal access token and return its plaintext value."""
    plaintext = new_token()
    db.add(AuthToken(user_id=user.id, name=name, token=hash_token(plaintext)))
    db.flush()
    return plaintext


def revoke_current_token(request: Request, db: Session) -> None:
    token = _bearer_token(request)
    if not token:
        return
    record = db.scalar(select(AuthToken).where(AuthToken.token == hash_token(token)))
    if record:
        db.delete(record)


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = _bearer_token(request)
    if not token:
        return None
    record = db.scalar(select(AuthToken).where(AuthToken.token == hash_token(token)))
    if record is None:
        return None
    user = db.get(User, record.user_id)
    if user is None:
        return None

    # Touch last_used_at at most once a minute to keep writes cheap.
    now = utcnow()
    last = record.last_used_at
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    if last is None or now - last > timedelta(seconds=60):
        record.last_used_at = now
        db.commit()

    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_optional_user(request, db)
    if user is None:
        raise unauthenticated()
    return user
