"""JSON serialisers that reproduce Laravel's Eloquent output byte-for-byte.

The React storefront was written against Laravel's ``decimal:2`` casts (money
and rating arrive as strings like ``"454.00"``) and ISO-8601 timestamps, so
these helpers keep that contract intact.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from .models import Brand, Category, Order, OrderItem, Product, Review, User


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #


def money(value: Any) -> Optional[str]:
    """Laravel ``decimal:2`` → ``"30.99"`` (string, always 2 decimals)."""
    if value is None:
        return None
    quantised = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantised:.2f}"


def iso(dt: Optional[datetime]) -> Optional[str]:
    """Eloquent's default datetime serialisation (UTC, microseconds, ``Z``)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def iso_8601(dt: Optional[datetime]) -> Optional[str]:
    """``Carbon::toIso8601String()`` → ``2026-10-01T13:41:22+00:00``."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Relationships
# --------------------------------------------------------------------------- #


def category_payload(category: Optional[Category], with_emoji: bool = True) -> Optional[dict]:
    if category is None:
        return None
    payload = {"id": category.id, "name": category.name, "slug": category.slug}
    if with_emoji:
        payload["emoji"] = category.emoji
    return payload


def brand_payload(brand: Optional[Brand]) -> Optional[dict]:
    if brand is None:
        return None
    return {
        "id": brand.id,
        "name": brand.name,
        "slug": brand.slug,
        "initials": brand.initials,
        "color": brand.color,
    }


# --------------------------------------------------------------------------- #
# Catalogue
# --------------------------------------------------------------------------- #


def product_payload(
    product: Product,
    *,
    with_category: bool = True,
    category_emoji: bool = True,
    with_brand: bool = True,
) -> dict:
    payload: dict[str, Any] = {
        "id": product.id,
        "category_id": product.category_id,
        "brand_id": product.brand_id,
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "price": money(product.price),
        "compare_at_price": money(product.compare_at_price),
        "emoji": product.emoji,
        "image_url": product.image_url,
        "badge": product.badge,
        "featured": bool(product.featured),
        "is_deal": bool(product.is_deal),
        "rating": money(product.rating),
        "reviews_count": int(product.reviews_count or 0),
        "rating_chips": product.rating_chips,
        "options": product.options,
        "delivery_standard": bool(product.delivery_standard),
        "delivery_pickup": bool(product.delivery_pickup),
        "stock": int(product.stock or 0),
        "created_at": iso(product.created_at),
        "updated_at": iso(product.updated_at),
    }
    if with_category:
        payload["category"] = category_payload(product.category, with_emoji=category_emoji)
    if with_brand:
        payload["brand"] = brand_payload(product.brand)
    return payload


def review_payload(review: Review) -> dict:
    return {
        "id": review.id,
        "author": review.author,
        "avatar": review.avatar,
        "rating": int(review.rating),
        "comment": review.comment,
        "created_at": iso(review.created_at),
    }


# --------------------------------------------------------------------------- #
# Commerce
# --------------------------------------------------------------------------- #


def order_item_payload(item: OrderItem) -> dict:
    return {
        "id": item.id,
        "order_id": item.order_id,
        "product_id": item.product_id,
        "name": item.name,
        "emoji": item.emoji,
        "image_url": item.image_url,
        "price": money(item.price),
        "quantity": int(item.quantity),
        "created_at": iso(item.created_at),
        "updated_at": iso(item.updated_at),
    }


def order_payload(order: Order, *, with_items: bool = True) -> dict:
    payload: dict[str, Any] = {
        "id": order.id,
        "reference": order.reference,
        "user_id": order.user_id,
        "email": order.email,
        "name": order.name,
        "phone": order.phone,
        "status": order.status,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "card_last4": order.card_last4,
        "delivery_method": order.delivery_method,
        "subtotal": money(order.subtotal),
        "shipping": money(order.shipping),
        "total": money(order.total),
        "address": order.address,
        "placed_at": iso(order.placed_at),
        "created_at": iso(order.created_at),
        "updated_at": iso(order.updated_at),
    }
    if with_items:
        payload["items"] = [order_item_payload(item) for item in order.items]
    return payload


# --------------------------------------------------------------------------- #
# Accounts
# --------------------------------------------------------------------------- #


def user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "email_verified_at": iso_8601(user.email_verified_at),
        "avatar_emoji": "🧑‍🚀",
        "avatar_url": user.avatar_url,
    }


def cart_item_payload(cart_item: Any) -> dict:
    product = cart_item.product
    price_val = float(product.price) if product else 0.0
    compare_val = float(product.compare_at_price) if product and product.compare_at_price else None
    return {
        "id": product.id if product else cart_item.product_id,
        "cart_item_id": cart_item.id,
        "slug": product.slug if product else "",
        "name": product.name if product else "",
        "price": price_val,
        "compare_at_price": compare_val,
        "emoji": product.emoji if product else "🛍️",
        "image_url": product.image_url if product else None,
        "quantity": cart_item.quantity,
        "size": cart_item.size,
        "color": cart_item.color,
        "stock": product.stock if product else 100,
        "delivery_standard": product.delivery_standard if product else True,
        "delivery_pickup": product.delivery_pickup if product else False,
    }

