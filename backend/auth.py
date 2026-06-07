"""用户认证模块：JWT 签发/验证、密码哈希、注册/登录 API、get_current_user 依赖

SaaS 扩展：
- PyJWT 替换 python-jose
- 邮箱验证端点
- 密码重置端点
"""
import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES, IS_PRODUCTION

logger = logging.getLogger(__name__)

# ==================== JWT 密钥初始化 ====================

_SECRET_KEY = JWT_SECRET
if not _SECRET_KEY:
    _SECRET_KEY = secrets.token_hex(32)
    if IS_PRODUCTION:
        raise ValueError("生产环境必须设置 OZON_JWT_SECRET 环境变量")
    logger.warning("Auto-generated JWT secret (dev mode). Set OZON_JWT_SECRET env var for production!")

ALGORITHM = JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = JWT_EXPIRE_MINUTES

# API 路由
router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


# ==================== Pydantic 模型 ====================

class RegisterRequest(BaseModel):
    email: str = Field(..., pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    password: str = Field(..., min_length=6, max_length=128)

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserMeResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    email_verified: bool
    role: str
    display_name: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}

class VerifyEmailRequest(BaseModel):
    token: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6, max_length=128)

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=128)

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)


# ==================== 工具函数 ====================

def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, _SECRET_KEY, algorithm=ALGORITHM)

def _generate_token() -> str:
    """生成安全的随机令牌"""
    return secrets.token_urlsafe(32)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[ALGORITHM])
        sub_val = payload.get("sub")
        if sub_val is None:
            raise HTTPException(status_code=401, detail="无效的 Token")
        user_id = int(sub_val)
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="无效的 Token")

    user = db.query(User).filter_by(id=user_id, is_active=True).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """仅管理员可访问的依赖"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


# ==================== API 路由 ====================

@router.post("/register", status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter_by(email=data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        email_verified=False,
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 创建试用订阅
    try:
        from subscription_service import SubscriptionService
        sub_svc = SubscriptionService(db)
        sub_svc.create_trial_subscription(user.id)
    except Exception as e:
        logger.error(f"Failed to create trial subscription for user {user.id}: {e}")

    # 发送验证邮件
    try:
        verify_token = _generate_token()
        user.email_verify_token = verify_token
        user.email_verify_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        db.commit()

        from email_service import send_verification_email
        send_verification_email(user.email, verify_token)
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")

    access_token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "email_verified": user.email_verified,
            "role": user.role,
        },
    )


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户已被禁用")

    access_token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "email_verified": user.email_verified,
            "role": user.role,
        },
    )


@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ==================== 邮箱验证 ====================

@router.post("/verify-email")
def verify_email(data: VerifyEmailRequest, db: Session = Depends(get_db)):
    """验证邮箱"""
    user = db.query(User).filter_by(email_verify_token=data.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="无效的验证令牌")

    if user.email_verify_token_expires and user.email_verify_token_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="验证令牌已过期，请重新发送")

    user.email_verified = True
    user.email_verify_token = None
    user.email_verify_token_expires = None
    db.commit()

    return {"message": "邮箱验证成功"}


@router.post("/resend-verification")
def resend_verification(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """重新发送验证邮件"""
    if current_user.email_verified:
        raise HTTPException(status_code=400, detail="邮箱已验证")

    verify_token = _generate_token()
    current_user.email_verify_token = verify_token
    current_user.email_verify_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    db.commit()

    from email_service import send_verification_email
    success = send_verification_email(current_user.email, verify_token)

    if not success and IS_PRODUCTION:
        raise HTTPException(status_code=500, detail="邮件发送失败，请稍后重试")

    return {"message": "验证邮件已发送"}


# ==================== 密码重置 ====================

@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """请求密码重置"""
    user = db.query(User).filter_by(email=data.email).first()
    if not user:
        # 安全考虑：不暴露邮箱是否存在
        return {"message": "如果该邮箱已注册，重置邮件已发送"}

    reset_token = _generate_token()
    user.password_reset_token = reset_token
    user.password_reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()

    from email_service import send_password_reset_email
    send_password_reset_email(user.email, reset_token)

    return {"message": "如果该邮箱已注册，重置邮件已发送"}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """重置密码"""
    user = db.query(User).filter_by(password_reset_token=data.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="无效的重置令牌")

    if user.password_reset_token_expires and user.password_reset_token_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="重置令牌已过期，请重新申请")

    user.hashed_password = hash_password(data.new_password)
    user.password_reset_token = None
    user.password_reset_token_expires = None
    db.commit()

    return {"message": "密码重置成功"}


# ==================== 密码修改 ====================

@router.post("/change-password")
def change_password(data: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """修改密码（需登录）"""
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="当前密码错误")

    current_user.hashed_password = hash_password(data.new_password)
    db.commit()

    return {"message": "密码修改成功"}
