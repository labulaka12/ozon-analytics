"""Stripe 支付集成 — Checkout Session、Webhook 处理、Customer Portal"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from models import User, Subscription, PaymentHistory

from config import (
    STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET,
    STRIPE_PRO_PRICE_ID, STRIPE_ENTERPRISE_PRICE_ID,
    FRONTEND_URL,
)

logger = logging.getLogger(__name__)

# Stripe SDK 按需导入（未配置时优雅降级）
_stripe = None

def _get_stripe():
    global _stripe
    if _stripe is None:
        if STRIPE_SECRET_KEY:
            try:
                import stripe
                stripe.api_key = STRIPE_SECRET_KEY
                _stripe = stripe
            except ImportError:
                logger.warning("stripe package not installed, payment features disabled")
        else:
            logger.info("STRIPE_SECRET_KEY not configured, payment features disabled")
    return _stripe


class PaymentService:
    """Stripe 支付服务"""

    def __init__(self, db: Session):
        self.db = db
        self.stripe = _get_stripe()

    # ==================== Checkout ====================

    def create_checkout_session(self, user_id: int, plan_name: str) -> Optional[str]:
        """创建 Stripe Checkout Session，返回 checkout_url"""
        if not self.stripe:
            raise ValueError("Stripe 未配置，无法创建支付会话")

        user = self.db.query(User).filter_by(id=user_id).first()
        if not user:
            raise ValueError("用户不存在")

        # 获取或创建 Stripe Customer
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer = self.stripe.Customer.create(
                email=user.email,
                metadata={"user_id": user_id},
            )
            customer_id = customer.id
            user.stripe_customer_id = customer_id
            self.db.commit()

        # 选择 Price ID
        price_id = self._get_price_id(plan_name)
        if not price_id:
            raise ValueError(f"套餐 {plan_name} 未配置 Stripe Price ID")

        try:
            session = self.stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=f"{FRONTEND_URL}/subscription?success=true",
                cancel_url=f"{FRONTEND_URL}/pricing?canceled=true",
                metadata={"user_id": user_id, "plan_name": plan_name},
            )
            return session.url
        except Exception as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise

    # ==================== Customer Portal ====================

    def create_portal_session(self, user_id: int) -> Optional[str]:
        """创建 Stripe Customer Portal Session，返回 portal_url"""
        if not self.stripe:
            raise ValueError("Stripe 未配置")

        user = self.db.query(User).filter_by(id=user_id).first()
        if not user or not user.stripe_customer_id:
            raise ValueError("未找到 Stripe 客户信息")

        try:
            session = self.stripe.billing_portal.Session.create(
                customer=user.stripe_customer_id,
                return_url=f"{FRONTEND_URL}/subscription",
            )
            return session.url
        except Exception as e:
            logger.error(f"Failed to create portal session: {e}")
            raise

    # ==================== Webhook ====================

    def handle_webhook(self, payload: bytes, sig_header: str) -> dict:
        """处理 Stripe Webhook 事件"""
        if not self.stripe:
            raise ValueError("Stripe 未配置")

        try:
            event = self.stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except self.stripe.WebhookSignatureVerifier.error as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise ValueError("Webhook 签名验证失败")
        except Exception as e:
            logger.error(f"Webhook construction failed: {e}")
            raise ValueError("Webhook 解析失败")

        event_type = event["type"]
        logger.info(f"Stripe webhook: {event_type}")

        handler = {
            "checkout.session.completed": self._handle_checkout_completed,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.paid": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_invoice_payment_failed,
        }.get(event_type)

        if handler:
            try:
                return handler(event)
            except Exception as e:
                logger.error(f"Webhook handler error for {event_type}: {e}")
                raise
        else:
            logger.info(f"Unhandled webhook event: {event_type}")
            return {"status": "ignored"}

    # ==================== Webhook Handlers ====================

    def _handle_checkout_completed(self, event: dict) -> dict:
        """Checkout 完成 → 激活订阅"""
        session = event["data"]["object"]
        user_id = int(session.get("metadata", {}).get("user_id", 0))
        plan_name = session.get("metadata", {}).get("plan_name", "")

        if not user_id:
            return {"status": "error", "message": "Missing user_id in metadata"}

        # 获取 Stripe Subscription 信息
        stripe_sub_id = session.get("subscription")
        stripe_customer_id = session.get("customer")

        if stripe_sub_id and self.stripe:
            stripe_sub = self.stripe.Subscription.retrieve(stripe_sub_id)
            period_start = datetime.fromtimestamp(stripe_sub.current_period_start, tz=timezone.utc)
            period_end = datetime.fromtimestamp(stripe_sub.current_period_end, tz=timezone.utc)
        else:
            period_start = None
            period_end = None

        # 获取 plan
        from subscription_service import SubscriptionService
        sub_svc = SubscriptionService(self.db)
        plan = sub_svc.get_plan_by_name(plan_name)
        if not plan:
            logger.error(f"Plan not found: {plan_name}")
            return {"status": "error", "message": f"Plan {plan_name} not found"}

        sub_svc.activate_subscription(
            user_id=user_id,
            plan_id=plan.id,
            stripe_subscription_id=stripe_sub_id or "",
            stripe_customer_id=stripe_customer_id or "",
            current_period_start=period_start,
            current_period_end=period_end,
        )

        # 发送激活通知
        try:
            from email_service import send_subscription_activated_email
            user = self.db.query(User).filter_by(id=user_id).first()
            if user:
                send_subscription_activated_email(user.email, plan.display_name)
        except Exception as e:
            logger.error(f"Failed to send activation email: {e}")

        return {"status": "ok"}

    def _handle_subscription_updated(self, event: dict) -> dict:
        """订阅更新（升级/降级）"""
        stripe_sub = event["data"]["object"]
        stripe_sub_id = stripe_sub["id"]
        stripe_customer_id = stripe_sub["customer"]

        # 查找本地订阅
        local_sub = self.db.query(Subscription).filter_by(
            stripe_subscription_id=stripe_sub_id
        ).first()

        if not local_sub:
            logger.warning(f"Subscription not found for Stripe sub {stripe_sub_id}")
            return {"status": "ignored"}

        # 更新计费周期
        period_start = datetime.fromtimestamp(stripe_sub["current_period_start"], tz=timezone.utc)
        period_end = datetime.fromtimestamp(stripe_sub["current_period_end"], tz=timezone.utc)
        local_sub.current_period_start = period_start
        local_sub.current_period_end = period_end

        # 更新状态
        status_map = {
            "trialing": "trialing",
            "active": "active",
            "past_due": "past_due",
            "canceled": "cancelled",
            "unpaid": "expired",
        }
        stripe_status = stripe_sub.get("status", "")
        mapped_status = status_map.get(stripe_status)
        if mapped_status and local_sub.status != mapped_status:
            try:
                from subscription_service import SubscriptionService
                sub_svc = SubscriptionService(self.db)
                sub_svc.transition_status(local_sub.id, mapped_status)
            except ValueError:
                local_sub.status = mapped_status

        self.db.commit()
        return {"status": "ok"}

    def _handle_subscription_deleted(self, event: dict) -> dict:
        """订阅删除（取消后到期）"""
        stripe_sub = event["data"]["object"]
        stripe_sub_id = stripe_sub["id"]

        local_sub = self.db.query(Subscription).filter_by(
            stripe_subscription_id=stripe_sub_id
        ).first()

        if local_sub:
            try:
                from subscription_service import SubscriptionService
                sub_svc = SubscriptionService(self.db)
                sub_svc.transition_status(local_sub.id, "expired")
            except ValueError:
                local_sub.status = "expired"
                self.db.commit()

        return {"status": "ok"}

    def _handle_invoice_paid(self, event: dict) -> dict:
        """发票支付成功 → 记录支付历史"""
        invoice = event["data"]["object"]
        stripe_customer_id = invoice.get("customer")
        stripe_invoice_id = invoice.get("id")
        amount_cents = invoice.get("amount_paid", 0)
        currency = invoice.get("currency", "usd")

        # 查找用户
        user = self.db.query(User).filter_by(stripe_customer_id=stripe_customer_id).first()
        if not user:
            return {"status": "ignored", "message": "User not found"}

        # 记录支付历史
        payment = PaymentHistory(
            user_id=user.id,
            stripe_invoice_id=stripe_invoice_id,
            amount_cents=amount_cents,
            currency=currency,
            status="paid",
            description=f"Invoice {stripe_invoice_id}",
            paid_at=datetime.now(timezone.utc),
        )
        self.db.add(payment)
        self.db.commit()

        return {"status": "ok"}

    def _handle_invoice_payment_failed(self, event: dict) -> dict:
        """发票支付失败 → 记录失败支付"""
        invoice = event["data"]["object"]
        stripe_customer_id = invoice.get("customer")
        stripe_invoice_id = invoice.get("id")
        amount_cents = invoice.get("amount_due", 0)
        currency = invoice.get("currency", "usd")

        user = self.db.query(User).filter_by(stripe_customer_id=stripe_customer_id).first()
        if not user:
            return {"status": "ignored"}

        payment = PaymentHistory(
            user_id=user.id,
            stripe_invoice_id=stripe_invoice_id,
            amount_cents=amount_cents,
            currency=currency,
            status="failed",
            description=f"Payment failed: Invoice {stripe_invoice_id}",
        )
        self.db.add(payment)
        self.db.commit()

        # 订阅状态改为 past_due
        sub = self.db.query(Subscription).filter_by(
            user_id=user.id, stripe_customer_id=stripe_customer_id
        ).first()
        if sub and sub.status == "active":
            try:
                from subscription_service import SubscriptionService
                sub_svc = SubscriptionService(self.db)
                sub_svc.transition_status(sub.id, "past_due")
            except ValueError:
                sub.status = "past_due"
                self.db.commit()

        return {"status": "ok"}

    # ==================== Helpers ====================

    def _get_price_id(self, plan_name: str) -> Optional[str]:
        """根据套餐名获取 Stripe Price ID"""
        price_map = {
            "pro": STRIPE_PRO_PRICE_ID,
            "enterprise": STRIPE_ENTERPRISE_PRICE_ID,
        }
        return price_map.get(plan_name)

    def get_payment_history(self, user_id: int, limit: int = 20) -> list:
        """获取用户支付历史"""
        return self.db.query(PaymentHistory).filter_by(user_id=user_id).order_by(
            PaymentHistory.created_at.desc()
        ).limit(limit).all()
