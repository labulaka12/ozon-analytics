"""Quota Check 依赖 — FastAPI Depends 限额检查"""
import logging
from typing import Callable

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from models import User
from quota_service import QuotaService

logger = logging.getLogger(__name__)


def check_quota(resource: str) -> Callable:
    """FastAPI 依赖：检查用户配额

    用法:
        @app.post("/api/stores", dependencies=[Depends(check_quota("stores"))])
        async def create_store(...):
            ...
    """

    async def _check(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        quota_svc = QuotaService(db, redis=_get_redis())
        quota_svc.enforce(current_user.id, resource)

    return _check


def _get_redis():
    """获取 Redis 客户端（如果可用）"""
    try:
        from config import REDIS_URL
        if REDIS_URL:
            import redis
            return redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        pass
    return None
