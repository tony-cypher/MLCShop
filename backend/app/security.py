"""Password hashing (bcrypt) and opaque bearer-token helpers.

Tokens mirror Sanctum's behaviour: the plaintext value goes to the client once,
only a SHA-256 digest is stored in the database.
"""

from __future__ import annotations

import hashlib
import secrets

import bcrypt

_BCRYPT_MAX_BYTES = 72


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(_prepare(password), hashed.encode("utf-8"))
    except ValueError:
        return False


def new_token() -> str:
    """A fresh plaintext bearer token (40 URL-safe characters)."""
    return secrets.token_urlsafe(30)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_verification_token() -> str:
    """48-character email confirmation token (config expects <= 64 chars)."""
    return secrets.token_hex(24)


def random_suffix(length: int = 4) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))
