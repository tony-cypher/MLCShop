"""Pydantic → Laravel-style validation error translation."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .errors import ApiValidationError

T = TypeVar("T", bound=BaseModel)


def _field_label(loc: tuple[Any, ...]) -> str:
    return ".".join(str(part) for part in loc)


def _message(error: dict) -> str:
    loc = tuple(error.get("loc", ()))
    label = _field_label(loc) or "field"
    kind = error.get("type", "")
    ctx = error.get("ctx") or {}

    if kind == "missing":
        return f"The {label} field is required."
    if kind == "string_too_short":
        return f"The {label} field must be at least {ctx.get('min_length')} characters."
    if kind == "string_too_long":
        return f"The {label} field must not be greater than {ctx.get('max_length')} characters."
    if kind in {"too_short", "list_too_short"}:
        return f"The {label} field must have at least {ctx.get('min_length')} items."
    if kind in {"too_long", "list_too_long"}:
        return f"The {label} field must not have more than {ctx.get('max_length')} items."
    if kind in {"int_parsing", "int_type", "float_parsing", "decimal_parsing"}:
        return f"The {label} field must be a number."
    if kind == "bool_parsing":
        return f"The {label} field must be true or false."
    if kind in {"literal_error", "enum"}:
        return f"The selected {label} is invalid."
    if kind == "value_error" and "email" in str(error.get("msg", "")).lower():
        return f"The {label} field must be a valid email address."
    if kind == "greater_than_equal":
        return f"The {label} field must be at least {ctx.get('ge')}."
    if kind == "less_than_equal":
        return f"The {label} field must not be greater than {ctx.get('le')}."
    if kind == "greater_than":
        return f"The {label} field must be greater than {ctx.get('gt')}."
    if kind == "less_than":
        return f"The {label} field must be less than {ctx.get('lt')}."

    message = error.get("msg", "The given data was invalid.")
    return message[0].upper() + message[1:] if message else "The given data was invalid."


def errors_from_pydantic(error: ValidationError, *, strip_loc: tuple[str, ...] = ()) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for item in error.errors():
        loc = tuple(item.get("loc", ()))
        if strip_loc and loc[: len(strip_loc)] == strip_loc:
            loc = loc[len(strip_loc) :]
        key = _field_label(loc) or "error"
        grouped.setdefault(key, []).append(_message(item))
    return grouped


def parse_model(model: type[T], payload: Any, *, strip_loc: tuple[str, ...] = ()) -> T:
    """Validate ``payload`` against ``model``, raising ``ApiValidationError``."""
    try:
        return model.model_validate(payload)
    except ValidationError as error:
        raise ApiValidationError(errors_from_pydantic(error, strip_loc=strip_loc)) from None
