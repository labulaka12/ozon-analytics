"""告警通知模块

功能：
  - 销量骤降预警：检测某商品销量较前几天下跌超过阈值
  - 库存预警：商品库存低于阈值时告警
  - 价格异常预警：商品价格异常波动时告警
  - 同步失败通知：Ozon API 同步失败时通知

通知渠道：
  - 邮件（SMTP）
  - 企业微信机器人 Webhook
  - 钉钉机器人 Webhook
  - 飞书机器人 Webhook

使用：
  from alerts import AlertManager
  am = AlertManager(db)
  am.check_all_rules(user_id=1)
"""
import os
import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any

import requests
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Product, Store, AnalyticsDaily, SyncLog, AlertRule as AlertRuleModel

logger = logging.getLogger(__name__)


# ==================== 默认规则模板 ====================

DEFAULT_RULES_TEMPLATES = [
    {
        "name": "销量骤降预警", "rule_type": "sales_drop", "threshold": 50.0,
        "channel": "email", "target": "", "enabled": False,
        "description": "某商品销量较前一日下降超过 50%",
    },
    {
        "name": "同步失败通知", "rule_type": "sync_fail", "threshold": 0,
        "channel": "email", "target": "", "enabled": True,
        "description": "Ozon API 数据同步失败时告警",
    },
    {
        "name": "价格异常预警", "rule_type": "price_change", "threshold": 20.0,
        "channel": "email", "target": "", "enabled": False,
        "description": "商品价格较前日变动超过 20%",
    },
]


# ==================== 封装规则对象（兼容原接口） ====================


class AlertRule:
    """告警规则（封装 DB 模型，保持与原有接口兼容）"""

    def __init__(self, db_row: Optional[AlertRuleModel] = None):
        if db_row:
            self.id = db_row.id
            self.user_id = db_row.user_id
            self.store_id = db_row.store_id
            self.name = db_row.name
            self.rule_type = db_row.rule_type
            self.threshold = db_row.threshold
            self.channel = db_row.channel
            self.target = db_row.target
            self.enabled = db_row.enabled
            self.last_triggered = db_row.last_triggered
            self.description = db_row.description
        else:
            self.id = None
            self.user_id = None
            self.store_id = None
            self.name = ""
            self.rule_type = ""
            self.threshold = 0.0
            self.channel = "email"
            self.target = ""
            self.enabled = True
            self.last_triggered = None
            self.description = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "store_id": self.store_id,
            "name": self.name,
            "rule_type": self.rule_type,
            "threshold": self.threshold,
            "channel": self.channel,
            "target": self.target,
            "enabled": self.enabled,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "description": self.description or "",
        }


# ==================== 告警管理器 ====================


