"""设置管理 API 路由"""
import logging
from typing import Optional
from datetime import date, timedelta, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc
import csv
import io

from database import get_db
from models import User, Store, ExchangeRate, ProductCost, ManualExpense, Product, RealizationReport
from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["settings"])


# ==================== 汇率 ====================

@router.get("/api/settings/exchange-rate")
def get_exchange_rate(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取汇率"""
    rate = db.query(ExchangeRate).filter_by(user_id=current_user.id).first()
    if not rate:
        return {"rate": 12.0}
    return {"rate": rate.rate, "updated_at": rate.updated_at.strftime("%Y-%m-%d %H:%M:%S") if rate.updated_at else None}


class ExchangeRateUpdate(BaseModel):
    rate: float = Field(..., ge=0.1, le=1000)


@router.put("/api/settings/exchange-rate")
def update_exchange_rate(
    data: ExchangeRateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新汇率"""
    rate = db.query(ExchangeRate).filter_by(user_id=current_user.id).first()
    if rate:
        rate.rate = data.rate
    else:
        db.add(ExchangeRate(user_id=current_user.id, rate=data.rate))
    db.commit()
    return {"message": "汇率已更新", "rate": data.rate}


# ==================== 采购成本 ====================

@router.put("/api/products/{product_id}/cost")
def update_product_cost(
    product_id: int,
    store_id: int = Query(...),
    cost_price: float = Query(..., ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新商品采购成本"""
    # 验证商品归属
    product = db.query(Product).filter_by(
        store_id=store_id, product_id=product_id, user_id=current_user.id
    ).first()
    if not product:
        raise HTTPException(404, "商品不存在")

    cost = db.query(ProductCost).filter_by(
        store_id=store_id, product_id=product_id, user_id=current_user.id
    ).first()
    if cost:
        cost.cost_price = cost_price
        cost.cost_updated_at = datetime.now()
    else:
        db.add(ProductCost(
            user_id=current_user.id,
            store_id=store_id,
            product_id=product_id,
            cost_price=cost_price,
            cost_updated_at=datetime.now(),
        ))
    db.commit()

    # 同步更新 Product 表的冗余字段
    product.cost_price = cost_price
    db.commit()

    return {"message": "采购成本已更新", "cost_price": cost_price}


# ==================== 手动费用 ====================

class ManualExpenseCreate(BaseModel):
    store_id: int
    expense_type: str = Field(..., description="费用类型: logistics/customs/other")
    amount_cny: float = Field(..., gt=0)
    product_id: Optional[int] = None
    description: Optional[str] = None
    expense_date: Optional[str] = None


class ManualExpenseUpdate(BaseModel):
    expense_type: Optional[str] = None
    amount_cny: Optional[float] = None
    product_id: Optional[int] = None
    description: Optional[str] = None
    expense_date: Optional[str] = None


@router.get("/api/expenses")
def list_expenses(
    store_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出手动费用"""
    expenses = db.query(ManualExpense).filter(
        ManualExpense.store_id == store_id,
        ManualExpense.user_id == current_user.id,
    ).order_by(desc(ManualExpense.created_at)).all()

    return [
        {
            "id": e.id,
            "expense_type": e.expense_type,
            "amount_cny": e.amount_cny,
            "product_id": e.product_id,
            "description": e.description,
            "expense_date": e.expense_date.strftime("%Y-%m-%d") if e.expense_date else None,
            "created_at": e.created_at.strftime("%Y-%m-%d %H:%M:%S") if e.created_at else None,
        }
        for e in expenses
    ]


@router.post("/api/expenses")
def create_expense(
    data: ManualExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新增手动费用"""
    store = db.query(Store).filter_by(id=data.store_id, user_id=current_user.id).first()
    if not store:
        raise HTTPException(404, "店铺不存在")

    expense_date = None
    if data.expense_date:
        try:
            expense_date = datetime.strptime(data.expense_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "日期格式错误，请使用 YYYY-MM-DD")

    expense = ManualExpense(
        user_id=current_user.id,
        store_id=data.store_id,
        product_id=data.product_id,
        expense_type=data.expense_type,
        amount_cny=data.amount_cny,
        description=data.description,
        expense_date=expense_date,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    return {"message": "费用已添加", "id": expense.id}


@router.put("/api/expenses/{expense_id}")
def update_expense(
    expense_id: int,
    data: ManualExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """编辑手动费用"""
    expense = db.query(ManualExpense).filter_by(id=expense_id, user_id=current_user.id).first()
    if not expense:
        raise HTTPException(404, "费用记录不存在")

    if data.expense_type is not None:
        expense.expense_type = data.expense_type
    if data.amount_cny is not None:
        expense.amount_cny = data.amount_cny
    if data.product_id is not None:
        expense.product_id = data.product_id
    if data.description is not None:
        expense.description = data.description
    if data.expense_date is not None:
        try:
            expense.expense_date = datetime.strptime(data.expense_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "日期格式错误")

    db.commit()
    return {"message": "费用已更新"}


@router.delete("/api/expenses/{expense_id}")
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除手动费用"""
    expense = db.query(ManualExpense).filter_by(id=expense_id, user_id=current_user.id).first()
    if not expense:
        raise HTTPException(404, "费用记录不存在")
    db.delete(expense)
    db.commit()
    return {"message": "费用已删除"}


# ==================== CSV 导出 ====================

@router.get("/api/export/profit-csv")
def export_profit_csv(
    store_id: int = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """导出利润明细 CSV"""
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

    rate_row = db.query(ExchangeRate).filter_by(user_id=current_user.id).first()
    rate = rate_row.rate if rate_row else 12.0

    cost_map = {c.product_id: c.cost_price for c in db.query(ProductCost).filter_by(store_id=store_id).all()}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["商品ID", "货号", "商品名称", "销量", "收入(RUB)", "成本(RUB)", "费用(RUB)", "利润(RUB)", "毛利率(%)"])

    product_groups = {}
    for r in rows:
        pid = r.product_id
        if pid not in product_groups:
            product_groups[pid] = {"offer_id": r.offer_id, "name": r.product_name, "revenue": 0, "fees": 0, "sold": 0}
        pg = product_groups[pid]
        pg["revenue"] += r.revenue
        pg["fees"] += r.commission + r.logistics_cost + r.marketing_cost + r.penalty + r.other_cost
        pg["sold"] += r.sold_units

    for pid, pg in product_groups.items():
        cost = cost_map.get(pid, 0) * rate
        profit = pg["revenue"] - pg["fees"] - cost
        margin = (profit / pg["revenue"] * 100) if pg["revenue"] > 0 else 0
        writer.writerow([pid, pg["offer_id"], pg["name"], pg["sold"], round(pg["revenue"], 2), round(cost, 2), round(pg["fees"], 2), round(profit, 2), round(margin, 2)])

    from fastapi.responses import Response
    bom = "\ufeff"
    return Response(
        content=bom + output.getvalue(),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename=profit_{date_from}_{date_to}.csv"}
    )
