"""利润看板 API 路由"""
import logging
from typing import Optional
from datetime import date, timedelta, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import csv
import io

from database import get_db
from models import User, Store, RealizationReport, ProductCost, ManualExpense, ExchangeRate
from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["profit"])


def _get_rate(db: Session, user_id: int) -> float:
    """获取用户汇率"""
    rate = db.query(ExchangeRate).filter_by(user_id=user_id).first()
    return rate.rate if rate else 12.0


def _get_cost_map(db: Session, store_id: int) -> dict:
    """获取商品采购成本映射 {product_id: cost_price}"""
    costs = db.query(ProductCost).filter_by(store_id=store_id).all()
    return {c.product_id: c.cost_price for c in costs}


def _get_total_manual_expense(db: Session, store_id: int, rate: float) -> float:
    """获取手动补录费用（转为 RUB）"""
    expenses = db.query(ManualExpense).filter_by(store_id=store_id).all()
    return sum(e.amount_cny for e in expenses) * rate


@router.get("/api/profit/summary")
def get_profit_summary(
    store_id: int = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """利润 KPI 摘要"""
    store = db.query(Store).filter_by(id=store_id, user_id=current_user.id).first()
    if not store:
        raise HTTPException(404, "店铺不存在")

    if not date_to:
        date_to = date.today().strftime("%Y-%m-%d")
    if not date_from:
        date_from = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")

    rows = db.query(RealizationReport).filter(
        RealizationReport.store_id == store_id,
        RealizationReport.user_id == current_user.id,
        RealizationReport.period_from >= date_from,
        RealizationReport.period_to <= date_to,
    ).all()

    rate = _get_rate(db, current_user.id)
    cost_map = _get_cost_map(db, store_id)
    total_expense_rub = _get_total_manual_expense(db, store_id, rate)

    total_revenue = sum(r.revenue for r in rows)
    total_fees = sum(
        r.commission + r.logistics_cost + r.marketing_cost + r.penalty + r.other_cost
        for r in rows
    ) + total_expense_rub
    total_cost = sum(cost_map.get(r.product_id, 0) for r in rows) * rate
    total_profit = total_revenue - total_fees - total_cost
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

    return {
        "total_revenue": round(total_revenue, 2),
        "total_fees": round(total_fees, 2),
        "total_cost": round(total_cost, 2),
        "total_profit": round(total_profit, 2),
        "profit_margin": round(profit_margin, 2),
    }


@router.get("/api/profit/trend")
def get_profit_trend(
    store_id: int = Query(...),
    group_by: str = Query("day", regex="^(day|week|month)$"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """利润趋势"""
    store = db.query(Store).filter_by(id=store_id, user_id=current_user.id).first()
    if not store:
        raise HTTPException(404, "店铺不存在")

    if not date_to:
        date_to = date.today().strftime("%Y-%m-%d")
    if not date_from:
        date_from = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")

    rows = db.query(RealizationReport).filter(
        RealizationReport.store_id == store_id,
        RealizationReport.user_id == current_user.id,
        RealizationReport.period_from >= date_from,
        RealizationReport.period_to <= date_to,
    ).all()

    rate = _get_rate(db, current_user.id)
    cost_map = _get_cost_map(db, store_id)

    # 按聚合键分组
    groups = {}
    for r in rows:
        if group_by == "month":
            key = r.period_from.strftime("%Y-%m") if hasattr(r.period_from, "strftime") else str(r.period_from)[:7]
        elif group_by == "week":
            key = r.period_from.isocalendar() if hasattr(r.period_from, "isocalendar") else str(r.period_from)
            key = f"{key[0]}-W{key[1]:02d}" if isinstance(key, tuple) else str(r.period_from)[:10]
        else:
            key = r.period_from.strftime("%Y-%m-%d") if hasattr(r.period_from, "strftime") else str(r.period_from)[:10]

        if key not in groups:
            groups[key] = {"revenue": 0, "fees": 0, "cost": 0}
        groups[key]["revenue"] += r.revenue
        groups[key]["fees"] += r.commission + r.logistics_cost + r.marketing_cost + r.penalty + r.other_cost
        groups[key]["cost"] += cost_map.get(r.product_id, 0) * rate

    sorted_keys = sorted(groups.keys())
    data = []
    for k in sorted_keys:
        g = groups[k]
        profit = g["revenue"] - g["fees"] - g["cost"]
        margin = (profit / g["revenue"] * 100) if g["revenue"] > 0 else 0
        data.append({
            "date": k,
            "revenue": round(g["revenue"], 2),
            "fees": round(g["fees"], 2),
            "cost": round(g["cost"], 2),
            "profit": round(profit, 2),
            "margin": round(margin, 2),
        })

    return {"items": data, "group_by": group_by}


@router.get("/api/profit/products")
def get_profit_products(
    store_id: int = Query(...),
    limit: int = Query(10, ge=1, le=100),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """商品利润排行"""
    store = db.query(Store).filter_by(id=store_id, user_id=current_user.id).first()
    if not store:
        raise HTTPException(404, "店铺不存在")

    if not date_to:
        date_to = date.today().strftime("%Y-%m-%d")
    if not date_from:
        date_from = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")

    rows = db.query(RealizationReport).filter(
        RealizationReport.store_id == store_id,
        RealizationReport.user_id == current_user.id,
        RealizationReport.period_from >= date_from,
        RealizationReport.period_to <= date_to,
    ).all()

    rate = _get_rate(db, current_user.id)
    cost_map = _get_cost_map(db, store_id)

    product_groups = {}
    for r in rows:
        pid = r.product_id
        if pid not in product_groups:
            product_groups[pid] = {
                "product_id": pid,
                "offer_id": r.offer_id,
                "product_name": r.product_name,
                "revenue": 0, "fees": 0, "sold_units": 0,
            }
        pg = product_groups[pid]
        pg["revenue"] += r.revenue
        pg["fees"] += r.commission + r.logistics_cost + r.marketing_cost + r.penalty + r.other_cost
        pg["sold_units"] += r.sold_units

    result = []
    for pid, pg in product_groups.items():
        cost_rub = cost_map.get(pid, 0) * rate
        profit = pg["revenue"] - pg["fees"] - cost_rub
        margin = (profit / pg["revenue"] * 100) if pg["revenue"] > 0 else 0
        result.append({
            "product_id": pid,
            "offer_id": pg["offer_id"],
            "product_name": pg["product_name"],
            "sold_units": pg["sold_units"],
            "revenue": round(pg["revenue"], 2),
            "profit": round(profit, 2),
            "margin": round(margin, 2),
        })

    result.sort(key=lambda x: x["profit"], reverse=True)
    return {"items": result[:limit]}


@router.get("/api/profit/fees")
def get_profit_fees(
    store_id: int = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """费用构成"""
    store = db.query(Store).filter_by(id=store_id, user_id=current_user.id).first()
    if not store:
        raise HTTPException(404, "店铺不存在")

    if not date_to:
        date_to = date.today().strftime("%Y-%m-%d")
    if not date_from:
        date_from = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")

    rows = db.query(RealizationReport).filter(
        RealizationReport.store_id == store_id,
        RealizationReport.user_id == current_user.id,
        RealizationReport.period_from >= date_from,
        RealizationReport.period_to <= date_to,
    ).all()

    fees = {"佣金": 0.0, "物流": 0.0, "广告": 0.0, "罚款": 0.0, "其他": 0.0}
    for r in rows:
        fees["佣金"] += r.commission
        fees["物流"] += r.logistics_cost
        fees["广告"] += r.marketing_cost
        fees["罚款"] += r.penalty
        fees["其他"] += r.other_cost

    # 手动费用
    rate = _get_rate(db, current_user.id)
    expenses = db.query(ManualExpense).filter_by(store_id=store_id).all()
    for e in expenses:
        fees["其他"] += e.amount_cny * rate

    total = sum(fees.values())
    return {
        "items": [
            {"name": k, "amount": round(v, 2), "pct": round(v / total * 100, 2) if total > 0 else 0}
            for k, v in fees.items() if v > 0
        ],
        "total": round(total, 2),
    }


@router.get("/api/profit/detail")
def get_profit_detail(
    store_id: int = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    sort_by: str = Query("profit", regex="^(profit|revenue|margin|sold_units)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """利润明细表格数据"""
    store = db.query(Store).filter_by(id=store_id, user_id=current_user.id).first()
    if not store:
        raise HTTPException(404, "店铺不存在")

    if not date_to:
        date_to = date.today().strftime("%Y-%m-%d")
    if not date_from:
        date_from = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")

    rows = db.query(RealizationReport).filter(
        RealizationReport.store_id == store_id,
        RealizationReport.user_id == current_user.id,
        RealizationReport.period_from >= date_from,
        RealizationReport.period_to <= date_to,
    ).all()

    rate = _get_rate(db, current_user.id)
    cost_map = _get_cost_map(db, store_id)

    # 按商品聚合
    product_groups = {}
    for r in rows:
        pid = r.product_id
        if pid not in product_groups:
            product_groups[pid] = {
                "product_id": pid,
                "offer_id": r.offer_id,
                "product_name": r.product_name,
                "sku": r.sku,
                "revenue": 0, "commission": 0, "logistics": 0,
                "marketing": 0, "penalty": 0, "other": 0, "sold_units": 0,
            }
        pg = product_groups[pid]
        pg["revenue"] += r.revenue
        pg["commission"] += r.commission
        pg["logistics"] += r.logistics_cost
        pg["marketing"] += r.marketing_cost
        pg["penalty"] += r.penalty
        pg["other"] += r.other_cost
        pg["sold_units"] += r.sold_units

    items = []
    for pid, pg in product_groups.items():
        fees = pg["commission"] + pg["logistics"] + pg["marketing"] + pg["penalty"] + pg["other"]
        cost_rub = cost_map.get(pid, 0) * rate
        profit = pg["revenue"] - fees - cost_rub
        margin = (profit / pg["revenue"] * 100) if pg["revenue"] > 0 else 0
        items.append({
            "product_id": pid,
            "offer_id": pg["offer_id"],
            "product_name": pg["product_name"],
            "sold_units": pg["sold_units"],
            "revenue": round(pg["revenue"], 2),
            "cost": round(cost_rub, 2),
            "fees": round(fees, 2),
            "profit": round(profit, 2),
            "margin": round(margin, 2),
        })

    # 排序
    reverse = sort_order == "desc"
    items.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)

    total = len(items)
    start = (page - 1) * page_size
    paged = items[start:start + page_size]

    return {
        "items": paged,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }
