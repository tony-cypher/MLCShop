"""Authentication: tokens, email confirmation and Google OAuth."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import google_oauth, urls
from ..config import settings
from ..database import get_db
from ..deps import create_token, get_current_user, revoke_current_token
from ..errors import ApiValidationError
from ..mailer import send_verification_email
from ..models import User, utcnow
from ..ratelimit import RateLimiter, auth_throttle
from ..schemas import LoginRequest, RegisterRequest, VerifyEmailRequest
from ..security import hash_password, new_verification_token, random_suffix, verify_password
from ..serializers import user_payload

router = APIRouter(prefix="/auth")
logger = logging.getLogger("mlc.auth")

# "Resend email" is limited to 3 attempts per user per minute.
resend_limiter = RateLimiter(3, 60)


# --------------------------------------------------------------------------- #
# Email + password
# --------------------------------------------------------------------------- #


@router.post("/register", status_code=201, dependencies=[Depends(auth_throttle)])
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    if payload.password != payload.password_confirmation:
        raise ApiValidationError(
            {"password": ["The password field confirmation does not match."]}
        )

    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise ApiValidationError({"email": ["The email has already been taken."]})

    user = User(
        name=payload.name,
        email=email,
        password=hash_password(payload.password),
        verification_token=new_verification_token(),
    )
    db.add(user)
    db.flush()

    _send_verification(user, request)

    token = create_token(db, user, name="spa")
    db.commit()
    db.refresh(user)

    return {
        "data": user_payload(user),
        "token": token,
        "message": f"Account created. We sent a confirmation link to {user.email}.",
    }


@router.post("/login", dependencies=[Depends(auth_throttle)])
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password):
        raise ApiValidationError(
            {"email": ["Those credentials do not match our records."]}
        )

    token = create_token(db, user, name="spa")
    db.commit()

    return {"data": user_payload(user), "token": token}


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return {"data": user_payload(user)}


@router.post("/logout")
def logout(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    revoke_current_token(request, db)
    db.commit()
    return {"message": "Signed out."}


@router.post("/verify-email")
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.verification_token == payload.token))
    if user is None:
        raise ApiValidationError(
            {"token": ["This confirmation link is invalid or has expired."]}
        )

    if user.email_verified_at is None:
        user.email_verified_at = utcnow()
        user.verification_token = None
        db.commit()
        db.refresh(user)

    return {
        "data": user_payload(user),
        "message": "Your email address is confirmed. Welcome aboard!",
    }


@router.post("/resend-verification", dependencies=[Depends(auth_throttle)])
def resend_verification(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    if user.email_verified_at is not None:
        return {"message": "Your email is already confirmed."}

    retry_after = resend_limiter.retry_after(f"resend:{user.id}")
    if retry_after is not None:
        raise ApiValidationError(
            {"email": [f"Too many requests. Please wait {retry_after} seconds."]}
        )

    user.verification_token = new_verification_token()
    db.flush()
    _send_verification(user, request)
    db.commit()

    return {"message": "A new confirmation link is on its way."}


# --------------------------------------------------------------------------- #
# Google OAuth
# --------------------------------------------------------------------------- #


@router.get("/google/config")
def google_config() -> dict:
    return {"data": {"enabled": settings.google_enabled}}


@router.get("/google/redirect", dependencies=[Depends(auth_throttle)])
def google_redirect(request: Request, origin: str | None = None) -> RedirectResponse:
    """Kick off the Google consent screen.

    ``origin`` (sent by the SPA) is remembered in the OAuth ``state`` so the
    callback can return the browser to the correct storefront — no hard-coded
    frontend host required.
    """
    if not settings.google_enabled:
        return _frontend_redirect(request, "/login?error=google", origin)

    redirect_uri = urls.google_callback_url(request)
    if not redirect_uri:
        logger.error(
            "Google OAuth: could not determine the callback URL — set APP_URL "
            "(or GOOGLE_REDIRECT_URI) in the environment."
        )
        return _frontend_redirect(request, "/login?error=google_config", origin)

    state = urls.encode_state(urls.frontend_origin(request, origin))
    logger.info("Google OAuth: starting flow with redirect_uri=%s", redirect_uri)
    return RedirectResponse(
        google_oauth.authorization_url(redirect_uri, state), status_code=302
    )


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    state: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    return_origin = urls.decode_state(state)

    if error or not code or not settings.google_enabled:
        logger.warning("Google OAuth: callback aborted (error=%s, has_code=%s)", error, bool(code))
        return _frontend_redirect(request, "/login?error=google", return_origin)

    redirect_uri = urls.google_callback_url(request)
    try:
        tokens = await google_oauth.exchange_code(code, redirect_uri)
        profile = await google_oauth.fetch_userinfo(tokens.get("access_token", ""))
    except httpx.HTTPStatusError as exc:
        # Google explains the real reason (redirect_uri_mismatch, invalid_client…)
        body = exc.response.text[:500] if exc.response is not None else ""
        logger.error(
            "Google OAuth token/userinfo call failed: %s (redirect_uri=%s) %s",
            exc, redirect_uri, body,
        )
        return _frontend_redirect(request, "/login?error=google", return_origin)
    except Exception:
        logger.exception("Google OAuth callback failed (redirect_uri=%s)", redirect_uri)
        return _frontend_redirect(request, "/login?error=google", return_origin)

    email = (profile.get("email") or "").strip().lower()
    if not email:
        return _frontend_redirect(request, "/login?error=google_email", return_origin)

    google_id = str(profile.get("id") or "") or None
    avatar = profile.get("picture")

    user = db.scalar(select(User).where(User.email == email))

    if user is None:
        user = User(
            name=profile.get("name") or "Google Shopper",
            email=email,
            password=hash_password(random_suffix(40)),
            google_id=google_id,
            avatar_url=avatar,
            # Google has already verified this address.
            email_verified_at=utcnow(),
        )
        db.add(user)
        db.flush()
    else:
        if not user.google_id:
            user.google_id = google_id
        if not user.avatar_url:
            user.avatar_url = avatar

    token = create_token(db, user, name="google-spa")
    db.commit()

    # Fragments never reach server logs.
    return _frontend_redirect(
        request, f"/auth/google/callback#token={token}", return_origin
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _frontend_redirect(
    request: Request, path: str, origin: str | None = None
) -> RedirectResponse:
    base = urls.frontend_origin(request, origin)
    return RedirectResponse(f"{base}{path}", status_code=302)


def _send_verification(user: User, request: Request | None = None) -> None:
    base = urls.frontend_origin(request)
    verify_url = f"{base}/verify?token={user.verification_token}"
    send_verification_email(user, verify_url, frontend_base=base)
