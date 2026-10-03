"""Cart management for synchronized cart across web and mobile."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..errors import not_found
from ..models import CartItem, Product, User
from ..schemas import CartItemAdd, CartItemUpdate, CartSyncRequest
from ..serializers import cart_item_payload

router = APIRouter(prefix="/cart")


def _get_user_cart(db: Session, user: User) -> list[dict]:
    items = list(
        db.scalars(
            select(CartItem)
            .where(CartItem.user_id == user.id)
            .options(selectinload(CartItem.product))
            .order_by(CartItem.created_at.asc())
        ).all()
    )
    return [cart_item_payload(item) for item in items]


@router.get("")
def get_cart(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    """Fetch current user's cart."""
    return {"data": _get_user_cart(db, user)}


@router.post("")
def add_to_cart(
    payload: CartItemAdd,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Add an item to the user's cart (or increment quantity if already present)."""
    product = db.get(Product, payload.product_id)
    if product is None:
        raise not_found("Product not found.")

    existing = db.scalar(
        select(CartItem).where(
            CartItem.user_id == user.id,
            CartItem.product_id == payload.product_id,
            CartItem.size == payload.size,
            CartItem.color == payload.color,
        )
    )

    if existing:
        existing.quantity = min(product.stock, existing.quantity + payload.quantity)
    else:
        new_item = CartItem(
            user_id=user.id,
            product_id=payload.product_id,
            quantity=min(product.stock, payload.quantity),
            size=payload.size,
            color=payload.color,
        )
        db.add(new_item)

    db.commit()
    return {"data": _get_user_cart(db, user), "message": "Item added to cart."}


@router.put("")
def update_quantity(
    payload: CartItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Update item quantity in user's cart (or remove if quantity <= 0)."""
    existing = db.scalar(
        select(CartItem).where(
            CartItem.user_id == user.id,
            CartItem.product_id == payload.product_id,
            CartItem.size == payload.size,
            CartItem.color == payload.color,
        )
    )

    if existing:
        if payload.quantity <= 0:
            db.delete(existing)
        else:
            product = db.get(Product, payload.product_id)
            stock = product.stock if product else 100
            existing.quantity = min(stock, payload.quantity)
        db.commit()

    return {"data": _get_user_cart(db, user), "message": "Cart updated."}


@router.delete("")
def remove_item(
    product_id: int,
    size: Optional[str] = None,
    color: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Remove a specific item variant from user's cart."""
    db.execute(
        delete(CartItem).where(
            CartItem.user_id == user.id,
            CartItem.product_id == product_id,
            CartItem.size == size,
            CartItem.color == color,
        )
    )
    db.commit()
    return {"data": _get_user_cart(db, user), "message": "Item removed from cart."}


@router.delete("/clear")
def clear_cart(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Clear all items in user's cart."""
    db.execute(delete(CartItem).where(CartItem.user_id == user.id))
    db.commit()
    return {"data": [], "message": "Cart cleared."}


@router.post("/sync")
def sync_cart(
    payload: CartSyncRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Merge client-side cart items into the server cart.
    Useful when a guest user signs in or when an app connects.
    """
    for item in payload.items:
        product = db.get(Product, item.id)
        if not product:
            continue
        existing = db.scalar(
            select(CartItem).where(
                CartItem.user_id == user.id,
                CartItem.product_id == item.id,
                CartItem.size == item.size,
                CartItem.color == item.color,
            )
        )
        if existing:
            existing.quantity = min(product.stock, max(existing.quantity, item.quantity))
        else:
            db.add(
                CartItem(
                    user_id=user.id,
                    product_id=item.id,
                    quantity=min(product.stock, item.quantity),
                    size=item.size,
                    color=item.color,
                )
            )
    db.commit()
    return {"data": _get_user_cart(db, user), "message": "Cart synchronized."}
