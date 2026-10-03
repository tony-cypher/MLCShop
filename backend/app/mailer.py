"""Transactional email.

Uses SMTP (e.g. Gmail) when ``MAIL_MAILER=smtp``, Resend when
``MAIL_MAILER=resend``, and otherwise writes each message to the application
log (the Laravel ``log`` driver equivalent) so sign-up and checkout work
end-to-end without keys.
"""

from __future__ import annotations

import logging
import smtplib
from decimal import Decimal
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
import resend

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


def _send_smtp(to: str, subject: str, html: str, text: str | None = None) -> bool:
    """Send via SMTP (e.g. Gmail with TLS)."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((settings.mail_from_name, settings.mail_from_address))
        msg["To"] = to

        if text:
            msg.attach(MIMEText(text, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15.0) as server:
            if settings.smtp_tls:
                server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.mail_from_address, [to], msg.as_string())

        logger.info("SMTP email delivered to %s via %s", to, settings.smtp_host)
        return True
    except Exception:
        logger.exception("SMTP delivery to %s failed", to)
        return False


def _send_resend(to: str, subject: str, html: str, text: str | None = None) -> bool:
    """Send via Resend API."""
    sender = f"{settings.mail_from_name} <{settings.mail_from_address}>"
    try:
        resend.api_key = settings.resend_api_key
        params: resend.Emails.SendParams = {
            "from": sender,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if text:
            params["text"] = text

        response = resend.Emails.send(params)
        logger.info("Resend email delivered to %s, id=%s", to, response.get("id"))
        return True
    except Exception:
        logger.exception("Resend delivery to %s failed", to)
        return False


def send(to: str, subject: str, html: str, text: str | None = None) -> bool:
    """Deliver a message. Never raises — mail failure must not break requests."""
    if settings.mail_mailer.lower() == "smtp":
        if not settings.smtp_enabled:
            logger.info(
                "[mail:log] to=%s subject=%r (MAIL_MAILER=smtp but credentials missing — message not sent)\n%s",
                to,
                subject,
                html,
            )
            return False
        return _send_smtp(to, subject, html, text)

    if settings.mail_mailer.lower() == "resend":
        if not settings.resend_enabled:
            logger.info(
                "[mail:log] to=%s subject=%r (MAIL_MAILER=resend but RESEND_API_KEY missing — message not sent)\n%s",
                to,
                subject,
                html,
            )
            return False
        return _send_resend(to, subject, html, text)

    logger.info(
        "[mail:log] to=%s subject=%r (MAIL_MAILER=%s — message not sent)\n%s",
        to,
        subject,
        settings.mail_mailer,
        html,
    )
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
