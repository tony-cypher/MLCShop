"""Application configuration.

Mirrors the environment surface of the original Laravel backend so the same
Render/Vercel deployment variables keep working: ``DB_*`` for Supabase
Postgres, ``RESEND_*`` for email, ``GOOGLE_*`` for OAuth, ``FRONTEND_URL``
for CORS + email links.
"""

from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

# Origins accepted when the operator configures an explicit allow-list.
# Only used as a safety net when nothing is set, so the SPA + local dev keep
# working without hard-coding a deployment host.
FALLBACK_ORIGIN_PATTERNS = [
    r"https://[a-z0-9-]+\.vercel\.app",
    r"https://[a-z0-9-]+\.onrender\.com",
    r"http://localhost(:\d+)?",
    r"http://127\.0\.0\.1(:\d+)?",
    r"http://\[::1\](:\d+)?",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------- general
    app_name: str = "MLC"
    app_env: str = "local"
    app_debug: bool = True
    # Public base URL of THIS API. Leave blank to auto-detect: Render injects
    # RENDER_EXTERNAL_URL, and the request host is used as a last resort.
    # Never hard-code a host here.
    app_url: str = ""
    # Public base URL of the React storefront. Leave blank to auto-detect from
    # the browser (Origin/Referer). Set it in production — it also drives CORS
    # and the links inside confirmation emails.
    frontend_url: str = ""

    # CORS — the storefront origin (FRONTEND_URL) plus optional extras.
    cors_allowed_origins: str = ""
    cors_allowed_origins_patterns: str = ""

    # ------------------------------------------------------------ database
    # A full SQLAlchemy URL wins when present (Render/Supabase style).
    database_url: str = ""
    # Otherwise assemble one from the individual DB_* values.
    db_connection: str = "sqlite"
    db_host: str = ""
    db_port: int = 5432
    db_database: str = "postgres"
    db_username: str = ""
    db_password: str = ""
    db_sslmode: str = "require"
    # Local dev fallback (SQLite) when nothing else is configured.
    sqlite_path: str = "shop.db"

    # ---------------------------------------------------------------- mail
    mail_mailer: str = "resend"  # "resend" | "log"
    mail_from_address: str = "onboarding@resend.dev"
    mail_from_name: str = "MLC"
    resend_api_key: str = ""

    # --------------------------------------------------------------- google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

    # ------------------------------------------------------------ runtime
    # Set true for a single deploy to seed the catalogue, then back to false.
    run_seed: bool = False
    log_level: str = "info"

    # ------------------------------------------------------------ derived
    @property
    def resolved_database_url(self) -> str:
        """Normalise whatever the platform gave us into a SQLAlchemy URL."""
        if self.database_url:
            return _normalise_url(self.database_url)

        if self.db_connection in {"pgsql", "postgres", "postgresql"} and self.db_host:
            user = quote_plus(self.db_username)
            password = quote_plus(self.db_password)
            url = (
                f"postgresql+psycopg://{user}:{password}"
                f"@{self.db_host}:{self.db_port}/{self.db_database}"
            )
            if self.db_sslmode:
                url += f"?sslmode={quote_plus(self.db_sslmode)}"
            return url

        return f"sqlite:///{self.sqlite_path}"

    @property
    def is_sqlite(self) -> bool:
        return self.resolved_database_url.startswith("sqlite")

    @property
    def allowed_origins(self) -> list[str]:
        raw = self.cors_allowed_origins or self.frontend_url
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def resolved_app_url(self) -> str:
        """Explicit APP_URL, else Render's auto-injected service URL, else ''."""
        return (self.app_url or os.environ.get("RENDER_EXTERNAL_URL", "")).rstrip("/")

    @property
    def frontend_is_public(self) -> bool:
        """False when FRONTEND_URL is unset or still a leftover localhost."""
        url = (self.frontend_url or "").strip().lower()
        if not url:
            return False
        return not any(host in url for host in ("localhost", "127.0.0.1", "[::1]", "0.0.0.0"))

    @property
    def allowed_origin_regex(self) -> str | None:
        patterns = [p.strip() for p in self.cors_allowed_origins_patterns.split(",") if p.strip()]
        if not patterns and not self.frontend_is_public and not self.cors_allowed_origins.strip():
            # Nothing usable configured (unset, or still localhost): keep local
            # dev and common hosts (Vercel/Render) working instead of blocking
            # every cross-origin request.
            patterns = list(FALLBACK_ORIGIN_PATTERNS)
        return "|".join(f"(?:{p})" for p in patterns) if patterns else None

    @property
    def google_callback_url(self) -> str:
        """Env-based callback URL (request-aware resolution lives in app.urls)."""
        base = self.resolved_app_url
        if self.google_redirect_uri:
            return self.google_redirect_uri.strip()
        return f"{base}/api/auth/google/callback" if base else ""

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def resend_enabled(self) -> bool:
        return (
            self.mail_mailer.lower() == "resend"
            and bool(self.resend_api_key)
        )


def _normalise_url(url: str) -> str:
    """Turn a plain Postgres URL into a SQLAlchemy + psycopg one."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
