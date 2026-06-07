"""pytest 配置

环境变量必须在任何导入前设置。
"""
import os
import sys

# 确保 backend 目录在 Python 路径中
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# 必须在导入任何模块前设置环境变量
os.environ["ENV"] = "test"
os.environ["OZON_JWT_SECRET"] = "test-jwt-secret-42"
os.environ["OZON_ENCRYPTION_KEY"] = "WwFkT7JQuMQZgFm1qWDrRIAiLTX7uVcR-Jw-hpabaKQ="
os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "sqlite:///:memory:")

# 加载 fixtures
pytest_plugins = ["tests.fixtures"]
