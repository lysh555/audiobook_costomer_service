from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    Book,
    Coupon,
    CouponRedemption,
    HandoffRequest,
    Order,
    OrderItem,
    User,
    VipMembership,
)
from app.schemas import (
    ApiResponse,
    BookData,
    BookSearchData,
    BookSearchResultData,
    BookSummaryData,
    CouponRedeemData,
    CouponRedeemRequest,
    CouponSummaryData,
    HandoffCreateData,
    HandoffCreateRequest,
    OrderCreateData,
    OrderCreateRequest,
    OrderDetailData,
    OrderItemData,
    OrderPayData,
    OrderSummaryData,
    RefundSubmitData,
    RefundSubmitRequest,
    UserBooksData,
    UserCouponsData,
    UserOrdersData,
    VipStatusData,
    VipSubscribeData,
    VipSubscribeRequest,
)


router = APIRouter()

VIP_MONTHLY_PRICE = Decimal("18.00")
VIP_MINUTES_PER_MONTH = 1200


def _wrap(data) -> ApiResponse:
    return ApiResponse(data=data)


def _find_user(db: Session, user_id: str | None) -> User | None:
    """对话侧传入的是聊天会话用户标识，查不到时退回默认演示用户"""
    if user_id:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            return user
    return db.query(User).order_by(User.id.asc()).first()


def _resolve_coupon(db: Session, coupon_code: str | None) -> tuple[Coupon | None, str]:
    """校验优惠码可用性，返回可用的优惠券与不可用原因说明"""
    code = (coupon_code or "").strip()
    if not code:
        return None, ""

    coupon = db.query(Coupon).filter(Coupon.coupon_code == code).first()
    if not coupon:
        return None, f"优惠码 {code} 无效，本次未使用优惠。"

    if coupon.status != "未使用":
        return None, f"优惠码 {code} 当前状态为{coupon.status}，本次未使用优惠。"

    if coupon.expires_at < datetime.now():
        expired_on = coupon.expires_at.strftime("%Y-%m-%d")
        return None, f"优惠码 {code} 已于 {expired_on} 过期，本次未使用优惠。"

    return coupon, ""


def _discounted_amount(amount: Decimal, coupon: Coupon) -> Decimal:
    if coupon.discount_type == "折扣":
        return (amount * coupon.discount_value).quantize(Decimal("0.01"))
    if coupon.discount_type in ("满减", "无门槛"):
        return max(Decimal("0.00"), amount - coupon.discount_value).quantize(Decimal("0.01"))
    return amount.quantize(Decimal("0.01"))


def _get_user(db: Session, user_id: str) -> User:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"书友 {user_id} 不存在。")
    return user


def _get_order(db: Session, order_id: str) -> Order:
    order = (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.book))
        .filter(Order.order_id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail=f"订单 {order_id} 不存在。")
    return order


def _build_order_summary(order: Order) -> OrderSummaryData:
    first_item = order.items[0] if order.items else None
    title = first_item.title_snapshot if first_item else "未知听书"
    cover_url = None
    if first_item and first_item.book:
        cover_url = first_item.book.cover_url
    return OrderSummaryData(
        order_id=order.order_id,
        title=title,
        status=order.status,
        amount=order.amount,
        created_at=order.created_at,
        cover_url=cover_url,
    )


@router.get("/health")
def health() -> ApiResponse:
    return _wrap({"status": "ok"})


