"""In-memory rate limiting.

The original app throttled ``auth`` routes to 10/min and ``checkout`` to
8/min per IP. This reproduces that behaviour for a single process; behind
multiple instances a shared store (Redis) would be the next step.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from fastapi import Request

from .errors import ApiError


class RateLimiter:
    def __init__(self, times: int, seconds: int = 60):
        self.times = times
        self.seconds = seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def retry_after(self, key: str) -> Optional[int]:
        """Record a hit; return seconds to wait when the limit is exceeded."""
        now = time.monotonic()
        with self._lock:
            bucket = [stamp for stamp in self._hits.get(key, []) if now - stamp < self.seconds]
            if len(bucket) >= self.times:
                self._hits[key] = bucket
                return max(1, int(self.seconds - (now - bucket[0])) + 1)
            bucket.append(now)
            self._hits[key] = bucket
        return None

    def clear(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def make_throttle(name: str, times: int, seconds: int = 60):
    """Build a FastAPI dependency enforcing ``times`` requests per ``seconds``."""
    limiter = RateLimiter(times, seconds)

    def dependency(request: Request) -> None:
        retry_after = limiter.retry_after(f"{name}:{client_ip(request)}")
        if retry_after is not None:
            raise ApiError(429, "Too Many Attempts.")

    dependency.limiter = limiter  # type: ignore[attr-defined]
    return dependency


auth_throttle = make_throttle("auth", 10, 60)
checkout_throttle = make_throttle("checkout", 8, 60)
