"""审计日志记录服务"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """审计日志服务"""

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        user_id: Optional[int] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        detail: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """记录审计日志"""
        try:
            entry = AuditLog(
                user_id=user_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                detail=detail,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.db.add(entry)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            self.db.rollback()

    def query_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        """查询审计日志"""
        query = self.db.query(AuditLog)

        if user_id:
            query = query.filter_by(user_id=user_id)
        if action:
            query = query.filter_by(action=action)
        if target_type:
            query = query.filter_by(target_type=target_type)

        return query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    def count_logs(self, user_id: Optional[int] = None, action: Optional[str] = None) -> int:
        """统计审计日志数量"""
        query = self.db.query(AuditLog)
        if user_id:
            query = query.filter_by(user_id=user_id)
        if action:
            query = query.filter_by(action=action)
        return query.count()
