"""利润核算引擎 API 路由

提供深度利润分析、利润预测、盈亏平衡分析等高级功能。
"""
import logging
from typing import Optional
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import User, Store
from auth import get_current_user
from profit_engine import (
    ProfitCalculator,
    calculate_store_profit,
    calculate_product_profit,
    predict_profit,
    breakeven_analysis,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["profit_engine"])


def _resolve_dates(date_from: Optional[str], date_to: Optional[str]) -> tuple:
    """解析日期范围，默认最近30天"""
    if not date_to:
        date_to = date.today().strftime("%Y-%m-%d")
    if not date_from:
        date_from = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    return date_from, date_to


@router.get("/api/profit/v2/summary")
def get_profit_v2_summary(
    store_id: int = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """V2 利润汇总 — 完整费用分解"""
    store = db.query(Store).filter_by(id=store_id, user_id=current_user.id).first()
    if not store:
        raise HTTPException(404, "店铺不存在")

    date_from, date_to = _resolve_dates(date_from, date_to)
    result = calculate_store_profit(db, store_id, current_user.id, date_from, date_to)
    return result.to_dict()


@router.get("/api/profit/v2/product/{product_id}")
def get_product_profit_v2(
    product_id: int,
    store_id: int = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """V2 单商品利润分解"""
    store = db.query(Store).filter_by(id=store_id, user_id=current_user.id).first()
    if not store:
        raise HTTPException(404, "店铺不存在")

    date_from, date_to = _resolve_dates(date_from, date_to)
    result = calculate_product_profit(db, store_id, current_user.id, product_id, date_from, date_to)
    return result.to_dict()


@router.get("/api/profit/v2/products")
def get_product_profits_v2(
    store_id: int = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("profit", pattern="^(profit|revenue|margin|sold_units|roi)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """V2 商品利润排行榜"""
    store = db.query(Store).filter_by(id=store_id, user_id=current_user.id).first()
    if not store:
        raise HTTPException(404, "店铺不存在")

    date_from, date_to = _resolve_dates(date_from, date_to)
    calc = ProfitCalculator(db, store_id, current_user.id, date_from, date_to)
    profits = calc.calc_product_profits_all()

    reverse = sort_order == "desc"
    if sort_by == "profit":
        profits.sort(key=lambda x: x.breakdown.net_profit, reverse=reverse)
    elif sort_by == "revenue":
        profits.sort(key=lambda x: x.breakdown.revenue, reverse=reverse)
    elif sort_by == "margin":
        profits.sort(key=lambda x: x.breakdown.profit_margin, reverse=reverse)
    elif sort_by == "roi":
        profits.sort(key=lambda x: x.breakdown.roi, reverse=reverse)
    elif sort_by == "sold_units":
        profits.sort(key=lambda x: x.sold_units, reverse=reverse)

    return {
        "items": [p.to_dict() for p in profits[:limit]],
        "total": len(profits),
    }


@router.get("/api/profit/v2/predict")
def get_profit_predict(
    store_id: int = Query(...),
    days_ahead: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """利润预测 — 基于历史趋势"""
    store = db.query(Store).filter_by(id=store_id, user_id=current_user.id).first()
    if not store:
        raise HTTPException(404, "店铺不存在")

    result = predict_profit(db, store_id, current_user.id, days_ahead)
    return result


@router.get("/api/profit/v2/breakeven")
def get_breakeven(
    store_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """盈亏平衡分析"""
    store = db.query(Store).filter_by(id=store_id, user_id=current_user.id).first()
    if not store:
        raise HTTPException(404, "店铺不存在")

    result = breakeven_analysis(db, store_id, current_user.id)
    return result
