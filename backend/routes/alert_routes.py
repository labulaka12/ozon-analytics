"""告警通知 API 路由

完整 CRUD：
  - GET    /api/alerts/rules              — 列出规则（支持 store_id 过滤）
  - POST   /api/alerts/rules              — 创建规则
  - PUT    /api/alerts/rules/{rule_id}    — 更新规则
  - DELETE /api/alerts/rules/{rule_id}    — 删除规则
  - POST   /api/alerts/rules/{rule_id}/toggle — 切换启用状态
  - GET    /api/alerts/check              — 手动触发告警检查
  - GET    /api/alerts/send-test          — 发送测试告警
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db
from models import User, Store
from auth import get_current_user
from alerts import AlertManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["alerts"])


# ==================== Pydantic 模型 ====================


class AlertRuleCreate(BaseModel):
    store_id: Optional[int] = Field(None, description="关联店铺ID（为空则全局规则）")
    name: str = Field(..., min_length=1, max_length=100, description="规则名称")
    rule_type: str = Field(..., pattern="^(sales_drop|stock|price_change|sync_fail)$",
                           description="规则类型")
    threshold: float = Field(0.0, ge=0, description="阈值")
    channel: str = Field("email", pattern="^(email|wechat_work|dingtalk|feishu)$",
                         description="通知渠道")
    target: str = Field("", max_length=500, description="接收地址")
    enabled: bool = Field(True, description="是否启用")
    description: Optional[str] = Field(None, max_length=500, description="规则描述")


class AlertRuleUpdate(BaseModel):
    store_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    rule_type: Optional[str] = Field(None, pattern="^(sales_drop|stock|price_change|sync_fail)$")
    threshold: Optional[float] = Field(None, ge=0)
    channel: Optional[str] = Field(None, pattern="^(email|wechat_work|dingtalk|feishu)$")
    target: Optional[str] = Field(None, max_length=500)
    enabled: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=500)


# ==================== API 路由 ====================


@router.get("/api/alerts/rules")
def list_alert_rules(
    store_id: Optional[int] = Query(None, description="按店铺过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的告警规则列表"""
    am = AlertManager(db)
    rules = am._load_rules(current_user.id, store_id=store_id)
    return {"rules": [r.to_dict() for r in rules]}


@router.post("/api/alerts/rules", status_code=201)
def create_alert_rule(
    data: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建告警规则"""
    am = AlertManager(db)
    rule = am.create_rule(current_user.id, data.model_dump())
    return {"message": "告警规则创建成功", "rule": rule.to_dict()}


@router.put("/api/alerts/rules/{rule_id}")
def update_alert_rule(
    rule_id: int,
    data: AlertRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新告警规则"""
    am = AlertManager(db)
    # 过滤掉 None 值（只传需要更新的字段）
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(400, "没有需要更新的字段")

    rule = am.update_rule(rule_id, current_user.id, update_data)
    if not rule:
        raise HTTPException(404, "告警规则不存在")
    return {"message": "告警规则已更新", "rule": rule.to_dict()}


@router.delete("/api/alerts/rules/{rule_id}")
def delete_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除告警规则"""
    am = AlertManager(db)
    if not am.delete_rule(rule_id, current_user.id):
        raise HTTPException(404, "告警规则不存在")
    return {"message": "告警规则已删除"}


@router.post("/api/alerts/rules/{rule_id}/toggle")
def toggle_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """切换告警规则启用/禁用状态"""
    am = AlertManager(db)
    rule = am.toggle_rule(rule_id, current_user.id)
    if not rule:
        raise HTTPException(404, "告警规则不存在")
    action = "已启用" if rule.enabled else "已禁用"
    return {"message": f"告警规则{action}", "rule": rule.to_dict()}


@router.get("/api/alerts/check")
def check_alerts(
    store_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动触发告警检查"""
    am = AlertManager(db)
    triggered = am.check_all_rules(current_user.id)

    # 过滤指定店铺
    if store_id:
        triggered = [a for a in triggered if a.get("store_id") == store_id]

    return {
        "triggered_count": len(triggered),
        "alerts": triggered,
    }


@router.get("/api/alerts/send-test")
def send_test_alert(
    channel: str = Query("email"),
    target: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送测试告警"""
    am = AlertManager(db)
    test_alert = {
        "rule_name": "测试告警",
        "severity": "info",
        "message": "这是一条测试告警，用于验证通知配置是否正常。",
        "triggered_at": __import__("datetime").datetime.now().isoformat(),
    }
    success = am.send_notification(test_alert, channel, target)
    if success:
        return {"message": "测试通知发送成功"}
    else:
        raise HTTPException(500, f"通知发送失败，请检查 {channel} 配置")
