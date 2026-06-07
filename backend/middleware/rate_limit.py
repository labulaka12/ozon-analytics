"""Rate Limiting 中间件 — slowapi + Redis"""
import logging
from fastapi import Request, HTTPException

from config import RATE_LIMIT_PER_MINUTE, REDIS_URL

logger = logging.getLogger(__name__)

# slowapi 按需导入
_limiter = None

def get_limiter():
    """获取 rate limiter 实例（懒加载）"""
    global _limiter
    if _limiter is None:
        try:
            from slowapi import Limiter
            from slowapi.util import get_remote_address

            # Redis 存储配置
            storage_uri = REDIS_URL if REDIS_URL else "memory://"

            _limiter = Limiter(
                key_func=get_remote_address,
                storage_uri=storage_uri,
                default_limits=[f"{RATE_LIMIT_PER_MINUTE}/minute"],
                enabled=True,
            )
            logger.info(f"Rate limiter initialized: {RATE_LIMIT_PER_MINUTE}/min, storage={storage_uri}")
        except ImportError:
            logger.warning("slowapi not installed, rate limiting disabled")
            _limiter = None
    return _limiter


def setup_rate_limiting(app):
    """为 FastAPI app 添加 rate limiting"""
    limiter = get_limiter()
    if limiter:
        try:
            from slowapi import _rate_limit_exceeded_handler
            from slowapi.errors import RateLimitExceeded

            app.state.limiter = limiter
            app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
            logger.info("Rate limiting middleware registered")
        except Exception as e:
            logger.error(f"Failed to setup rate limiting: {e}")
    else:
        logger.info("Rate limiting not available (slowapi not installed)")
