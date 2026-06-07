"""账户设置路由 — 修改密码、邮箱、数据导出/删除"""
import io
import csv
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user, hash_password, verify_password
from models import User, Store, Product, Order, FinanceTransaction, AnalyticsDaily, AlertRule

logger = logging.getLogger(__name__)

router = APIRouter(tags=["account"])


# ==================== Pydantic ====================

class UpdateProfileRequest(BaseModel):
    display_name: str = Field(None, max_length=100)

class UpdateEmailRequest(BaseModel):
    new_email: str = Field(..., pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    password: str

class DeleteAccountRequest(BaseModel):
    password: str
    confirm: str = Field(..., pattern=r"^DELETE$")


# ==================== 个人资料 ====================

@router.put("/api/account/profile")
def update_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新个人资料"""
    if data.display_name is not None:
        current_user.display_name = data.display_name
    db.commit()
    return {"message": "资料更新成功"}


# ==================== 邮箱修改 ====================

@router.put("/api/account/email")
def update_email(
    data: UpdateEmailRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改邮箱"""
    if not verify_password(data.password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="密码错误")

    existing = db.query(User).filter_by(email=data.new_email).first()
    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=400, detail="该邮箱已被使用")

    current_user.email = data.new_email
    current_user.email_verified = False

    # 发送验证邮件
    import secrets
    from email_service import send_verification_email
    verify_token = secrets.token_urlsafe(32)
    current_user.email_verify_token = verify_token
    current_user.email_verify_token_expires = datetime.now(timezone.utc) + __import__("datetime").timedelta(hours=24)
    db.commit()

    send_verification_email(data.new_email, verify_token)

    return {"message": "邮箱已更新，请验证新邮箱"}


# ==================== 数据导出 ====================

@router.get("/api/account/export")
def export_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出用户所有数据为 JSON"""
    user_id = current_user.id

    data = {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        },
        "stores": [],
        "products": [],
        "orders": [],
        "alert_rules": [],
    }

    # 店铺
    stores = db.query(Store).filter_by(user_id=user_id).all()
    for s in stores:
        data["stores"].append({
            "id": s.id,
            "name": s.name,
            "client_id": s.client_id,
            "is_active": s.is_active,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    # 商品
    products = db.query(Product).filter_by(user_id=user_id).all()
    for p in products:
        data["products"].append({
            "id": p.id,
            "store_id": p.store_id,
            "offer_id": p.offer_id,
            "product_id": p.product_id,
            "name": p.name,
            "price": p.price,
        })

    # 订单
    orders = db.query(Order).filter_by(user_id=user_id).limit(1000).all()
    for o in orders:
        data["orders"].append({
            "posting_number": o.posting_number,
            "status": o.status,
            "price": o.price,
            "order_created_at": o.order_created_at.isoformat() if o.order_created_at else None,
        })

    # 告警规则
    alerts = db.query(AlertRule).filter_by(user_id=user_id).all()
    for a in alerts:
        data["alert_rules"].append({
            "id": a.id,
            "name": a.name,
            "rule_type": a.rule_type,
            "enabled": a.enabled,
        })

    json_str = json.dumps(data, ensure_ascii=False, indent=2)

    return Response(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=ozon_data_{user_id}_{datetime.now().strftime('%Y%m%d')}.json"
        },
    )


# ==================== 账户删除 ====================

@router.delete("/api/account")
def delete_account(
    data: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除账户及所有关联数据（不可恢复）"""
    if not verify_password(data.password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="密码错误")

    if data.confirm != "DELETE":
        raise HTTPException(status_code=400, detail="请输入 DELETE 确认删除")

    user_id = current_user.id

    # 删除所有关联数据
    db.query(AnalyticsDaily).filter_by(user_id=user_id).delete()
    db.query(FinanceTransaction).filter_by(user_id=user_id).delete()
    db.query(Order).filter_by(user_id=user_id).delete()
    db.query(Product).filter_by(user_id=user_id).delete()
    db.query(AlertRule).filter_by(user_id=user_id).delete()
    db.query(Store).filter_by(user_id=user_id).delete()

    # 删除用户
    db.delete(current_user)
    db.commit()

    logger.info(f"User {user_id} account deleted")
    return {"message": "账户已删除"}
