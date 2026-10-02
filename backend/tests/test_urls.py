"""Dynamic URL resolution — the OAuth callback and frontend redirect must adapt
to the deployment (Render/Vercel) without any hard-coded host."""

from __future__ import annotations

from starlette.requests import Request

from app import urls
from app.config import settings


def make_request(headers: dict[str, str] | None = None, host: str = "mlc-api.onrender.com") -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": raw,
            "server": (host, 443),
            "scheme": "https",
            "query_string": b"",
        }
    )


def test_callback_url_prefers_explicit_redirect_uri(monkeypatch):
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    monkeypatch.setattr(settings, "google_redirect_uri", "https://shop.example.com/api/auth/google/callback")
    monkeypatch.setattr(settings, "app_url", "https://ignored.example.com")
    assert urls.google_callback_url(make_request()) == "https://shop.example.com/api/auth/google/callback"


def test_callback_url_uses_render_external_url(monkeypatch):
    monkeypatch.setattr(settings, "google_redirect_uri", "")
    monkeypatch.setattr(settings, "app_url", "")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://mlcshop.onrender.com")
    assert urls.google_callback_url(make_request()) == "https://mlcshop.onrender.com/api/auth/google/callback"


def test_callback_url_falls_back_to_request_host(monkeypatch):
    monkeypatch.setattr(settings, "google_redirect_uri", "")
    monkeypatch.setattr(settings, "app_url", "")
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    request = make_request({"x-forwarded-proto": "https", "host": "custom.example.com"})
    assert urls.google_callback_url(request) == "https://custom.example.com/api/auth/google/callback"


def test_frontend_origin_prefers_allowlisted_candidate(monkeypatch):
    monkeypatch.setattr(settings, "frontend_url", "https://mlc-shop.vercel.app")
    monkeypatch.setattr(settings, "cors_allowed_origins", "")
    assert urls.frontend_origin(make_request(), "https://mlc-shop.vercel.app") == "https://mlc-shop.vercel.app"


def test_frontend_origin_rejects_unknown_candidate(monkeypatch):
    monkeypatch.setattr(settings, "frontend_url", "https://mlc-shop.vercel.app")
    monkeypatch.setattr(settings, "cors_allowed_origins", "")
    monkeypatch.setattr(settings, "cors_allowed_origins_patterns", "")
    # Evil origin is ignored; the configured frontend wins.
    assert urls.frontend_origin(make_request(), "https://evil.example.com") == "https://mlc-shop.vercel.app"


def test_frontend_origin_accepts_real_origin_when_frontend_is_left_localhost(monkeypatch):
    # The classic failure: FRONTEND_URL still points at localhost after deploy.
    monkeypatch.setattr(settings, "frontend_url", "http://localhost:5173")
    monkeypatch.setattr(settings, "cors_allowed_origins", "")
    monkeypatch.setattr(settings, "cors_allowed_origins_patterns", "")
    request = make_request({"referer": "https://mlc-shop.vercel.app/login"})
    assert urls.frontend_origin(request) == "https://mlc-shop.vercel.app"
    assert settings.frontend_is_public is False


def test_frontend_origin_uses_referer_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "frontend_url", "")
    monkeypatch.setattr(settings, "cors_allowed_origins", "")
    monkeypatch.setattr(settings, "cors_allowed_origins_patterns", "")
    request = make_request({"referer": "https://my-app.vercel.app/login"})
    assert urls.frontend_origin(request) == "https://my-app.vercel.app"


def test_state_roundtrip():
    state = urls.encode_state("https://mlc-shop.vercel.app")
    assert urls.decode_state(state) == "https://mlc-shop.vercel.app"
    assert urls.decode_state("not-base64!!") is None
    assert urls.decode_state(None) is None


def test_google_redirect_builds_callback_from_request(client, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "client-id")
    monkeypatch.setattr(settings, "google_client_secret", "client-secret")
    monkeypatch.setattr(settings, "google_redirect_uri", "")
    monkeypatch.setattr(settings, "app_url", "")
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)

    response = client.get(
        "/api/auth/google/redirect",
        params={"origin": "http://testserver"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "redirect_uri=http%3A%2F%2Ftestserver%2Fapi%2Fauth%2Fgoogle%2Fcallback" in location
    assert "state=" in location
    assert "localhost" not in location
