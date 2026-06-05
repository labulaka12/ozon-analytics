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
    from models import Store, Product, AnalyticsDaily  # noqa: F401
    Base.metadata.create_all(bind=engine)
