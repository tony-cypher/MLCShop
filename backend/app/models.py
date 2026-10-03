"""SQLAlchemy models.

Column-for-column equivalents of the original Laravel migrations, so the React
storefront (and the Postgres schema it expects) keeps working unchanged.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


# --------------------------------------------------------------------------- #
# Accounts
# --------------------------------------------------------------------------- #


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    password: Mapped[str] = mapped_column(String(255))
    verification_token: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))

    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user")
    cart_items: Mapped[list["CartItem"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    tokens: Mapped[list["AuthToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def has_verified_email(self) -> bool:
        return self.email_verified_at is not None


class AuthToken(TimestampMixin, Base):
    """Personal access tokens (the Sanctum equivalent)."""

    __tablename__ = "personal_access_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), default="spa")
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="tokens")


# --------------------------------------------------------------------------- #
# Catalogue
# --------------------------------------------------------------------------- #


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    emoji: Mapped[Optional[str]] = mapped_column(String(16))
    position: Mapped[int] = mapped_column(Integer, default=0)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Brand(TimestampMixin, Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    initials: Mapped[str] = mapped_column(String(4))
    color: Mapped[str] = mapped_column(String(7), default="#6C5CE7")

    products: Mapped[list["Product"]] = relationship(back_populates="brand")


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True
    )
    brand_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    compare_at_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    emoji: Mapped[str] = mapped_column(String(16), default="🛍️")
    image_url: Mapped[Optional[str]] = mapped_column(String(255))
    badge: Mapped[Optional[str]] = mapped_column(String(16))
    featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_deal: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    rating_chips: Mapped[Optional[list]] = mapped_column(JSON)
    options: Mapped[Optional[dict]] = mapped_column(JSON)
    delivery_standard: Mapped[bool] = mapped_column(Boolean, default=True)
    delivery_pickup: Mapped[bool] = mapped_column(Boolean, default=False)
    stock: Mapped[int] = mapped_column(Integer, default=100)

    category: Mapped[Category] = relationship(back_populates="products")
    brand: Mapped[Optional[Brand]] = relationship(back_populates="products")
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("products_category_id_is_deal_index", "category_id", "is_deal"),)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    author: Mapped[str] = mapped_column(String(255))
    avatar: Mapped[str] = mapped_column(String(16), default="🙂")
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    # Reviews are immutable — only created_at is maintained.
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=utcnow)

    product: Mapped[Product] = relationship(back_populates="reviews")


# --------------------------------------------------------------------------- #
# Commerce
# --------------------------------------------------------------------------- #


class Favorite(TimestampMixin, Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))

    user: Mapped[User] = relationship(back_populates="favorites")
    product: Mapped[Product] = relationship()

    __table_args__ = (UniqueConstraint("user_id", "product_id", name="favorites_user_id_product_id_unique"),)


class CartItem(TimestampMixin, Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    user: Mapped[User] = relationship(back_populates="cart_items")
    product: Mapped[Product] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", "size", "color", name="cart_items_user_prod_variant_unique"),
    )


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(255), unique=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    email: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    payment_status: Mapped[str] = mapped_column(String(20), default="test_paid")
    payment_method: Mapped[str] = mapped_column(String(20), default="test_card")
    card_last4: Mapped[Optional[str]] = mapped_column(String(4))
    delivery_method: Mapped[str] = mapped_column(String(20), default="standard")
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2))
    shipping: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(10, 2))
    address: Mapped[Optional[dict]] = mapped_column(JSON)
    placed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped[Optional[User]] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(TimestampMixin, Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(255))
    emoji: Mapped[Optional[str]] = mapped_column(String(16))
    image_url: Mapped[Optional[str]] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    quantity: Mapped[int] = mapped_column(Integer)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Optional[Product]] = relationship()
