"""管理后台路由 — 用户管理、订阅管理、系统监控"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from auth import get_admin_user, get_current_user
from models import User, Subscription, Plan, AuditLog, Store, PaymentHistory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ==================== 用户管理 ====================

@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """获取用户列表"""
    query = db.query(User)

    if search:
        query = query.filter(User.email.ilike(f"%{search}%"))

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "is_active": u.is_active,
                "email_verified": u.email_verified,
                "role": u.role,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.put("/users/{user_id}/status")
def toggle_user_status(
    user_id: int,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """切换用户启用/禁用状态"""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.role == "admin":
        raise HTTPException(status_code=400, detail="不能禁用管理员")

    user.is_active = not user.is_active
    db.commit()

    return {"message": f"用户已{'启用' if user.is_active else '禁用'}", "is_active": user.is_active}


@router.put("/users/{user_id}/role")
def change_user_role(
    user_id: int,
    data: dict,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """修改用户角色"""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    new_role = data.get("role")
    if new_role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="无效角色")

    user.role = new_role
    db.commit()

    return {"message": f"用户角色已更新为 {new_role}"}


# ==================== 订阅管理 ====================

@router.get("/subscriptions")
def list_subscriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """获取订阅列表"""
    query = db.query(Subscription)

    if status:
        query = query.filter_by(status=status)

    total = query.count()
    subs = query.order_by(Subscription.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for s in subs:
        user = db.query(User).filter_by(id=s.user_id).first()
        plan = db.query(Plan).filter_by(id=s.plan_id).first()
        items.append({
            "id": s.id,
            "user_id": s.user_id,
            "user_email": user.email if user else "",
            "plan_name": plan.display_name if plan else "",
            "status": s.status,
            "trial_end": s.trial_end.isoformat() if s.trial_end else None,
            "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ==================== 审计日志 ====================

@router.get("/audit-logs")
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """查询审计日志"""
    from audit_service import AuditService
    audit_svc = AuditService(db)

    logs = audit_svc.query_logs(
        user_id=user_id,
        action=action,
        limit=page_size,
        offset=(page - 1) * page_size,
    )

    return {
        "items": [
            {
                "id": l.id,
                "user_id": l.user_id,
                "action": l.action,
                "target_type": l.target_type,
                "target_id": l.target_id,
                "detail": l.detail,
                "ip_address": l.ip_address,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ],
    }


# ==================== 系统统计 ====================

@router.get("/stats")
def get_system_stats(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """获取系统统计信息"""
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter_by(is_active=True).scalar()
    total_stores = db.query(func.count(Store.id)).scalar()

    # 订阅分布
    sub_dist = db.query(
        Subscription.status, func.count(Subscription.id)
    ).group_by(Subscription.status).all()

    # 套餐分布
    plan_dist = db.query(
        Plan.name, func.count(Subscription.id)
    ).join(Subscription, Plan.id == Subscription.plan_id
    ).group_by(Plan.name).all()

    return {
        "users": {"total": total_users, "active": active_users},
        "stores": {"total": total_stores},
        "subscriptions": {
            "by_status": {s: c for s, c in sub_dist},
            "by_plan": {p: c for p, c in plan_dist},
        },
    }


# ==================== 健康检查 ====================

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """系统健康检查（无需认证）"""
    try:
        # 检查数据库连接
        db.execute(func.count(User.id))
        db_status = "ok"
    except Exception:
        db_status = "error"

    # 检查 Redis
    redis_status = "not_configured"
    try:
        from config import REDIS_URL
        if REDIS_URL:
            import redis as redis_lib
            r = redis_lib.from_url(REDIS_URL)
            r.ping()
            redis_status = "ok"
    except Exception:
        redis_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "redis": redis_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
