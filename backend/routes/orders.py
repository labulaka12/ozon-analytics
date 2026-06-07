"""订单管理 API 路由"""
import logging
from typing import Optional
from datetime import date, timedelta, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import User, Order, Store
from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["orders"])


@router.get("/api/orders")
def list_orders(
    store_id: int = Query(...),
    status: Optional[str] = Query(None),
    product_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询订单列表"""
    # 验证店铺归属
    store = db.query(Store).filter_by(id=store_id, user_id=current_user.id).first()
    if not store:
        raise HTTPException(404, "店铺不存在")

    # 日期范围默认值
    if not date_to:
        date_to = date.today().strftime("%Y-%m-%d")
    if not date_from:
        date_from = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")

    query = db.query(Order).filter(
        Order.store_id == store_id,
        Order.user_id == current_user.id,
        Order.order_created_at >= date_from,
        Order.order_created_at <= date_to + "T23:59:59",
    )
    if status:
        query = query.filter(Order.status == status)
    if product_id:
        query = query.filter(Order.product_id == product_id)

    total = query.count()
    items = query.order_by(desc(Order.order_created_at)).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [
            {
                "posting_number": o.posting_number,
                "order_type": o.order_type,
                "product_id": o.product_id,
                "offer_id": o.offer_id,
                "product_name": o.product_name,
                "quantity": o.quantity,
                "price": o.price,
                "total_price": o.total_price,
                "status": o.status,
                "order_created_at": o.order_created_at.strftime("%Y-%m-%d %H:%M:%S") if o.order_created_at else None,
                "shipped_at": o.shipped_at.strftime("%Y-%m-%d %H:%M:%S") if o.shipped_at else None,
                "delivered_at": o.delivered_at.strftime("%Y-%m-%d %H:%M:%S") if o.delivered_at else None,
                "commission": o.commission,
                "payout": o.payout,
            }
            for o in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/api/orders/{posting_number}")
def get_order_detail(
    posting_number: str,
    store_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """订单详情"""
    orders = db.query(Order).filter(
        Order.store_id == store_id,
        Order.user_id == current_user.id,
        Order.posting_number == posting_number,
    ).all()
    if not orders:
        raise HTTPException(404, "订单不存在")

    return {
        "posting_number": posting_number,
        "items": [
            {
                "product_id": o.product_id,
                "offer_id": o.offer_id,
                "product_name": o.product_name,
                "quantity": o.quantity,
                "price": o.price,
                "total_price": o.total_price,
                "commission": o.commission,
                "payout": o.payout,
            }
            for o in orders
        ],
        "status": orders[0].status,
        "order_type": orders[0].order_type,
        "order_created_at": orders[0].order_created_at.strftime("%Y-%m-%d %H:%M:%S") if orders[0].order_created_at else None,
        "shipped_at": orders[0].shipped_at.strftime("%Y-%m-%d %H:%M:%S") if orders[0].shipped_at else None,
        "delivered_at": orders[0].delivered_at.strftime("%Y-%m-%d %H:%M:%S") if orders[0].delivered_at else None,
    }