@router.get("/users/{user_id}/orders", response_model=ApiResponse)
def user_orders(user_id: str, db: Session = Depends(get_db)) -> ApiResponse:
    user = _get_user(db, user_id)
    orders = (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.book))
        .filter(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return _wrap(
        UserOrdersData(
            user_id=user.user_id,
            orders=[_build_order_summary(order) for order in orders],
        )
    )


@router.get("/users/{user_id}/books", response_model=ApiResponse)
def user_books(user_id: str, db: Session = Depends(get_db)) -> ApiResponse:
    user = _get_user(db, user_id)
    recent_items = (
        db.query(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Book, Book.id == OrderItem.book_id)
        .filter(Order.user_id == user.id)
        .options(joinedload(OrderItem.book))
        .order_by(Order.created_at.desc())
        .all()
    )

    seen_book_ids: set[str] = set()
    books: list[BookSummaryData] = []
    for item in recent_items:
        book = item.book
        if not book or book.book_id in seen_book_ids:
            continue
        seen_book_ids.add(book.book_id)
        books.append(
            BookSummaryData(
                book_id=book.book_id,
                title=book.title,
                author=book.author,
                narrator=book.narrator,
                category=book.category,
                price=book.price,
                cover_url=book.cover_url,
            )
        )
    return _wrap(UserBooksData(user_id=user.user_id, books=books))


@router.get("/orders/{order_id}", response_model=ApiResponse)
def order_detail(order_id: str, db: Session = Depends(get_db)) -> ApiResponse:
    order = _get_order(db, order_id)
    items = [
        OrderItemData(
            book_id=item.book.book_id if item.book else "",
            title=item.title_snapshot,
            quantity=item.quantity,
            price=item.price,
        )
        for item in order.items
    ]
    return _wrap(
        OrderDetailData(
            order_id=order.order_id,
            status=order.status,
            status_desc=order.status_desc,
            amount=order.amount,
            created_at=order.created_at,
            items=items,
        )
    )


@router.get("/books/search", response_model=ApiResponse)
def search_books(
    keyword: str | None = None,
    name: str | None = None,
    db: Session = Depends(get_db),
) -> ApiResponse:
    term = (name or keyword or "").strip()
    query = db.query(Book)
    if term:
        like = f"%{term}%"
        query = query.filter(
            or_(
                Book.title.like(like),
                Book.author.like(like),
                Book.category.like(like),
            )
        )
    books = query.order_by(Book.id.asc()).limit(10).all()
    return _wrap(
        BookSearchData(
            keyword=term,
            books=[
                BookSearchResultData(
                    id=book.book_id,
                    title=book.title,
                    author=book.author,
                    narrator=book.narrator,
                    category=book.category,
                    price=book.price,
                    cover_url=book.cover_url,
                )
                for book in books
            ],
        )
    )


@router.get("/books/{book_id}", response_model=ApiResponse)
def book_detail(book_id: str, db: Session = Depends(get_db)) -> ApiResponse:
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail=f"听书 {book_id} 不存在。")
    return _wrap(
        BookData(
            book_id=book.book_id,
            title=book.title,
            author=book.author,
            narrator=book.narrator,
            category=book.category,
            description=book.description,
            price=book.price,
            chapter_count=book.chapter_count,
            duration_minutes=book.duration_minutes,
            cover_url=book.cover_url,
        )
    )


@router.get("/vip/status", response_model=ApiResponse)
def vip_status(
    user_id: str | None = None,
    db: Session = Depends(get_db),
) -> ApiResponse:
    membership: VipMembership | None = None
    if user_id:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            membership = (
                db.query(VipMembership)
                .filter(VipMembership.user_id == user.id)
                .first()
            )
    if membership is None and not user_id:
        membership = db.query(VipMembership).order_by(VipMembership.id.asc()).first()

    if membership is None:
        return _wrap(
            VipStatusData(
                user_id=user_id or "demo",
                vip_status="未开通",
                remaining_listening_minutes=0,
            )
        )

    owner = db.query(User).filter(User.id == membership.user_id).first()
    owner_id = owner.user_id if owner else (user_id or "demo")
    return _wrap(
        VipStatusData(
            user_id=owner_id,
            vip_status=membership.vip_status,
            remaining_listening_minutes=membership.remaining_listening_minutes,
            expires_at=membership.expires_at,
        )
    )


