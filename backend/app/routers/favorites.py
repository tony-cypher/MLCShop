"""Favourites for signed-in users."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..errors import not_found
from ..models import Favorite, Product, User
from ..serializers import product_payload

router = APIRouter(prefix="/favorites")


@router.get("")
def index(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    # Most-recently favourited first.
    ids = list(
        db.scalars(
            select(Favorite.product_id)
            .where(Favorite.user_id == user.id)
            .order_by(Favorite.created_at.desc())
        ).all()
    )

    if not ids:
        return {"data": []}

    products = {
        product.id: product
        for product in db.scalars(
            select(Product)
            .where(Product.id.in_(ids))
            .options(selectinload(Product.category), selectinload(Product.brand))
        ).all()
    }

    ordered = [products[product_id] for product_id in ids if product_id in products]
    return {"data": [product_payload(product) for product in ordered]}


@router.post("/{product_id}", status_code=201)
def store(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    product = db.get(Product, product_id)
    if product is None:
        raise not_found("Product not found.")

    existing = db.scalar(
        select(Favorite).where(
            Favorite.user_id == user.id, Favorite.product_id == product.id
        )
    )
    if existing is None:
        db.add(Favorite(user_id=user.id, product_id=product.id))
        db.commit()

    return {"data": _favorite_ids(db, user), "message": "Added to favourites."}


@router.delete("/{product_id}")
def destroy(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    db.execute(
        delete(Favorite).where(
            Favorite.user_id == user.id, Favorite.product_id == product_id
        )
    )
    db.commit()

    return {"data": _favorite_ids(db, user), "message": "Removed from favourites."}


def _favorite_ids(db: Session, user: User) -> list[int]:
    return list(db.scalars(select(Favorite.product_id).where(Favorite.user_id == user.id)).all())
