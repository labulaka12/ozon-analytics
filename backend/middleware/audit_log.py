"""审计日志中间件 — 自动记录关键 API 操作"""
import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# 需要审计的路径前缀
AUDITED_PATHS = [
    "/api/auth/register",
    "/api/auth/login",
    "/api/stores",
    "/api/subscription",
    "/api/account",
]

# 不需要审计的路径（健康检查、静态文件等）
EXCLUDED_PATHS = [
    "/api/auth/me",
    "/api/analytics",
    "/api/products",
    "/api/sync",
    "/api/export",
    "/static",
    "/",
]


class AuditLogMiddleware(BaseHTTPMiddleware):
    """审计日志中间件 — 记录关键 API 请求"""

    async def dispatch(self, request: Request, call_next) -> Response:
        # 判断是否需要审计
        path = request.url.path
        should_audit = any(path.startswith(p) for p in AUDITED_PATHS)

        if not should_audit:
            return await call_next(request)

        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        # 异步记录审计日志（不阻塞响应）
        try:
            self._log_request(request, response.status_code, duration)
        except Exception as e:
            logger.error(f"Audit log middleware error: {e}")

        return response

    def _log_request(self, request: Request, status_code: int, duration: float):
        """记录请求到审计日志"""
        try:
            from database import SessionLocal
            from audit_service import AuditService

            db = SessionLocal()
            try:
                audit = AuditService(db)

                # 从 token 获取 user_id
                user_id = None
                auth_header = request.headers.get("authorization", "")
                if auth_header.startswith("Bearer "):
                    try:
                        from auth import _SECRET_KEY, ALGORITHM
                        import jwt
                        token = auth_header.split(" ")[1]
                        payload = jwt.decode(token, _SECRET_KEY, algorithms=[ALGORITHM])
                        user_id = int(payload.get("sub", 0))
                    except Exception:
                        pass

                # 确定操作类型
                action = f"{request.method.lower()}.{request.url.path.replace('/', '_').strip('_')}"

                audit.log(
                    action=action,
                    user_id=user_id,
                    detail={
                        "method": request.method,
                        "path": str(request.url.path),
                        "status_code": status_code,
                        "duration_ms": round(duration * 1000, 2),
                    },
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent", ""),
                )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Audit log write failed: {e}")
