"""订阅/计费路由 — Plan 列表、Checkout、Webhook、Portal"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from models import User
from subscription_service import SubscriptionService
from payment_service import PaymentService
from quota_service import QuotaService
from config import STRIPE_WEBHOOK_SECRET

logger = logging.getLogger(__name__)

router = APIRouter(tags=["subscription"])


# ==================== Pydantic ====================

class CheckoutRequest(BaseModel):
    plan_name: str  # pro / enterprise


class PlanResponse(BaseModel):
    id: int
    name: str
    display_name: str
    price_cents: int
    currency: str
    limits: dict
    is_active: bool

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    id: int
    plan_id: int
    plan_name: Optional[str] = None
    plan_display_name: Optional[str] = None
    status: str
    trial_end: Optional[str] = None
    current_period_end: Optional[str] = None
    cancelled_at: Optional[str] = None

    class Config:
        from_attributes = True


class UsageStatsResponse(BaseModel):
    stores: dict
    alert_rules: dict
    products: dict
    features: dict


# ==================== Plan 列表 ====================

@router.get("/api/subscription/plans")
def list_plans(db: Session = Depends(get_db)):
    """获取所有可用套餐"""
    sub_svc = SubscriptionService(db)
    plans = sub_svc.get_all_plans(active_only=True)
    return [
        {
            "id": p.id,
            "name": p.name,
            "display_name": p.display_name,
            "price_cents": p.price_cents,
            "currency": p.currency,
            "limits": p.limits,
            "stripe_price_id": p.stripe_price_id,
        }
        for p in plans
    ]


# ==================== 当前订阅 ====================

@router.get("/api/subscription/current")
def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的订阅状态 + 用量统计"""
    sub_svc = SubscriptionService(db)
    quota_svc = QuotaService(db)

    sub = sub_svc.get_subscription(current_user.id)
    usage = quota_svc.get_all_usage_stats(current_user.id)

    result = {
        "subscription": None,
        "usage": usage,
    }

    if sub:
        plan = sub_svc.get_plan(sub.plan_id)
        result["subscription"] = {
            "id": sub.id,
            "plan_id": sub.plan_id,
            "plan_name": plan.name if plan else "unknown",
            "plan_display_name": plan.display_name if plan else "Unknown",
            "status": sub.status,
            "trial_end": sub.trial_end.isoformat() if sub.trial_end else None,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None,
        }

    return result


# ==================== Checkout ====================

@router.post("/api/subscription/checkout")
def create_checkout(
    data: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建 Stripe Checkout 会话"""
    payment_svc = PaymentService(db)

    try:
        checkout_url = payment_svc.create_checkout_session(current_user.id, data.plan_name)
        if not checkout_url:
            raise HTTPException(status_code=500, detail="无法创建支付会话")
        return {"checkout_url": checkout_url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Checkout creation failed: {e}")
        raise HTTPException(status_code=500, detail="创建支付会话失败")


# ==================== Webhook ====================

@router.post("/api/subscription/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Stripe Webhook 端点"""
    body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    payment_svc = PaymentService(db)

    try:
        result = payment_svc.handle_webhook(body, sig_header)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail="Webhook 处理失败")


# ==================== Customer Portal ====================

@router.post("/api/subscription/portal")
def create_portal(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建 Stripe Customer Portal 会话"""
    payment_svc = PaymentService(db)

    try:
        portal_url = payment_svc.create_portal_session(current_user.id)
        if not portal_url:
            raise HTTPException(status_code=500, detail="无法创建管理会话")
        return {"portal_url": portal_url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Portal creation failed: {e}")
        raise HTTPException(status_code=500, detail="创建管理会话失败")


# ==================== 支付历史 ====================

@router.get("/api/subscription/payments")
def get_payment_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取支付历史"""
    payment_svc = PaymentService(db)
    payments = payment_svc.get_payment_history(current_user.id, limit)
    return [
        {
            "id": p.id,
            "amount_cents": p.amount_cents,
            "currency": p.currency,
            "status": p.status,
            "description": p.description,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in payments
    ]


# ==================== 取消订阅 ====================

@router.post("/api/subscription/cancel")
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消订阅"""
    sub_svc = SubscriptionService(db)
    try:
        sub = sub_svc.cancel_subscription(current_user.id)
        # 清除限额缓存
        quota_svc = QuotaService(db)
        quota_svc.invalidate_cache(current_user.id)
        return {"message": "订阅已取消", "status": sub.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
