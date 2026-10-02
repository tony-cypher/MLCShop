"""Test-only checkout.

Validates the card shape (Luhn) and stock, writes the order and decrements
inventory — but never talks to a payment processor and never charges anything.
"""

from __future__ import annotations

import calendar
import re
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import urls
from ..database import get_db
from ..deps import get_optional_user
from ..errors import ApiValidationError
from ..mailer import send_order_confirmed_email
from ..models import Order, OrderItem, Product, User, utcnow
from ..ratelimit import checkout_throttle
from ..schemas import CheckoutRequest
from ..security import random_suffix
from ..serializers import order_payload

router = APIRouter()

FREE_SHIPPING_OVER = 100
SHIPPING_FLAT = Decimal("9.99")

_EXPIRY_RE = re.compile(r"^(0[1-9]|1[0-2])/\d{2}$")


def _round(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@router.post("/checkout", status_code=201, dependencies=[Depends(checkout_throttle)])
def store(
    payload: CheckoutRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> dict:
    address = _validated_address(payload)
    _assert_test_card_is_valid(payload)

    try:
        order = _place_order(db, payload, address, user)
    except ApiValidationError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    db.commit()
    db.refresh(order)

    send_order_confirmed_email(order, frontend_base=urls.frontend_origin(request))

    return {
        "data": order_payload(order),
        "message": "Order placed — test payment approved. A confirmation email is on its way.",
    }


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #


def _validated_address(payload: CheckoutRequest) -> dict | None:
    if payload.delivery_method != "standard":
        return None

    address = payload.address
    values = {
        "line1": address.line1 if address else None,
        "city": address.city if address else None,
        "state": address.state if address else None,
        "zip": address.zip if address else None,
        "country": address.country if address else None,
    }

    errors = {
        f"address.{field}": [f"The address.{field} field is required."]
        for field, value in values.items()
        if not value
    }
    if errors:
        raise ApiValidationError(errors)

    return {field: value.strip() for field, value in values.items() if value}


def _assert_test_card_is_valid(payload: CheckoutRequest) -> None:
    payment = payload.payment
    number = re.sub(r"\D", "", payment.card_number)

    if len(number) < 13 or len(number) > 19 or not _passes_luhn(number):
        raise ApiValidationError(
            {
                "payment.card_number": [
                    "That test card number is invalid. Try 4242 4242 4242 4242."
                ]
            }
        )

    if not _EXPIRY_RE.match(payment.expiry):
        raise ApiValidationError(
            {"payment.expiry": ["Use the MM/YY format, e.g. 12/29."]}
        )

    month, year = payment.expiry.split("/")
    last_day = calendar.monthrange(2000 + int(year), int(month))[1]
    expires_at = datetime(2000 + int(year), int(month), last_day, 23, 59, 59, tzinfo=timezone.utc)

    if expires_at < utcnow():
        raise ApiValidationError({"payment.expiry": ["That test card is expired."]})


def _passes_luhn(number: str) -> bool:
    total = 0
    alternate = False
    for char in reversed(number):
        digit = int(char)
        if alternate:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
        alternate = not alternate
    return total % 10 == 0


# --------------------------------------------------------------------------- #
# Order placement
# --------------------------------------------------------------------------- #


def _place_order(
    db: Session,
    payload: CheckoutRequest,
    address: dict | None,
    user: User | None,
) -> Order:
    product_ids = [item.product_id for item in payload.items]
    products = {
        product.id: product
        for product in db.scalars(
            select(Product).where(Product.id.in_(product_ids)).with_for_update()
        ).all()
    }

    subtotal = Decimal("0.00")
    lines: list[tuple[Product, int]] = []

    for item in payload.items:
        product = products.get(item.product_id)
        if product is None:
            raise ApiValidationError(
                {"items": ["A product in your cart is no longer available."]}
            )

        if product.stock < item.quantity:
            raise ApiValidationError(
                {"items": [f'Not enough stock for "{product.name}".']}
            )

        if payload.delivery_method == "standard" and not product.delivery_standard:
            raise ApiValidationError(
                {"items": [f'"{product.name}" is not available for standard delivery.']}
            )

        if payload.delivery_method == "pickup" and not product.delivery_pickup:
            raise ApiValidationError(
                {"items": [f'"{product.name}" is not available for pick up.']}
            )

        subtotal += Decimal(str(product.price)) * item.quantity
        lines.append((product, item.quantity))

    subtotal = _round(subtotal)
    # Free standard shipping over $100 — pick up is always free.
    shipping = (
        Decimal("0.00")
        if payload.delivery_method == "pickup" or subtotal >= FREE_SHIPPING_OVER
        else SHIPPING_FLAT
    )
    total = _round(subtotal + shipping)

    card_last4 = re.sub(r"\D", "", payload.payment.card_number)[-4:]

    order = Order(
        reference=f"MLC-{utcnow().strftime('%y%m%d')}-{random_suffix(4)}",
        user_id=user.id if user else None,
        email=payload.customer.email.lower(),
        name=payload.customer.name,
        phone=payload.customer.phone,
        status="confirmed",
        payment_status="test_paid",
        payment_method="test_card",
        card_last4=card_last4,
        delivery_method=payload.delivery_method,
        subtotal=subtotal,
        shipping=shipping,
        total=total,
        address=address,
        placed_at=utcnow(),
    )
    db.add(order)
    db.flush()

    for product, quantity in lines:
        order.items.append(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                name=product.name,
                emoji=product.emoji,
                image_url=product.image_url,
                price=product.price,
                quantity=quantity,
            )
        )
        product.stock -= quantity

    db.flush()
    return order
