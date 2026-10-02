"""Application configuration.

Mirrors the environment surface of the original Laravel backend so the same
Render/Vercel deployment variables keep working: ``DB_*`` for Supabase
Postgres, ``MAILGUN_*`` for email, ``GOOGLE_*`` for OAuth, ``FRONTEND_URL``
for CORS + email links.
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    app_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

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
    mail_mailer: str = "log"  # "log" | "mailgun"
    mail_from_address: str = "no-reply@mg.yourdomain.com"
    mail_from_name: str = "MLC"
    mailgun_domain: str = ""
    mailgun_secret: str = ""
    mailgun_endpoint: str = "default"  # "default" | "api.eu.mailgun.net" | full URL

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
    def allowed_origin_regex(self) -> str | None:
        patterns = [p.strip() for p in self.cors_allowed_origins_patterns.split(",") if p.strip()]
        return "|".join(patterns) if patterns else None

    @property
    def google_callback_url(self) -> str:
        return self.google_redirect_uri or f"{self.app_url.rstrip('/')}/api/auth/google/callback"

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def mailgun_enabled(self) -> bool:
        return (
            self.mail_mailer.lower() == "mailgun"
            and bool(self.mailgun_domain)
            and bool(self.mailgun_secret)
        )

    @property
    def mailgun_base_url(self) -> str:
        endpoint = (self.mailgun_endpoint or "default").strip()
        if endpoint.startswith("http"):
            return endpoint.rstrip("/")
        if endpoint in {"default", ""}:
            return "https://api.mailgun.net"
        return f"https://{endpoint.strip('/')}"


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
