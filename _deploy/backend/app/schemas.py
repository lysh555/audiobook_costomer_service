from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: Any


class OrderSummaryData(BaseModel):
    order_id: str
    title: str
    status: str
    amount: Decimal
    created_at: datetime
    cover_url: str | None = None


class BookSummaryData(BaseModel):
    book_id: str
    title: str
    author: str
    narrator: str
    category: str
    price: Decimal
    cover_url: str | None = None


class UserOrdersData(BaseModel):
    user_id: str
    orders: list[OrderSummaryData]


class UserBooksData(BaseModel):
    user_id: str
    books: list[BookSummaryData]


class OrderItemData(BaseModel):
    book_id: str
    title: str
    quantity: int
    price: Decimal


class OrderDetailData(BaseModel):
    order_id: str
    status: str
    status_desc: str
    amount: Decimal
    created_at: datetime
    items: list[OrderItemData]


class BookData(BaseModel):
    book_id: str
    title: str
    author: str
    narrator: str
    category: str
    description: str
    price: Decimal
    chapter_count: int = 0
    duration_minutes: int = 0
    cover_url: str | None = None


class BookSearchResultData(BaseModel):
    id: str
    title: str
    author: str
    narrator: str
    category: str
    price: Decimal
    cover_url: str | None = None


class BookSearchData(BaseModel):
    keyword: str
    books: list[BookSearchResultData]


class VipStatusData(BaseModel):
    user_id: str
    vip_status: str
    remaining_listening_minutes: int
    expires_at: datetime | None = None


class CouponRedeemRequest(BaseModel):
    coupon_code: str
    user_id: str | None = None


class CouponRedeemData(BaseModel):
    coupon_info: str
    message: str
    success: bool = False


class CouponSummaryData(BaseModel):
    coupon_code: str
    coupon_info: str
    discount_type: str
    discount_value: Decimal
    expires_at: datetime


class UserCouponsData(BaseModel):
    user_id: str
    coupons: list[CouponSummaryData]


class OrderCreateRequest(BaseModel):
    user_id: str | None = None
    book_id: str
    coupon_code: str | None = None


class OrderCreateData(BaseModel):
    success: bool = False
    order_id: str = ""
    book_title: str = ""
    amount: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    message: str = ""


class OrderPayData(BaseModel):
    success: bool = False
    order_id: str = ""
    status: str = ""
    message: str = ""


class VipSubscribeRequest(BaseModel):
    user_id: str | None = None
    months: int = 1
    coupon_code: str | None = None


class VipSubscribeData(BaseModel):
    success: bool = False
    vip_status: str = ""
    months: int = 0
    amount: Decimal = Decimal("0")
    expires_at: datetime | None = None
    message: str = ""


class HandoffCreateRequest(BaseModel):
    user_id: str | None = None
    reason: str | None = None


class HandoffCreateData(BaseModel):
    success: bool = False
    handoff_id: str = ""
    queue_position: int = 0
    message: str = ""


class RefundSubmitRequest(BaseModel):
    reason: str | None = None


class RefundSubmitData(BaseModel):
    success: bool = False
    order_status: str = ""
    message: str = ""