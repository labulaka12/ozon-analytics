"""限额检查服务 — Redis 缓存 + DB 回源、用量计量"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import User, Store, AlertRule, Subscription, Usage
from subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

# Redis 缓存 TTL（秒）
SUBSCRIPTION_CACHE_TTL = 300  # 5 分钟


class QuotaService:
    """限额检查服务"""

    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis = redis_client
        self.sub_svc = SubscriptionService(db)

    def get_user_limits(self, user_id: int) -> dict:
        """获取用户当前套餐限额（优先从 Redis 缓存读取）"""
        cache_key = f"user_limits:{user_id}"

        if self.redis:
            try:
                cached = self.redis.get(cache_key)
                if cached:
                    import json
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")

        # DB 回源
        limits = self.sub_svc.get_user_plan_limits(user_id)

        # 写入缓存
        if self.redis:
            try:
                import json
                self.redis.setex(cache_key, SUBSCRIPTION_CACHE_TTL, json.dumps(limits))
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")

        return limits

    def get_current_usage(self, user_id: int, resource: str) -> int:
        """获取用户当前资源使用量"""
        if resource == "stores":
            return self.db.query(Store).filter_by(user_id=user_id, is_active=True).count()
        elif resource == "alert_rules":
            return self.db.query(AlertRule).filter_by(user_id=user_id, enabled=True).count()
        elif resource == "products":
            # 使用月度用量统计
            period = datetime.now(timezone.utc).strftime("%Y-%m")
            usage = self.db.query(Usage).filter_by(
                user_id=user_id, resource="products", period=period
            ).first()
            return usage.quantity if usage else 0
        else:
            # 通用：从 Usage 表读取当月统计
            period = datetime.now(timezone.utc).strftime("%Y-%m")
            usage = self.db.query(Usage).filter_by(
                user_id=user_id, resource=resource, period=period
            ).first()
            return usage.quantity if usage else 0

    def check_quota(self, user_id: int, resource: str) -> bool:
        """检查用户是否还有配额

        Returns:
            True: 配额充足  False: 配额已满

        Raises:
            HTTPException: 配额超限时抛出 403
        """
        limits = self.get_user_limits(user_id)
        current = self.get_current_usage(user_id, resource)

        # 限额键名映射
        limit_key_map = {
            "stores": "max_stores",
            "alert_rules": "max_alert_rules",
            "products": "max_products_per_store",
            "team_members": "max_team_members",
            "syncs": "max_syncs_per_day",
        }

        limit_key = limit_key_map.get(resource)
        if not limit_key:
            return True  # 未知资源不限制

        max_val = limits.get(limit_key, 99999)
        if current >= max_val:
            limit_display = max_val
            plan_name = limits.get("name", "Free")
            raise HTTPException(
                status_code=403,
                detail=f"配额已满：{resource} 使用量 {current}/{limit_display}。请升级到更高套餐以获取更多配额。",
                headers={"X-Quota-Resource": resource, "X-Quota-Limit": str(max_val), "X-Quota-Current": str(current)},
            )

        return True

    def enforce(self, user_id: int, resource: str):
        """强制限额检查（配额超限抛异常）"""
        self.check_quota(user_id, resource)

    def increment_usage(self, user_id: int, resource: str, quantity: int = 1):
        """递增用量统计"""
        period = datetime.now(timezone.utc).strftime("%Y-%m")
        usage = self.db.query(Usage).filter_by(
            user_id=user_id, resource=resource, period=period
        ).first()

        if usage:
            usage.quantity += quantity
            usage.updated_at = datetime.now(timezone.utc)
        else:
            usage = Usage(
                user_id=user_id,
                resource=resource,
                quantity=quantity,
                period=period,
            )
            self.db.add(usage)

        self.db.commit()

    def get_all_usage_stats(self, user_id: int) -> dict:
        """获取用户所有资源的用量统计"""
        limits = self.get_user_limits(user_id)

        stats = {
            "stores": {
                "current": self.get_current_usage(user_id, "stores"),
                "limit": limits.get("max_stores", 1),
            },
            "alert_rules": {
                "current": self.get_current_usage(user_id, "alert_rules"),
                "limit": limits.get("max_alert_rules", 3),
            },
            "products": {
                "current": self.get_current_usage(user_id, "products"),
                "limit": limits.get("max_products_per_store", 100),
            },
        }

        # 功能开关
        stats["features"] = {
            "profit_analysis": limits.get("profit_analysis", False),
            "profit_prediction": limits.get("profit_prediction", False),
            "csv_export": limits.get("csv_export", True),
            "api_access": limits.get("api_access", "none"),
            "sync_frequency": limits.get("sync_frequency", "daily"),
            "data_retention_days": limits.get("data_retention_days", 30),
        }

        return stats

    def invalidate_cache(self, user_id: int):
        """清除用户限额缓存（订阅变更后调用）"""
        if self.redis:
            try:
                self.redis.delete(f"user_limits:{user_id}")
            except Exception as e:
                logger.warning(f"Redis cache delete failed: {e}")