@router.post("/coupons/redeem", response_model=ApiResponse)
def redeem_coupon(
    payload: CouponRedeemRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    code = (payload.coupon_code or "").strip()
    coupon = db.query(Coupon).filter(Coupon.coupon_code == code).first()
    if not coupon:
        return _wrap(
            CouponRedeemData(
                coupon_info=f"优惠码 {code} 无效，请确认后重试。",
                message="优惠码无效",
                success=False,
            )
        )

    if coupon.expires_at < datetime.now():
        expired_on = coupon.expires_at.strftime("%Y-%m-%d")
        return _wrap(
            CouponRedeemData(
                coupon_info=f"优惠码 {code} 已于 {expired_on} 过期，无法兑换。",
                message="优惠码已过期",
                success=False,
            )
        )

    if coupon.status == "已使用":
        return _wrap(
            CouponRedeemData(
                coupon_info=f"优惠码 {code} 已经使用过，无法重复使用。",
                message="已使用",
                success=False,
            )
        )

    existing = (
        db.query(CouponRedemption)
        .filter(CouponRedemption.coupon_id == coupon.id)
        .first()
    )
    if existing:
        return _wrap(
            CouponRedeemData(
                coupon_info=f"优惠码 {code} 已被兑换，无法重复使用。",
                message="已兑换",
                success=False,
            )
        )

    user = None
    if payload.user_id:
        user = db.query(User).filter(User.user_id == payload.user_id).first()
    if user is None:
        user = db.query(User).order_by(User.id.asc()).first()

    if user is not None:
        redemption = CouponRedemption(
            redemption_id=f"CR{datetime.now().strftime('%Y%m%d%H%M%S')}",
            coupon_id=coupon.id,
            user_id=user.id,
            operator="system",
            status="success",
            status_desc=f"优惠码兑换成功，{coupon.coupon_info}已到账。",
            created_at=datetime.now(),
        )
        db.add(redemption)

    coupon.status = "已使用"
    db.commit()

    return _wrap(
        CouponRedeemData(
            coupon_info=f"{coupon.coupon_info}（{coupon.discount_type}）已发放到你的账户。",
            message=f"{coupon.coupon_info} 兑换成功",
            success=True,
        )
    )


@router.post("/orders/{order_id}/refund", response_model=ApiResponse)
def submit_refund(
    order_id: str,
    payload: RefundSubmitRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        return _wrap(
            RefundSubmitData(
                success=False,
                order_status="",
                message=f"没有查到订单 {order_id}，请确认订单号是否准确。",
            )
        )

    if order.status in ("已退款", "退款中"):
        return _wrap(
            RefundSubmitData(
                success=False,
                order_status=order.status,
                message=f"订单 {order_id} 当前状态为{order.status}，无需重复申请退款。",
            )
        )

    reason = (payload.reason or "").strip()
    order.status = "退款中"
    order.status_desc = "退款申请已提交，等待审核"
    db.commit()

    reason_text = f"（原因：{reason}）" if reason else ""
    return _wrap(
        RefundSubmitData(
            success=True,
            order_status=order.status,
            message=f"订单 {order_id} 的退款申请已提交{reason_text}，正在等待审核。",
        )
    )


@router.get("/users/{user_id}/coupons", response_model=ApiResponse)
def user_coupons(user_id: str, db: Session = Depends(get_db)) -> ApiResponse:
    user = _get_user(db, user_id)
    now = datetime.now()
    coupons = (
        db.query(Coupon)
        .filter(Coupon.status == "未使用", Coupon.expires_at > now)
        .order_by(Coupon.expires_at.asc())
        .all()
    )
    return _wrap(
        UserCouponsData(
            user_id=user.user_id,
            coupons=[
                CouponSummaryData(
                    coupon_code=coupon.coupon_code,
                    coupon_info=coupon.coupon_info,
                    discount_type=coupon.discount_type,
                    discount_value=coupon.discount_value,
                    expires_at=coupon.expires_at,
                )
                for coupon in coupons
            ],
        )
    )


@router.post("/orders", response_model=ApiResponse)
def create_order(
    payload: OrderCreateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    user = _find_user(db, payload.user_id)
    if user is None:
        return _wrap(OrderCreateData(success=False, message="没有找到可下单的用户，请稍后再试。"))

    book = db.query(Book).filter(Book.book_id == payload.book_id).first()
    if not book:
        return _wrap(
            OrderCreateData(
                success=False,
                message=f"没有查到听书 {payload.book_id}，请确认书名或听书ID后再试。",
            )
        )

    purchased = (
        db.query(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .filter(
            Order.user_id == user.id,
            OrderItem.book_id == book.id,
            Order.status == "已完成",
        )
        .first()
    )
    if purchased:
        return _wrap(
            OrderCreateData(
                success=False,
                book_title=book.title,
                message=f"你已购买过《{book.title}》，可以直接收听，无需重复下单。",
            )
        )

    pending = (
        db.query(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .filter(
            Order.user_id == user.id,
            OrderItem.book_id == book.id,
            Order.status == "待支付",
        )
        .order_by(Order.id.desc())
        .first()
    )
    if pending:
        return _wrap(
            OrderCreateData(
                success=False,
                order_id=pending.order_id,
                book_title=book.title,
                amount=pending.amount,
                message=(
                    f"你有一笔《{book.title}》的待支付订单 {pending.order_id}，应付金额 ¥{pending.amount}，"
                    f"直接支付这笔订单即可，无需重复下单。"
                ),
            )
        )

    amount = book.price.quantize(Decimal("0.01"))
    discount_amount = Decimal("0.00")
    notice = ""

    coupon, coupon_notice = _resolve_coupon(db, payload.coupon_code)
    if coupon is not None:
        if coupon.discount_type == "兑换":
            notice = f"优惠码 {coupon.coupon_code} 是会员兑换码，不能用于购买听书，本次未使用优惠。"
        else:
            discounted = _discounted_amount(amount, coupon)
            discount_amount = (amount - discounted).quantize(Decimal("0.01"))
            amount = discounted
            coupon.status = "已使用"
            notice = f"已使用优惠码 {coupon.coupon_code}，为你优惠 ¥{discount_amount}。"
    elif coupon_notice:
        notice = coupon_notice

    now = datetime.now()
    order = Order(
        order_id=f"D{now.strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}",
        user_id=user.id,
        status="待支付",
        status_desc="订单待支付，请尽快完成付款。",
        amount=amount,
        created_at=now,
    )
    db.add(order)
    db.flush()

    db.add(
        OrderItem(
            order_id=order.id,
            book_id=book.id,
            title_snapshot=book.title,
            quantity=1,
            price=book.price.quantize(Decimal("0.01")),
        )
    )
    db.commit()

    return _wrap(
        OrderCreateData(
            success=True,
            order_id=order.order_id,
            book_title=book.title,
            amount=amount,
            discount_amount=discount_amount,
            message=(
                f"已为你创建订单 {order.order_id}：《{book.title}》，应付金额 ¥{amount}。{notice}"
                f"需要支付的话，直接告诉我“支付订单 {order.order_id}”即可。"
            ),
        )
    )


@router.post("/orders/{order_id}/pay", response_model=ApiResponse)
def pay_order(order_id: str, db: Session = Depends(get_db)) -> ApiResponse:
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        return _wrap(
            OrderPayData(
                success=False,
                order_id=order_id,
                message=f"没有查到订单 {order_id}，请确认订单号是否准确。",
            )
        )

    if order.status == "已完成":
        return _wrap(
            OrderPayData(
                success=False,
                order_id=order_id,
                status=order.status,
                message=f"订单 {order_id} 已完成支付，无需重复支付。",
            )
        )

    if order.status != "待支付":
        return _wrap(
            OrderPayData(
                success=False,
                order_id=order_id,
                status=order.status,
                message=f"订单 {order_id} 当前状态为{order.status}，暂时无法支付。",
            )
        )

    order.status = "已完成"
    order.status_desc = "订单已完成，听书已解锁，可随时收听。"
    db.commit()

    return _wrap(
        OrderPayData(
            success=True,
            order_id=order_id,
            status=order.status,
            message=f"订单 {order_id} 支付成功，金额 ¥{order.amount}，听书已解锁，可以开始收听了。",
        )
    )


@router.post("/vip/subscribe", response_model=ApiResponse)
def subscribe_vip(
    payload: VipSubscribeRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    user = _find_user(db, payload.user_id)
    if user is None:
        return _wrap(VipSubscribeData(success=False, message="没有找到可开通会员的用户，请稍后再试。"))

    months = payload.months or 1
    if months < 1 or months > 12:
        return _wrap(VipSubscribeData(success=False, message="单次开通时长需在 1 到 12 个月之间。"))

    amount = (VIP_MONTHLY_PRICE * months).quantize(Decimal("0.01"))
    notice = ""

    coupon, coupon_notice = _resolve_coupon(db, payload.coupon_code)
    if coupon is not None:
        if coupon.discount_type == "兑换":
            months += 1
            notice = f"已使用兑换码 {coupon.coupon_code}，额外赠送 1 个月会员。"
        else:
            discounted = _discounted_amount(amount, coupon)
            notice = f"已使用优惠码 {coupon.coupon_code}，为你优惠 ¥{(amount - discounted).quantize(Decimal('0.01'))}。"
            amount = discounted
        coupon.status = "已使用"
    elif coupon_notice:
        notice = coupon_notice

    now = datetime.now()
    membership = db.query(VipMembership).filter(VipMembership.user_id == user.id).first()
    if membership is None:
        membership = VipMembership(
            user_id=user.id,
            vip_status="已开通",
            remaining_listening_minutes=months * VIP_MINUTES_PER_MONTH,
            started_at=now,
            expires_at=now,
        )
        db.add(membership)
    else:
        membership.vip_status = "已开通"
        membership.remaining_listening_minutes += months * VIP_MINUTES_PER_MONTH

    base = membership.expires_at if membership.expires_at and membership.expires_at > now else now
    membership.expires_at = base + timedelta(days=30 * months)
    db.commit()

    return _wrap(
        VipSubscribeData(
            success=True,
            vip_status=membership.vip_status,
            months=months,
            amount=amount,
            expires_at=membership.expires_at,
            message=(
                f"VIP会员已开通 {months} 个月，到期时间 {membership.expires_at.strftime('%Y-%m-%d')}，"
                f"本次支付 ¥{amount}。{notice}"
            ),
        )
    )


@router.post("/handoff", response_model=ApiResponse)
def create_handoff(
    payload: HandoffCreateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    user = _find_user(db, payload.user_id)
    if user is None:
        return _wrap(HandoffCreateData(success=False, message="没有找到可登记人工客服的用户，请稍后再试。"))

    reason = (payload.reason or "用户请求转接人工客服").strip()[:255]
    now = datetime.now()
    handoff = HandoffRequest(
        handoff_id=f"H{now.strftime('%Y%m%d%H%M%S')}",
        user_id=user.id,
        reason=reason,
        status="pending",
        status_desc="已登记，等待人工客服接入。",
        created_at=now,
    )
    db.add(handoff)
    db.commit()

    queue_position = (
        db.query(HandoffRequest)
        .filter(HandoffRequest.status == "pending")
        .count()
    )

    return _wrap(
        HandoffCreateData(
            success=True,
            handoff_id=handoff.handoff_id,
            queue_position=queue_position,
            message=(
                f"已为你登记人工客服请求，工单号 {handoff.handoff_id}，当前排队第 {queue_position} 位，"
                "人工客服接入后会第一时间联系你，请保持会话不要关闭。"
            ),
        )
    )