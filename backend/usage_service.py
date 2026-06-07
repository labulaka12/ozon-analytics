"""用量计量服务 — 定时统计店铺数/同步次数/API调用量"""
import logging
from datetime import datetime, timezone

from database import SessionLocal
from models import User, Store, AlertRule, Usage

logger = logging.getLogger(__name__)


class UsageMeteringService:
    """用量计量服务"""

    @staticmethod
    def snapshot_monthly_usage():
        """定时任务：快照当月用量（店铺数、告警规则数）

        每天运行一次，更新 Usage 表中当月的统计值。
        """
        db = SessionLocal()
        try:
            period = datetime.now(timezone.utc).strftime("%Y-%m")
            active_users = db.query(User).filter_by(is_active=True).all()

            for user in active_users:
                try:
                    # 店铺数
                    store_count = db.query(Store).filter_by(
                        user_id=user.id, is_active=True
                    ).count()
                    UsageMeteringService._upsert_usage(db, user.id, "stores", store_count, period)

                    # 告警规则数
                    alert_count = db.query(AlertRule).filter_by(
                        user_id=user.id, enabled=True
                    ).count()
                    UsageMeteringService._upsert_usage(db, user.id, "alert_rules", alert_count, period)

                except Exception as e:
                    logger.error(f"Usage snapshot failed for user {user.id}: {e}")

            db.commit()
            logger.info(f"Monthly usage snapshot completed for {len(active_users)} users, period={period}")

        except Exception as e:
            db.rollback()
            logger.error(f"Usage snapshot failed: {e}")
        finally:
            db.close()

    @staticmethod
    def _upsert_usage(db, user_id: int, resource: str, quantity: int, period: str):
        usage = db.query(Usage).filter_by(
            user_id=user_id, resource=resource, period=period
        ).first()

        if usage:
            usage.quantity = quantity
            usage.updated_at = datetime.now(timezone.utc)
        else:
            db.add(Usage(
                user_id=user_id,
                resource=resource,
                quantity=quantity,
                period=period,
            ))
