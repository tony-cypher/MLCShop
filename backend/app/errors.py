"""Laravel-shaped error responses.

The React client reads ``json.message`` plus an optional ``json.errors`` map
keyed by dotted field names (``customer.name``, ``payment.card_number`` …),
so the API must answer in exactly that shape.
"""

from __future__ import annotations


class ApiError(Exception):
    """Non-validation error rendered as ``{"message": ...}``."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class ApiValidationError(Exception):
    """422 with ``{"message": ..., "errors": {field: [messages]}}``."""

    def __init__(self, errors: dict[str, list[str]], message: str | None = None):
        self.errors = {key: list(value) for key, value in errors.items()}
        first = next((messages[0] for messages in self.errors.values() if messages), None)
        self.message = message or first or "The given data was invalid."
        super().__init__(self.message)


def unauthenticated() -> ApiError:
    return ApiError(401, "Unauthenticated.")


def not_found(message: str = "Not found.") -> ApiError:
    return ApiError(404, message)
