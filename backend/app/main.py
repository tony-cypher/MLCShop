"""MLC API — FastAPI application entry point."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .database import create_all
from .errors import ApiError, ApiValidationError
from .routers import auth, cart, catalog, checkout, favorites, orders
from .validation import errors_from_pydantic

logging.basicConfig(
    level=getattr(logging, (settings.log_level or "info").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("mlc")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _initialise_database()
    yield


def _initialise_database() -> None:
    """Create any missing tables, then optionally seed (RUN_SEED=true)."""
    delay = 3
    for attempt in range(1, 6):
        try:
            create_all()
            break
        except Exception as exc:  # pragma: no cover - startup retry path
            if attempt >= 5:
                logger.error("Database still unreachable after %s attempts: %s", attempt, exc)
                raise
            logger.warning("Database not ready (%s) — retrying in %ss", exc, delay)
            time.sleep(delay)
            delay = min(delay * 2, 15)

    if settings.run_seed:
        from .seed import run_seeders

        logger.info("RUN_SEED=true — seeding catalogue")
        run_seeders()
        logger.info("Seeding complete")


app = FastAPI(
    title=f"{settings.app_name} API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=0,
)


# --------------------------------------------------------------------------- #
# Error handlers — every error answers in Laravel's shape
# --------------------------------------------------------------------------- #


@app.exception_handler(ApiError)
async def handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"message": exc.message})


@app.exception_handler(ApiValidationError)
async def handle_validation_error(_request: Request, exc: ApiValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"message": exc.message, "errors": exc.errors},
    )


@app.exception_handler(RequestValidationError)
async def handle_request_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
    from pydantic import ValidationError

    errors = errors_from_pydantic(ValidationError.from_exception_data("Request", exc.errors()), strip_loc=("body",))
    first = next((messages[0] for messages in errors.values() if messages), None)
    return JSONResponse(
        status_code=422,
        content={"message": first or "The given data was invalid.", "errors": errors},
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) and exc.detail else "Not found."
    return JSONResponse(status_code=exc.status_code, content={"message": message})


@app.exception_handler(Exception)
async def handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"message": "Server Error"})


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

app.include_router(catalog.router, prefix="/api", tags=["catalog"])
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(cart.router, prefix="/api", tags=["cart"])
app.include_router(checkout.router, prefix="/api", tags=["checkout"])
app.include_router(favorites.router, prefix="/api", tags=["favorites"])
app.include_router(orders.router, prefix="/api", tags=["orders"])


@app.get("/up", response_class=PlainTextResponse, include_in_schema=False)
def health() -> str:
    """Render's health check path."""
    return "OK"


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"name": f"{settings.app_name} API", "status": "ok", "docs": "/docs"}
