"""APScheduler 独立进程入口

由 Render worker 服务启动，与 Web 服务共享同一代码库和数据库。
负责每日定时数据同步任务和告警检查。

启动方式:
    python backend/scheduler_worker.py
"""
import os
import sys
import logging

# 确保 backend 目录在 Python 路径中
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# 加载 .env 环境变量
from dotenv import load_dotenv
_load_path = os.path.join(os.path.dirname(_backend_dir), ".env")
load_dotenv(_load_path, override=False)

from apscheduler.schedulers.background import BackgroundScheduler
from database import init_db
from scheduler import sync_analytics_all_stores, sync_orders_all_stores, sync_finance_all_stores, sync_realization_all_stores

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scheduler_worker")


def check_alerts_all_users():
    """定时检查所有用户的告警规则"""
    from database import SessionLocal
    from alerts import AlertManager

    db = SessionLocal()
    try:
        from models import User
        users = db.query(User).filter_by(is_active=True).all()
        for user in users:
            try:
                am = AlertManager(db)
                triggered = am.check_all_rules(user.id)
                if triggered:
                    logger.info(f"Alert check for user {user.id}: {len(triggered)} alerts triggered")
                    # 发送默认通知（如果配置了）
                    for alert in triggered:
                        logger.warning(f"ALERT: [{alert.get('severity','info')}] {alert.get('message','')}")
            except Exception as e:
                logger.error(f"Alert check failed for user {user.id}: {e}")
    finally:
        db.close()


def main():
    logger.info("Scheduler worker starting...")
    init_db()
    logger.info("Database initialized.")

    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

    # ---- 原有定时任务 ----
    scheduler.add_job(
        sync_analytics_all_stores,
        "cron",
        hour=8,
        minute=0,
        id="daily_analytics_sync",
        replace_existing=True,
    )
    logger.info("Scheduler configured: daily analytics sync at 08:00 Asia/Shanghai")

    scheduler.add_job(
        sync_orders_all_stores,
        "cron",
        hour=8,
        minute=30,
        id="daily_orders_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        sync_finance_all_stores,
        "cron",
        hour=9,
        minute=0,
        id="daily_finance_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        sync_realization_all_stores,
        "cron",
        hour=9,
        minute=30,
        id="daily_realization_sync",
        replace_existing=True,
    )
    logger.info("Scheduler configured: daily orders sync at 08:30, finance at 09:00, realization at 09:30 Asia/Shanghai")

    # ---- 新增：告警检查（每小时） ----
    scheduler.add_job(
        check_alerts_all_users,
        "interval",
        hours=1,
        id="hourly_alert_check",
        replace_existing=True,
    )
    logger.info("Scheduler configured: hourly alert check")

    # ---- 新增：订阅到期检查（每天 06:00） ----
    def check_subscriptions():
        """检查订阅到期状态"""
        try:
            from database import SessionLocal
            from subscription_service import SubscriptionService
            db = SessionLocal()
            try:
                sub_svc = SubscriptionService(db)
                sub_svc.check_expired_trials()
                sub_svc.check_expired_subscriptions()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Subscription check failed: {e}")

    scheduler.add_job(
        check_subscriptions,
        "cron",
        hour=6,
        minute=0,
        id="daily_subscription_check",
        replace_existing=True,
    )
    logger.info("Scheduler configured: daily subscription expiry check at 06:00")

    # ---- 新增：用量统计快照（每天 07:00） ----
    def snapshot_usage():
        """快照月度用量统计"""
        try:
            from usage_service import UsageMeteringService
            UsageMeteringService.snapshot_monthly_usage()
        except Exception as e:
            logger.error(f"Usage snapshot failed: {e}")

    scheduler.add_job(
        snapshot_usage,
        "cron",
        hour=7,
        minute=0,
        id="daily_usage_snapshot",
        replace_existing=True,
    )
    logger.info("Scheduler configured: daily usage snapshot at 07:00")

    scheduler.start()
    logger.info("Scheduler worker started successfully. Running forever...")

    try:
        import time
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler worker shutting down...")
        scheduler.shutdown(wait=False)
        logger.info("Scheduler worker stopped.")


if __name__ == "__main__":
    main()
