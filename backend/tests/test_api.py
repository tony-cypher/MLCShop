"""End-to-end tests for the FastAPI backend.

They assert the exact JSON contract the React storefront relies on
(Laravel-compatible field names, string decimals, pagination meta, error maps).
"""

from __future__ import annotations

import itertools
import uuid

import pytest
from sqlalchemy import select

from app.models import Product, User

_counter = itertools.count(1)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def unique_email() -> str:
    return f"shopper{next(_counter)}-{uuid.uuid4().hex[:6]}@example.com"


def register(client, email: str | None = None) -> dict:
    payload = {
        "name": "Test Shopper",
        "email": email or unique_email(),
        "password": "password123",
        "password_confirmation": "password123",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------- #
# Health & CORS
# --------------------------------------------------------------------------- #


def test_health_check(client):
    response = client.get("/up")
    assert response.status_code == 200
    assert response.text == "OK"


def test_cors_preflight_for_storefront_origin(client):
    response = client.options(
        "/api/products",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


# --------------------------------------------------------------------------- #
# Catalogue
# --------------------------------------------------------------------------- #


def test_categories_and_brands(client):
    categories = client.get("/api/categories").json()["data"]
    assert len(categories) == 8
    assert categories[0]["slug"] == "crypto"
    assert set(categories[0]) == {"id", "name", "slug", "emoji"}

    brands = client.get("/api/brands").json()["data"]
    assert len(brands) == 10
    assert set(brands[0]) == {"id", "name", "slug", "initials", "color"}
    assert brands == sorted(brands, key=lambda brand: brand["name"])


def test_products_default_page_and_meta(client):
    response = client.get("/api/products?per_page=12&sort=featured")
    assert response.status_code == 200
    body = response.json()

    assert len(body["data"]) == 12
    meta = body["meta"]
    assert meta["current_page"] == 1
    assert meta["per_page"] == 12
    assert meta["total"] == 33
    assert meta["last_page"] == 3
    assert len(meta["price_histogram"]) == 24
    assert sum(meta["price_histogram"]) == 33
    assert meta["deals_count"] == 8
    assert meta["price"]["min"] == 12
    assert meta["price"]["max"] == 454

    first = body["data"][0]
    assert first["featured"] is True
    assert isinstance(first["price"], str) and first["price"].endswith("00")
    assert isinstance(first["rating"], str)
    assert isinstance(first["reviews_count"], int)
    assert first["category"]["emoji"]
    assert set(first["brand"]) == {"id", "name", "slug", "initials", "color"}


def test_products_pagination(client):
    page_two = client.get("/api/products?per_page=12&page=2&sort=featured").json()
    assert page_two["meta"]["current_page"] == 2
    assert len(page_two["data"]) == 12


def test_product_filters(client):
    sport = client.get("/api/products?category=sport&per_page=48").json()
    assert sport["meta"]["total"] == 9

    nike = client.get("/api/products?brands[]=nike&per_page=48").json()
    assert nike["meta"]["total"] == 2
    assert all(product["brand"]["slug"] == "nike" for product in nike["data"])

    hoodie = client.get("/api/products?search=hoodie").json()
    assert hoodie["meta"]["total"] == 1

    deals = client.get("/api/products?deals=1&per_page=48").json()
    assert deals["meta"]["total"] == 8
    assert all(product["is_deal"] for product in deals["data"])

    pickup = client.get("/api/products?delivery=pickup&per_page=48").json()
    assert pickup["meta"]["total"] == 29
    assert all(product["delivery_pickup"] for product in pickup["data"])

    cheap = client.get("/api/products?max_price=30&per_page=48").json()
    assert cheap["meta"]["total"] == 7
    assert all(float(product["price"]) <= 30 for product in cheap["data"])


def test_product_sorting(client):
    ascending = client.get("/api/products?sort=price_asc&per_page=48").json()["data"]
    prices = [float(product["price"]) for product in ascending]
    assert prices == sorted(prices)

    descending = client.get("/api/products?sort=price_desc&per_page=48").json()["data"]
    assert float(descending[0]["price"]) == 454.00


def test_invalid_filter_is_rejected(client):
    response = client.get("/api/products?sort=sideways")
    assert response.status_code == 422
    assert "sort" in response.json()["errors"]


def test_product_detail(client):
    response = client.get("/api/products/smart-watch-wh22-6-fitness-tracker")
    assert response.status_code == 200
    body = response.json()

    product = body["data"]
    assert product["price"] == "454.00"
    assert product["rating"] == "4.80"
    assert product["badge"] == "top"
    assert product["options"] == {"sizes": ["41mm", "45mm"], "colors": ["Silver", "Midnight"]}

    assert len(body["reviews"]) == 3
    assert set(body["reviews"][0]) == {"id", "author", "avatar", "rating", "comment", "created_at"}

    assert 0 < len(body["related"]) <= 4
    assert all(item["category_id"] == product["category_id"] for item in body["related"])


def test_product_detail_missing(client):
    response = client.get("/api/products/does-not-exist")
    assert response.status_code == 404
    assert response.json()["message"] == "Product not found."


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #


def test_register_requires_matching_password(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Ada",
            "email": unique_email(),
            "password": "password123",
            "password_confirmation": "password124",
        },
    )
    assert response.status_code == 422
    assert "password" in response.json()["errors"]


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Ada",
            "email": unique_email(),
            "password": "short",
            "password_confirmation": "short",
        },
    )
    assert response.status_code == 422
    assert "password" in response.json()["errors"]


