"""数据库配置 & 连接管理

支持通过 DATABASE_URL 环境变量切换数据库（生产 -> PostgreSQL，开发 -> SQLite）
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# 生产环境：优先使用 DATABASE_URL 环境变量（Render 自动注入 PostgreSQL URL）
# 开发环境：默认使用 SQLite
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    os.makedirs(DATA_DIR, exist_ok=True)
    DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'ozon_analytics.db')}"

# 判断是否为 PostgreSQL
_is_postgres = DATABASE_URL.startswith("postgresql")

if _is_postgres:
    # PostgreSQL: 需要 SSL 的 Render 连接
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
else:
    # SQLite: 开发模式
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库 — 生产环境使用 Alembic 迁移，开发环境使用 create_all

    检测逻辑：
    1. 如果存在 alembic 目录且 DATABASE_URL 为 PostgreSQL → 运行 Alembic upgrade
    2. 否则 → create_all（开发模式 SQLite / 兼容旧部署）
    """
    from models import Store, Product, AnalyticsDaily, SyncLog, User, Order, FinanceTransaction, RealizationReport, ProductCost, ManualExpense, ExchangeRate, AlertRule, Plan, Subscription, PaymentHistory, Usage, AuditLog  # noqa: F401

    # 先用 create_all 确保所有表存在（幂等操作）
    Base.metadata.create_all(bind=engine)

    # 如果是 PostgreSQL 且有 Alembic 配置，同步 stamp 到最新版本
    if os.environ.get("DATABASE_URL", "").startswith("postgresql"):
        _alembic_cfg = os.path.join(os.path.dirname(__file__), "alembic.ini")
        if os.path.exists(_alembic_cfg):
            try:
                from alembic.config import Config
                from alembic import command
                import logging
                logger = logging.getLogger(__name__)
                alembic_cfg = Config(_alembic_cfg)
                alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "alembic"))
                # stamp 而非 upgrade：表已由 create_all 创建，只需标记版本
                command.stamp(alembic_cfg, "head")
                logger.info("Database tables ensured & Alembic stamped to head.")
                return
            except ImportError:
                pass  # alembic 未安装，忽略
