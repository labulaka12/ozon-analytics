"""加密工具 - 使用 Fernet 对称加密保护 API 密钥

安全修复：
1. 解密失败抛出异常而非返回明文
2. per-tenant 密钥派生（基于 user_id 增强隔离）
"""
import os
import base64
import hashlib
import logging
from cryptography.fernet import Fernet, InvalidToken

from config import ENCRYPTION_KEY

logger = logging.getLogger(__name__)

# ==================== 主密钥初始化 ====================

_ENCRYPTION_KEY = ENCRYPTION_KEY

if not _ENCRYPTION_KEY:
    # 开发模式：从文件读取或生成
    _key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", ".encryption_key")
    _key_file = os.path.normpath(_key_file)
    os.makedirs(os.path.dirname(_key_file), exist_ok=True)
    if os.path.exists(_key_file):
        with open(_key_file, "r") as f:
            _ENCRYPTION_KEY = f.read().strip()
    else:
        _ENCRYPTION_KEY = Fernet.generate_key().decode()
        with open(_key_file, "w") as f:
            f.write(_ENCRYPTION_KEY)
        logger.warning("Auto-generated encryption key (dev mode). Set OZON_ENCRYPTION_KEY env var for production!")

_fernet = Fernet(_ENCRYPTION_KEY.encode() if isinstance(_ENCRYPTION_KEY, str) else _ENCRYPTION_KEY)


# ==================== per-tenant 密钥派生 ====================

def _derive_tenant_key(user_id: int) -> bytes:
    """基于主密钥 + user_id 派生租户专属密钥

    使用 SHA256 HKDF 简化方案：master_key || user_id → Fernet key
    """
    raw = (_ENCRYPTION_KEY.encode() if isinstance(_ENCRYPTION_KEY, str) else _ENCRYPTION_KEY) + str(user_id).encode()
    derived = hashlib.sha256(raw).digest()
    # Fernet 需要 URL-safe base64 编码的 32 字节密钥
    return base64.urlsafe_b64encode(derived)


def _get_tenant_fernet(user_id: int) -> Fernet:
    """获取租户专属 Fernet 实例"""
    return Fernet(_derive_tenant_key(user_id))


# ==================== 公共 API ====================

def encrypt_value(plaintext: str, user_id: int = 0) -> str:
    """加密明文，返回 base64 编码的密文

    Args:
        plaintext: 明文字符串
        user_id: 用户 ID，用于 per-tenant 密钥派生。0 表示使用全局密钥（向后兼容）
    """
    if not plaintext:
        return ""
    if user_id > 0:
        return _get_tenant_fernet(user_id).encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


class DecryptionError(Exception):
    """解密失败异常"""
    pass


def decrypt_value(ciphertext: str, user_id: int = 0) -> str:
    """解密密文，返回明文

    安全修复：解密失败时抛出 DecryptionError，而非返回原始密文。
    这避免了将密文当作明文使用（可能导致 API Key 被当作密码发送）。

    Args:
        ciphertext: 密文字符串
        user_id: 用户 ID，用于 per-tenant 密钥派生。0 表示使用全局密钥（向后兼容）

    Raises:
        DecryptionError: 解密失败时
    """
    if not ciphertext:
        return ""
    try:
        if user_id > 0:
            return _get_tenant_fernet(user_id).decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception) as e:
        logger.error(f"Decryption failed for user_id={user_id}: {e}")
        raise DecryptionError(f"解密失败：数据可能已损坏或密钥已变更") from e


def decrypt_value_safe(ciphertext: str, user_id: int = 0) -> str:
    """安全解密 — 兼容旧数据：先尝试 per-tenant 密钥，失败则回退到全局密钥，最终回退返回原文

    仅用于迁移过渡期，新代码应使用 decrypt_value()。
    """
    if not ciphertext:
        return ""
    # 尝试 per-tenant 密钥
    if user_id > 0:
        try:
            return _get_tenant_fernet(user_id).decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except (InvalidToken, Exception):
            pass
    # 尝试全局密钥
    try:
        return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        pass
    # 回退：返回原文（兼容未加密的旧数据）
    logger.warning(f"decrypt_value_safe fallback to raw text for user_id={user_id}")
    return ciphertext
