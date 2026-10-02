"""Order history for signed-in users."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..errors import not_found
from ..models import Order, User
from ..serializers import order_payload

router = APIRouter(prefix="/orders")


@router.get("")
def index(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    orders = db.scalars(
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(Order.placed_at.desc())
        .options(selectinload(Order.items))
    ).all()

    return {"data": [order_payload(order) for order in orders]}


@router.get("/{reference}")
def show(
    reference: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    order = db.scalar(
        select(Order)
        .where(Order.reference == reference, Order.user_id == user.id)
        .options(selectinload(Order.items))
    )
    if order is None:
        raise not_found("Order not found.")

    return {"data": order_payload(order)}
