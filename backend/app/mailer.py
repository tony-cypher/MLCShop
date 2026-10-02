"""Transactional email.

Uses Mailgun when ``MAIL_MAILER=mailgun`` and credentials are present, and
otherwise writes each message to the application log (the Laravel ``log``
driver equivalent) so sign-up and checkout work end-to-end without keys.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import settings
from .models import Order, User

logger = logging.getLogger("mlc.mail")

_TEMPLATES = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _money(value: Any) -> str:
    return f"{Decimal(str(value)):,.2f}"


def render(template: str, **context: Any) -> str:
    return _env.get_template(template).render(**context)


def send(to: str, subject: str, html: str, text: str | None = None) -> bool:
    """Deliver a message. Never raises — mail failure must not break requests."""
    sender = f"{settings.mail_from_name} <{settings.mail_from_address}>"

    if not settings.mailgun_enabled:
        logger.info(
            "[mail:log] to=%s subject=%r (MAIL_MAILER=%s — message not sent)\n%s",
            to,
            subject,
            settings.mail_mailer,
            html,
        )
        return False

    try:
        response = httpx.post(
            f"{settings.mailgun_base_url}/v3/{settings.mailgun_domain}/messages",
            auth=("api", settings.mailgun_secret),
            data={
                "from": sender,
                "to": to,
                "subject": subject,
                "html": html,
                "text": text or "",
            },
            timeout=15.0,
        )
        response.raise_for_status()
        return True
    except Exception:  # pragma: no cover - network failure path
        logger.exception("Mailgun delivery to %s failed", to)
        return False


# --------------------------------------------------------------------------- #
# Messages
# --------------------------------------------------------------------------- #


def send_verification_email(
    user: User, verify_url: str, frontend_base: str | None = None
) -> bool:
    subject = f"Confirm your email — {settings.app_name}"
    html = render(
        "mail/verify_email.html",
        app_name=settings.app_name,
        name=user.name,
        verify_url=verify_url,
        frontend_url=(frontend_base or settings.frontend_url).rstrip("/"),
    )
    text = (
        f"Hi {user.name},\n\n"
        f"Confirm your email for {settings.app_name}:\n{verify_url}\n"
    )
    return send(user.email, subject, html, text)


def send_order_confirmed_email(order: Order, frontend_base: str | None = None) -> bool:
    frontend = (frontend_base or settings.frontend_url).rstrip("/")

    items = [
        {
            "name": item.name,
            "emoji": item.emoji or "",
            "quantity": item.quantity,
            "line_total": _money(Decimal(str(item.price)) * item.quantity),
            "image_src": f"{frontend}{item.image_url}" if item.image_url else None,
        }
        for item in order.items
    ]

    shipping = Decimal(str(order.shipping or 0))
    address = order.address or {}
    if order.delivery_method == "standard" and address:
        fulfilment_note = "Ship to: " + ", ".join(str(value) for value in address.values())
    elif order.delivery_method == "pickup":
        fulfilment_note = "Pick up: collect at your nearest MLC pickup point."
    else:
        fulfilment_note = ""

    html = render(
        "mail/order_confirmed.html",
        app_name=settings.app_name,
        order={
            "name": order.name,
            "reference": order.reference,
            "delivery_method": order.delivery_method,
            "subtotal": _money(order.subtotal),
            "shipping": _money(shipping),
            "shipping_charged": shipping > 0,
            "total": _money(order.total),
        },
        items=items,
        fulfilment_note=fulfilment_note,
    )
    text = (
        f"Thanks, {order.name}!\n\n"
        f"Your order {order.reference} is confirmed (test order — no card was charged).\n"
        f"Total: ${_money(order.total)}\n"
    )
    return send(order.email, f"Order {order.reference} confirmed — {settings.app_name}", html, text)
