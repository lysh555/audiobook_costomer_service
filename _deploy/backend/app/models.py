from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    nickname: Mapped[str] = mapped_column(String(100))
    level: Mapped[str] = mapped_column(String(32))
    mobile_masked: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime)

    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    vip_membership: Mapped["VipMembership | None"] = relationship(
        back_populates="user", uselist=False
    )


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255))
    narrator: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    chapter_count: Mapped[int]
    duration_minutes: Mapped[int]
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attributes_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(32))
    status_desc: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime)

    user: Mapped[User] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    title_snapshot: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int]
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    order: Mapped[Order] = relationship(back_populates="items")
    book: Mapped[Book] = relationship()


class VipMembership(Base):
    __tablename__ = "vip_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    vip_status: Mapped[str] = mapped_column(String(32))
    remaining_listening_minutes: Mapped[int]
    started_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime)

    user: Mapped[User] = relationship(back_populates="vip_membership")


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(primary_key=True)
    coupon_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    coupon_info: Mapped[str] = mapped_column(String(255))
    discount_type: Mapped[str] = mapped_column(String(32))
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[datetime] = mapped_column(DateTime)

    redemptions: Mapped[list["CouponRedemption"]] = relationship(
        back_populates="coupon"
    )


class CouponRedemption(Base):
    __tablename__ = "coupon_redemptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    redemption_id: Mapped[str] = mapped_column(String(64), unique=True)
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupons.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    operator: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    status_desc: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime)

    coupon: Mapped[Coupon] = relationship(back_populates="redemptions")
    user: Mapped[User] = relationship()


class HandoffRequest(Base):
    __tablename__ = "handoff_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    handoff_id: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))
    status_desc: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime)

    user: Mapped[User] = relationship()