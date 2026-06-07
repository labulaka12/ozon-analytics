"""初始化管理员账号脚本

用法:
    cd backend
    python seed_admin.py

会在数据库里创建一个初始用户账号（如果不存在的话）。
"""
import os
import sys

# 确保 backend 目录在 Python 路径中
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# 加载 .env 环境变量
from dotenv import load_dotenv
_load_path = os.path.join(os.path.dirname(_backend_dir), ".env")
load_dotenv(_load_path, override=False)

from database import init_db, SessionLocal
from models import User
from auth import hash_password


def create_user(email: str, password: str, is_active: bool = True):
    """创建初始用户，如果邮箱不存在的话"""
    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(email=email).first()
        if existing:
            print(f"用户已存在: {email} (id={existing.id})")
            return existing

        user = User(
            email=email,
            hashed_password=hash_password(password),
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"用户创建成功: {email} (id={user.id})")
        return user
    except Exception as e:
        db.rollback()
        print(f"创建失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # 从命令行参数读取，或使用默认值
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@ozon.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "admin123"

    print(f"初始化数据库...")
    init_db()

    print(f"创建用户: {email}")
    create_user(email, password)

    print("\n完成！你可以使用以下账号登录:")
    print(f"  邮箱: {email}")
    print(f"  密码: {password}")
    print("  -> http://localhost:8848")
