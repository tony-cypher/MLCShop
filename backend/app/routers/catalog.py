"""Public catalogue: categories, brands, filtered products and detail."""

from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..errors import not_found
from ..models import Brand, Category, Product, Review
from ..schemas import ProductQuery
from ..serializers import (
    brand_payload,
    category_payload,
    product_payload,
    review_payload,
)
from ..validation import parse_model

router = APIRouter()

HISTOGRAM_BINS = 24


def _query_params(request: Request) -> dict[str, Any]:
    """Flatten query params, gathering ``brands[]`` repeats into a list."""
    data: dict[str, Any] = {}
    for key, value in request.query_params.multi_items():
        if key.endswith("[]"):
            data.setdefault(key[:-2], []).append(value)
        elif key not in data:
            data[key] = value
    return data


@router.get("/categories")
def categories(db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(Category).order_by(Category.position, Category.name)).all()
    return {"data": [category_payload(category) for category in rows]}


@router.get("/brands")
def brands(db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(Brand).order_by(Brand.name)).all()
    return {"data": [brand_payload(brand) for brand in rows]}


@router.get("/products")
def products(request: Request, db: Session = Depends(get_db)) -> dict:
    params = parse_model(ProductQuery, _query_params(request))

    per_page = params.per_page or 12
    page = params.page or 1

    filters = _filters(params)
    base: Select = select(Product).where(*filters) if filters else select(Product)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    last_page = max(1, math.ceil(total / per_page)) if total else 1

    stmt = _apply_sort(base, params.sort).limit(per_page).offset((page - 1) * per_page)
    stmt = stmt.options(selectinload(Product.category), selectinload(Product.brand))

    rows = db.scalars(stmt).all()

    # Slider bounds + histogram come from the whole catalogue so they stay
    # stable while filters are applied (one query, matching the original).
    catalogue = db.execute(select(Product.price, Product.is_deal)).all()
    prices = [float(row[0]) for row in catalogue]
    price_min = min(prices) if prices else 0.0
    price_max = max(prices) if prices else 0.0
    price_avg = (sum(prices) / len(prices)) if prices else 0.0
    deals_count = sum(1 for row in catalogue if row[1])

    histogram = [0] * HISTOGRAM_BINS
    span = price_max - price_min
    for price in prices:
        index = (
            min(HISTOGRAM_BINS - 1, int(math.floor((price - price_min) / span * HISTOGRAM_BINS)))
            if span > 0
            else 0
        )
        histogram[index] += 1

    return {
        "data": [product_payload(product) for product in rows],
        "meta": {
            "current_page": page,
            "per_page": per_page,
            "total": total,
            "last_page": last_page,
            "price": {
                "min": math.floor(price_min),
                "max": math.ceil(price_max),
                "avg": round(price_avg),
            },
            "price_histogram": histogram,
            "deals_count": deals_count,
        },
    }


@router.get("/products/{slug}")
def show(slug: str, db: Session = Depends(get_db)) -> dict:
    product = db.scalar(
        select(Product)
        .where(Product.slug == slug)
        .options(selectinload(Product.category), selectinload(Product.brand))
    )
    if product is None:
        raise not_found("Product not found.")

    reviews = db.scalars(
        select(Review)
        .where(Review.product_id == product.id)
        .order_by(Review.created_at.desc())
        .limit(10)
    ).all()

    related = db.scalars(
        select(Product)
        .where(Product.category_id == product.category_id, Product.id != product.id)
        .order_by(func.random())
        .limit(4)
        .options(selectinload(Product.category), selectinload(Product.brand))
    ).all()

    return {
        "data": product_payload(product, category_emoji=False),
        "reviews": [review_payload(review) for review in reviews],
        "related": [product_payload(item, category_emoji=False) for item in related],
    }


# --------------------------------------------------------------------------- #
# Query building
# --------------------------------------------------------------------------- #


def _filters(params: ProductQuery) -> list:
    conditions = []

    if params.search:
        term = f"%{params.search.strip().lower()}%"
        conditions.append(
            func.lower(Product.name).like(term)
            | func.lower(func.coalesce(Product.description, "")).like(term)
        )

    if params.category:
        conditions.append(
            Product.category_id.in_(
                select(Category.id).where(Category.slug == params.category)
            )
        )

    brand_slugs = [slug for slug in params.brands if slug]
    if brand_slugs:
        conditions.append(
            Product.brand_id.in_(select(Brand.id).where(Brand.slug.in_(brand_slugs)))
        )

    if params.min_price is not None:
        conditions.append(Product.price >= params.min_price)
    if params.max_price is not None:
        conditions.append(Product.price <= params.max_price)
    if params.min_rating is not None:
        conditions.append(Product.rating >= params.min_rating)

    if params.delivery == "standard":
        conditions.append(Product.delivery_standard.is_(True))
    elif params.delivery == "pickup":
        conditions.append(Product.delivery_pickup.is_(True))

    if params.deals:
        conditions.append(Product.is_deal.is_(True))

    return conditions


def _apply_sort(stmt: Select, sort: str | None) -> Select:
    if sort == "newest":
        return stmt.order_by(Product.created_at.desc(), Product.id.desc())
    if sort == "price_asc":
        return stmt.order_by(Product.price.asc())
    if sort == "price_desc":
        return stmt.order_by(Product.price.desc())
    if sort == "rating":
        return stmt.order_by(Product.rating.desc(), Product.reviews_count.desc())
    if sort == "featured":
        return stmt.order_by(Product.featured.desc(), Product.rating.desc())
    return stmt.order_by(Product.id.asc())
