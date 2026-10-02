"""Idempotent seeders.

Every seeder uses an "update or create" pattern (like the Laravel seeders), so
re-running them is safe. Run with ``python -m app.seed`` or set ``RUN_SEED=true``.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import SessionLocal, create_all
from .models import Brand, Category, Product, Review, User, utcnow
from .security import hash_password
from .seed_data import BRANDS, CATEGORIES, PRODUCTS, REVIEWS


def slugify(value: str) -> str:
    """Laravel ``Str::slug()`` equivalent (no locale support needed here)."""
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    return re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()


def run_seeders() -> None:
    with SessionLocal() as db:
        _seed_categories(db)
        _seed_brands(db)
        _seed_products(db)
        _seed_reviews(db)
        _seed_demo_user(db)
        db.commit()


def _seed_categories(db: Session) -> None:
    for index, row in enumerate(CATEGORIES):
        category = db.scalar(select(Category).where(Category.slug == row["slug"]))
        if category is None:
            category = Category(slug=row["slug"])
            db.add(category)
        category.name = row["name"]
        category.emoji = row["emoji"]
        category.position = index + 1
    db.flush()


def _seed_brands(db: Session) -> None:
    for row in BRANDS:
        brand = db.scalar(select(Brand).where(Brand.slug == row["slug"]))
        if brand is None:
            brand = Brand(slug=row["slug"])
            db.add(brand)
        brand.name = row["name"]
        brand.initials = row["initials"]
        brand.color = row["color"]
    db.flush()


def _seed_products(db: Session) -> None:
    for row in PRODUCTS:
        category = db.scalar(select(Category).where(Category.slug == row["category"]))
        if category is None:
            continue

        brand = None
        if row.get("brand"):
            brand = db.scalar(select(Brand).where(Brand.slug == row["brand"]))

        slug = slugify(row["name"])
        product = db.scalar(select(Product).where(Product.slug == slug))
        if product is None:
            product = Product(slug=slug)
            db.add(product)

        product.category_id = category.id
        product.brand_id = brand.id if brand else None
        product.name = row["name"]
        product.description = row.get("description")
        product.price = row["price"]
        product.compare_at_price = row.get("compare")
        product.emoji = row["emoji"]
        product.image_url = f"/img/products/{slug}.jpg"
        product.badge = row.get("badge")
        product.featured = row.get("featured", False)
        product.is_deal = row.get("is_deal", False)
        product.rating = row["rating"]
        product.reviews_count = row["reviews"]
        product.rating_chips = row.get("chips")
        product.options = row.get("options")
        product.delivery_standard = row.get("delivery_standard", True)
        product.delivery_pickup = row.get("delivery_pickup", True)
        product.stock = row.get("stock", 120)

    db.flush()


def _seed_reviews(db: Session) -> None:
    for slug, items in REVIEWS.items():
        product = db.scalar(select(Product).where(Product.slug == slug))
        if product is None:
            continue

        for author, avatar, rating, comment, days_ago in items:
            review = db.scalar(
                select(Review).where(
                    Review.product_id == product.id, Review.author == author
                )
            )
            if review is None:
                review = Review(product_id=product.id, author=author)
                db.add(review)
            review.avatar = avatar
            review.rating = rating
            review.comment = comment
            review.created_at = utcnow() - timedelta(days=days_ago)
    db.flush()


def _seed_demo_user(db: Session) -> None:
    user = db.scalar(select(User).where(User.email == "demo@mlc.test"))
    if user is None:
        user = User(email="demo@mlc.test")
        db.add(user)
    user.name = "Demo Shopper"
    user.password = hash_password("password123")
    user.email_verified_at = utcnow()
    user.verification_token = None
    db.flush()


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    create_all()
    run_seeders()
    print("Seeding complete.")