def test_register_and_verify_email(client, db):
    email = unique_email()
    body = register(client, email)

    assert body["data"]["email"] == email
    assert body["data"]["email_verified_at"] is None
    assert body["token"]

    user = db.scalar(select(User).where(User.email == email))
    assert user is not None and user.verification_token

    verified = client.post("/api/auth/verify-email", json={"token": user.verification_token})
    assert verified.status_code == 200
    assert verified.json()["data"]["email_verified_at"] is not None

    db.refresh(user)
    assert user.verification_token is None


def test_register_duplicate_email(client):
    email = unique_email()
    register(client, email)

    response = client.post(
        "/api/auth/register",
        json={
            "name": "Copy Cat",
            "email": email.upper(),
            "password": "password123",
            "password_confirmation": "password123",
        },
    )
    assert response.status_code == 422
    assert response.json()["errors"]["email"] == ["The email has already been taken."]


def test_invalid_verification_token(client):
    response = client.post("/api/auth/verify-email", json={"token": "nope"})
    assert response.status_code == 422
    assert response.json()["errors"]["token"]


def test_login_with_demo_account(client):
    response = client.post(
        "/api/auth/login", json={"email": "demo@mlc.test", "password": "password123"}
    )
    assert response.status_code == 200
    assert response.json()["token"]


def test_login_with_wrong_password(client):
    response = client.post(
        "/api/auth/login", json={"email": "demo@mlc.test", "password": "wrong-password"}
    )
    assert response.status_code == 422
    assert response.json()["message"] == "Those credentials do not match our records."


def test_me_requires_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json() == {"message": "Unauthenticated."}


def test_me_and_logout(client):
    token = register(client)["token"]

    me = client.get("/api/auth/me", headers=auth_header(token))
    assert me.status_code == 200
    assert me.json()["data"]["avatar_emoji"] == "🧑‍🚀"

    logout = client.post("/api/auth/logout", headers=auth_header(token))
    assert logout.status_code == 200
    assert logout.json()["message"] == "Signed out."

    assert client.get("/api/auth/me", headers=auth_header(token)).status_code == 401


