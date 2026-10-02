"""Reusable validated field types."""

from __future__ import annotations

from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator


def _validate_email(value: str) -> str:
    """Validate an address, matching Laravel's permissive ``email`` rule.

    ``test_environment=True`` keeps reserved/example domains usable (the demo
    account is ``demo@mlc.test`` and emails are never really delivered there).
    """
    try:
        validate_email(value, check_deliverability=False, test_environment=True)
    except EmailNotValidError as exc:
        raise ValueError("The email field must be a valid email address.") from exc
    return value


EmailAddress = Annotated[str, AfterValidator(_validate_email)]
