"""邮件发送服务 — 验证邮件、密码重置、订阅通知

使用 SMTP 发送，支持 HTML 模板。开发环境可配置为仅打印日志不发真实邮件。
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM,
    SMTP_USE_TLS, FRONTEND_URL, IS_PRODUCTION,
)

logger = logging.getLogger(__name__)


def _is_smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def _send_email(to: str, subject: str, html_body: str) -> bool:
    """发送 HTML 邮件，返回是否成功"""
    if not _is_smtp_configured():
        logger.info(f"[DEV] 邮件未发送 (SMTP 未配置): to={to}, subject={subject}")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to], msg.as_string())

        logger.info(f"邮件发送成功: to={to}, subject={subject}")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败: to={to}, error={e}")
        return False


# ==================== 验证邮件 ====================

def send_verification_email(email: str, token: str) -> bool:
    """发送邮箱验证邮件"""
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"
    html = f"""
    <div style="max-width:600px;margin:0 auto;font-family:sans-serif;">
        <h2 style="color:#1a73e8;">Ozon Analytics — 验证您的邮箱</h2>
        <p>请点击下方按钮验证您的邮箱地址：</p>
        <a href="{verify_url}" style="display:inline-block;padding:12px 24px;background:#1a73e8;color:#fff;
           text-decoration:none;border-radius:6px;margin:16px 0;">验证邮箱</a>
        <p style="color:#666;font-size:14px;">如果按钮无法点击，请复制此链接到浏览器：<br>{verify_url}</p>
        <p style="color:#999;font-size:12px;">此链接 24 小时内有效。如非本人操作，请忽略此邮件。</p>
    </div>
    """
    return _send_email(email, "Ozon Analytics — 验证您的邮箱", html)


# ==================== 密码重置 ====================

def send_password_reset_email(email: str, token: str) -> bool:
    """发送密码重置邮件"""
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
    html = f"""
    <div style="max-width:600px;margin:0 auto;font-family:sans-serif;">
        <h2 style="color:#1a73e8;">Ozon Analytics — 重置密码</h2>
        <p>我们收到了重置您密码的请求，请点击下方按钮：</p>
        <a href="{reset_url}" style="display:inline-block;padding:12px 24px;background:#1a73e8;color:#fff;
           text-decoration:none;border-radius:6px;margin:16px 0;">重置密码</a>
        <p style="color:#666;font-size:14px;">如果按钮无法点击，请复制此链接到浏览器：<br>{reset_url}</p>
        <p style="color:#999;font-size:12px;">此链接 1 小时内有效。如非本人操作，请忽略此邮件。</p>
    </div>
    """
    return _send_email(email, "Ozon Analytics — 重置您的密码", html)


# ==================== 订阅通知 ====================

def send_subscription_activated_email(email: str, plan_name: str) -> bool:
    """发送订阅激活通知"""
    html = f"""
    <div style="max-width:600px;margin:0 auto;font-family:sans-serif;">
        <h2 style="color:#1a73e8;">Ozon Analytics — 订阅已激活</h2>
        <p>您的 <strong>{plan_name}</strong> 套餐已激活，现在可以享受所有相关功能。</p>
        <a href="{FRONTEND_URL}/dashboard" style="display:inline-block;padding:12px 24px;background:#1a73e8;
           color:#fff;text-decoration:none;border-radius:6px;margin:16px 0;">进入控制台</a>
    </div>
    """
    return _send_email(email, f"Ozon Analytics — {plan_name} 套餐已激活", html)


def send_subscription_expired_email(email: str) -> bool:
    """发送订阅到期通知"""
    html = f"""
    <div style="max-width:600px;margin:0 auto;font-family:sans-serif;">
        <h2 style="color:#e53935;">Ozon Analytics — 订阅已过期</h2>
        <p>您的订阅已过期，部分功能将受限。请续费以恢复完整功能。</p>
        <a href="{FRONTEND_URL}/pricing" style="display:inline-block;padding:12px 24px;background:#1a73e8;
           color:#fff;text-decoration:none;border-radius:6px;margin:16px 0;">查看套餐</a>
    </div>
    """
    return _send_email(email, "Ozon Analytics — 您的订阅已过期", html)
