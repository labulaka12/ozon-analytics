"""利润核算引擎

提供完整的利润计算能力：
  - 单商品 / 多商品 / 店铺级利润核算
  - 费用构成分解（佣金、物流、广告、罚款、退货、仓储、头程）
  - 汇率自动换算（CNY <-> RUB）
  - 利润预测（基于历史趋势）
  - 盈亏平衡点分析

核心公式：
  净利润 = 销售收入(RUB) - 平台佣金 - 物流费 - 广告费 - 罚款 - 退货损失
         - 其他平台费用 - 采购成本(CNY→RUB) - 头程物流 - 关税 - 仓储费

数据来源：
  - RealizationReport: Ozon 销售实现报告（收入 + 平台费用）
  - FinanceTransaction: 财务交易明细（广告费等补充）
  - ProductCost: 用户录入的采购成本
  - ManualExpense: 手动补录费用（头程物流、关税等）
  - ExchangeRate: 用户自定义汇率
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    Store, Product, RealizationReport, FinanceTransaction,
    ProductCost, ManualExpense, ExchangeRate, Order
)

logger = logging.getLogger(__name__)


# ==================== 数据类 ====================


@dataclass
class ProfitBreakdown:
    """利润分解"""
    # 收入
    revenue: float = 0.0                    # 销售收入 (RUB)
    returns_loss: float = 0.0               # 退货损失 (RUB)

    # 平台费用
    commission: float = 0.0                 # 佣金 (RUB)
    logistics: float = 0.0                  # 物流费 (RUB)
    advertising: float = 0.0                # 广告费 (RUB)
    penalty: float = 0.0                    # 罚款 (RUB)
    other_platform_fees: float = 0.0        # 其他平台费用 (RUB)

    # 用户录入成本
    purchase_cost_cny: float = 0.0          # 采购成本 (CNY)
    freight_cost_cny: float = 0.0           # 头程物流 (CNY)
    customs_cost_cny: float = 0.0           # 关税 (CNY)
    other_manual_cost_cny: float = 0.0      # 其他手动费用 (CNY)

    # 汇率
    exchange_rate: float = 12.0             # 1 CNY = ? RUB

    @property
    def total_revenue(self) -> float:
        """净收入（扣除退货）"""
        return self.revenue - self.returns_loss

    @property
    def total_platform_fees(self) -> float:
        """平台总费用 (RUB)"""
        return (self.commission + self.logistics + self.advertising +
                self.penalty + self.other_platform_fees)

    @property
    def total_manual_cost_rub(self) -> float:
        """手动费用转 RUB"""
        return (self.purchase_cost_cny + self.freight_cost_cny +
                self.customs_cost_cny + self.other_manual_cost_cny) * self.exchange_rate

    @property
    def total_cost(self) -> float:
        """总成本 (RUB)"""
        return self.total_platform_fees + self.total_manual_cost_rub

    @property
    def net_profit(self) -> float:
        """净利润 (RUB)"""
        return self.total_revenue - self.total_cost

    @property
    def profit_margin(self) -> float:
        """利润率 (%)"""
        if self.total_revenue <= 0:
            return 0.0
        return (self.net_profit / self.total_revenue) * 100

    @property
    def net_profit_cny(self) -> float:
        """净利润 (CNY)"""
        return self.net_profit / self.exchange_rate if self.exchange_rate > 0 else 0.0

    @property
    def roi(self) -> float:
        """投资回报率 (%)"""
        if self.total_cost <= 0:
            return 0.0
        return (self.net_profit / self.total_cost) * 100

    def to_dict(self) -> dict:
        return {
            "revenue": round(self.revenue, 2),
            "returns_loss": round(self.returns_loss, 2),
            "net_revenue": round(self.total_revenue, 2),
            "commission": round(self.commission, 2),
            "logistics": round(self.logistics, 2),
            "advertising": round(self.advertising, 2),
            "penalty": round(self.penalty, 2),
            "other_platform_fees": round(self.other_platform_fees, 2),
            "total_platform_fees": round(self.total_platform_fees, 2),
            "purchase_cost_cny": round(self.purchase_cost_cny, 2),
            "freight_cost_cny": round(self.freight_cost_cny, 2),
            "customs_cost_cny": round(self.customs_cost_cny, 2),
            "other_manual_cost_cny": round(self.other_manual_cost_cny, 2),
            "total_manual_cost_rub": round(self.total_manual_cost_rub, 2),
            "total_cost": round(self.total_cost, 2),
            "net_profit": round(self.net_profit, 2),
            "net_profit_cny": round(self.net_profit_cny, 2),
            "profit_margin": round(self.profit_margin, 2),
            "roi": round(self.roi, 2),
            "exchange_rate": self.exchange_rate,
        }


@dataclass
class ProductProfit:
    """单商品利润"""
    product_id: int
    offer_id: str = ""
    product_name: str = ""
    sold_units: int = 0
    breakdown: ProfitBreakdown = field(default_factory=ProfitBreakdown)

    @property
    def unit_profit(self) -> float:
        """单品利润 (RUB)"""
        return self.breakdown.net_profit / self.sold_units if self.sold_units > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "offer_id": self.offer_id,
            "product_name": self.product_name,
            "sold_units": self.sold_units,
            "unit_profit": round(self.unit_profit, 2),
            **self.breakdown.to_dict(),
        }


@dataclass
class StoreProfit:
    """店铺级利润汇总"""
    store_id: int
    store_name: str = ""
    total_products: int = 0
    total_sold_units: int = 0
    breakdown: ProfitBreakdown = field(default_factory=ProfitBreakdown)
    top_products: List[ProductProfit] = field(default_factory=list)
    worst_products: List[ProductProfit] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "store_id": self.store_id,
            "store_name": self.store_name,
            "total_products": self.total_products,
            "total_sold_units": self.total_sold_units,
            **self.breakdown.to_dict(),
            "top_products": [p.to_dict() for p in self.top_products],
            "worst_products": [p.to_dict() for p in self.worst_products],
        }


# ==================== 核算引擎 ====================


class ProfitCalculator:
    """利润计算器"""

    def __init__(self, db: Session, store_id: int, user_id: int,
                 date_from: str, date_to: str):
        self.db = db
        self.store_id = store_id
        self.user_id = user_id
        self.date_from = date_from
        self.date_to = date_to

        # 缓存
        self._rate: Optional[float] = None
        self._cost_map: Optional[Dict[int, float]] = None
        self._manual_expenses: Optional[List] = None
        self._realization_rows: Optional[List] = None
        self._finance_rows: Optional[List] = None
        self._advertising_total: Optional[float] = None

    # ==================== 数据加载 ====================

    @property
    def rate(self) -> float:
        if self._rate is None:
            row = self.db.query(ExchangeRate).filter_by(user_id=self.user_id).first()
            self._rate = row.rate if row else 12.0
        return self._rate

    @property
    def cost_map(self) -> Dict[int, float]:
        """{product_id: cost_price_cny}"""
        if self._cost_map is None:
            costs = self.db.query(ProductCost).filter_by(
                store_id=self.store_id
            ).all()
            self._cost_map = {c.product_id: c.cost_price for c in costs}
        return self._cost_map

    @property
    def manual_expenses(self) -> List:
        if self._manual_expenses is None:
            self._manual_expenses = self.db.query(ManualExpense).filter(
                ManualExpense.store_id == self.store_id,
                ManualExpense.user_id == self.user_id,
            ).all()
        return self._manual_expenses

    @property
    def realization_rows(self) -> List[RealizationReport]:
        if self._realization_rows is None:
            self._realization_rows = self.db.query(RealizationReport).filter(
                RealizationReport.store_id == self.store_id,
                RealizationReport.user_id == self.user_id,
                RealizationReport.period_from >= self.date_from,
                RealizationReport.period_to <= self.date_to,
            ).all()
        return self._realization_rows

    @property
    def advertising_total(self) -> float:
        """从财务交易中提取广告费"""
        if self._advertising_total is None:
            # 广告费用在 FinanceTransaction 中，operation_type 通常为 "MarketplaceMarketingExpense"
            result = self.db.query(
                func.coalesce(func.sum(FinanceTransaction.amount), 0)
            ).filter(
                FinanceTransaction.store_id == self.store_id,
                FinanceTransaction.user_id == self.user_id,
                FinanceTransaction.transaction_date >= self.date_from,
                FinanceTransaction.transaction_date <= self.date_to + "T23:59:59",
                FinanceTransaction.transaction_type.contains("Marketing"),
            ).scalar()
            self._advertising_total = abs(float(result))  # 金额为负数，取绝对值
        return self._advertising_total

    # ==================== 费用计算 ====================

    def _calc_manual_costs(self, product_id: Optional[int] = None) -> Tuple[float, float, float, float]:
        """计算手动费用分解：采购、头程、关税、其他"""
        purchase = 0.0
        freight = 0.0
        customs = 0.0
        other = 0.0

        for e in self.manual_expenses:
            # 如果指定了商品，只取该商品或全局费用
            if product_id is not None and e.product_id is not None and e.product_id != product_id:
                continue

            if e.expense_type == "logistics":
                freight += e.amount_cny
            elif e.expense_type == "customs":
                customs += e.amount_cny
            else:
                other += e.amount_cny

        # 采购成本
        if product_id is not None:
            purchase = self.cost_map.get(product_id, 0)
        else:
            purchase = sum(self.cost_map.values())

        return purchase, freight, customs, other

    # ==================== 核心计算 ====================

    def calc_product_profit(self, product_id: int) -> ProductProfit:
        """计算单商品利润"""
        rows = [r for r in self.realization_rows if r.product_id == product_id]
        if not rows:
            return ProductProfit(
                product_id=product_id,
                breakdown=ProfitBreakdown(exchange_rate=self.rate),
            )

        # 聚合数据
        total_revenue = sum(r.revenue for r in rows)
        total_commission = sum(r.commission for r in rows)
        total_logistics = sum(r.logistics_cost for r in rows)
        total_marketing = sum(r.marketing_cost for r in rows)
        total_penalty = sum(r.penalty for r in rows)
        total_other = sum(r.other_cost for r in rows)
        total_sold = sum(r.sold_units for r in rows)

        # 广告费：按销售收入比例分摊
        store_total_revenue = sum(r.revenue for r in self.realization_rows)
        ad_share = (total_revenue / store_total_revenue * self.advertising_total) if store_total_revenue > 0 else 0

        # 手动费用
        purchase, freight, customs, other_manual = self._calc_manual_costs(product_id)

        # 退货损失估算（从订单数据）
        returns_loss = self._calc_returns_loss(product_id)

        first_row = rows[0]
        breakdown = ProfitBreakdown(
            revenue=total_revenue,
            returns_loss=returns_loss,
            commission=total_commission,
            logistics=total_logistics,
            advertising=total_marketing + ad_share,
            penalty=total_penalty,
            other_platform_fees=total_other,
            purchase_cost_cny=purchase,
            freight_cost_cny=freight,
            customs_cost_cny=customs,
            other_manual_cost_cny=other_manual,
            exchange_rate=self.rate,
        )

        return ProductProfit(
            product_id=product_id,
            offer_id=first_row.offer_id or "",
            product_name=first_row.product_name or "",
            sold_units=total_sold,
            breakdown=breakdown,
        )

    def calc_store_profit(self) -> StoreProfit:
        """计算店铺级利润汇总"""
        rows = self.realization_rows

        # 聚合
        total_revenue = sum(r.revenue for r in rows)
        total_commission = sum(r.commission for r in rows)
        total_logistics = sum(r.logistics_cost for r in rows)
        total_marketing = sum(r.marketing_cost for r in rows)
        total_penalty = sum(r.penalty for r in rows)
        total_other = sum(r.other_cost for r in rows)
        total_sold = sum(r.sold_units for r in rows)

        # 广告费（财务交易）
        total_advertising = total_marketing + self.advertising_total

        # 退货损失（全局）
        total_returns = sum(self._calc_returns_loss(None) for _ in [1])  # 全局退货
        # 实际：聚合所有商品退货
        all_product_ids = set(r.product_id for r in rows)
        total_returns = sum(self._calc_returns_loss(pid) for pid in all_product_ids)

        # 手动费用
        purchase, freight, customs, other_manual = self._calc_manual_costs()

        # 商品数量
        unique_products = len(set(r.product_id for r in rows))

        # 店铺名称
        store = self.db.query(Store).filter_by(id=self.store_id).first()
        store_name = store.name if store else ""

        breakdown = ProfitBreakdown(
            revenue=total_revenue,
            returns_loss=total_returns,
            commission=total_commission,
            logistics=total_logistics,
            advertising=total_advertising,
            penalty=total_penalty,
            other_platform_fees=total_other,
            purchase_cost_cny=purchase,
            freight_cost_cny=freight,
            customs_cost_cny=customs,
            other_manual_cost_cny=other_manual,
            exchange_rate=self.rate,
        )

        # 计算每个商品的利润用于排名
        product_profits = []
        for pid in all_product_ids:
            try:
                pp = self.calc_product_profit(pid)
                if pp.sold_units > 0:
                    product_profits.append(pp)
            except Exception:
                pass

        product_profits.sort(key=lambda x: x.breakdown.net_profit, reverse=True)
        top_n = min(10, len(product_profits))

        return StoreProfit(
            store_id=self.store_id,
            store_name=store_name,
            total_products=unique_products,
            total_sold_units=total_sold,
            breakdown=breakdown,
            top_products=product_profits[:top_n],
            worst_products=product_profits[-top_n:] if top_n > 0 else [],
        )

    def calc_product_profits_all(self) -> List[ProductProfit]:
        """计算所有商品利润（用于排行榜）"""
        all_pids = set(r.product_id for r in self.realization_rows)
        profits = []
        for pid in all_pids:
            try:
                pp = self.calc_product_profit(pid)
                if pp.sold_units > 0:
                    profits.append(pp)
            except Exception as e:
                logger.warning(f"Failed to calc profit for product {pid}: {e}")

        profits.sort(key=lambda x: x.breakdown.net_profit, reverse=True)
        return profits

    def _calc_returns_loss(self, product_id: Optional[int] = None) -> float:
        """计算退货损失

        从订单数据中统计已退货的订单金额作为退货损失。
        """
        query = self.db.query(
            func.coalesce(func.sum(Order.total_price), 0)
        ).filter(
            Order.store_id == self.store_id,
            Order.user_id == self.user_id,
            Order.status == "cancelled",
            Order.order_created_at >= self.date_from,
            Order.order_created_at <= self.date_to + "T23:59:59",
        )
        if product_id is not None:
            query = query.filter(Order.product_id == product_id)

        return float(query.scalar() or 0)

    # ==================== 利润预测 ====================

    def predict_profit(self, days_ahead: int = 30) -> dict:
        """基于近期趋势预测未来利润

        使用简单移动平均法，基于近 14 天数据预测未来 N 天。
        """
        from datetime import date, timedelta

        # 获取近 14 天每日利润
        today = date.today()
        past_14 = (today - timedelta(days=14)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        rows = self.db.query(RealizationReport).filter(
            RealizationReport.store_id == self.store_id,
            RealizationReport.user_id == self.user_id,
            RealizationReport.period_from >= past_14,
            RealizationReport.period_to <= today_str,
        ).all()

        # 按天分组计算利润
        daily_profits = {}
        for r in rows:
            day_key = str(r.period_from)[:10]
            if day_key not in daily_profits:
                daily_profits[day_key] = {"revenue": 0, "fees": 0, "cost": 0}
            daily_profits[day_key]["revenue"] += r.revenue
            daily_profits[day_key]["fees"] += (
                r.commission + r.logistics_cost + r.marketing_cost +
                r.penalty + r.other_cost
            )
            pid_cost = self.cost_map.get(r.product_id, 0) * self.rate
            daily_profits[day_key]["cost"] += pid_cost

        profits_list = []
        for k in sorted(daily_profits.keys()):
            d = daily_profits[k]
            profit = d["revenue"] - d["fees"] - d["cost"]
            profits_list.append(profit)

        if not profits_list:
            return {"predicted_daily_profit": 0, "predicted_total": 0, "confidence": "low"}

        # 简单移动平均
        avg_daily_profit = sum(profits_list) / len(profits_list)

        # 趋势：最后 3 天 vs 前 3 天
        recent = profits_list[-3:] if len(profits_list) >= 6 else profits_list
        earlier = profits_list[:3] if len(profits_list) >= 6 else profits_list
        trend = (sum(recent) / len(recent)) - (sum(earlier) / len(earlier)) if recent else 0

        # 预测
        predicted_total = 0
        for i in range(days_ahead):
            daily_pred = avg_daily_profit + trend * (i / 7)  # 趋势缓慢影响
            predicted_total += daily_pred

        confidence = "high" if len(profits_list) >= 10 else "medium" if len(profits_list) >= 5 else "low"

        return {
            "avg_daily_profit": round(avg_daily_profit, 2),
            "trend_direction": "up" if trend > 0 else "down" if trend < 0 else "flat",
            "trend_amount": round(trend, 2),
            "predicted_daily_profit": round(avg_daily_profit + trend, 2),
            "predicted_total": round(predicted_total, 2),
            "days_ahead": days_ahead,
            "data_points": len(profits_list),
            "confidence": confidence,
        }

    def breakeven_analysis(self) -> dict:
        """盈亏平衡点分析

        计算需要卖出多少件商品才能覆盖所有固定成本。
        固定成本 = 头程物流 + 关税 + 其他手动费用
        单位贡献 = 单价 - 佣金率 - 物流费率 - 采购成本
        """
        rows = self.realization_rows
        if not rows:
            return {"breakeven_units": 0, "is_profitable": False, "message": "暂无销售数据"}

        # 固定成本 (CNY)
        _, freight, customs, other_manual = self._calc_manual_costs()
        fixed_cost_cny = freight + customs + other_manual
        fixed_cost_rub = fixed_cost_cny * self.rate

        # 单位贡献 (RUB)
        total_sold = sum(r.sold_units for r in rows)
        if total_sold == 0:
            return {"breakeven_units": 0, "is_profitable": False, "message": "暂无销售数据"}

        total_revenue = sum(r.revenue for r in rows)
        total_variable_fees = sum(
            r.commission + r.logistics_cost + r.marketing_cost +
            r.penalty + r.other_cost
            for r in rows
        )
        total_purchase_rub = sum(
            self.cost_map.get(r.product_id, 0) * self.rate * r.sold_units
            for r in rows
        )

        avg_price = total_revenue / total_sold
        avg_variable_fee = total_variable_fees / total_sold
        avg_purchase_cost = total_purchase_rub / total_sold

        unit_contribution = avg_price - avg_variable_fee - avg_purchase_cost

        if unit_contribution <= 0:
            return {
                "breakeven_units": -1,
                "is_profitable": False,
                "message": "单品毛利为负，无法达到盈亏平衡",
                "avg_price": round(avg_price, 2),
                "avg_cost": round(avg_variable_fee + avg_purchase_cost, 2),
                "unit_contribution": round(unit_contribution, 2),
            }

        breakeven_units = int(fixed_cost_rub / unit_contribution) + 1

        return {
            "breakeven_units": breakeven_units,
            "is_profitable": total_sold >= breakeven_units,
            "fixed_cost_rub": round(fixed_cost_rub, 2),
            "fixed_cost_cny": round(fixed_cost_cny, 2),
            "avg_price": round(avg_price, 2),
            "avg_variable_fee": round(avg_variable_fee, 2),
            "avg_purchase_cost": round(avg_purchase_cost, 2),
            "unit_contribution": round(unit_contribution, 2),
            "current_sold_units": total_sold,
            "message": (
                f"当前已售 {total_sold} 件，已盈利"
                if total_sold >= breakeven_units
                else f"还需销售 {breakeven_units - total_sold} 件达到盈亏平衡"
            ),
        }


# ==================== 便捷函数 ====================


def calculate_store_profit(
    db: Session,
    store_id: int,
    user_id: int,
    date_from: str,
    date_to: str,
) -> StoreProfit:
    """便捷函数：计算店铺利润"""
    calc = ProfitCalculator(db, store_id, user_id, date_from, date_to)
    return calc.calc_store_profit()


def calculate_product_profit(
    db: Session,
    store_id: int,
    user_id: int,
    product_id: int,
    date_from: str,
    date_to: str,
) -> ProductProfit:
    """便捷函数：计算单商品利润"""
    calc = ProfitCalculator(db, store_id, user_id, date_from, date_to)
    return calc.calc_product_profit(product_id)


def predict_profit(
    db: Session,
    store_id: int,
    user_id: int,
    days_ahead: int = 30,
) -> dict:
    """便捷函数：利润预测"""
    today = date.today()
    date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    date_to = today.strftime("%Y-%m-%d")
    calc = ProfitCalculator(db, store_id, user_id, date_from, date_to)
    return calc.predict_profit(days_ahead)


def breakeven_analysis(
    db: Session,
    store_id: int,
    user_id: int,
) -> dict:
    """便捷函数：盈亏平衡分析"""
    today = date.today()
    date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    date_to = today.strftime("%Y-%m-%d")
    calc = ProfitCalculator(db, store_id, user_id, date_from, date_to)
    return calc.breakeven_analysis()
