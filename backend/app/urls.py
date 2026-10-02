"""Request-aware URL resolution.

Deploying must not depend on hard-coded hosts. Render injects
``RENDER_EXTERNAL_URL`` for the API, and the browser always knows the storefront
origin, so both the OAuth callback URL (for Google) and the final redirect back
to the React app are derived from the environment and the incoming request, with
explicit ``APP_URL`` / ``FRONTEND_URL`` / ``GOOGLE_REDIRECT_URI`` overrides when
the operator sets them.
"""

from __future__ import annotations

import base64
import json
import os
import re
import secrets
from urllib.parse import urlsplit

from fastapi import Request

from .config import FALLBACK_ORIGIN_PATTERNS, settings


def _first(value: str | None) -> str:
    """Return the first entry of a comma-separated proxy header."""
    return (value or "").split(",")[0].strip()


def _as_origin(value: str | None) -> str | None:
    """Normalise an absolute http(s) URL to ``scheme://host[:port]``."""
    if not value:
        return None
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    return f"{parts.scheme}://{parts.netloc}"


def server_base(request: Request | None = None) -> str:
    """Public base URL of this API, without a trailing slash.

    Precedence: explicit ``APP_URL`` -> Render's ``RENDER_EXTERNAL_URL`` -> the
    host/proto of the incoming request (honouring proxy headers).
    """
    if settings.app_url:
        return settings.app_url.rstrip("/")

    render_url = _first(os.environ.get("RENDER_EXTERNAL_URL"))
    if render_url:
        return render_url.rstrip("/")

    if request is not None:
        host = _first(request.headers.get("x-forwarded-host")) or _first(
            request.headers.get("host")
        )
        if host:
            scheme = _first(request.headers.get("x-forwarded-proto")) or request.url.scheme or "https"
            return f"{scheme}://{host}"
        return str(request.base_url).rstrip("/")

    return ""


def google_callback_url(request: Request | None = None) -> str:
    """The redirect_uri registered with Google — identical for authorize + token."""
    if settings.google_redirect_uri:
        return settings.google_redirect_uri.strip()

    base = server_base(request)
    if not base:
        return ""
    return f"{base}/api/auth/google/callback"


def _patterns() -> list[str]:
    if settings.cors_allowed_origins_patterns.strip():
        return [p.strip() for p in settings.cors_allowed_origins_patterns.split(",") if p.strip()]
    if not settings.frontend_is_public and not settings.cors_allowed_origins.strip():
        # Nothing usable configured (unset, or still localhost) — accept the
        # common deploy + local hosts so the app works out of the box without
        # opening the door to arbitrary origins.
        return list(FALLBACK_ORIGIN_PATTERNS)
    return []


def is_allowed_origin(origin: str | None) -> bool:
    """Whether ``origin`` is one we may redirect the browser back to."""
    origin = _as_origin(origin)
    if not origin:
        return False

    if settings.frontend_url and origin == settings.frontend_url.rstrip("/"):
        return True
    if origin in settings.allowed_origins:
        return True

    return any(re.fullmatch(pattern, origin) for pattern in _patterns())


def frontend_origin(request: Request | None = None, candidate: str | None = None) -> str:
    """Best storefront base URL to hand the browser after OAuth.

    Precedence: an explicitly-passed (and allow-listed) origin -> the request's
    Referer origin -> ``FRONTEND_URL`` -> a localhost dev fallback.
    """
    for source in (candidate, request.headers.get("referer") if request else None):
        origin = _as_origin(source)
        if origin and is_allowed_origin(origin):
            return origin

    if settings.frontend_url:
        return settings.frontend_url.rstrip("/")

    return "http://localhost:5173"


# --------------------------------------------------------------------------- #
# OAuth ``state`` — carries the storefront origin back to the callback
# --------------------------------------------------------------------------- #


def encode_state(frontend_base: str) -> str:
    payload = json.dumps({"o": frontend_base, "n": secrets.token_urlsafe(12)})
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_state(state: str | None) -> str | None:
    if not state:
        return None
    try:
        padded = state + "=" * (-len(state) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded).decode())
    except Exception:
        return None
    origin = data.get("o")
    return origin if isinstance(origin, str) else None
