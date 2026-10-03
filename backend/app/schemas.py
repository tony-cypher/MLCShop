"""Request payloads.

Field limits mirror the original Laravel validation rules; semantic checks
(password confirmation, stock, Luhn, …) live in the routers.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .types import EmailAddress


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailAddress = Field(max_length=255)
    password: str = Field(min_length=8, max_length=100)
    password_confirmation: str = Field(min_length=8, max_length=100)


class LoginRequest(BaseModel):
    email: EmailAddress
    password: str


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1, max_length=64)


# --------------------------------------------------------------------------- #
# Checkout
# --------------------------------------------------------------------------- #


class CartItemSync(BaseModel):
    id: int
    quantity: int = Field(ge=1, le=100)
    size: Optional[str] = None
    color: Optional[str] = None


class CartSyncRequest(BaseModel):
    items: list[CartItemSync] = Field(default_factory=list)


class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=100)
    size: Optional[str] = None
    color: Optional[str] = None


class CartItemUpdate(BaseModel):
    product_id: int
    quantity: int = Field(ge=0, le=100)
    size: Optional[str] = None
    color: Optional[str] = None


class CheckoutItem(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=10)


class Customer(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailAddress = Field(max_length=255)
    phone: Optional[str] = Field(default=None, max_length=30)


class Address(BaseModel):
    line1: Optional[str] = Field(default=None, max_length=120)
    city: Optional[str] = Field(default=None, max_length=60)
    state: Optional[str] = Field(default=None, max_length=60)
    zip: Optional[str] = Field(default=None, max_length=20)
    country: Optional[str] = Field(default=None, max_length=60)


class Payment(BaseModel):
    cardholder: str = Field(min_length=1, max_length=80)
    card_number: str = Field(min_length=1, max_length=25)
    expiry: str = Field(min_length=1, max_length=5)
    cvc: str = Field(min_length=3, max_length=4)


class CheckoutRequest(BaseModel):
    items: list[CheckoutItem] = Field(min_length=1, max_length=30)
    customer: Customer
    delivery_method: Literal["standard", "pickup"]
    address: Optional[Address] = None
    payment: Payment


# --------------------------------------------------------------------------- #
# Catalogue filters
# --------------------------------------------------------------------------- #


class ProductQuery(BaseModel):
    search: Optional[str] = Field(default=None, max_length=100)
    category: Optional[str] = Field(default=None, max_length=100)
    brands: list[str] = Field(default_factory=list)
    min_price: Optional[float] = Field(default=None, ge=0)
    max_price: Optional[float] = Field(default=None, ge=0)
    min_rating: Optional[float] = Field(default=None, ge=0, le=5)
    delivery: Optional[Literal["standard", "pickup"]] = None
    deals: Optional[bool] = None
    sort: Optional[Literal["featured", "newest", "price_asc", "price_desc", "rating"]] = None
    per_page: Optional[int] = Field(default=None, ge=1, le=48)
    page: Optional[int] = Field(default=None, ge=1)
