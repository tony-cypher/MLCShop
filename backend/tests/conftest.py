"""Pytest fixtures.

The environment is configured *before* the app package is imported so the
settings singleton points at a throwaway SQLite database and the log mail
driver.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_shop.db")
os.environ.setdefault("MAIL_MAILER", "log")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")
os.environ.setdefault("RUN_SEED", "false")
# A developer's backend/.env can hold real Google credentials; the suite asserts
# the "not configured" behaviour, so force them off regardless of .env.
os.environ["GOOGLE_CLIENT_ID"] = ""
os.environ["GOOGLE_CLIENT_SECRET"] = ""
os.environ["GOOGLE_REDIRECT_URI"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal, create_all, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.ratelimit import auth_throttle, checkout_throttle  # noqa: E402
from app.seed import run_seeders  # noqa: E402

DB_PATH = Path(__file__).resolve().parent.parent / "test_shop.db"


@pytest.fixture(scope="session", autouse=True)
def _prepared_database():
    Base.metadata.drop_all(bind=engine)
    create_all()
    run_seeders()
    yield
    engine.dispose()
    if DB_PATH.exists():
        DB_PATH.unlink()


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """Each test starts with a clean throttle window (all requests share one IP)."""
    auth_throttle.limiter._hits.clear()
    checkout_throttle.limiter._hits.clear()
    yield


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
