"""Database engine/session wiring.

Works against Supabase Postgres in production (``DB_*`` env vars) and against
SQLite out of the box for local development.
"""

from __future__ import annotations

import warnings
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import Base

# SQLite has no native DECIMAL — SQLAlchemy converts through floats and emits
# a one-off warning. The values are 2-decimal catalogue prices, so this is safe.
warnings.filterwarnings(
    "ignore",
    message="Dialect sqlite.*does \\*not\\* support Decimal objects natively",
    category=Warning,
)

if settings.is_sqlite:
    engine = create_engine(
        settings.resolved_database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _connection_record):  # pragma: no cover - trivial
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

else:
    engine = create_engine(
        settings.resolved_database_url,
        pool_pre_ping=True,
        pool_recycle=280,
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    Base.metadata.create_all(bind=engine)
