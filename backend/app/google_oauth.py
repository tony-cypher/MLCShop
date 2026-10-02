"""Google OAuth 2.0 (the Socialite equivalent, implemented directly)."""

from __future__ import annotations

from urllib.parse import urlencode

import httpx

from .config import settings

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def authorization_url() -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_callback_url,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    """Trade the authorization code for tokens."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_callback_url,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        return response.json()


async def fetch_userinfo(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()
