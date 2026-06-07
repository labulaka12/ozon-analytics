"""统一配置管理 — 集中所有环境变量读取和校验

所有模块从 config.py 获取配置，不再散布 os.environ.get()。
启动时校验必填项，生产环境缺失关键配置将抛出异常。
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _get_env(key: str, default: str = "", required: bool = False) -> str:
    """读取环境变量，required=True 时缺失则抛出 ValueError"""
    val = os.environ.get(key, default)
    if required and not val:
        raise ValueError(f"环境变量 {key} 必须设置（生产环境）")
    return val


def _is_production() -> bool:
    return os.environ.get("RENDER", "") == "true" or os.environ.get("ENV", "") == "production"


# ==================== 通用 ====================

ENVIRONMENT: str = _get_env("ENV", "development")
IS_PRODUCTION: bool = _is_production()
SERVER_PORT: int = int(_get_env("PORT", _get_env("SERVER_PORT", "8848")))

# ==================== 数据库 ====================

DATABASE_URL: str = _get_env("DATABASE_URL", "")

# ==================== 加密 ====================

ENCRYPTION_KEY: str = _get_env("OZON_ENCRYPTION_KEY", "")

# ==================== JWT ====================

JWT_SECRET: str = _get_env("OZON_JWT_SECRET", "")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_MINUTES: int = int(_get_env("OZON_JWT_EXPIRE_MINUTES", "1440"))  # 24h

# ==================== CORS ====================

CORS_ORIGINS_STR: str = _get_env("CORS_ORIGINS", "")

# ==================== 代理 ====================

OZON_PROXY_URL: str = _get_env("OZON_PROXY_URL", "")

# ==================== Redis ====================

REDIS_URL: str = _get_env("REDIS_URL", "")

# ==================== Stripe ====================

STRIPE_SECRET_KEY: str = _get_env("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET: str = _get_env("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRO_PRICE_ID: str = _get_env("STRIPE_PRO_PRICE_ID", "")
STRIPE_ENTERPRISE_PRICE_ID: str = _get_env("STRIPE_ENTERPRISE_PRICE_ID", "")

# ==================== 邮件 SMTP ====================

SMTP_HOST: str = _get_env("SMTP_HOST", "")
SMTP_PORT: int = int(_get_env("SMTP_PORT", "587"))
SMTP_USER: str = _get_env("SMTP_USER", "")
SMTP_PASSWORD: str = _get_env("SMTP_PASSWORD", "")
SMTP_FROM: str = _get_env("SMTP_FROM", "noreply@ozon-analytics.com")
SMTP_USE_TLS: bool = _get_env("SMTP_USE_TLS", "true").lower() == "true"

# ==================== 前端 URL（用于邮件链接） ====================

FRONTEND_URL: str = _get_env("FRONTEND_URL", "http://localhost:8848")

# ==================== 试用天数 ====================

TRIAL_DAYS: int = int(_get_env("TRIAL_DAYS", "14"))

# ==================== 限流 ====================

RATE_LIMIT_PER_MINUTE: int = int(_get_env("RATE_LIMIT_PER_MINUTE", "60"))

# ==================== 启动校验 ====================


def validate_config():
    """生产环境启动时校验关键配置"""
    warnings = []

    if IS_PRODUCTION:
        if not ENCRYPTION_KEY:
            raise ValueError("生产环境必须设置 OZON_ENCRYPTION_KEY")
        if not JWT_SECRET:
            raise ValueError("生产环境必须设置 OZON_JWT_SECRET")
        if not DATABASE_URL:
            raise ValueError("生产环境必须设置 DATABASE_URL")

    if not ENCRYPTION_KEY:
        warnings.append("OZON_ENCRYPTION_KEY 未设置，将自动生成（仅开发模式）")
    if not JWT_SECRET:
        warnings.append("OZON_JWT_SECRET 未设置，将自动生成（仅开发模式）")

    for w in warnings:
        logger.warning(w)
