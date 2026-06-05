"""加密工具 - 使用 Fernet 对称加密保护 API 密钥"""
import os
import base64
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# 从环境变量读取加密密钥，若不存在则自动生成（仅开发环境，生产必须设定）
_ENCRYPTION_KEY = os.environ.get("OZON_ENCRYPTION_KEY", "")

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


def encrypt_value(plaintext: str) -> str:
    """加密明文，返回 base64 编码的密文"""
    if not plaintext:
        return ""
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """解密密文，返回明文"""
    if not ciphertext:
        return ""
    try:
        return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        # 如果解密失败，说明是明文数据（兼容旧数据）
        return ciphertext