def test_resend_verification_issues_a_new_token(client, db):
    body = register(client)
    token = body["token"]

    user = db.scalar(select(User).where(User.email == body["data"]["email"]))
    original = user.verification_token

    response = client.post("/api/auth/resend-verification", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["message"] == "A new confirmation link is on its way."

    db.refresh(user)
    assert user.verification_token and user.verification_token != original


def test_resend_verification_for_verified_user(client):
    login = client.post(
        "/api/auth/login", json={"email": "demo@mlc.test", "password": "password123"}
    ).json()

    response = client.post("/api/auth/resend-verification", headers=auth_header(login["token"]))
    assert response.status_code == 200
    assert response.json()["message"] == "Your email is already confirmed."


def test_google_config_disabled_without_credentials(client):
    response = client.get("/api/auth/google/config")
    assert response.status_code == 200
    assert response.json() == {"data": {"enabled": False}}


# --------------------------------------------------------------------------- #
# Favourites
# --------------------------------------------------------------------------- #


def test_favorites_roundtrip(client):
    token = register(client)["token"]
    headers = auth_header(token)

    assert client.get("/api/favorites", headers=headers).json()["data"] == []
    assert client.get("/api/favorites").status_code == 401

    created = client.post("/api/favorites/1", headers=headers)
    assert created.status_code == 201
    assert created.json()["data"] == [1]
    assert created.json()["message"] == "Added to favourites."

    # Idempotent.
    assert client.post("/api/favorites/1", headers=headers).json()["data"] == [1]

    listing = client.get("/api/favorites", headers=headers).json()["data"]
    assert [product["id"] for product in listing] == [1]

    removed = client.delete("/api/favorites/1", headers=headers)
    assert removed.status_code == 200
    assert removed.json()["data"] == []

    assert client.post("/api/favorites/999999", headers=headers).status_code == 404


# --------------------------------------------------------------------------- #
# Checkout & orders
# --------------------------------------------------------------------------- #


def checkout_payload(product_id: int, quantity: int = 1, delivery: str = "standard", **payment):
    payload = {
        "items": [{"product_id": product_id, "quantity": quantity}],
        "customer": {"name": "Ada Lovelace", "email": "ada@example.com"},
        "delivery_method": delivery,
        "payment": {
            "cardholder": "Ada Lovelace",
            "card_number": "4242 4242 4242 4242",
            "expiry": "12/29",
            "cvc": "123",
        },
    }
    if delivery == "standard":
        payload["address"] = {
            "line1": "12 Purple Avenue",
            "city": "Lagos",
            "state": "LA",
            "zip": "100001",
            "country": "Nigeria",
        }
    payload["payment"].update(payment)
    return payload


def test_checkout_rejects_bad_card(client):
    response = client.post("/api/checkout", json=checkout_payload(1, card_number="1234 5678 9012 3456"))
    assert response.status_code == 422
    assert response.json()["errors"]["payment.card_number"]

    expired = client.post("/api/checkout", json=checkout_payload(1, expiry="01/20"))
    assert expired.status_code == 422
    assert expired.json()["errors"]["payment.expiry"]

    malformed = client.post("/api/checkout", json=checkout_payload(1, expiry="13/29"))
    assert malformed.status_code == 422
    assert malformed.json()["errors"]["payment.expiry"]


def test_checkout_requires_address_for_standard_delivery(client):
    payload = checkout_payload(1)
    payload.pop("address")
    response = client.post("/api/checkout", json=payload)
    assert response.status_code == 422
    assert response.json()["errors"]["address.line1"]


def test_checkout_places_order_and_creates_history(client, db):
    token = register(client)["token"]
    headers = auth_header(token)

    product = db.scalar(select(Product).where(Product.slug == "smart-watch-wh22-6-fitness-tracker"))
    stock_before = product.stock

    response = client.post("/api/checkout", json=checkout_payload(product.id, quantity=2), headers=headers)
    assert response.status_code == 201, response.text
    order = response.json()["data"]

    assert order["reference"].startswith("MLC-")
    assert order["status"] == "confirmed"
    assert order["payment_status"] == "test_paid"
    assert order["card_last4"] == "4242"
    assert order["subtotal"] == "908.00"
    assert order["shipping"] == "0.00"
    assert order["total"] == "908.00"
    assert order["address"]["city"] == "Lagos"
    assert len(order["items"]) == 1
    assert order["items"][0]["quantity"] == 2
    assert order["items"][0]["image_url"].startswith("/img/products/")

    db.refresh(product)
    assert product.stock == stock_before - 2

    orders = client.get("/api/orders", headers=headers).json()["data"]
    assert [item["reference"] for item in orders] == [order["reference"]]

    by_reference = client.get(f"/api/orders/{order['reference']}", headers=headers)
    assert by_reference.status_code == 200
    assert by_reference.json()["data"]["reference"] == order["reference"]


def test_checkout_charges_shipping_under_threshold(client):
    response = client.post("/api/checkout", json=checkout_payload(6, quantity=1))
    assert response.status_code == 201
    order = response.json()["data"]
    assert order["subtotal"] == "12.99"
    assert order["shipping"] == "9.99"
    assert order["total"] == "22.98"


def test_checkout_pickup_is_free_and_skips_address(client):
    response = client.post("/api/checkout", json=checkout_payload(6, delivery="pickup"))
    assert response.status_code == 201
    order = response.json()["data"]
    assert order["delivery_method"] == "pickup"
    assert order["shipping"] == "0.00"
    assert order["address"] is None


def test_checkout_rejects_product_unavailable_for_delivery(client, db):
    product = db.scalar(select(Product).where(Product.slug == "adjustable-dumbbell-set-20-kg"))
    response = client.post("/api/checkout", json=checkout_payload(product.id, delivery="pickup"))
    assert response.status_code == 422
    assert "pick up" in response.json()["errors"]["items"][0]


def test_checkout_rejects_insufficient_stock(client, db):
    product = db.scalar(select(Product).where(Product.slug == "crypto-trader-enamel-mug"))
    product.stock = 3
    db.commit()
    response = client.post(
        "/api/checkout",
        json={
            "items": [{"product_id": product.id, "quantity": 10}],
            "customer": {"name": "Ada", "email": "ada@example.com"},
            "delivery_method": "standard",
            "address": {
                "line1": "1 Main St",
                "city": "Lagos",
                "state": "LA",
                "zip": "100001",
                "country": "Nigeria",
            },
            "payment": {
                "cardholder": "Ada",
                "card_number": "4242424242424242",
                "expiry": "12/29",
                "cvc": "123",
            },
        },
    )
    assert response.status_code == 422
    assert "Not enough stock" in response.json()["message"]


def test_orders_require_authentication(client):
    assert client.get("/api/orders").status_code == 401
    assert client.get("/api/orders/MLC-261002-ABCD").status_code == 401


def test_guest_checkout_is_allowed_but_not_in_any_history(client):
    response = client.post("/api/checkout", json=checkout_payload(6, quantity=1))
    assert response.status_code == 201
    assert response.json()["data"]["user_id"] is None


def test_auth_routes_are_throttled(client):
    for _ in range(10):
        client.post(
            "/api/auth/login", json={"email": "demo@mlc.test", "password": "wrong"}
        )

    response = client.post(
        "/api/auth/login", json={"email": "demo@mlc.test", "password": "wrong"}
    )
    assert response.status_code == 429
    assert response.json() == {"message": "Too Many Attempts."}
