"""订阅核心业务逻辑 — 状态机、升级/降级/取消、试用管理"""
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session
from models import User, Plan, Subscription, PaymentHistory
from config import TRIAL_DAYS

logger = logging.getLogger(__name__)


class SubscriptionStatus(str, Enum):
    """订阅状态枚举"""
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


# 合法状态转换映射
VALID_TRANSITIONS = {
    SubscriptionStatus.TRIALING: [SubscriptionStatus.ACTIVE, SubscriptionStatus.EXPIRED],
    SubscriptionStatus.ACTIVE: [SubscriptionStatus.PAST_DUE, SubscriptionStatus.CANCELLED],
    SubscriptionStatus.PAST_DUE: [SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELLED, SubscriptionStatus.EXPIRED],
    SubscriptionStatus.CANCELLED: [SubscriptionStatus.EXPIRED],
    SubscriptionStatus.EXPIRED: [SubscriptionStatus.ACTIVE],  # re-subscribe
}


class SubscriptionService:
    """订阅业务服务"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 查询 ====================

    def get_active_subscription(self, user_id: int) -> Optional[Subscription]:
        """获取用户当前有效订阅（活跃状态）"""
        return self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status.in_(["trialing", "active", "past_due"]),
        ).order_by(Subscription.created_at.desc()).first()

    def get_subscription(self, user_id: int) -> Optional[Subscription]:
        """获取用户最新订阅（任意状态）"""
        return self.db.query(Subscription).filter_by(user_id=user_id).order_by(
            Subscription.created_at.desc()
        ).first()

    def get_plan(self, plan_id: int) -> Optional[Plan]:
        return self.db.query(Plan).filter_by(id=plan_id).first()

    def get_plan_by_name(self, name: str) -> Optional[Plan]:
        return self.db.query(Plan).filter_by(name=name).first()

    def get_all_plans(self, active_only: bool = True) -> list:
        query = self.db.query(Plan)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(Plan.sort_order).all()

    def get_user_plan_limits(self, user_id: int) -> dict:
        """获取用户当前套餐的限额配置"""
        sub = self.get_active_subscription(user_id)
        if sub:
            plan = self.get_plan(sub.plan_id)
            if plan:
                return plan.limits or {}
        # 无订阅 → 返回 free 套餐限额
        free_plan = self.get_plan_by_name("free")
        if free_plan:
            return free_plan.limits or {}
        # 兜底默认值
        return DEFAULT_FREE_LIMITS

    # ==================== 状态机 ====================

    def _validate_transition(self, current: str, target: str) -> bool:
        """校验状态转换是否合法"""
        current_status = SubscriptionStatus(current)
        target_status = SubscriptionStatus(target)
        return target_status in VALID_TRANSITIONS.get(current_status, [])

    def transition_status(self, subscription_id: int, new_status: str) -> Subscription:
        """执行订阅状态转换"""
        sub = self.db.query(Subscription).filter_by(id=subscription_id).first()
        if not sub:
            raise ValueError(f"Subscription {subscription_id} not found")

        if not self._validate_transition(sub.status, new_status):
            raise ValueError(f"Invalid transition: {sub.status} → {new_status}")

        old_status = sub.status
        sub.status = new_status

        if new_status == SubscriptionStatus.EXPIRED:
            sub.expired_at = datetime.now(timezone.utc)
        elif new_status == SubscriptionStatus.CANCELLED:
            sub.cancelled_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(sub)
        logger.info(f"Subscription {subscription_id}: {old_status} → {new_status}")
        return sub

    # ==================== 试用管理 ====================

    def create_trial_subscription(self, user_id: int) -> Subscription:
        """为新用户创建 Free 试用订阅"""
        free_plan = self.get_plan_by_name("free")
        if not free_plan:
            # 如果 free plan 不存在，创建默认的
            free_plan = self._ensure_free_plan()

        now = datetime.now(timezone.utc)
        sub = Subscription(
            user_id=user_id,
            plan_id=free_plan.id,
            status=SubscriptionStatus.TRIALING,
            trial_start=now,
            trial_end=now + timedelta(days=TRIAL_DAYS),
            current_period_start=now,
            current_period_end=now + timedelta(days=TRIAL_DAYS),
        )
        self.db.add(sub)
        self.db.commit()
        self.db.refresh(sub)
        logger.info(f"Created trial subscription for user {user_id}")
        return sub

    def _ensure_free_plan(self) -> Plan:
        """确保 Free Plan 存在"""
        free_plan = self.get_plan_by_name("free")
        if free_plan:
            return free_plan

        free_plan = Plan(
            name="free",
            display_name="Free",
            price_cents=0,
            currency="usd",
            limits=DEFAULT_FREE_LIMITS,
            is_active=True,
            sort_order=1,
        )
        self.db.add(free_plan)
        self.db.commit()
        self.db.refresh(free_plan)
        return free_plan

    def ensure_default_plans(self):
        """确保默认套餐存在（启动时调用）"""
        defaults = [
            {"name": "free", "display_name": "Free", "price_cents": 0, "limits": DEFAULT_FREE_LIMITS, "sort_order": 1},
            {"name": "pro", "display_name": "Pro", "price_cents": 2990, "limits": DEFAULT_PRO_LIMITS, "sort_order": 2},
            {"name": "enterprise", "display_name": "Enterprise", "price_cents": 9900, "limits": DEFAULT_ENTERPRISE_LIMITS, "sort_order": 3},
        ]
        for d in defaults:
            existing = self.get_plan_by_name(d["name"])
            if not existing:
                plan = Plan(**d, currency="usd", is_active=True)
                self.db.add(plan)
                logger.info(f"Created default plan: {d['name']}")
        self.db.commit()

    # ==================== 订阅变更 ====================

    def activate_subscription(self, user_id: int, plan_id: int,
                              stripe_subscription_id: str = "",
                              stripe_customer_id: str = "",
                              current_period_start: datetime = None,
                              current_period_end: datetime = None) -> Subscription:
        """激活订阅（Stripe 支付成功后调用）"""
        sub = self.get_active_subscription(user_id)

        if sub and sub.status == SubscriptionStatus.TRIALING:
            # 试用 → 付费
            sub.plan_id = plan_id
            sub.status = SubscriptionStatus.ACTIVE
            sub.stripe_subscription_id = stripe_subscription_id
            sub.stripe_customer_id = stripe_customer_id
            sub.current_period_start = current_period_start or datetime.now(timezone.utc)
            sub.current_period_end = current_period_end
        elif sub and sub.status == SubscriptionStatus.ACTIVE:
            # 升级/降级
            sub.plan_id = plan_id
            sub.stripe_subscription_id = stripe_subscription_id or sub.stripe_subscription_id
        else:
            # 重新订阅（从 expired）
            now = datetime.now(timezone.utc)
            sub = Subscription(
                user_id=user_id,
                plan_id=plan_id,
                status=SubscriptionStatus.ACTIVE,
                stripe_subscription_id=stripe_subscription_id,
                stripe_customer_id=stripe_customer_id,
                current_period_start=current_period_start or now,
                current_period_end=current_period_end,
            )
            self.db.add(sub)

        self.db.commit()
        self.db.refresh(sub)
        logger.info(f"Activated subscription for user {user_id}, plan_id={plan_id}")
        return sub

    def cancel_subscription(self, user_id: int) -> Subscription:
        """取消订阅"""
        sub = self.get_active_subscription(user_id)
        if not sub:
            raise ValueError("No active subscription to cancel")
        return self.transition_status(sub.id, SubscriptionStatus.CANCELLED)

    # ==================== 到期检查 ====================

    def check_expired_trials(self):
        """检查并过期试用期已结束的订阅（定时任务）"""
        now = datetime.now(timezone.utc)
        expired_trials = self.db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.TRIALING,
            Subscription.trial_end < now,
        ).all()

        for sub in expired_trials:
            try:
                self.transition_status(sub.id, SubscriptionStatus.EXPIRED)
                logger.info(f"Trial expired for user {sub.user_id}")
                # 发送到期通知
                try:
                    from email_service import send_subscription_expired_email
                    user = self.db.query(User).filter_by(id=sub.user_id).first()
                    if user:
                        send_subscription_expired_email(user.email)
                except Exception as e:
                    logger.error(f"Failed to send expiry email: {e}")
            except Exception as e:
                logger.error(f"Failed to expire trial for subscription {sub.id}: {e}")

    def check_expired_subscriptions(self):
        """检查并过期计费周期已结束的订阅"""
        now = datetime.now(timezone.utc)
        expired = self.db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.current_period_end < now,
        ).all()

        for sub in expired:
            try:
                self.transition_status(sub.id, SubscriptionStatus.EXPIRED)
                logger.info(f"Subscription expired for user {sub.user_id}")
            except Exception as e:
                logger.error(f"Failed to expire subscription {sub.id}: {e}")


# ==================== 默认套餐限额 ====================

DEFAULT_FREE_LIMITS = {
    "max_stores": 1,
    "max_products_per_store": 100,
    "sync_frequency": "daily",
    "data_retention_days": 30,
    "max_alert_rules": 3,
    "max_team_members": 1,
    "profit_analysis": False,
    "profit_prediction": False,
    "api_access": "none",
    "csv_export": True,
}

DEFAULT_PRO_LIMITS = {
    "max_stores": 5,
    "max_products_per_store": 1000,
    "sync_frequency": "every_8_hours",
    "data_retention_days": 90,
    "max_alert_rules": 20,
    "max_team_members": 3,
    "profit_analysis": True,
    "profit_prediction": False,
    "api_access": "readonly",
    "csv_export": True,
}

DEFAULT_ENTERPRISE_LIMITS = {
    "max_stores": 50,
    "max_products_per_store": 99999,
    "sync_frequency": "hourly",
    "data_retention_days": 365,
    "max_alert_rules": 999,
    "max_team_members": 50,
    "profit_analysis": True,
    "profit_prediction": True,
    "api_access": "full",
    "csv_export": True,
}