class AlertManager:
    """告警管理器"""

    def __init__(self, db: Session):
        self.db = db
        self._notification_senders = {
            "email": self._send_email,
            "wechat_work": self._send_wechat_work,
            "dingtalk": self._send_dingtalk,
            "feishu": self._send_feishu,
        }

    # ==================== 规则管理（持久化） ====================

    def ensure_default_rules(self, user_id: int):
        """为新用户自动创建默认规则（如果用户还没有任何规则）"""
        existing = self.db.query(AlertRuleModel).filter_by(user_id=user_id).count()
        if existing > 0:
            return
        for tpl in DEFAULT_RULES_TEMPLATES:
            rule = AlertRuleModel(
                user_id=user_id,
                name=tpl["name"],
                rule_type=tpl["rule_type"],
                threshold=tpl["threshold"],
                channel=tpl["channel"],
                target=tpl.get("target", ""),
                enabled=tpl["enabled"],
                description=tpl.get("description", ""),
            )
            self.db.add(rule)
        self.db.commit()
        logger.info(f"Created {len(DEFAULT_RULES_TEMPLATES)} default alert rules for user {user_id}")

    def _load_rules(self, user_id: int, rule_type: Optional[str] = None,
                    store_id: Optional[int] = None) -> List[AlertRule]:
        """从数据库加载告警规则"""
        # 确保用户有默认规则
        self.ensure_default_rules(user_id)

        query = self.db.query(AlertRuleModel).filter_by(user_id=user_id)
        if rule_type:
            query = query.filter_by(rule_type=rule_type)
        if store_id is not None:
            query = query.filter(
                (AlertRuleModel.store_id == store_id) | (AlertRuleModel.store_id.is_(None))
            )

        rows = query.order_by(AlertRuleModel.id).all()
        return [AlertRule(r) for r in rows]

    def get_rule_by_id(self, rule_id: int, user_id: int) -> Optional[AlertRule]:
        """按 ID 获取规则"""
        row = self.db.query(AlertRuleModel).filter_by(id=rule_id, user_id=user_id).first()
        return AlertRule(row) if row else None

    def create_rule(self, user_id: int, data: dict) -> AlertRule:
        """创建告警规则"""
        rule = AlertRuleModel(
            user_id=user_id,
            store_id=data.get("store_id"),
            name=data.get("name", ""),
            rule_type=data.get("rule_type", ""),
            threshold=data.get("threshold", 0.0),
            channel=data.get("channel", "email"),
            target=data.get("target", ""),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return AlertRule(rule)

    def update_rule(self, rule_id: int, user_id: int, data: dict) -> Optional[AlertRule]:
        """更新告警规则（部分更新）"""
        row = self.db.query(AlertRuleModel).filter_by(id=rule_id, user_id=user_id).first()
        if not row:
            return None

        updatable_fields = ["store_id", "name", "rule_type", "threshold",
                            "channel", "target", "enabled", "description"]
        for field in updatable_fields:
            if field in data:
                setattr(row, field, data[field])

        self.db.commit()
        self.db.refresh(row)
        return AlertRule(row)

    def delete_rule(self, rule_id: int, user_id: int) -> bool:
        """删除告警规则"""
        row = self.db.query(AlertRuleModel).filter_by(id=rule_id, user_id=user_id).first()
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def toggle_rule(self, rule_id: int, user_id: int) -> Optional[AlertRule]:
        """切换告警规则启用/禁用状态"""
        row = self.db.query(AlertRuleModel).filter_by(id=rule_id, user_id=user_id).first()
        if not row:
            return None
        row.enabled = not row.enabled
        self.db.commit()
        self.db.refresh(row)
        return AlertRule(row)

    # ==================== 告警检查 ====================

    def check_all_rules(self, user_id: int) -> List[Dict]:
        """检查用户所有告警规则，返回触发的告警列表"""
        triggered = []
        rules = self._load_rules(user_id)

        for rule in rules:
            if not rule.enabled:
                continue

            try:
                alerts = self._check_rule(rule)
                triggered.extend(alerts)
            except Exception as e:
                logger.error(f"Alert rule check failed: {rule.name} - {e}")

        return triggered

    def _check_rule(self, rule: AlertRule) -> List[Dict]:
        """检查单条规则"""
        if rule.rule_type == "sales_drop":
            return self._check_sales_drop(rule)
        elif rule.rule_type == "sync_fail":
            return self._check_sync_fail(rule)
        elif rule.rule_type == "price_change":
            return self._check_price_change(rule)
        return []

    def _check_sales_drop(self, rule: AlertRule) -> List[Dict]:
        """检查销量是否骤降"""
        alerts = []
        today = date.today()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)

        # 获取昨日销量
        yesterday_data = self.db.query(
            AnalyticsDaily.product_id, func.sum(AnalyticsDaily.ordered_units)
        ).filter(
            AnalyticsDaily.date == yesterday,
        ).group_by(AnalyticsDaily.product_id).all()

        # 获取前日销量
        before_data = self.db.query(
            AnalyticsDaily.product_id, func.sum(AnalyticsDaily.ordered_units)
        ).filter(
            AnalyticsDaily.date == day_before,
        ).group_by(AnalyticsDaily.product_id).all()

        before_map = {p[0]: p[1] for p in before_data}

        for pid, today_sales in yesterday_data:
            yesterday_sales = before_map.get(pid, 0)
            if yesterday_sales > 0:
                drop_pct = (yesterday_sales - today_sales) / yesterday_sales * 100
                if drop_pct >= rule.threshold:
                    product = self.db.query(Product).filter_by(product_id=pid).first()
                    alerts.append({
                        "rule_name": rule.name,
                        "rule_type": rule.rule_type,
                        "severity": "warning",
                        "product_id": pid,
                        "product_name": product.name if product else str(pid),
                        "message": f"销量骤降 {drop_pct:.0f}%（前日 {yesterday_sales} → 昨日 {today_sales}）",
                        "threshold": rule.threshold,
                        "current_value": round(drop_pct, 2),
                        "triggered_at": datetime.now().isoformat(),
                    })

        return alerts

    def _check_sync_fail(self, rule: AlertRule) -> List[Dict]:
        """检查同步失败"""
        alerts = []
        recent_fails = self.db.query(SyncLog).filter(
            SyncLog.status == "error",
            SyncLog.created_at >= datetime.now() - timedelta(hours=24),
        ).limit(10).all()

        for log in recent_fails:
            alerts.append({
                "rule_name": rule.name,
                "rule_type": rule.rule_type,
                "severity": "error",
                "store_id": log.store_id,
                "sync_type": log.sync_type,
                "message": f"数据同步失败: {log.sync_type} - {log.message}",
                "triggered_at": log.created_at.isoformat() if log.created_at else datetime.now().isoformat(),
            })

        return alerts

    def _check_price_change(self, rule: AlertRule) -> List[Dict]:
        """检查价格异常"""
        alerts = []

        # 检查最近更新的商品价格
        products = self.db.query(Product).filter(
            Product.updated_at >= datetime.now() - timedelta(days=2),
        ).all()

        for p in products:
            if p.price and p.old_price and p.old_price > 0:
                change_pct = abs(p.price - p.old_price) / p.old_price * 100
                if change_pct >= rule.threshold:
                    alerts.append({
                        "rule_name": rule.name,
                        "rule_type": rule.rule_type,
                        "severity": "info",
                        "product_id": p.product_id,
                        "product_name": p.name or p.offer_id,
                        "message": f"价格变动 {change_pct:.0f}%（{p.old_price} → {p.price} RUB）",
                        "threshold": rule.threshold,
                        "current_value": round(change_pct, 2),
                        "triggered_at": datetime.now().isoformat(),
                    })

        return alerts

    # ==================== 通知发送 ====================

    def send_notification(self, alert: Dict, channel: str, target: str) -> bool:
        """发送告警通知"""
        sender = self._notification_senders.get(channel)
        if not sender:
            logger.warning(f"Unknown notification channel: {channel}")
            return False

        try:
            return sender(target, alert)
        except Exception as e:
            logger.error(f"Failed to send notification via {channel}: {e}")
            return False

    def send_notifications_batch(self, alerts: List[Dict], channel: str, target: str) -> int:
        """批量发送通知"""
        sent = 0
        for alert in alerts:
            if self.send_notification(alert, channel, target):
                sent += 1
        return sent

    def _send_email(self, target: str, alert: Dict) -> bool:
        """发送邮件通知"""
        host = os.environ.get("ALERT_SMTP_HOST")
        if not host:
            logger.warning("SMTP not configured, skip email alert")
            return False

        port = int(os.environ.get("ALERT_SMTP_PORT", 587))
        user = os.environ.get("ALERT_SMTP_USER", "")
        password = os.environ.get("ALERT_SMTP_PASS", "")
        from_email = os.environ.get("ALERT_FROM_EMAIL", "alert@ozon-analytics.com")

        subject = f"[Ozon Analytics] {alert.get('rule_name', '告警')}"
        body = self._format_alert_text(alert)

        try:
            import smtplib
            from email.mime.text import MIMEText

            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = target

            with smtplib.SMTP(host, port) as smtp:
                smtp.starttls()
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)

            logger.info(f"Email alert sent to {target}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _send_wechat_work(self, webhook_url: str, alert: Dict) -> bool:
        """发送企业微信机器人通知"""
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": self._format_alert_markdown(alert),
            },
        }
        return self._post_webhook(webhook_url, payload)

    def _send_dingtalk(self, webhook_url: str, alert: Dict) -> bool:
        """发送钉钉机器人通知"""
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": alert.get("rule_name", "告警"),
                "text": self._format_alert_markdown(alert),
            },
        }
        return self._post_webhook(webhook_url, payload)

    def _send_feishu(self, webhook_url: str, alert: Dict) -> bool:
        """发送飞书机器人通知"""
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": alert.get("rule_name", "告警"),
                        "content": [
                            [{"tag": "text", "text": self._format_alert_text(alert)}],
                        ],
                    }
                }
            },
        }
        return self._post_webhook(webhook_url, payload)

    # ==================== 工具方法 ====================

    def _post_webhook(self, url: str, payload: Dict) -> bool:
        """发送 Webhook 请求"""
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Webhook returned {resp.status_code}: {resp.text[:200]}")
                return False
            return True
        except requests.RequestException as e:
            logger.error(f"Webhook request failed: {e}")
            return False

    def _format_alert_text(self, alert: Dict) -> str:
        """格式化告警为纯文本"""
        return (
            f"【{alert.get('rule_name', '告警')}】\n"
            f"级别: {alert.get('severity', 'info')}\n"
            f"消息: {alert.get('message', '')}\n"
            f"时间: {alert.get('triggered_at', datetime.now().isoformat())}"
        )

    def _format_alert_markdown(self, alert: Dict) -> str:
        """格式化告警为 Markdown"""
        severity_icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}
        icon = severity_icon.get(alert.get("severity", "info"), "⚪")
        return (
            f"{icon} **{alert.get('rule_name', '告警')}**\n"
            f"> {alert.get('message', '')}\n"
            f"> 时间: {alert.get('triggered_at', datetime.now().isoformat())[:19]}"
        )
